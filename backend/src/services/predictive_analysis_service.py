"""
Predictive Financial Analysis Service.
Provides AI-powered financial forecasting, trend analysis, and personalized insights
using machine learning models and statistical analysis.
"""

import asyncio
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from decimal import Decimal
import structlog
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

from src.config import settings

logger = structlog.get_logger()


class PredictionType(Enum):
    """Types of financial predictions."""
    INCOME_FORECAST = "income_forecast"
    EXPENSE_FORECAST = "expense_forecast"
    CASHFLOW_PREDICTION = "cashflow_prediction"
    BUDGET_PERFORMANCE = "budget_performance"
    SAVINGS_PROJECTION = "savings_projection"
    CATEGORY_TRENDS = "category_trends"
    GOAL_ACHIEVEMENT = "goal_achievement"
    SPENDING_ANOMALY = "spending_anomaly"


class TimeHorizon(Enum):
    """Prediction time horizons."""
    NEXT_WEEK = "next_week"
    NEXT_MONTH = "next_month"
    NEXT_QUARTER = "next_quarter"
    NEXT_6_MONTHS = "next_6_months"
    NEXT_YEAR = "next_year"


class ConfidenceLevel(Enum):
    """Confidence levels for predictions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class PredictionConfig:
    """Configuration for prediction analysis."""
    prediction_type: PredictionType
    time_horizon: TimeHorizon
    user_id: str
    include_seasonal: bool = True
    include_trends: bool = True
    confidence_interval: float = 0.95
    min_data_points: int = 30
    categories: Optional[List[str]] = None
    accounts: Optional[List[str]] = None


@dataclass
class PredictionResult:
    """Result of predictive analysis."""
    config: PredictionConfig
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    confidence_level: ConfidenceLevel = ConfidenceLevel.MEDIUM
    accuracy_metrics: Dict[str, float] = field(default_factory=dict)
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    model_info: Dict[str, Any] = field(default_factory=dict)
    generated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FinancialGoal:
    """Financial goal configuration."""
    id: str
    name: str
    target_amount: float
    current_amount: float
    target_date: datetime
    category: Optional[str] = None
    monthly_contribution: Optional[float] = None


class DataPreprocessor:
    """Preprocesses financial data for ML models."""
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    def prepare_time_series(self, transactions: List[Dict[str, Any]], 
                           frequency: str = 'D') -> pd.DataFrame:
        """Prepare time series data from transactions."""
        if not transactions:
            return pd.DataFrame()
        
        df = pd.DataFrame(transactions)
        df['date'] = pd.to_datetime(df['date'])
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        
        # Create time series with specified frequency
        df.set_index('date', inplace=True)
        
        # Separate income and expenses
        income_df = df[df['amount'] > 0].resample(frequency)['amount'].sum()
        expense_df = df[df['amount'] < 0].resample(frequency)['amount'].sum()
        
        # Create combined time series
        time_series = pd.DataFrame({
            'income': income_df,
            'expenses': abs(expense_df),
            'net': income_df + expense_df
        }).fillna(0)
        
        return time_series
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create feature engineering for ML models."""
        features_df = df.copy()
        
        # Time-based features
        features_df['day_of_week'] = features_df.index.dayofweek
        features_df['month'] = features_df.index.month
        features_df['quarter'] = features_df.index.quarter
        features_df['is_weekend'] = features_df['day_of_week'].isin([5, 6])
        features_df['is_month_end'] = features_df.index.is_month_end
        
        # Rolling statistics
        for column in ['income', 'expenses', 'net']:
            if column in features_df.columns:
                features_df[f'{column}_ma_7'] = features_df[column].rolling(7).mean()
                features_df[f'{column}_ma_30'] = features_df[column].rolling(30).mean()
                features_df[f'{column}_std_7'] = features_df[column].rolling(7).std()
                features_df[f'{column}_trend'] = features_df[column].diff()
        
        # Lag features
        for lag in [1, 7, 30]:
            for column in ['income', 'expenses', 'net']:
                if column in features_df.columns:
                    features_df[f'{column}_lag_{lag}'] = features_df[column].shift(lag)
        
        return features_df.fillna(0)
    
    def detect_seasonality(self, series: pd.Series, period: int = 365) -> Dict[str, float]:
        """Detect seasonal patterns in financial data."""
        if len(series) < period * 2:
            return {"has_seasonality": 0.0, "seasonal_strength": 0.0}
        
        # Simple seasonality detection using autocorrelation
        autocorr = series.autocorr(lag=period)
        seasonal_strength = abs(autocorr) if not np.isnan(autocorr) else 0.0
        
        return {
            "has_seasonality": 1.0 if seasonal_strength > 0.3 else 0.0,
            "seasonal_strength": seasonal_strength
        }


