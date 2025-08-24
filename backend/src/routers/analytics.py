"""
Predictive Analytics endpoints.
Handles financial forecasting, trend analysis, and AI-powered insights.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, status, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field, validator
import structlog

from src.config import settings
from src.utils.dependencies import get_current_user_optional
from src.services.predictive_analysis_service import (
    get_predictive_analysis_service,
    PredictionConfig,
    PredictionType,
    TimeHorizon,
    FinancialGoal,
    generate_income_forecast,
    generate_expense_forecast,
    predict_goal_achievement
)

logger = structlog.get_logger()
router = APIRouter()


class ForecastRequest(BaseModel):
    """Forecast request model."""
    forecast_type: str = Field(..., description="Type of forecast (income, expenses, cashflow)")
    horizon_days: int = Field(default=30, ge=1, le=365, description="Forecast horizon in days")
    include_confidence_intervals: bool = Field(default=True, description="Include confidence intervals")
    categories: Optional[List[str]] = Field(None, description="Filter by specific categories")
    
    @validator('forecast_type')
    def validate_forecast_type(cls, v):
        valid_types = ['income', 'expenses', 'cashflow']
        if v not in valid_types:
            raise ValueError(f'Invalid forecast type. Must be one of: {valid_types}')
        return v


class GoalAnalysisRequest(BaseModel):
    """Goal analysis request model."""
    goal_name: str = Field(..., description="Goal name")
    target_amount: float = Field(..., ge=0, description="Target amount")
    current_amount: float = Field(default=0, ge=0, description="Current saved amount")
    target_date: str = Field(..., description="Target achievement date (ISO format)")
    category: Optional[str] = Field(None, description="Goal category")
    monthly_contribution: Optional[float] = Field(None, ge=0, description="Planned monthly contribution")


class InsightResponse(BaseModel):
    """Financial insight response."""
    type: str = Field(..., description="Insight type")
    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Detailed description")
    confidence: str = Field(..., description="Confidence level")
    actionable: bool = Field(..., description="Whether insight is actionable")
    priority: str = Field(..., description="Priority level")


class ForecastResponse(BaseModel):
    """Forecast response model."""
    forecast_type: str = Field(..., description="Type of forecast")
    horizon_days: int = Field(..., description="Forecast horizon")
    total_predicted: float = Field(..., description="Total predicted amount")
    confidence_level: str = Field(..., description="Overall confidence level")
    predictions: List[Dict[str, Any]] = Field(..., description="Daily predictions")
    accuracy_metrics: Dict[str, float] = Field(..., description="Model accuracy metrics")


class SpendingAnomalyResponse(BaseModel):
    """Spending anomaly response."""
    date: str = Field(..., description="Transaction date")
    amount: float = Field(..., description="Transaction amount")
    description: str = Field(..., description="Transaction description")
    category: str = Field(..., description="Transaction category")
    anomaly_score: int = Field(..., description="Anomaly score (0-100)")
    deviation_from_normal: float = Field(..., description="Standard deviations from normal")


class GoalPredictionResponse(BaseModel):
    """Goal prediction response."""
    goal_id: str = Field(..., description="Goal identifier")
    status: str = Field(..., description="Achievement status")
    probability: float = Field(..., description="Achievement probability")
    predicted_achievement_date: str = Field(..., description="Predicted achievement date")
    required_monthly_savings: float = Field(..., description="Required monthly savings")
    current_monthly_capacity: float = Field(..., description="Current monthly savings capacity")
    recommendation: str = Field(..., description="Recommendation for goal achievement")


@router.post(
    "/forecast",
    status_code=status.HTTP_200_OK,
    summary="Generate Financial Forecast",
    description="Generates AI-powered forecasts for income, expenses, or cashflow",
    response_model=ForecastResponse,
    tags=["Analytics"]
)
async def generate_forecast(
    request: ForecastRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> ForecastResponse:
    """
    **Generate financial forecast**
    
    Uses machine learning models to predict future financial trends:
    - Income forecasting based on historical patterns
    - Expense prediction with seasonal adjustments
    - Cashflow projections with confidence intervals
    - Trend analysis and pattern recognition
    
    Requires at least 30 days of transaction history for accurate predictions.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_predictive_analysis_service()
        
        # In real implementation, fetch user's transaction data from database
        # For now, using mock data
        transactions = []
        
        if request.forecast_type == "income":
            forecast = await generate_income_forecast(
                current_user.get('id'),
                transactions,
                request.horizon_days
            )
        elif request.forecast_type == "expenses":
            forecast = await generate_expense_forecast(
                current_user.get('id'),
                transactions,
                request.horizon_days
            )
        elif request.forecast_type == "cashflow":
            # Generate both income and expense forecasts, then combine
            income_forecast = await generate_income_forecast(
                current_user.get('id'),
                transactions,
                request.horizon_days
            )
            expense_forecast = await generate_expense_forecast(
                current_user.get('id'),
                transactions,
                request.horizon_days
            )
            
            # Combine forecasts for cashflow
            cashflow_predictions = []
            income_preds = income_forecast.get('predictions', [])
            expense_preds = expense_forecast.get('predictions', [])
            
            total_cashflow = 0
            for inc_pred, exp_pred in zip(income_preds, expense_preds):
                cashflow = inc_pred.get('predicted_value', 0) - exp_pred.get('predicted_value', 0)
                total_cashflow += cashflow
                
                cashflow_predictions.append({
                    "date": inc_pred.get('date'),
                    "predicted_value": cashflow,
                    "income_component": inc_pred.get('predicted_value', 0),
                    "expense_component": exp_pred.get('predicted_value', 0),
                    "confidence": "medium"
                })
            
            forecast = {
                "type": "cashflow_forecast",
                "horizon_days": request.horizon_days,
                "predictions": cashflow_predictions,
                "total_predicted": total_cashflow,
                "confidence_level": "medium",
                "accuracy_metrics": {}
            }
        
        logger.info("Financial forecast generated",
                   user_id=current_user.get('id'),
                   forecast_type=request.forecast_type,
                   horizon=request.horizon_days)
        
        return ForecastResponse(
            forecast_type=forecast.get('type', request.forecast_type),
            horizon_days=request.horizon_days,
            total_predicted=forecast.get('total_predicted', 0),
            confidence_level=forecast.get('confidence_level', 'medium'),
            predictions=forecast.get('predictions', []),
            accuracy_metrics=forecast.get('accuracy_metrics', {})
        )
        
    except Exception as e:
        logger.error("Failed to generate forecast",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate financial forecast"
        )


