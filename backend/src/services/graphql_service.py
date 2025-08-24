"""
GraphQL Service for Flexible API Queries.
Provides GraphQL schema, resolvers, and advanced querying capabilities
for financial data with real-time subscriptions and complex filtering.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import structlog
import strawberry
from strawberry.types import Info
from strawberry.scalars import JSON
from enum import Enum

from src.config import settings

logger = structlog.get_logger()


# GraphQL Scalars and Enums
@strawberry.scalar
class DateTime:
    """DateTime scalar for GraphQL."""
    
    @staticmethod
    def serialize(value: datetime) -> str:
        return value.isoformat() + "Z"
    
    @staticmethod
    def parse_value(value: str) -> datetime:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))


@strawberry.enum
class TransactionType(Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


@strawberry.enum
class AccountType(Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"
    CASH = "cash"


@strawberry.enum
class BudgetStatus(Enum):
    ON_TRACK = "on_track"
    WARNING = "warning"
    OVER_BUDGET = "over_budget"


@strawberry.enum
class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"


# Input Types
@strawberry.input
class DateRangeInput:
    """Date range filter input."""
    start_date: Optional[DateTime] = None
    end_date: Optional[DateTime] = None


@strawberry.input
class TransactionFilterInput:
    """Transaction filtering input."""
    account_ids: Optional[List[str]] = None
    category_ids: Optional[List[str]] = None
    transaction_type: Optional[TransactionType] = None
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    date_range: Optional[DateRangeInput] = None
    description_contains: Optional[str] = None


@strawberry.input
class PaginationInput:
    """Pagination input."""
    limit: Optional[int] = 20
    offset: Optional[int] = 0


@strawberry.input
class SortInput:
    """Sorting input."""
    field: str
    order: SortOrder = SortOrder.DESC


@strawberry.input
class TransactionCreateInput:
    """Transaction creation input."""
    account_id: str
    category_id: str
    amount: float
    description: str
    date: DateTime
    type: TransactionType


@strawberry.input
class BudgetCreateInput:
    """Budget creation input."""
    name: str
    category_id: str
    amount: float
    start_date: DateTime
    end_date: DateTime


# Output Types
@strawberry.type
class User:
    """User type."""
    id: str
    email: str
    name: str
    created_at: DateTime
    updated_at: DateTime


@strawberry.type
class Account:
    """Account type."""
    id: str
    user_id: str
    name: str
    type: AccountType
    balance: float
    currency: str = "USD"
    is_active: bool = True
    created_at: DateTime
    updated_at: DateTime
    
    @strawberry.field
    async def transactions(self, info: Info, 
                          filters: Optional[TransactionFilterInput] = None,
                          pagination: Optional[PaginationInput] = None) -> List["Transaction"]:
        """Get transactions for this account."""
        # In real implementation, fetch from database
        return []
    
    @strawberry.field
    async def balance_history(self, info: Info,
                            date_range: Optional[DateRangeInput] = None) -> List["BalancePoint"]:
        """Get balance history for this account."""
        # In real implementation, calculate balance history
        return []


@strawberry.type
class Category:
    """Category type."""
    id: str
    user_id: str
    name: str
    parent_id: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: bool = True
    created_at: DateTime
    updated_at: DateTime
    
    @strawberry.field
    async def children(self, info: Info) -> List["Category"]:
        """Get child categories."""
        # In real implementation, fetch subcategories
        return []
    
    @strawberry.field
    async def parent(self, info: Info) -> Optional["Category"]:
        """Get parent category."""
        # In real implementation, fetch parent
        return None
    
    @strawberry.field
    async def transactions(self, info: Info,
                          filters: Optional[TransactionFilterInput] = None,
                          pagination: Optional[PaginationInput] = None) -> List["Transaction"]:
        """Get transactions in this category."""
        # In real implementation, fetch from database
        return []
    
    @strawberry.field
    async def spending_total(self, info: Info,
                           date_range: Optional[DateRangeInput] = None) -> float:
        """Get total spending in this category."""
        # In real implementation, calculate from transactions
        return 0.0


@strawberry.type
class Transaction:
    """Transaction type."""
    id: str
    user_id: str
    account_id: str
    category_id: str
    amount: float
    description: str
    date: DateTime
    type: TransactionType
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    created_at: DateTime
    updated_at: DateTime
    
    @strawberry.field
    async def account(self, info: Info) -> Optional[Account]:
        """Get transaction account."""
        # In real implementation, fetch account
        return None
    
    @strawberry.field
    async def category(self, info: Info) -> Optional[Category]:
        """Get transaction category."""
        # In real implementation, fetch category
        return None


@strawberry.type
class Budget:
    """Budget type."""
    id: str
    user_id: str
    category_id: str
    name: str
    amount: float
    spent: float
    remaining: float
    percentage_used: float
    status: BudgetStatus
    start_date: DateTime
    end_date: DateTime
    created_at: DateTime
    updated_at: DateTime
    
    @strawberry.field
    async def category(self, info: Info) -> Optional[Category]:
        """Get budget category."""
        # In real implementation, fetch category
        return None
    
    @strawberry.field
    async def transactions(self, info: Info) -> List[Transaction]:
        """Get transactions affecting this budget."""
        # In real implementation, fetch transactions
        return []


@strawberry.type
class BalancePoint:
    """Balance history point."""
    date: DateTime
    balance: float
    change: float


@strawberry.type
class FinancialSummary:
    """Financial summary statistics."""
    total_income: float
    total_expenses: float
    net_amount: float
    account_balances: float
    budget_utilization: float
    savings_rate: float
    period_start: DateTime
    period_end: DateTime


@strawberry.type
class SpendingByCategory:
    """Spending breakdown by category."""
    category_id: str
    category_name: str
    amount: float
    percentage: float
    transaction_count: int


@strawberry.type
class MonthlyTrend:
    """Monthly financial trend."""
    month: str
    income: float
    expenses: float
    net: float
    savings_rate: float


@strawberry.type
class PaginatedTransactions:
    """Paginated transaction results."""
    items: List[Transaction]
    total_count: int
    has_next_page: bool
    has_previous_page: bool


@strawberry.type
class PaginatedAccounts:
    """Paginated account results."""
    items: List[Account]
    total_count: int
    has_next_page: bool
    has_previous_page: bool


# Subscription Types
@strawberry.type
class TransactionSubscription:
    """Transaction subscription payload."""
    action: str  # created, updated, deleted
    transaction: Transaction


@strawberry.type
class BudgetAlert:
    """Budget alert subscription payload."""
    budget_id: str
    budget_name: str
    alert_type: str  # warning, exceeded
    percentage_used: float
    amount_over: Optional[float] = None


# Query Resolvers
class QueryResolver:
    """GraphQL query resolver."""
    
    def __init__(self):
        pass
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        # In real implementation, fetch from database
        return User(
            id=user_id,
            email="user@example.com",
            name="John Doe",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    async def get_accounts(self, user_id: str, 
                          pagination: Optional[PaginationInput] = None) -> PaginatedAccounts:
        """Get user accounts."""
        # In real implementation, fetch from database with pagination
        accounts = []  # Mock data
        
        return PaginatedAccounts(
            items=accounts,
            total_count=len(accounts),
            has_next_page=False,
            has_previous_page=False
        )
    
    async def get_transactions(self, user_id: str,
                             filters: Optional[TransactionFilterInput] = None,
                             pagination: Optional[PaginationInput] = None,
                             sort: Optional[SortInput] = None) -> PaginatedTransactions:
        """Get user transactions with filtering and pagination."""
        # In real implementation, build complex query with filters
        transactions = []  # Mock data
        
        return PaginatedTransactions(
            items=transactions,
            total_count=len(transactions),
            has_next_page=False,
            has_previous_page=False
        )
    
    async def get_categories(self, user_id: str,
                           parent_id: Optional[str] = None) -> List[Category]:
        """Get categories, optionally filtered by parent."""
        # In real implementation, fetch from database
        return []
    
    async def get_budgets(self, user_id: str,
                         active_only: bool = True) -> List[Budget]:
        """Get user budgets."""
        # In real implementation, fetch from database
        return []
    
    async def get_financial_summary(self, user_id: str,
                                  date_range: DateRangeInput) -> FinancialSummary:
        """Get financial summary for date range."""
        # In real implementation, calculate from transactions
        return FinancialSummary(
            total_income=5000.0,
            total_expenses=3500.0,
            net_amount=1500.0,
            account_balances=15000.0,
            budget_utilization=75.5,
            savings_rate=20.0,
            period_start=date_range.start_date or datetime.now(),
            period_end=date_range.end_date or datetime.now()
        )
    
    async def get_spending_by_category(self, user_id: str,
                                     date_range: Optional[DateRangeInput] = None) -> List[SpendingByCategory]:
        """Get spending breakdown by category."""
        # In real implementation, aggregate from transactions
        return []
    
    async def get_monthly_trends(self, user_id: str,
                               months: int = 12) -> List[MonthlyTrend]:
        """Get monthly financial trends."""
        # In real implementation, calculate monthly aggregations
        return []
    
    async def search_transactions(self, user_id: str,
                                query: str,
                                pagination: Optional[PaginationInput] = None) -> PaginatedTransactions:
        """Search transactions by description or notes."""
        # In real implementation, perform full-text search
        return PaginatedTransactions(
            items=[],
            total_count=0,
            has_next_page=False,
            has_previous_page=False
        )


# Mutation Resolvers  
class MutationResolver:
    """GraphQL mutation resolver."""
    
    def __init__(self):
        pass
    
    async def create_transaction(self, user_id: str,
                               input: TransactionCreateInput) -> Transaction:
        """Create new transaction."""
        # In real implementation, validate and save to database
        transaction = Transaction(
            id=f"txn_{datetime.now().timestamp()}",
            user_id=user_id,
            account_id=input.account_id,
            category_id=input.category_id,
            amount=input.amount,
            description=input.description,
            date=input.date,
            type=input.type,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        logger.info("Transaction created via GraphQL",
                   user_id=user_id,
                   transaction_id=transaction.id)
        
        return transaction
    
    async def update_transaction(self, user_id: str, transaction_id: str,
                               input: TransactionCreateInput) -> Optional[Transaction]:
        """Update existing transaction."""
        # In real implementation, validate ownership and update
        return None
    
    async def delete_transaction(self, user_id: str,
                               transaction_id: str) -> bool:
        """Delete transaction."""
        # In real implementation, validate ownership and delete
        logger.info("Transaction deleted via GraphQL",
                   user_id=user_id,
                   transaction_id=transaction_id)
        return True
    
    async def create_budget(self, user_id: str,
                          input: BudgetCreateInput) -> Budget:
        """Create new budget."""
        # In real implementation, validate and save
        budget = Budget(
            id=f"bdg_{datetime.now().timestamp()}",
            user_id=user_id,
            category_id=input.category_id,
            name=input.name,
            amount=input.amount,
            spent=0.0,
            remaining=input.amount,
            percentage_used=0.0,
            status=BudgetStatus.ON_TRACK,
            start_date=input.start_date,
            end_date=input.end_date,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        logger.info("Budget created via GraphQL",
                   user_id=user_id,
                   budget_id=budget.id)
        
        return budget


# Subscription Resolvers
class SubscriptionResolver:
    """GraphQL subscription resolver."""
    
    def __init__(self):
        self.subscribers = {}
    
    async def transaction_updates(self, user_id: str):
        """Subscribe to real-time transaction updates."""
        # In real implementation, use WebSocket or similar for real-time updates
        while True:
            # Mock real-time update
            yield TransactionSubscription(
                action="created",
                transaction=Transaction(
                    id=f"txn_live_{datetime.now().timestamp()}",
                    user_id=user_id,
                    account_id="acc_123",
                    category_id="cat_456",
                    amount=-25.50,
                    description="Real-time transaction",
                    date=datetime.now(),
                    type=TransactionType.EXPENSE,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
            )
            await asyncio.sleep(30)  # Send update every 30 seconds
    
    async def budget_alerts(self, user_id: str):
        """Subscribe to budget alerts."""
        while True:
            # Mock budget alert
            yield BudgetAlert(
                budget_id="bdg_123",
                budget_name="Monthly Dining",
                alert_type="warning",
                percentage_used=85.0
            )
            await asyncio.sleep(60)  # Check every minute


# GraphQL Schema Definition
query_resolver = QueryResolver()
mutation_resolver = MutationResolver()
subscription_resolver = SubscriptionResolver()


@strawberry.type
class Query:
    """GraphQL Query root."""
    
    @strawberry.field
    async def me(self, info: Info) -> Optional[User]:
        """Get current user information."""
        # Extract user from context
        user_id = info.context.get("user_id")
        if not user_id:
            return None
        return await query_resolver.get_user(user_id)
    
    @strawberry.field
    async def accounts(self, info: Info,
                      pagination: Optional[PaginationInput] = None) -> PaginatedAccounts:
        """Get user accounts."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await query_resolver.get_accounts(user_id, pagination)
    
    @strawberry.field
    async def transactions(self, info: Info,
                          filters: Optional[TransactionFilterInput] = None,
                          pagination: Optional[PaginationInput] = None,
                          sort: Optional[SortInput] = None) -> PaginatedTransactions:
        """Get user transactions with advanced filtering."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await query_resolver.get_transactions(user_id, filters, pagination, sort)
    
    @strawberry.field
    async def categories(self, info: Info,
                        parent_id: Optional[str] = None) -> List[Category]:
        """Get categories."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await query_resolver.get_categories(user_id, parent_id)
    
    @strawberry.field
    async def budgets(self, info: Info,
                     active_only: bool = True) -> List[Budget]:
        """Get user budgets."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await query_resolver.get_budgets(user_id, active_only)
    
    @strawberry.field
    async def financial_summary(self, info: Info,
                               date_range: DateRangeInput) -> FinancialSummary:
        """Get financial summary for date range."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await query_resolver.get_financial_summary(user_id, date_range)
    
    @strawberry.field
    async def spending_by_category(self, info: Info,
                                  date_range: Optional[DateRangeInput] = None) -> List[SpendingByCategory]:
        """Get spending breakdown by category."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await query_resolver.get_spending_by_category(user_id, date_range)
    
    @strawberry.field
    async def monthly_trends(self, info: Info,
                           months: int = 12) -> List[MonthlyTrend]:
        """Get monthly financial trends."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await query_resolver.get_monthly_trends(user_id, months)
    
    @strawberry.field
    async def search_transactions(self, info: Info,
                                query: str,
                                pagination: Optional[PaginationInput] = None) -> PaginatedTransactions:
        """Search transactions."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await query_resolver.search_transactions(user_id, query, pagination)


@strawberry.type
class Mutation:
    """GraphQL Mutation root."""
    
    @strawberry.field
    async def create_transaction(self, info: Info,
                               input: TransactionCreateInput) -> Transaction:
        """Create new transaction."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await mutation_resolver.create_transaction(user_id, input)
    
    @strawberry.field
    async def update_transaction(self, info: Info,
                               transaction_id: str,
                               input: TransactionCreateInput) -> Optional[Transaction]:
        """Update existing transaction."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await mutation_resolver.update_transaction(user_id, transaction_id, input)
    
    @strawberry.field
    async def delete_transaction(self, info: Info,
                               transaction_id: str) -> bool:
        """Delete transaction."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await mutation_resolver.delete_transaction(user_id, transaction_id)
    
    @strawberry.field
    async def create_budget(self, info: Info,
                          input: BudgetCreateInput) -> Budget:
        """Create new budget."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        return await mutation_resolver.create_budget(user_id, input)


@strawberry.type
class Subscription:
    """GraphQL Subscription root."""
    
    @strawberry.field
    async def transaction_updates(self, info: Info) -> TransactionSubscription:
        """Subscribe to real-time transaction updates."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        
        async for update in subscription_resolver.transaction_updates(user_id):
            yield update
    
    @strawberry.field
    async def budget_alerts(self, info: Info) -> BudgetAlert:
        """Subscribe to budget alerts."""
        user_id = info.context.get("user_id")
        if not user_id:
            raise Exception("Authentication required")
        
        async for alert in subscription_resolver.budget_alerts(user_id):
            yield alert