class PredictiveModel:
    """Base class for predictive models."""
    
    def __init__(self, model_type: str = "linear"):
        self.model_type = model_type
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
    
    def train(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """Train the predictive model."""
        if len(X) == 0 or len(y) == 0:
            raise ValueError("Insufficient data for training")
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Initialize model based on type
        if self.model_type == "linear":
            self.model = LinearRegression()
        elif self.model_type == "random_forest":
            self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        else:
            self.model = LinearRegression()
        
        # Train model
        self.model.fit(X_scaled, y)
        self.is_trained = True
        
        # Calculate training metrics
        y_pred = self.model.predict(X_scaled)
        metrics = {
            "mae": mean_absolute_error(y, y_pred),
            "mse": mean_squared_error(y, y_pred),
            "rmse": np.sqrt(mean_squared_error(y, y_pred))
        }
        
        return metrics
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Make predictions."""
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        X_scaled = self.scaler.transform(X)
        return self.model.predict(X_scaled)
    
    def predict_with_confidence(self, X: np.ndarray, 
                              confidence: float = 0.95) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Make predictions with confidence intervals."""
        predictions = self.predict(X)
        
        # Simple confidence interval based on training error
        # In production, use more sophisticated methods like bootstrapping
        error_margin = np.std(predictions) * 1.96  # 95% confidence
        lower_bound = predictions - error_margin
        upper_bound = predictions + error_margin
        
        return predictions, lower_bound, upper_bound


class FinancialForecaster:
    """Financial forecasting engine."""
    
    def __init__(self):
        self.preprocessor = DataPreprocessor()
        self.models = {}
    
    def forecast_income(self, transactions: List[Dict[str, Any]], 
                       horizon_days: int = 30) -> Dict[str, Any]:
        """Forecast income for specified horizon."""
        if not transactions:
            return self._empty_forecast("income")
        
        # Prepare data
        df = self.preprocessor.prepare_time_series(transactions, 'D')
        if df.empty or 'income' not in df.columns:
            return self._empty_forecast("income")
        
        features_df = self.preprocessor.create_features(df)
        
        # Prepare training data
        X = features_df.drop(['income', 'expenses', 'net'], axis=1).select_dtypes(include=[np.number])
        y = features_df['income']
        
        # Remove rows with insufficient data
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        
        if len(X) < 30:
            return self._empty_forecast("income")
        
        # Train model
        model = PredictiveModel("random_forest")
        try:
            metrics = model.train(X.values, y.values)
        except Exception as e:
            logger.error("Income forecasting model training failed", error=str(e))
            return self._empty_forecast("income")
        
        # Generate future dates
        last_date = df.index.max()
        future_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=horizon_days,
            freq='D'
        )
        
        # Create future features (simplified)
        future_features = []
        for date in future_dates:
            features = [
                date.dayofweek,
                date.month,
                date.quarter,
                1 if date.dayofweek in [5, 6] else 0,
                1 if date.is_month_end else 0,
                y.mean(),  # Average income
                y.mean(),  # 30-day MA placeholder
                y.std(),   # Std placeholder
                0,         # Trend placeholder
                y.iloc[-1] if len(y) > 0 else 0,  # Last value
                y.iloc[-7] if len(y) > 7 else 0,  # 7-day lag
                y.iloc[-30] if len(y) > 30 else 0  # 30-day lag
            ]
            future_features.append(features)
        
        future_X = np.array(future_features)
        
        # Make predictions
        try:
            predictions, lower_bound, upper_bound = model.predict_with_confidence(future_X)
            
            forecast_data = []
            for i, date in enumerate(future_dates):
                forecast_data.append({
                    "date": date.isoformat(),
                    "predicted_value": float(max(0, predictions[i])),
                    "lower_bound": float(max(0, lower_bound[i])),
                    "upper_bound": float(upper_bound[i]),
                    "confidence": "medium"
                })
            
            return {
                "type": "income_forecast",
                "horizon_days": horizon_days,
                "predictions": forecast_data,
                "total_predicted": float(max(0, predictions.sum())),
                "accuracy_metrics": metrics,
                "confidence_level": "medium"
            }
            
        except Exception as e:
            logger.error("Income prediction failed", error=str(e))
            return self._empty_forecast("income")
    
    def forecast_expenses(self, transactions: List[Dict[str, Any]], 
                         horizon_days: int = 30) -> Dict[str, Any]:
        """Forecast expenses for specified horizon."""
        if not transactions:
            return self._empty_forecast("expenses")
        
        # Similar implementation to income forecast but for expenses
        df = self.preprocessor.prepare_time_series(transactions, 'D')
        if df.empty or 'expenses' not in df.columns:
            return self._empty_forecast("expenses")
        
        features_df = self.preprocessor.create_features(df)
        
        X = features_df.drop(['income', 'expenses', 'net'], axis=1).select_dtypes(include=[np.number])
        y = features_df['expenses']
        
        mask = ~(X.isna().any(axis=1) | y.isna())
        X = X[mask]
        y = y[mask]
        
        if len(X) < 30:
            return self._empty_forecast("expenses")
        
        model = PredictiveModel("random_forest")
        try:
            metrics = model.train(X.values, y.values)
        except Exception as e:
            logger.error("Expense forecasting model training failed", error=str(e))
            return self._empty_forecast("expenses")
        
        # Generate predictions (similar to income forecast)
        last_date = df.index.max()
        future_dates = pd.date_range(
            start=last_date + timedelta(days=1),
            periods=horizon_days,
            freq='D'
        )
        
        future_features = []
        for date in future_dates:
            features = [
                date.dayofweek,
                date.month,
                date.quarter,
                1 if date.dayofweek in [5, 6] else 0,
                1 if date.is_month_end else 0,
                y.mean(),
                y.mean(),
                y.std(),
                0,
                y.iloc[-1] if len(y) > 0 else 0,
                y.iloc[-7] if len(y) > 7 else 0,
                y.iloc[-30] if len(y) > 30 else 0
            ]
            future_features.append(features)
        
        future_X = np.array(future_features)
        
        try:
            predictions, lower_bound, upper_bound = model.predict_with_confidence(future_X)
            
            forecast_data = []
            for i, date in enumerate(future_dates):
                forecast_data.append({
                    "date": date.isoformat(),
                    "predicted_value": float(max(0, predictions[i])),
                    "lower_bound": float(max(0, lower_bound[i])),
                    "upper_bound": float(upper_bound[i]),
                    "confidence": "medium"
                })
            
            return {
                "type": "expense_forecast",
                "horizon_days": horizon_days,
                "predictions": forecast_data,
                "total_predicted": float(max(0, predictions.sum())),
                "accuracy_metrics": metrics,
                "confidence_level": "medium"
            }
            
        except Exception as e:
            logger.error("Expense prediction failed", error=str(e))
            return self._empty_forecast("expenses")
    
    def _empty_forecast(self, forecast_type: str) -> Dict[str, Any]:
        """Return empty forecast structure."""
        return {
            "type": f"{forecast_type}_forecast",
            "horizon_days": 0,
            "predictions": [],
            "total_predicted": 0.0,
            "accuracy_metrics": {},
            "confidence_level": "low",
            "message": "Insufficient data for forecasting"
        }


