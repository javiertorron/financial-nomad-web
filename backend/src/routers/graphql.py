"""
GraphQL API endpoints.
Provides GraphQL query, mutation, and subscription capabilities for flexible data access.
"""

import json
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional
from src.services.graphql_service import get_graphql_service, EXAMPLE_QUERIES

logger = structlog.get_logger()
router = APIRouter()


class GraphQLRequest(BaseModel):
    """GraphQL request model."""
    query: str
    variables: Optional[Dict[str, Any]] = None
    operation_name: Optional[str] = None


class GraphQLResponse(BaseModel):
    """GraphQL response model."""
    data: Optional[Dict[str, Any]] = None
    errors: Optional[list] = None


@router.get(
    "/playground",
    response_class=HTMLResponse,
    summary="GraphQL Playground",
    description="Interactive GraphQL playground for testing queries",
    tags=["GraphQL"]
)
async def graphql_playground():
    """
    **GraphQL Playground**
    
    Interactive GraphQL development environment:
    - Query builder and syntax highlighting
    - Schema introspection and documentation
    - Real-time query execution
    - Examples and tutorials
    
    Perfect for exploring the GraphQL API and building queries.
    """
    playground_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset=utf-8/>
        <meta name="viewport" content="user-scalable=no, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, minimal-ui">
        <title>Financial Nomad GraphQL Playground</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
        <link rel="shortcut icon" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/favicon.png" />
        <script src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js"></script>
        <style>
            body {{ margin: 0; background: #1f2937; }}
            .playground {{ height: 100vh; }}
        </style>
    </head>
    <body>
        <div id="root">
            <style>
                body {{ background-color: rgb(23, 42, 58); font-family: Open Sans, sans-serif; height: 90vh; }}
                #root {{ height: 100vh; width: 100vw; display: flex; align-items: center; justify-content: center; }}
                .loading {{ font-size: 32px; font-weight: 200; color: rgba(255, 255, 255, .6); margin-left: 20px; }}
                img {{ width: 78px; height: 78px; }}
                .title {{ font-weight: 400; }}
            </style>
            <div class="loading"> 
                <img src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/logo.png" alt=""> 
                <div class="title">Loading
                    <span class="loading-title">GraphQL Playground</span>
                </div>
            </div>
        </div>
        <script>
            window.addEventListener('load', function (event) {{
                GraphQLPlayground.init(document.getElementById('root'), {{
                    endpoint: '{settings.api_prefix}/graphql',
                    settings: {{
                        'editor.theme': 'dark',
                        'editor.fontSize': 14,
                        'request.credentials': 'include'
                    }},
                    tabs: [
                        {{
                            endpoint: '{settings.api_prefix}/graphql',
                            query: `# Welcome to Financial Nomad GraphQL API!
# 
# Here are some example queries to get you started:

# 1. Get your financial summary
query GetFinancialSummary {{
  financialSummary(dateRange: {{
    startDate: "2024-01-01T00:00:00Z"
    endDate: "2024-12-31T23:59:59Z"
  }}) {{
    totalIncome
    totalExpenses
    netAmount
    savingsRate
    periodStart
    periodEnd
  }}
}}

# 2. Get your accounts
query GetAccounts {{
  accounts {{
    items {{
      id
      name
      type
      balance
      currency
    }}
    totalCount
  }}
}}

# 3. Get recent transactions
query GetTransactions {{
  transactions(pagination: {{ limit: 10 }}) {{
    items {{
      id
      amount
      description
      date
      type
      account {{
        name
      }}
      category {{
        name
      }}
    }}
    totalCount
    hasNextPage
  }}
}}`,
                            variables: JSON.stringify({{}}),
                            headers: {{
                                "Authorization": "Bearer YOUR_TOKEN_HERE"
                            }}
                        }}
                    ]
                }})
            }})
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=playground_html)


@router.get(
    "/schema",
    summary="Get GraphQL Schema",
    description="Returns the GraphQL schema definition (SDL)",
    tags=["GraphQL"]
)
async def get_graphql_schema():
    """
    **Get GraphQL Schema**
    
    Returns the complete GraphQL schema definition:
    - All available types and fields
    - Input and output type definitions
    - Available queries, mutations, and subscriptions
    - Field documentation and descriptions
    
    Useful for code generation and API documentation.
    """
    try:
        service = get_graphql_service()
        schema_sdl = service.get_schema_sdl()
        
        return {
            "schema": schema_sdl,
            "introspection_url": f"{settings.api_prefix}/graphql",
            "playground_url": f"{settings.api_prefix}/graphql/playground"
        }
        
    except Exception as e:
        logger.error("Failed to get GraphQL schema", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve GraphQL schema"
        )


@router.get(
    "/examples",
    summary="Get Example Queries",
    description="Returns example GraphQL queries and mutations",
    tags=["GraphQL"]
)
async def get_example_queries():
    """
    **Get example queries**
    
    Returns a collection of example GraphQL queries:
    - Common query patterns
    - Mutation examples
    - Subscription usage
    - Complex filtering examples
    
    Perfect for learning the GraphQL API and getting started quickly.
    """
    return {
        "examples": EXAMPLE_QUERIES,
        "playground_url": f"{settings.api_prefix}/graphql/playground",
        "documentation": {
            "queries": "Use queries to fetch data without side effects",
            "mutations": "Use mutations to create, update, or delete data",
            "subscriptions": "Use subscriptions for real-time updates",
            "filtering": "Use input types like TransactionFilterInput for advanced filtering",
            "pagination": "Use PaginationInput for efficient data loading"
        }
    }


@router.post(
    "",
    summary="Execute GraphQL Query",
    description="Execute GraphQL queries, mutations, and subscriptions",
    response_model=GraphQLResponse,
    tags=["GraphQL"]
)
async def execute_graphql(
    request: GraphQLRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> GraphQLResponse:
    """
    **Execute GraphQL query**
    
    Execute GraphQL operations with full feature support:
    - **Queries**: Fetch data with complex filtering and pagination
    - **Mutations**: Create, update, and delete financial records
    - **Subscriptions**: Real-time updates for transactions and budgets
    - **Introspection**: Schema exploration and documentation
    
    ### Authentication
    Most operations require authentication. Include Bearer token in Authorization header.
    
    ### Error Handling
    GraphQL errors are returned in the `errors` field with detailed messages.
    
    ### Performance
    Use field selection to minimize data transfer and improve performance.
    """
    try:
        service = get_graphql_service()
        
        # Prepare context with user information
        context = {}
        if current_user:
            context["user_id"] = current_user.get("id")
            context["user"] = current_user
        
        # Execute GraphQL operation
        result = await service.execute_query(
            query=request.query,
            variables=request.variables,
            context=context
        )
        
        # Log the operation
        operation_type = "unknown"
        if request.query.strip().startswith("query"):
            operation_type = "query"
        elif request.query.strip().startswith("mutation"):
            operation_type = "mutation"
        elif request.query.strip().startswith("subscription"):
            operation_type = "subscription"
        
        logger.info("GraphQL operation executed",
                   user_id=current_user.get("id") if current_user else None,
                   operation_type=operation_type,
                   operation_name=request.operation_name,
                   has_errors=bool(result.get("errors")))
        
        return GraphQLResponse(
            data=result.get("data"),
            errors=result.get("errors")
        )
        
    except Exception as e:
        logger.error("GraphQL execution failed", error=str(e))
        return GraphQLResponse(
            data=None,
            errors=[{"message": "Internal server error", "type": "INTERNAL_ERROR"}]
        )


@router.post(
    "/validate",
    summary="Validate GraphQL Query",
    description="Validates GraphQL query syntax without execution",
    tags=["GraphQL"]
)
async def validate_graphql_query(request: GraphQLRequest):
    """
    **Validate GraphQL query**
    
    Validates query syntax and structure without execution:
    - Syntax validation
    - Schema compliance checking
    - Field existence verification
    - Type compatibility validation
    
    Useful for query builders and development tools.
    """
    try:
        service = get_graphql_service()
        
        # Validate query
        errors = await service.validate_query(request.query)
        
        if errors:
            return {
                "valid": False,
                "errors": errors
            }
        else:
            return {
                "valid": True,
                "message": "Query is valid"
            }
            
    except Exception as e:
        logger.error("GraphQL validation failed", error=str(e))
        return {
            "valid": False,
            "errors": [str(e)]
        }


@router.get(
    "/introspection",
    summary="GraphQL Introspection",
    description="Get GraphQL schema introspection data",
    tags=["GraphQL"]
)
async def get_introspection():
    """
    **GraphQL Introspection**
    
    Returns complete schema introspection data:
    - Type definitions and relationships
    - Field arguments and return types
    - Enum values and descriptions
    - Directive information
    
    Used by GraphQL tools and clients for automatic schema discovery.
    """
    introspection_query = """
        query IntrospectionQuery {
            __schema {
                queryType { name }
                mutationType { name }
                subscriptionType { name }
                types {
                    ...FullType
                }
                directives {
                    name
                    description
                    locations
                    args {
                        ...InputValue
                    }
                }
            }
        }

        fragment FullType on __Type {
            kind
            name
            description
            fields(includeDeprecated: true) {
                name
                description
                args {
                    ...InputValue
                }
                type {
                    ...TypeRef
                }
                isDeprecated
                deprecationReason
            }
            inputFields {
                ...InputValue
            }
            interfaces {
                ...TypeRef
            }
            enumValues(includeDeprecated: true) {
                name
                description
                isDeprecated
                deprecationReason
            }
            possibleTypes {
                ...TypeRef
            }
        }

        fragment InputValue on __InputValue {
            name
            description
            type { ...TypeRef }
            defaultValue
        }

        fragment TypeRef on __Type {
            kind
            name
            ofType {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                    ofType {
                                        kind
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    """
    
    try:
        service = get_graphql_service()
        result = await service.execute_query(introspection_query)
        
        return result
        
    except Exception as e:
        logger.error("GraphQL introspection failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schema introspection"
        )


@router.get(
    "/docs",
    response_class=HTMLResponse,
    summary="GraphQL Documentation",
    description="Interactive GraphQL API documentation",
    tags=["GraphQL"]
)
async def graphql_docs():
    """
    **GraphQL Documentation**
    
    Interactive API documentation with:
    - Schema browser and type explorer
    - Query examples and tutorials
    - Field documentation and descriptions
    - Real-time query testing
    
    Complete guide to using the Financial Nomad GraphQL API.
    """
    docs_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Financial Nomad GraphQL API Documentation</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background: #f8fafc;
                color: #334155;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 2rem;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5rem;
                font-weight: 700;
            }}
            .header p {{
                margin: 1rem 0 0;
                font-size: 1.2rem;
                opacity: 0.9;
            }}
            .content {{
                padding: 2rem;
            }}
            .section {{
                margin-bottom: 3rem;
            }}
            .section h2 {{
                color: #1e293b;
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 0.5rem;
                margin-bottom: 1.5rem;
            }}
            .feature-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 2rem;
                margin-top: 2rem;
            }}
            .feature-card {{
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 1.5rem;
            }}
            .feature-card h3 {{
                color: #4c51bf;
                margin-top: 0;
            }}
            .code-block {{
                background: #1e293b;
                color: #e2e8f0;
                padding: 1.5rem;
                border-radius: 6px;
                overflow-x: auto;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 0.9rem;
                line-height: 1.5;
            }}
            .btn {{
                display: inline-block;
                padding: 12px 24px;
                background: #4c51bf;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 500;
                margin: 10px 10px 10px 0;
            }}
            .btn:hover {{
                background: #4338ca;
            }}
            .btn-secondary {{
                background: #64748b;
            }}
            .btn-secondary:hover {{
                background: #475569;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Financial Nomad GraphQL API</h1>
                <p>Flexible, powerful, and real-time financial data access</p>
            </div>
            
            <div class="content">
                <div class="section">
                    <h2>🎯 Quick Start</h2>
                    <p>Get started with the Financial Nomad GraphQL API in seconds:</p>
                    <a href="{settings.api_prefix}/graphql/playground" class="btn">🎮 Open Playground</a>
                    <a href="{settings.api_prefix}/graphql/examples" class="btn btn-secondary">📖 View Examples</a>
                    <a href="{settings.api_prefix}/graphql/schema" class="btn btn-secondary">📋 Schema Definition</a>
                </div>

                <div class="section">
                    <h2>✨ Key Features</h2>
                    <div class="feature-grid">
                        <div class="feature-card">
                            <h3>🔍 Advanced Querying</h3>
                            <p>Fetch exactly the data you need with powerful filtering, pagination, and sorting capabilities.</p>
                        </div>
                        <div class="feature-card">
                            <h3>⚡ Real-time Updates</h3>
                            <p>Subscribe to live data changes with GraphQL subscriptions for transactions and budget alerts.</p>
                        </div>
                        <div class="feature-card">
                            <h3>🎯 Type Safety</h3>
                            <p>Strongly typed schema with automatic validation and comprehensive error handling.</p>
                        </div>
                        <div class="feature-card">
                            <h3>📊 Financial Analytics</h3>
                            <p>Access comprehensive financial summaries, trends, and category breakdowns.</p>
                        </div>
                    </div>
                </div>

                <div class="section">
                    <h2>🔧 Example Query</h2>
                    <p>Here's a simple query to get your financial summary:</p>
                    <div class="code-block">query GetFinancialSummary {{
  financialSummary(dateRange: {{
    startDate: "2024-01-01T00:00:00Z"
    endDate: "2024-12-31T23:59:59Z"
  }}) {{
    totalIncome
    totalExpenses
    netAmount
    savingsRate
    accountBalances
  }}
}}</div>
                </div>

                <div class="section">
                    <h2>🔐 Authentication</h2>
                    <p>Most GraphQL operations require authentication. Include your Bearer token in the Authorization header:</p>
                    <div class="code-block">{{
  "Authorization": "Bearer YOUR_ACCESS_TOKEN"
}}</div>
                </div>

                <div class="section">
                    <h2>🎬 Available Operations</h2>
                    <div class="feature-grid">
                        <div class="feature-card">
                            <h3>📖 Queries</h3>
                            <ul>
                                <li>accounts - Get user accounts</li>
                                <li>transactions - Fetch transactions with filters</li>
                                <li>categories - Get spending categories</li>
                                <li>budgets - View budget information</li>
                                <li>financialSummary - Get financial overview</li>
                                <li>spendingByCategory - Category breakdown</li>
                                <li>monthlyTrends - Financial trends over time</li>
                            </ul>
                        </div>
                        <div class="feature-card">
                            <h3>✏️ Mutations</h3>
                            <ul>
                                <li>createTransaction - Add new transaction</li>
                                <li>updateTransaction - Modify existing transaction</li>
                                <li>deleteTransaction - Remove transaction</li>
                                <li>createBudget - Set up new budget</li>
                            </ul>
                        </div>
                        <div class="feature-card">
                            <h3>🔔 Subscriptions</h3>
                            <ul>
                                <li>transactionUpdates - Real-time transaction changes</li>
                                <li>budgetAlerts - Budget warning notifications</li>
                            </ul>
                        </div>
                    </div>
                </div>

                <div class="section">
                    <h2>🛠️ Tools & Resources</h2>
                    <a href="{settings.api_prefix}/graphql/playground" class="btn">GraphQL Playground</a>
                    <a href="{settings.api_prefix}/graphql/introspection" class="btn btn-secondary">Schema Introspection</a>
                    <a href="{settings.api_prefix}/docs" class="btn btn-secondary">REST API Docs</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=docs_html)