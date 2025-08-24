import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject, combineLatest } from 'rxjs';
import { map, shareReplay, tap } from 'rxjs/operators';

import { ConfigService } from './config.service';
import {
  FinancialInsights,
  SpendingTrend,
  BudgetAnalysis,
  CategoryInsight,
  FinancialPrediction,
  TransactionAnomaly,
  FinancialRecommendation,
  ReportParameters
} from '../types/enterprise.types';

export interface AnalyticsFilters {
  dateRange: {
    startDate: string;
    endDate: string;
  };
  accounts?: string[];
  categories?: string[];
  groupBy: 'day' | 'week' | 'month' | 'quarter' | 'year';
}

export interface ChartDataPoint {
  label: string;
  value: number;
  color?: string;
  metadata?: any;
}

export interface ChartConfiguration {
  type: 'line' | 'bar' | 'pie' | 'doughnut' | 'area';
  data: ChartDataPoint[];
  options?: any;
}

@Injectable({
  providedIn: 'root'
})
export class AnalyticsService {
  private readonly apiUrl = `${this.config.apiUrl}/analytics`;

  private filtersSubject = new BehaviorSubject<AnalyticsFilters>(this.getDefaultFilters());
  public filters$ = this.filtersSubject.asObservable();

  private insightsSubject = new BehaviorSubject<FinancialInsights | null>(null);
  public insights$ = this.insightsSubject.asObservable();

  private loadingSubject = new BehaviorSubject<boolean>(false);
  public loading$ = this.loadingSubject.asObservable();

  constructor(
    private http: HttpClient,
    private config: ConfigService
  ) {
    this.initializeAnalytics();
  }

  private initializeAnalytics(): void {
    // Auto-refresh insights when filters change
    this.filters$.subscribe(filters => {
      this.refreshInsights(filters);
    });
  }

  private getDefaultFilters(): AnalyticsFilters {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(endDate.getMonth() - 6); // Last 6 months

    return {
      dateRange: {
        startDate: startDate.toISOString().split('T')[0],
        endDate: endDate.toISOString().split('T')[0]
      },
      groupBy: 'month'
    };
  }

  // Filter Management
  updateFilters(filters: Partial<AnalyticsFilters>): void {
    const currentFilters = this.filtersSubject.value;
    const newFilters = { ...currentFilters, ...filters };
    this.filtersSubject.next(newFilters);
  }

  getFilters(): AnalyticsFilters {
    return this.filtersSubject.value;
  }

  resetFilters(): void {
    this.filtersSubject.next(this.getDefaultFilters());
  }

  // Core Analytics API
  getFinancialInsights(filters?: AnalyticsFilters): Observable<FinancialInsights> {
    const params = this.buildParams(filters || this.getFilters());
    return this.http.get<FinancialInsights>(`${this.apiUrl}/insights`, { params })
      .pipe(
        tap(insights => this.insightsSubject.next(insights)),
        shareReplay(1)
      );
  }

  getSpendingTrends(filters?: AnalyticsFilters): Observable<SpendingTrend[]> {
    const params = this.buildParams(filters || this.getFilters());
    return this.http.get<SpendingTrend[]>(`${this.apiUrl}/spending-trends`, { params });
  }

  getBudgetAnalysis(filters?: AnalyticsFilters): Observable<BudgetAnalysis> {
    const params = this.buildParams(filters || this.getFilters());
    return this.http.get<BudgetAnalysis>(`${this.apiUrl}/budget-analysis`, { params });
  }

  getCategoryInsights(filters?: AnalyticsFilters): Observable<CategoryInsight[]> {
    const params = this.buildParams(filters || this.getFilters());
    return this.http.get<CategoryInsight[]>(`${this.apiUrl}/category-insights`, { params });
  }

  getFinancialPredictions(type?: string, filters?: AnalyticsFilters): Observable<FinancialPrediction[]> {
    let params = this.buildParams(filters || this.getFilters());
    if (type) {
      params = params.set('type', type);
    }
    return this.http.get<FinancialPrediction[]>(`${this.apiUrl}/predictions`, { params });
  }

