"""
Firestore query optimization service for Financial Nomad.
"""
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass

import structlog
from ..infrastructure import get_firestore
from ..services.caching import get_cache_service, CacheKeyBuilder
from ..middleware.monitoring import metrics_collector

logger = structlog.get_logger()


@dataclass
class QueryPlan:
    """Query execution plan with optimization hints."""
    collection: str
    where_clauses: List[Tuple[str, str, Any]]
    order_by: Optional[str]
    limit: Optional[int]
    use_cache: bool
    cache_ttl: int
    estimated_cost: int  # Relative cost estimate
    optimization_notes: List[str]


class FirestoreQueryOptimizer:
    """Service for optimizing Firestore queries and implementing caching strategies."""
    
    def __init__(self):
        self.firestore = get_firestore()
        self.cache_service = get_cache_service()
        
        # Query pattern statistics for optimization
        self.query_stats = {}
        
        # Index recommendations
        self.recommended_indexes = set()
    
    async def execute_optimized_query(
        self,
        collection: str,
        model_class,
        where_clauses: List[Tuple[str, str, Any]] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        use_cache: bool = True,
        cache_ttl: int = 300
    ) -> List[Any]:
        """Execute query with optimization and caching."""
        
        where_clauses = where_clauses or []
        
        # Create query plan
        query_plan = self._create_query_plan(
            collection, where_clauses, order_by, limit, use_cache, cache_ttl
        )
        
        # Log query for analysis
        await self._log_query_execution(query_plan)
        
        # Try cache first if enabled
        if query_plan.use_cache:
            cached_result = await self._get_cached_result(query_plan)
            if cached_result is not None:
                metrics_collector.record_database_operation("query", collection, "cache_hit")
                return cached_result
        
        # Execute optimized query
        start_time = datetime.utcnow()
        try:
            result = await self._execute_firestore_query(
                query_plan.collection,
                model_class,
                query_plan.where_clauses,
                query_plan.order_by,
                query_plan.limit
            )
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            metrics_collector.record_database_operation("query", collection, "success")
            
            # Cache result if appropriate
            if query_plan.use_cache and result:
                await self._cache_query_result(query_plan, result)
            
            # Update query statistics
            await self._update_query_stats(query_plan, duration, len(result))
            
            return result
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            metrics_collector.record_database_operation("query", collection, "error")
            
            logger.error(
                "Query execution failed",
                collection=collection,
                where_clauses=where_clauses,
                order_by=order_by,
                limit=limit,
                duration_seconds=duration,
                error=str(e)
            )
            raise
    
    async def execute_batch_query(
        self,
        queries: List[Dict[str, Any]],
        use_cache: bool = True
    ) -> List[List[Any]]:
        """Execute multiple queries in batch with optimization."""
        
        results = []
        
        # Group queries by collection for better batching
        queries_by_collection = {}
        for i, query in enumerate(queries):
            collection = query['collection']
            if collection not in queries_by_collection:
                queries_by_collection[collection] = []
            queries_by_collection[collection].append((i, query))
        
        # Execute queries by collection
        result_map = {}
        for collection, collection_queries in queries_by_collection.items():
            for original_index, query in collection_queries:
                result = await self.execute_optimized_query(
                    collection=query['collection'],
                    model_class=query.get('model_class'),
                    where_clauses=query.get('where_clauses'),
                    order_by=query.get('order_by'),
                    limit=query.get('limit'),
                    use_cache=use_cache
                )
                result_map[original_index] = result
        
        # Return results in original order
        return [result_map[i] for i in range(len(queries))]
    
    async def get_aggregated_data(
        self,
        user_id: str,
        collection: str,
        aggregation_type: str,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        group_by: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Get aggregated data with caching optimization."""
        
        # Create cache key for aggregation
        cache_params = {
            'user_id': user_id,
            'collection': collection,
            'aggregation_type': aggregation_type,
            'date_range': date_range,
            'group_by': group_by
        }
        
        if use_cache:
            cached_result = await self.cache_service.get_cached_computation(
                "aggregation", cache_params
            )
            if cached_result is not None:
                return cached_result
        
        # Execute aggregation query
        start_time = datetime.utcnow()
        
        try:
            if aggregation_type == "monthly_summary":
                result = await self._get_monthly_summary(user_id, collection, date_range)
            elif aggregation_type == "category_totals":
                result = await self._get_category_totals(user_id, collection, date_range)
            elif aggregation_type == "account_balances":
                result = await self._get_account_balances(user_id)
            else:
                raise ValueError(f"Unsupported aggregation type: {aggregation_type}")
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Cache the result
            if use_cache:
                cache_ttl = 600 if aggregation_type == "account_balances" else 1800  # 10 min or 30 min
                await self.cache_service.cache_computation_result(
                    "aggregation", cache_params, result, cache_ttl
                )
            
            logger.info(
                "Aggregation query completed",
                user_id=user_id,
                aggregation_type=aggregation_type,
                duration_seconds=duration
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "Aggregation query failed",
                user_id=user_id,
                aggregation_type=aggregation_type,
                error=str(e)
            )
            raise
    
    def _create_query_plan(
        self,
        collection: str,
        where_clauses: List[Tuple[str, str, Any]],
        order_by: Optional[str],
        limit: Optional[int],
        use_cache: bool,
        cache_ttl: int
    ) -> QueryPlan:
        """Create optimized query plan."""
        
        optimization_notes = []
        estimated_cost = 1
        
        # Analyze where clauses for optimization
        if where_clauses:
            # Check for inefficient patterns
            equality_filters = [clause for clause in where_clauses if clause[1] == "=="]
            range_filters = [clause for clause in where_clauses if clause[1] in ["<", "<=", ">", ">="]]
            
            if len(range_filters) > 1:
                optimization_notes.append("Multiple range filters may require composite index")
                estimated_cost += 2
            
            if order_by and range_filters:
                range_field = range_filters[0][0] if range_filters else None
                if range_field and order_by != range_field:
                    optimization_notes.append("Order by field differs from range filter - may need index")
                    estimated_cost += 1
        
        # Analyze limit for cost estimation
        if limit:
            if limit > 100:
                optimization_notes.append("Large limit - consider pagination")
                estimated_cost += 1
        else:
            optimization_notes.append("No limit specified - may return large result set")
            estimated_cost += 2
        
        # Cache optimization
        if not use_cache and estimated_cost > 2:
            optimization_notes.append("High-cost query without caching - consider enabling cache")
        
        return QueryPlan(
            collection=collection,
            where_clauses=where_clauses,
            order_by=order_by,
            limit=limit,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
            estimated_cost=estimated_cost,
            optimization_notes=optimization_notes
        )
    
    async def _execute_firestore_query(
        self,
        collection: str,
        model_class,
        where_clauses: List[Tuple[str, str, Any]],
        order_by: Optional[str],
        limit: Optional[int]
    ) -> List[Any]:
        """Execute the actual Firestore query."""
        
        return await self.firestore.query_documents(
            collection=collection,
            model_class=model_class,
            where_clauses=where_clauses,
            order_by=order_by,
            limit=limit
        )
    
    async def _get_cached_result(self, query_plan: QueryPlan) -> Optional[List[Any]]:
        """Get cached query result."""
        filters = {
            'where_clauses': query_plan.where_clauses,
            'order_by': query_plan.order_by,
            'limit': query_plan.limit
        }
        
        return await self.cache_service.get_cached_query(
            query_plan.collection, filters
        )
    
    async def _cache_query_result(self, query_plan: QueryPlan, result: List[Any]):
        """Cache query result."""
        filters = {
            'where_clauses': query_plan.where_clauses,
            'order_by': query_plan.order_by,
            'limit': query_plan.limit
        }
        
        await self.cache_service.cache_query_result(
            query_plan.collection, filters, 
            [item.dict() if hasattr(item, 'dict') else item for item in result],
            query_plan.cache_ttl
        )
    
    async def _log_query_execution(self, query_plan: QueryPlan):
        """Log query execution for analysis."""
        logger.debug(
            "Executing optimized query",
            collection=query_plan.collection,
            where_clauses=query_plan.where_clauses,
            order_by=query_plan.order_by,
            limit=query_plan.limit,
            estimated_cost=query_plan.estimated_cost,
            optimization_notes=query_plan.optimization_notes
        )
    
    async def _update_query_stats(self, query_plan: QueryPlan, duration: float, result_count: int):
        """Update query statistics for optimization analysis."""
        query_key = f"{query_plan.collection}:{len(query_plan.where_clauses)}:{query_plan.order_by}"
        
        if query_key not in self.query_stats:
            self.query_stats[query_key] = {
                'executions': 0,
                'total_duration': 0,
                'avg_duration': 0,
                'avg_result_count': 0,
                'total_results': 0
            }
        
        stats = self.query_stats[query_key]
        stats['executions'] += 1
        stats['total_duration'] += duration
        stats['total_results'] += result_count
        stats['avg_duration'] = stats['total_duration'] / stats['executions']
        stats['avg_result_count'] = stats['total_results'] / stats['executions']
    
    # Specific aggregation methods
    async def _get_monthly_summary(
        self, 
        user_id: str, 
        collection: str, 
        date_range: Optional[Tuple[datetime, datetime]]
    ) -> Dict[str, Any]:
        """Get monthly summary data."""
        
        # Default to last 12 months if no range provided
        if not date_range:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=365)
        else:
            start_date, end_date = date_range
        
        # Query transactions in date range
        transactions = await self.execute_optimized_query(
            collection=f"transactions/{user_id}/user_transactions",
            model_class=None,
            where_clauses=[
                ("transaction_date", ">=", start_date.date().isoformat()),
                ("transaction_date", "<=", end_date.date().isoformat())
            ],
            order_by="transaction_date",
            use_cache=True,
            cache_ttl=1800  # 30 minutes
        )
        
        # Process into monthly summaries
        monthly_data = {}
        for transaction in transactions:
            if isinstance(transaction, dict):
                date_str = transaction.get('transaction_date', '')
                amount = transaction.get('amount', 0)
                transaction_type = transaction.get('transaction_type', 'expense')
            else:
                date_str = getattr(transaction, 'transaction_date', '')
                amount = getattr(transaction, 'amount', 0)
                transaction_type = getattr(transaction, 'transaction_type', 'expense')
            
            if date_str:
                month_key = date_str[:7]  # YYYY-MM
                
                if month_key not in monthly_data:
                    monthly_data[month_key] = {
                        'income': 0,
                        'expenses': 0,
                        'net': 0,
                        'transactions_count': 0
                    }
                
                monthly_data[month_key]['transactions_count'] += 1
                
                if transaction_type == 'income':
                    monthly_data[month_key]['income'] += amount
                else:
                    monthly_data[month_key]['expenses'] += amount
                
                monthly_data[month_key]['net'] = (
                    monthly_data[month_key]['income'] - monthly_data[month_key]['expenses']
                )
        
        return {
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'monthly_data': monthly_data,
            'total_months': len(monthly_data)
        }
    
    async def _get_category_totals(
        self, 
        user_id: str, 
        collection: str, 
        date_range: Optional[Tuple[datetime, datetime]]
    ) -> Dict[str, Any]:
        """Get category totals."""
        
        # Query transactions
        where_clauses = []
        if date_range:
            start_date, end_date = date_range
            where_clauses.extend([
                ("transaction_date", ">=", start_date.date().isoformat()),
                ("transaction_date", "<=", end_date.date().isoformat())
            ])
        
        transactions = await self.execute_optimized_query(
            collection=f"transactions/{user_id}/user_transactions",
            model_class=None,
            where_clauses=where_clauses,
            use_cache=True,
            cache_ttl=900  # 15 minutes
        )
        
        # Process by category
        category_totals = {}
        for transaction in transactions:
            if isinstance(transaction, dict):
                category_id = transaction.get('category_id', 'unknown')
                amount = transaction.get('amount', 0)
                transaction_type = transaction.get('transaction_type', 'expense')
            else:
                category_id = getattr(transaction, 'category_id', 'unknown')
                amount = getattr(transaction, 'amount', 0)
                transaction_type = getattr(transaction, 'transaction_type', 'expense')
            
            if category_id not in category_totals:
                category_totals[category_id] = {
                    'income': 0,
                    'expenses': 0,
                    'net': 0,
                    'transactions_count': 0
                }
            
            category_totals[category_id]['transactions_count'] += 1
            
            if transaction_type == 'income':
                category_totals[category_id]['income'] += amount
            else:
                category_totals[category_id]['expenses'] += amount
            
            category_totals[category_id]['net'] = (
                category_totals[category_id]['income'] - category_totals[category_id]['expenses']
            )
        
        return {
            'date_range': {
                'start': date_range[0].isoformat() if date_range else None,
                'end': date_range[1].isoformat() if date_range else None
            },
            'category_totals': category_totals,
            'categories_count': len(category_totals)
        }
    
    async def _get_account_balances(self, user_id: str) -> Dict[str, Any]:
        """Get current account balances."""
        
        # Get all accounts
        accounts = await self.execute_optimized_query(
            collection=f"accounts/{user_id}/bank_accounts",
            model_class=None,
            use_cache=True,
            cache_ttl=300  # 5 minutes
        )
        
        balances = {}
        total_balance = 0
        
        for account in accounts:
            if isinstance(account, dict):
                account_id = account.get('id')
                balance = account.get('balance', 0)
                account_name = account.get('account_name', 'Unknown')
            else:
                account_id = getattr(account, 'id')
                balance = getattr(account, 'balance', 0)
                account_name = getattr(account, 'account_name', 'Unknown')
            
            balances[account_id] = {
                'name': account_name,
                'balance': balance
            }
            total_balance += balance
        
        return {
            'accounts': balances,
            'total_balance': total_balance,
            'accounts_count': len(balances),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def get_query_performance_report(self) -> Dict[str, Any]:
        """Get query performance analysis report."""
        
        # Analyze query statistics
        slow_queries = []
        frequent_queries = []
        
        for query_key, stats in self.query_stats.items():
            if stats['avg_duration'] > 1.0:  # Slow queries (>1 second)
                slow_queries.append({
                    'query': query_key,
                    'avg_duration': stats['avg_duration'],
                    'executions': stats['executions']
                })
            
            if stats['executions'] > 10:  # Frequent queries
                frequent_queries.append({
                    'query': query_key,
                    'executions': stats['executions'],
                    'avg_duration': stats['avg_duration']
                })
        
        return {
            'total_queries': len(self.query_stats),
            'slow_queries': sorted(slow_queries, key=lambda x: x['avg_duration'], reverse=True),
            'frequent_queries': sorted(frequent_queries, key=lambda x: x['executions'], reverse=True),
            'recommended_indexes': list(self.recommended_indexes),
            'cache_stats': await self.cache_service.get_all_cache_stats()
        }


# Global query optimizer instance
_query_optimizer: Optional[FirestoreQueryOptimizer] = None


def get_query_optimizer() -> FirestoreQueryOptimizer:
    """Get the global query optimizer instance."""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = FirestoreQueryOptimizer()
    return _query_optimizer