@router.get(
    "/insights",
    status_code=status.HTTP_200_OK,
    summary="Get AI Financial Insights",
    description="Returns AI-generated insights about spending patterns and financial health",
    response_model=List[InsightResponse],
    tags=["Analytics"]
)
async def get_financial_insights(
    categories: Optional[str] = Query(None, description="Comma-separated categories to analyze"),
    days_back: int = Query(default=90, ge=7, le=365, description="Days of history to analyze"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[InsightResponse]:
    """
    **Get AI-powered financial insights**
    
    Analyzes spending patterns and provides personalized insights:
    - Spending behavior analysis
    - Budget performance insights
    - Savings optimization recommendations
    - Category-specific trends
    - Anomaly detection results
    
    Uses machine learning to identify patterns and provide actionable advice.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_predictive_analysis_service()
        
        # In real implementation, fetch user's transaction data
        transactions = []
        
        # Parse categories filter
        category_filter = None
        if categories:
            category_filter = [cat.strip() for cat in categories.split(",")]
        
        # Generate comprehensive analysis
        analysis = await service.generate_comprehensive_analysis(
            user_id=current_user.get('id'),
            transactions=transactions,
            horizon_days=days_back
        )
        
        # Convert insights to response format
        insights = []
        
        for insight in analysis.insights:
            insights.append(InsightResponse(
                type="spending_pattern",
                title="Spending Pattern Insight",
                description=insight,
                confidence=analysis.confidence_level.value,
                actionable=True,
                priority="medium"
            ))
        
        for recommendation in analysis.recommendations:
            insights.append(InsightResponse(
                type="recommendation",
                title="Financial Recommendation",
                description=recommendation,
                confidence=analysis.confidence_level.value,
                actionable=True,
                priority="high"
            ))
        
        # Add model-based insights
        if analysis.model_info.get('data_points', 0) > 100:
            insights.append(InsightResponse(
                type="data_quality",
                title="Prediction Reliability",
                description=f"High-quality analysis based on {analysis.model_info['data_points']} data points. Predictions are highly reliable.",
                confidence="high",
                actionable=False,
                priority="low"
            ))
        elif analysis.model_info.get('data_points', 0) > 30:
            insights.append(InsightResponse(
                type="data_quality",
                title="Prediction Reliability",
                description="Moderate analysis quality. More transaction history would improve prediction accuracy.",
                confidence="medium",
                actionable=False,
                priority="low"
            ))
        
        logger.info("Financial insights generated",
                   user_id=current_user.get('id'),
                   insights_count=len(insights),
                   days_analyzed=days_back)
        
        return insights
        
    except Exception as e:
        logger.error("Failed to generate financial insights",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate financial insights"
        )


@router.get(
    "/spending-anomalies",
    status_code=status.HTTP_200_OK,
    summary="Detect Spending Anomalies",
    description="Identifies unusual spending patterns and potential anomalies",
    response_model=List[SpendingAnomalyResponse],
    tags=["Analytics"]
)
async def detect_spending_anomalies(
    days_back: int = Query(default=90, ge=30, le=365, description="Days of history to analyze"),
    min_anomaly_score: int = Query(default=70, ge=50, le=100, description="Minimum anomaly score"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> List[SpendingAnomalyResponse]:
    """
    **Detect spending anomalies**
    
    Uses statistical analysis to identify unusual transactions:
    - Outlier detection based on historical patterns
    - Category-specific anomaly analysis
    - Temporal pattern recognition
    - Fraud detection signals
    - Budget variance alerts
    
    Helps users identify potentially fraudulent or mistaken transactions.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        service = get_predictive_analysis_service()
        
        # In real implementation, fetch user's recent transactions
        transactions = []
        
        # Detect anomalies
        anomalies = await service.detect_spending_anomalies(transactions)
        
        # Filter by minimum anomaly score
        filtered_anomalies = [
            anomaly for anomaly in anomalies 
            if anomaly.get('anomaly_score', 0) >= min_anomaly_score
        ]
        
        # Convert to response format
        result = []
        for anomaly in filtered_anomalies:
            result.append(SpendingAnomalyResponse(
                date=anomaly['date'],
                amount=anomaly['amount'],
                description=anomaly['description'],
                category=anomaly['category'],
                anomaly_score=anomaly['anomaly_score'],
                deviation_from_normal=anomaly['deviation_from_normal']
            ))
        
        logger.info("Spending anomalies detected",
                   user_id=current_user.get('id'),
                   anomalies_found=len(result),
                   days_analyzed=days_back)
        
        return result
        
    except Exception as e:
        logger.error("Failed to detect spending anomalies",
                    user_id=current_user.get('id'),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to detect spending anomalies"
        )


@router.post(
    "/goal-analysis",
    status_code=status.HTTP_200_OK,
    summary="Analyze Financial Goal",
    description="Analyzes financial goal achievability and provides recommendations",
    response_model=GoalPredictionResponse,
    tags=["Analytics"]
)
async def analyze_financial_goal(
    request: GoalAnalysisRequest,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> GoalPredictionResponse:
    """
    **Analyze financial goal achievability**
    
    Provides AI-powered analysis of financial goals:
    - Achievement probability calculation
    - Required savings rate analysis
    - Timeline feasibility assessment
    - Alternative scenario modeling
    - Personalized recommendations
    
    Helps users understand if their financial goals are realistic and achievable.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # Parse target date
        target_date = datetime.fromisoformat(request.target_date)
        
        if target_date <= datetime.now():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target date must be in the future"
            )
        
        # Create goal object
        goal = FinancialGoal(
            id=f"goal_{current_user.get('id')}_{int(datetime.now().timestamp())}",
            name=request.goal_name,
            target_amount=request.target_amount,
            current_amount=request.current_amount,
            target_date=target_date,
            category=request.category,
            monthly_contribution=request.monthly_contribution
        )
        
        # In real implementation, calculate current savings rate from transaction history
        current_savings_rate = 20.0  # Default savings rate
        
        # In real implementation, get predicted income from recent forecasts
        predicted_monthly_income = 5000.0  # Default income
        
        # Analyze goal achievability
        prediction = await predict_goal_achievement(
            goal,
            current_savings_rate,
            predicted_monthly_income
        )
        
        logger.info("Goal analysis completed",
                   user_id=current_user.get('id'),
                   goal_name=request.goal_name,
                   target_amount=request.target_amount,
                   probability=prediction['probability'])
        
        return GoalPredictionResponse(
            goal_id=prediction['goal_id'],
            status=prediction['status'],
            probability=prediction['probability'],
            predicted_achievement_date=prediction['predicted_achievement_date'],
            required_monthly_savings=prediction['required_monthly_savings'],
            current_monthly_capacity=prediction.get('current_monthly_capacity', 0),
            recommendation=prediction['recommendation']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to analyze financial goal",
                    user_id=current_user.get('id'),
                    goal_name=request.goal_name,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze financial goal"
        )


@router.get(
    "/trend-analysis",
    status_code=status.HTTP_200_OK,
    summary="Get Trend Analysis",
    description="Provides detailed trend analysis of financial patterns",
    tags=["Analytics"]
)
async def get_trend_analysis(
    metric: str = Query(..., description="Metric to analyze (income, expenses, savings, category_spending)"),
    period: str = Query(default="monthly", description="Analysis period (daily, weekly, monthly, quarterly)"),
    lookback_months: int = Query(default=12, ge=3, le=36, description="Months of history to analyze"),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    **Get trend analysis**
    
    Provides detailed trend analysis of financial metrics:
    - Growth/decline rate calculations
    - Seasonal pattern identification
    - Volatility analysis
    - Correlation analysis
    - Forecasted trends
    
    Useful for understanding long-term financial patterns and planning.
    """
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        valid_metrics = ['income', 'expenses', 'savings', 'category_spending']
        if metric not in valid_metrics:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid metric. Must be one of: {valid_metrics}"
            )
        
        valid_periods = ['daily', 'weekly', 'monthly', 'quarterly']
        if period not in valid_periods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid period. Must be one of: {valid_periods}"
            )
        
        # In real implementation, fetch and analyze user's historical data
        # For now, returning mock trend analysis
        
        start_date = datetime.now() - timedelta(days=lookback_months * 30)
        end_date = datetime.now()
        
        # Mock trend data
        trend_analysis = {
            "metric": metric,
            "period": period,
            "analysis_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "total_periods": lookback_months
            },
            "trend_summary": {
                "direction": "increasing",
                "growth_rate": 5.2,  # % per period
                "volatility": "medium",
                "seasonality_detected": True,
                "strongest_period": "December" if metric == "expenses" else "Q4"
            },
            "statistical_analysis": {
                "mean": 2500.00,
                "median": 2450.00,
                "std_deviation": 450.00,
                "min_value": 1800.00,
                "max_value": 3200.00,
                "coefficient_of_variation": 0.18
            },
            "trend_data": [
                {"period": "2024-01", "value": 2200.00, "trend_component": 2180.00},
                {"period": "2024-02", "value": 2350.00, "trend_component": 2220.00},
                {"period": "2024-03", "value": 2400.00, "trend_component": 2260.00},
                # ... more periods
            ],
            "forecasted_trend": {
                "next_3_periods": [2650.00, 2700.00, 2750.00],
                "confidence_intervals": [
                    {"period": "next", "lower": 2500.00, "upper": 2800.00},
                    {"period": "next+1", "lower": 2520.00, "upper": 2880.00},
                    {"period": "next+2", "lower": 2540.00, "upper": 2960.00}
                ]
            },
            "insights": [
                f"Your {metric} shows a consistent upward trend of 5.2% per {period}",
                "Seasonal patterns suggest higher values in Q4",
                "Volatility is within normal ranges for this metric"
            ]
        }
        
        logger.info("Trend analysis generated",
                   user_id=current_user.get('id'),
                   metric=metric,
                   period=period,
                   lookback_months=lookback_months)
        
        return trend_analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate trend analysis",
                    user_id=current_user.get('id'),
                    metric=metric,
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate trend analysis"
        )