class InsightGenerator:
    """Generates financial insights and recommendations."""
    
    def __init__(self):
        pass
    
    def generate_spending_insights(self, transactions: List[Dict[str, Any]]) -> List[str]:
        """Generate insights about spending patterns."""
        if not transactions:
            return ["No transaction data available for analysis"]
        
        insights = []
        df = pd.DataFrame(transactions)
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'])
        
        # Expense analysis
        expenses = df[df['amount'] < 0]
        if not expenses.empty:
            # Category analysis
            category_spending = expenses.groupby('category')['amount'].sum().abs()
            top_category = category_spending.idxmax()
            top_amount = category_spending.max()
            
            insights.append(f"Your highest spending category is '{top_category}' with ${top_amount:.2f}")
            
            # Weekly vs weekend spending
            expenses['is_weekend'] = expenses['date'].dt.dayofweek.isin([5, 6])
            weekend_avg = expenses[expenses['is_weekend']]['amount'].mean()
            weekday_avg = expenses[~expenses['is_weekend']]['amount'].mean()
            
            if abs(weekend_avg) > abs(weekday_avg) * 1.2:
                insights.append("You tend to spend significantly more on weekends")
            
            # Monthly trend
            expenses['month'] = expenses['date'].dt.month
            monthly_spending = expenses.groupby('month')['amount'].sum().abs()
            if len(monthly_spending) > 1:
                trend = "increasing" if monthly_spending.iloc[-1] > monthly_spending.iloc[0] else "decreasing"
                insights.append(f"Your spending trend is {trend} over time")
        
        # Income analysis
        income = df[df['amount'] > 0]
        if not income.empty:
            avg_income = income['amount'].mean()
            insights.append(f"Your average income transaction is ${avg_income:.2f}")
        
        return insights[:5]  # Limit to top 5 insights
    
    def generate_budget_recommendations(self, budget_analysis: List[Dict[str, Any]]) -> List[str]:
        """Generate budget optimization recommendations."""
        if not budget_analysis:
            return ["No budget data available for recommendations"]
        
        recommendations = []
        
        for budget in budget_analysis:
            percentage_used = budget.get('percentage_used', 0)
            name = budget.get('name', 'Unknown Budget')
            
            if percentage_used > 100:
                recommendations.append(f"Consider reducing spending in '{name}' - you're {percentage_used-100:.1f}% over budget")
            elif percentage_used > 80:
                recommendations.append(f"Monitor spending in '{name}' - you're at {percentage_used:.1f}% of your budget")
            elif percentage_used < 50:
                recommendations.append(f"You have room to allocate more funds to '{name}' - only {percentage_used:.1f}% used")
        
        return recommendations[:5]
    
    def generate_savings_recommendations(self, income_forecast: Dict[str, Any], 
                                       expense_forecast: Dict[str, Any]) -> List[str]:
        """Generate savings optimization recommendations."""
        recommendations = []
        
        predicted_income = income_forecast.get('total_predicted', 0)
        predicted_expenses = expense_forecast.get('total_predicted', 0)
        predicted_savings = predicted_income - predicted_expenses
        
        if predicted_savings > 0:
            savings_rate = (predicted_savings / predicted_income * 100) if predicted_income > 0 else 0
            
            if savings_rate < 10:
                recommendations.append(f"Your predicted savings rate is {savings_rate:.1f}%. Consider increasing savings to at least 20%")
            elif savings_rate < 20:
                recommendations.append(f"Good progress! Your savings rate is {savings_rate:.1f}%. Try to reach 20% for optimal financial health")
            else:
                recommendations.append(f"Excellent! Your savings rate of {savings_rate:.1f}% exceeds recommended levels")
        else:
            recommendations.append("Predicted expenses exceed income. Consider reviewing your spending or increasing income")
        
        return recommendations