# Create GraphQL schema
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription
)


class GraphQLService:
    """GraphQL service manager."""
    
    def __init__(self):
        self.schema = schema
        logger.info("GraphQL service initialized")
    
    def get_schema(self):
        """Get GraphQL schema."""
        return self.schema
    
    async def execute_query(self, query: str, variables: Dict[str, Any] = None,
                          context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute GraphQL query."""
        try:
            result = await self.schema.execute(
                query,
                variable_values=variables or {},
                context_value=context or {}
            )
            
            return {
                "data": result.data,
                "errors": [{"message": str(error)} for error in result.errors] if result.errors else None
            }
            
        except Exception as e:
            logger.error("GraphQL query execution failed", error=str(e))
            return {
                "data": None,
                "errors": [{"message": str(e)}]
            }
    
    def get_schema_sdl(self) -> str:
        """Get schema definition language (SDL)."""
        return strawberry.export_schema.get_schema_as_string(self.schema)
    
    async def validate_query(self, query: str) -> List[str]:
        """Validate GraphQL query syntax."""
        try:
            # In real implementation, use GraphQL validation
            return []
        except Exception as e:
            return [str(e)]


# Global GraphQL service
_graphql_service = None


def get_graphql_service() -> GraphQLService:
    """Get global GraphQL service."""
    global _graphql_service
    if _graphql_service is None:
        _graphql_service = GraphQLService()
    return _graphql_service


# Example queries for documentation
EXAMPLE_QUERIES = {
    "get_financial_summary": """
        query GetFinancialSummary($dateRange: DateRangeInput!) {
            financialSummary(dateRange: $dateRange) {
                totalIncome
                totalExpenses
                netAmount
                accountBalances
                budgetUtilization
                savingsRate
                periodStart
                periodEnd
            }
        }
    """,
    
    "get_transactions_with_filters": """
        query GetTransactions($filters: TransactionFilterInput, $pagination: PaginationInput) {
            transactions(filters: $filters, pagination: $pagination) {
                items {
                    id
                    amount
                    description
                    date
                    type
                    account {
                        name
                        type
                    }
                    category {
                        name
                        color
                    }
                }
                totalCount
                hasNextPage
            }
        }
    """,
    
    "create_transaction": """
        mutation CreateTransaction($input: TransactionCreateInput!) {
            createTransaction(input: $input) {
                id
                amount
                description
                date
                type
                account {
                    name
                }
                category {
                    name
                }
            }
        }
    """,
    
    "transaction_updates_subscription": """
        subscription TransactionUpdates {
            transactionUpdates {
                action
                transaction {
                    id
                    amount
                    description
                    date
                    type
                }
            }
        }
    """
}