  getTransactionAnomalies(filters?: AnalyticsFilters): Observable<TransactionAnomaly[]> {
    const params = this.buildParams(filters || this.getFilters());
    return this.http.get<TransactionAnomaly[]>(`${this.apiUrl}/anomalies`, { params });
  }

  getFinancialRecommendations(type?: string): Observable<FinancialRecommendation[]> {
    let params = new HttpParams();
    if (type) {
      params = params.set('type', type);
    }
    return this.http.get<FinancialRecommendation[]>(`${this.apiUrl}/recommendations`, { params });
  }

  // Cash Flow Analysis
  getCashFlowAnalysis(filters?: AnalyticsFilters): Observable<any> {
    const params = this.buildParams(filters || this.getFilters());
    return this.http.get(`${this.apiUrl}/cash-flow`, { params });
  }

  getNetWorthTrends(filters?: AnalyticsFilters): Observable<any> {
    const params = this.buildParams(filters || this.getFilters());
    return this.http.get(`${this.apiUrl}/net-worth`, { params });
  }

  // Goal Tracking
  getGoalProgress(goalId?: string): Observable<any> {
    let params = new HttpParams();
    if (goalId) {
      params = params.set('goal_id', goalId);
    }
    return this.http.get(`${this.apiUrl}/goal-progress`, { params });
  }