class GoalTracker:
    """Tracks and predicts financial goal achievement."""
    
    def __init__(self):
        pass
    
    def predict_goal_achievement(self, goal: FinancialGoal, 
                                current_savings_rate: float,
                                predicted_income: float) -> Dict[str, Any]:
        """Predict when a financial goal will be achieved."""
        remaining_amount = goal.target_amount - goal.current_amount
        days_remaining = (goal.target_date - datetime.now()).days
        
        if remaining_amount <= 0:
            return {
                "goal_id": goal.id,
                "status": "achieved",
                "probability": 1.0,
                "predicted_achievement_date": datetime.now().isoformat(),
                "required_monthly_savings": 0,
                "recommendation": "Congratulations! You've achieved your goal."
            }
        
        # Calculate required monthly savings
        months_remaining = max(1, days_remaining / 30.44)  # Average days per month
        required_monthly_savings = remaining_amount / months_remaining
        
        # Estimate achievability based on current savings capacity
        available_monthly_savings = predicted_income * (current_savings_rate / 100)
        achievability_ratio = available_monthly_savings / required_monthly_savings if required_monthly_savings > 0 else 1
        
        if achievability_ratio >= 1:
            probability = min(0.95, 0.7 + (achievability_ratio - 1) * 0.25)
            status = "on_track"
        elif achievability_ratio >= 0.8:
            probability = 0.6
            status = "challenging"
        else:
            probability = 0.3
            status = "difficult"
        
        # Predict achievement date based on current savings rate
        if available_monthly_savings > 0:
            months_needed = remaining_amount / available_monthly_savings
            predicted_date = datetime.now() + timedelta(days=months_needed * 30.44)
        else:
            predicted_date = goal.target_date + timedelta(days=365)  # Far future
        
        recommendation = self._generate_goal_recommendation(goal, achievability_ratio, required_monthly_savings)
        
        return {
            "goal_id": goal.id,
            "status": status,
            "probability": probability,
            "predicted_achievement_date": predicted_date.isoformat(),
            "required_monthly_savings": required_monthly_savings,
            "current_monthly_capacity": available_monthly_savings,
            "achievability_ratio": achievability_ratio,
            "recommendation": recommendation
        }
    
    def _generate_goal_recommendation(self, goal: FinancialGoal, 
                                    achievability_ratio: float,
                                    required_monthly_savings: float) -> str:
        """Generate recommendation for goal achievement."""
        if achievability_ratio >= 1:
            return f"You're on track to achieve '{goal.name}'! Continue saving ${required_monthly_savings:.2f} monthly."
        elif achievability_ratio >= 0.8:
            shortfall = required_monthly_savings - (required_monthly_savings * achievability_ratio)
            return f"You need an additional ${shortfall:.2f} monthly to achieve '{goal.name}' on time. Consider reducing expenses or increasing income."
        else:
            return f"'{goal.name}' may be challenging to achieve by the target date. Consider extending the timeline or increasing your savings rate significantly."