  // Chart Data Generation
  generateSpendingTrendChart(trends: SpendingTrend[]): ChartConfiguration {
    return {
      type: 'line',
      data: trends.map(trend => ({
        label: this.formatPeriodLabel(trend.period),
        value: trend.total_spending,
        color: trend.net_change >= 0 ? '#4CAF50' : '#f44336',
        metadata: {
          income: trend.total_income,
          netChange: trend.net_change,
          trendDirection: trend.trend_direction
        }
      })),
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value: number) => this.formatCurrency(value)
            }
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (context: any) => {
                const data = context.raw.metadata;
                return [
                  `Spending: ${this.formatCurrency(context.raw.value)}`,
                  `Income: ${this.formatCurrency(data.income)}`,
                  `Net Change: ${this.formatCurrency(data.netChange)}`
                ];
              }
            }
          }
        }
      }
    };
  }

  generateCategoryBreakdownChart(insights: CategoryInsight[]): ChartConfiguration {
    const colors = [
      '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
      '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
    ];

    return {
      type: 'doughnut',
      data: insights.slice(0, 8).map((insight, index) => ({
        label: insight.category_name,
        value: insight.average_monthly_spending,
        color: colors[index % colors.length],
        metadata: {
          trend: insight.trend_direction,
          topMerchants: insight.top_merchants
        }
      })),
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'bottom'
          },
          tooltip: {
            callbacks: {
              label: (context: any) => {
                const percentage = ((context.raw.value / insights.reduce((sum, i) => sum + i.average_monthly_spending, 0)) * 100).toFixed(1);
                return `${context.label}: ${this.formatCurrency(context.raw.value)} (${percentage}%)`;
              }
            }
          }
        }
      }
    };
  }

  generateBudgetUtilizationChart(analysis: BudgetAnalysis): ChartConfiguration {
    return {
      type: 'bar',
      data: analysis.categories.map(category => ({
        label: category.category_name,
        value: category.utilization_percentage * 100,
        color: this.getBudgetStatusColor(category.status),
        metadata: {
          budgeted: category.budgeted,
          spent: category.spent,
          remaining: category.remaining,
          status: category.status
        }
      })),
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
            max: 150, // Allow for over-budget visualization
            ticks: {
              callback: (value: number) => `${value}%`
            }
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (context: any) => {
                const data = context.raw.metadata;
                return [
                  `Budgeted: ${this.formatCurrency(data.budgeted)}`,
                  `Spent: ${this.formatCurrency(data.spent)}`,
                  `Remaining: ${this.formatCurrency(data.remaining)}`,
                  `Utilization: ${context.raw.value.toFixed(1)}%`
                ];
              }
            }
          }
        }
      }
    };
  }

  // Prediction Visualization
  generatePredictionChart(predictions: FinancialPrediction[]): ChartConfiguration {
    return {
      type: 'line',
      data: predictions.map(pred => ({
        label: this.formatDate(pred.prediction_date),
        value: pred.predicted_amount,
        color: '#2196F3',
        metadata: {
          confidenceInterval: pred.confidence_interval,
          confidenceLevel: pred.confidence_level,
          type: pred.type,
          factors: pred.factors
        }
      })),
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value: number) => this.formatCurrency(value)
            }
          }
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (context: any) => {
                const data = context.raw.metadata;
                return [
                  `Predicted: ${this.formatCurrency(context.raw.value)}`,
                  `Confidence: ${(data.confidenceLevel * 100).toFixed(1)}%`,
                  `Range: ${this.formatCurrency(data.confidenceInterval.lower)} - ${this.formatCurrency(data.confidenceInterval.upper)}`
                ];
              }
            }
          }
        }
      }
    };
  }

  // Utility Methods
  private buildParams(filters: AnalyticsFilters): HttpParams {
    let params = new HttpParams()
      .set('start_date', filters.dateRange.startDate)
      .set('end_date', filters.dateRange.endDate)
      .set('group_by', filters.groupBy);

    if (filters.accounts?.length) {
      filters.accounts.forEach(account => {
        params = params.append('accounts', account);
      });
    }

    if (filters.categories?.length) {
      filters.categories.forEach(category => {
        params = params.append('categories', category);
      });
    }

    return params;
  }

  private refreshInsights(filters: AnalyticsFilters): void {
    this.loadingSubject.next(true);
    this.getFinancialInsights(filters).subscribe(
      insights => {
        this.loadingSubject.next(false);
      },
      error => {
        console.error('Error refreshing insights:', error);
        this.loadingSubject.next(false);
      }
    );
  }

  private getBudgetStatusColor(status: string): string {
    switch (status) {
      case 'under_budget': return '#4CAF50';
      case 'on_track': return '#2196F3';
      case 'warning': return '#FF9800';
      case 'over_budget': return '#f44336';
      default: return '#9E9E9E';
    }
  }

  private formatPeriodLabel(period: string): string {
    // Assuming period format is YYYY-MM or YYYY-Qx
    if (period.includes('Q')) {
      return period.replace('-', ' ');
    }
    const date = new Date(period + '-01');
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  }

  private formatCurrency(amount: number, currency = 'USD'): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency
    }).format(amount);
  }

  private formatDate(date: string | Date): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return dateObj.toLocaleDateString();
  }

  // Advanced Analytics
  compareTimeperiods(
    currentFilters: AnalyticsFilters, 
    comparisonFilters: AnalyticsFilters
  ): Observable<any> {
    const params = new HttpParams()
      .set('current_start', currentFilters.dateRange.startDate)
      .set('current_end', currentFilters.dateRange.endDate)
      .set('comparison_start', comparisonFilters.dateRange.startDate)
      .set('comparison_end', comparisonFilters.dateRange.endDate);

    return this.http.get(`${this.apiUrl}/compare-periods`, { params });
  }

  getSeasonalPatterns(category?: string): Observable<any> {
    let params = new HttpParams();
    if (category) {
      params = params.set('category', category);
    }
    return this.http.get(`${this.apiUrl}/seasonal-patterns`, { params });
  }

  getSpendingVelocity(): Observable<any> {
    return this.http.get(`${this.apiUrl}/spending-velocity`);
  }

  // Export Analytics Data
  exportAnalyticsData(format: 'csv' | 'excel', filters?: AnalyticsFilters): Observable<Blob> {
    const params = this.buildParams(filters || this.getFilters())
      .set('format', format);

    return this.http.get(`${this.apiUrl}/export`, {
      params,
      responseType: 'blob'
    });
  }
}