class PredictiveAnalysisService:
    """Main predictive analysis service."""
    
    def __init__(self):
        self.forecaster = FinancialForecaster()
        self.insight_generator = InsightGenerator()
        self.goal_tracker = GoalTracker()
        
        logger.info("Predictive analysis service initialized")
    
    async def generate_comprehensive_analysis(self, 
                                            user_id: str,
                                            transactions: List[Dict[str, Any]],
                                            budgets: List[Dict[str, Any]] = None,
                                            goals: List[FinancialGoal] = None,
                                            horizon_days: int = 90) -> PredictionResult:
        """Generate comprehensive predictive analysis."""
        
        budgets = budgets or []
        goals = goals or []
        
        try:
            # Generate forecasts
            income_forecast = self.forecaster.forecast_income(transactions, horizon_days)
            expense_forecast = self.forecaster.forecast_expenses(transactions, horizon_days)
            
            # Calculate cashflow prediction
            cashflow_predictions = []
            income_preds = income_forecast.get('predictions', [])
            expense_preds = expense_forecast.get('predictions', [])
            
            for i, (inc_pred, exp_pred) in enumerate(zip(income_preds, expense_preds)):
                cashflow_predictions.append({
                    "date": inc_pred.get('date'),
                    "predicted_cashflow": inc_pred.get('predicted_value', 0) - exp_pred.get('predicted_value', 0),
                    "income_component": inc_pred.get('predicted_value', 0),
                    "expense_component": exp_pred.get('predicted_value', 0)
                })
            
            # Generate insights
            spending_insights = self.insight_generator.generate_spending_insights(transactions)
            
            # Budget recommendations
            budget_analysis = []  # In real implementation, analyze budget performance
            budget_recommendations = self.insight_generator.generate_budget_recommendations(budget_analysis)
            
            # Savings recommendations
            savings_recommendations = self.insight_generator.generate_savings_recommendations(
                income_forecast, expense_forecast
            )
            
            # Goal predictions
            goal_predictions = []
            if goals:
                current_savings_rate = 20.0  # Default savings rate
                predicted_monthly_income = income_forecast.get('total_predicted', 0) / (horizon_days / 30.44)
                
                for goal in goals:
                    goal_prediction = self.goal_tracker.predict_goal_achievement(
                        goal, current_savings_rate, predicted_monthly_income
                    )
                    goal_predictions.append(goal_prediction)
            
            # Combine all predictions
            all_predictions = [
                {
                    "type": "income_forecast",
                    "data": income_forecast
                },
                {
                    "type": "expense_forecast", 
                    "data": expense_forecast
                },
                {
                    "type": "cashflow_prediction",
                    "data": {
                        "predictions": cashflow_predictions,
                        "total_predicted_cashflow": sum(p['predicted_cashflow'] for p in cashflow_predictions)
                    }
                },
                {
                    "type": "goal_predictions",
                    "data": goal_predictions
                }
            ]
            
            # Combine insights and recommendations
            all_insights = spending_insights[:3]
            all_recommendations = (budget_recommendations + savings_recommendations)[:5]
            
            # Determine overall confidence level
            confidence_level = ConfidenceLevel.MEDIUM
            if len(transactions) > 200:
                confidence_level = ConfidenceLevel.HIGH
            elif len(transactions) < 50:
                confidence_level = ConfidenceLevel.LOW
            
            config = PredictionConfig(
                prediction_type=PredictionType.CASHFLOW_PREDICTION,
                time_horizon=TimeHorizon.NEXT_QUARTER,
                user_id=user_id
            )
            
            return PredictionResult(
                config=config,
                predictions=all_predictions,
                confidence_level=confidence_level,
                insights=all_insights,
                recommendations=all_recommendations,
                model_info={
                    "data_points": len(transactions),
                    "forecast_horizon_days": horizon_days,
                    "models_used": ["random_forest", "linear_regression"]
                }
            )
            
        except Exception as e:
            logger.error("Comprehensive analysis failed", user_id=user_id, error=str(e))
            raise
    
    async def detect_spending_anomalies(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Detect unusual spending patterns."""
        if not transactions:
            return []
        
        try:
            df = pd.DataFrame(transactions)
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            df['date'] = pd.to_datetime(df['date'])
            
            # Focus on expenses
            expenses = df[df['amount'] < 0].copy()
            if expenses.empty:
                return []
            
            expenses['abs_amount'] = abs(expenses['amount'])
            
            # Calculate statistical thresholds
            mean_expense = expenses['abs_amount'].mean()
            std_expense = expenses['abs_amount'].std()
            threshold = mean_expense + (2 * std_expense)  # 2 standard deviations
            
            # Find anomalies
            anomalies = expenses[expenses['abs_amount'] > threshold]
            
            anomaly_list = []
            for _, row in anomalies.head(10).iterrows():  # Top 10 anomalies
                anomaly_list.append({
                    "date": row['date'].isoformat(),
                    "amount": float(row['amount']),
                    "description": row.get('description', 'N/A'),
                    "category": row.get('category', 'N/A'),
                    "deviation_from_normal": float((row['abs_amount'] - mean_expense) / std_expense),
                    "anomaly_score": min(100, int((row['abs_amount'] / threshold) * 100))
                })
            
            return anomaly_list
            
        except Exception as e:
            logger.error("Anomaly detection failed", error=str(e))
            return []


# Global predictive analysis service
_predictive_service = None


def get_predictive_analysis_service() -> PredictiveAnalysisService:
    """Get global predictive analysis service."""
    global _predictive_service
    if _predictive_service is None:
        _predictive_service = PredictiveAnalysisService()
    return _predictive_service


# Convenience functions
async def generate_income_forecast(user_id: str, transactions: List[Dict[str, Any]], 
                                 days: int = 30) -> Dict[str, Any]:
    """Generate income forecast for user."""
    service = get_predictive_analysis_service()
    return service.forecaster.forecast_income(transactions, days)


async def generate_expense_forecast(user_id: str, transactions: List[Dict[str, Any]], 
                                  days: int = 30) -> Dict[str, Any]:
    """Generate expense forecast for user."""
    service = get_predictive_analysis_service()
    return service.forecaster.forecast_expenses(transactions, days)


async def predict_goal_achievement(goal: FinancialGoal, 
                                 current_savings_rate: float,
                                 predicted_income: float) -> Dict[str, Any]:
    """Predict financial goal achievement."""
    service = get_predictive_analysis_service()
    return service.goal_tracker.predict_goal_achievement(goal, current_savings_rate, predicted_income)