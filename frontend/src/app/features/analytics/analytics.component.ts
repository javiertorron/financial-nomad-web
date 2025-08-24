import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatGridListModule } from '@angular/material/grid-list';
import { Subject, combineLatest } from 'rxjs';
import { takeUntil, debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { Chart, ChartConfiguration, ChartType, registerables } from 'chart.js';

import { AnalyticsService, AnalyticsFilters } from '../../core/services/analytics.service';
import { AccountService } from '../../core/services/account.service';
import { CategoryService } from '../../core/services/category.service';
import { 
  FinancialInsights,
  SpendingTrend,
  BudgetAnalysis,
  CategoryInsight,
  FinancialPrediction,
  TransactionAnomaly,
  FinancialRecommendation
} from '../../core/types/enterprise.types';
import { LayoutComponent } from '../../shared/components/layout/layout.component';

Chart.register(...registerables);

@Component({
  selector: 'app-analytics',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatChipsModule,
    MatGridListModule,
    LayoutComponent
  ],
  template: `
    <app-layout>
      <div class="analytics-dashboard">
        <!-- Header with Filters -->
        <div class="header">
          <h1>
            <mat-icon>analytics</mat-icon>
            Financial Analytics
          </h1>
          <div class="filters">
            <form [formGroup]="filtersForm">
              <mat-form-field appearance="outline">
                <mat-label>Start Date</mat-label>
                <input matInput [matDatepicker]="startPicker" formControlName="startDate">
                <mat-datepicker-toggle matIconSuffix [for]="startPicker"></mat-datepicker-toggle>
                <mat-datepicker #startPicker></mat-datepicker>
              </mat-form-field>

              <mat-form-field appearance="outline">
                <mat-label>End Date</mat-label>
                <input matInput [matDatepicker]="endPicker" formControlName="endDate">
                <mat-datepicker-toggle matIconSuffix [for]="endPicker"></mat-datepicker-toggle>
                <mat-datepicker #endPicker></mat-datepicker>
              </mat-form-field>

              <mat-form-field appearance="outline">
                <mat-label>Group By</mat-label>
                <mat-select formControlName="groupBy">
                  <mat-option value="day">Daily</mat-option>
                  <mat-option value="week">Weekly</mat-option>
                  <mat-option value="month">Monthly</mat-option>
                  <mat-option value="quarter">Quarterly</mat-option>
                  <mat-option value="year">Yearly</mat-option>
                </mat-select>
              </mat-form-field>

              <button mat-raised-button color="primary" (click)="applyFilters()">
                <mat-icon>filter_list</mat-icon>
                Apply Filters
              </button>
            </form>
          </div>
        </div>

        <!-- Loading State -->
        <div *ngIf="loading$ | async" class="loading-container">
          <mat-spinner diameter="50"></mat-spinner>
          <p>Analyzing your financial data...</p>
        </div>

        <!-- Analytics Content -->
        <div *ngIf="!(loading$ | async)" class="analytics-content">
          
          <!-- Summary Cards -->
          <div class="summary-cards">
            <mat-card class="summary-card income">
              <mat-card-content>
                <div class="card-header">
                  <mat-icon>trending_up</mat-icon>
                  <span>Total Income</span>
                </div>
                <div class="amount">{{ formatCurrency(summaryData.totalIncome) }}</div>
                <div class="change" [class.positive]="summaryData.incomeChange > 0" [class.negative]="summaryData.incomeChange < 0">
                  <mat-icon>{{ summaryData.incomeChange > 0 ? 'arrow_upward' : 'arrow_downward' }}</mat-icon>
                  {{ formatPercentage(getAbsoluteValue(summaryData.incomeChange)) }}
                </div>
              </mat-card-content>
            </mat-card>

            <mat-card class="summary-card expenses">
              <mat-card-content>
                <div class="card-header">
                  <mat-icon>trending_down</mat-icon>
                  <span>Total Expenses</span>
                </div>
                <div class="amount">{{ formatCurrency(summaryData.totalExpenses) }}</div>
                <div class="change" [class.positive]="summaryData.expensesChange < 0" [class.negative]="summaryData.expensesChange > 0">
                  <mat-icon>{{ summaryData.expensesChange > 0 ? 'arrow_upward' : 'arrow_downward' }}</mat-icon>
                  {{ formatPercentage(getAbsoluteValue(summaryData.expensesChange)) }}
                </div>
              </mat-card-content>
            </mat-card>

            <mat-card class="summary-card savings">
              <mat-card-content>
                <div class="card-header">
                  <mat-icon>savings</mat-icon>
                  <span>Net Savings</span>
                </div>
                <div class="amount">{{ formatCurrency(summaryData.netSavings) }}</div>
                <div class="change" [class.positive]="summaryData.savingsChange > 0" [class.negative]="summaryData.savingsChange < 0">
                  <mat-icon>{{ summaryData.savingsChange > 0 ? 'arrow_upward' : 'arrow_downward' }}</mat-icon>
                  {{ formatPercentage(getAbsoluteValue(summaryData.savingsChange)) }}
                </div>
              </mat-card-content>
            </mat-card>

            <mat-card class="summary-card budget">
              <mat-card-content>
                <div class="card-header">
                  <mat-icon>account_balance_wallet</mat-icon>
                  <span>Budget Utilization</span>
                </div>
                <div class="amount">{{ formatPercentage(summaryData.budgetUtilization) }}</div>
                <div class="status" [class]="getBudgetStatus(summaryData.budgetUtilization)">
                  {{ getBudgetStatusText(summaryData.budgetUtilization) }}
                </div>
              </mat-card-content>
            </mat-card>
          </div>

          <mat-tab-group [(selectedIndex)]="activeTab">
            <!-- Spending Trends Tab -->
            <mat-tab label="Spending Trends">
              <div class="tab-content">
                <mat-card>
                  <mat-card-header>
                    <mat-card-title>Spending Trends Over Time</mat-card-title>
                  </mat-card-header>
                  <mat-card-content>
                    <div class="chart-container">
                      <canvas #spendingChart></canvas>
                    </div>
                  </mat-card-content>
                </mat-card>

                <mat-card class="trends-analysis">
                  <mat-card-header>
                    <mat-card-title>Trend Analysis</mat-card-title>
                  </mat-card-header>
                  <mat-card-content>
                    <div *ngIf="spendingTrends.length > 0" class="trends-grid">
                      <div *ngFor="let trend of spendingTrends.slice(0, 6)" class="trend-item">
                        <div class="trend-period">{{ formatPeriod(trend.period) }}</div>
                        <div class="trend-amount">{{ formatCurrency(trend.total_spending) }}</div>
                        <div class="trend-change" [class]="getTrendClass(trend.trend_direction)">
                          <mat-icon>{{ getTrendIcon(trend.trend_direction) }}</mat-icon>
                          {{ formatPercentage(trend.percentage_change) }}
                        </div>
                      </div>
                    </div>
                  </mat-card-content>
                </mat-card>
              </div>
            </mat-tab>

            <!-- Category Analysis Tab -->
            <mat-tab label="Category Analysis">
              <div class="tab-content">
                <div class="category-analysis-grid">
                  <mat-card>
                    <mat-card-header>
                      <mat-card-title>Category Breakdown</mat-card-title>
                    </mat-card-header>
                    <mat-card-content>
                      <div class="chart-container">
                        <canvas #categoryChart></canvas>
                      </div>
                    </mat-card-content>
                  </mat-card>

                  <mat-card>
                    <mat-card-header>
                      <mat-card-title>Category Insights</mat-card-title>
                    </mat-card-header>
                    <mat-card-content>
                      <div *ngIf="categoryInsights.length > 0" class="category-list">
                        <div *ngFor="let insight of categoryInsights" class="category-item">
                          <div class="category-info">
                            <h4>{{ insight.category_name }}</h4>
                            <div class="category-amount">{{ formatCurrency(insight.average_monthly_spending) }}</div>
                          </div>
                          <div class="category-trend" [class]="getTrendClass(insight.trend_direction)">
                            <mat-icon>{{ getTrendIcon(insight.trend_direction) }}</mat-icon>
                            {{ insight.trend_direction }}
                          </div>
                        </div>
                      </div>
                    </mat-card-content>
                  </mat-card>
                </div>
              </div>
            </mat-tab>

            <!-- Budget Performance Tab -->
            <mat-tab label="Budget Performance">
              <div class="tab-content">
                <mat-card>
                  <mat-card-header>
                    <mat-card-title>Budget Utilization</mat-card-title>
                  </mat-card-header>
                  <mat-card-content>
                    <div class="chart-container">
                      <canvas #budgetChart></canvas>
                    </div>
                  </mat-card-content>
                </mat-card>

                <mat-card *ngIf="budgetAnalysis">
                  <mat-card-header>
                    <mat-card-title>Budget Summary</mat-card-title>
                  </mat-card-header>
                  <mat-card-content>
                    <div class="budget-summary">
                      <div class="budget-stat">
                        <span class="label">Total Budgeted:</span>
                        <span class="value">{{ formatCurrency(budgetAnalysis.total_budgeted) }}</span>
                      </div>
                      <div class="budget-stat">
                        <span class="label">Total Spent:</span>
                        <span class="value">{{ formatCurrency(budgetAnalysis.total_spent) }}</span>
                      </div>
                      <div class="budget-stat">
                        <span class="label">Utilization:</span>
                        <span class="value">{{ formatPercentage(budgetAnalysis.utilization_percentage) }}</span>
                      </div>
                      <div class="budget-stat">
                        <span class="label">Projected End-of-Month:</span>
                        <span class="value">{{ formatCurrency(budgetAnalysis.projected_end_of_month.projected_spending) }}</span>
                      </div>
                    </div>
                  </mat-card-content>
                </mat-card>
              </div>
            </mat-tab>

            <!-- Predictions Tab -->
            <mat-tab label="Predictions">
              <div class="tab-content">
                <mat-card>
                  <mat-card-header>
                    <mat-card-title>Financial Predictions</mat-card-title>
                  </mat-card-header>
                  <mat-card-content>
                    <div class="chart-container">
                      <canvas #predictionsChart></canvas>
                    </div>
                  </mat-card-content>
                </mat-card>

                <div class="predictions-grid">
                  <mat-card *ngFor="let prediction of predictions" class="prediction-card">
                    <mat-card-content>
                      <div class="prediction-type">
                        <mat-icon>{{ getPredictionIcon(prediction.type) }}</mat-icon>
                        {{ formatPredictionType(prediction.type) }}
                      </div>
                      <div class="prediction-amount">{{ formatCurrency(prediction.predicted_amount) }}</div>
                      <div class="prediction-confidence">
                        Confidence: {{ formatPercentage(prediction.confidence_level) }}
                      </div>
                      <div class="prediction-date">{{ formatDate(prediction.prediction_date) }}</div>
                    </mat-card-content>
                  </mat-card>
                </div>
              </div>
            </mat-tab>

            <!-- Anomalies Tab -->
            <mat-tab label="Anomalies">
              <div class="tab-content">
                <mat-card>
                  <mat-card-header>
                    <mat-card-title>Transaction Anomalies</mat-card-title>
                    <mat-card-subtitle>Unusual spending patterns detected by AI</mat-card-subtitle>
                  </mat-card-header>
                  <mat-card-content>
                    <div *ngIf="anomalies.length > 0; else noAnomalies" class="anomalies-list">
                      <div *ngFor="let anomaly of anomalies" class="anomaly-item" [class]="getAnomalySeverity(anomaly.confidence_score)">
                        <div class="anomaly-icon">
                          <mat-icon>{{ getAnomalyIcon(anomaly.type) }}</mat-icon>
                        </div>
                        <div class="anomaly-content">
                          <h4>{{ formatAnomalyType(anomaly.type) }}</h4>
                          <p>{{ anomaly.description }}</p>
                          <div class="anomaly-confidence">
                            Confidence: {{ formatPercentage(anomaly.confidence_score) }}
                          </div>
                          <div class="anomaly-actions">
                            <mat-chip-set>
                              <mat-chip *ngFor="let action of anomaly.suggested_actions">
                                {{ action }}
                              </mat-chip>
                            </mat-chip-set>
                          </div>
                        </div>
                      </div>
                    </div>
                    <ng-template #noAnomalies>
                      <div class="no-anomalies">
                        <mat-icon>check_circle</mat-icon>
                        <p>No unusual spending patterns detected. Your finances look normal!</p>
                      </div>
                    </ng-template>
                  </mat-card-content>
                </mat-card>
              </div>
            </mat-tab>

            <!-- Recommendations Tab -->
            <mat-tab label="Recommendations">
              <div class="tab-content">
                <div class="recommendations-grid">
                  <mat-card *ngFor="let recommendation of recommendations" class="recommendation-card" [class]="recommendation.difficulty">
                    <mat-card-header>
                      <div mat-card-avatar class="recommendation-avatar">
                        <mat-icon>{{ getRecommendationIcon(recommendation.type) }}</mat-icon>
                      </div>
                      <mat-card-title>{{ recommendation.title }}</mat-card-title>
                      <mat-card-subtitle>
                        Impact: {{ formatCurrency(recommendation.potential_impact) }} • 
                        {{ recommendation.difficulty }} difficulty
                      </mat-card-subtitle>
                    </mat-card-header>
                    <mat-card-content>
                      <p>{{ recommendation.description }}</p>
                      <div class="recommendation-actions">
                        <h5>Recommended Actions:</h5>
                        <ul>
                          <li *ngFor="let action of recommendation.actions">
                            <strong>{{ action.description }}</strong>
                            <span class="action-priority" [class]="action.priority">{{ action.priority }}</span>
                            <span class="action-time">{{ action.estimated_time }}</span>
                          </li>
                        </ul>
                      </div>
                    </mat-card-content>
                  </mat-card>
                </div>
              </div>
            </mat-tab>
          </mat-tab-group>

        </div>
      </div>
    </app-layout>
  `,
  styles: [`
    .analytics-dashboard {
      padding: 20px;
      max-width: 1400px;
      margin: 0 auto;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;
      flex-wrap: wrap;
      gap: 20px;
    }

    .header h1 {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 0;
      font-size: 28px;
      font-weight: 500;
    }

    .filters form {
      display: flex;
      gap: 16px;
      align-items: flex-end;
      flex-wrap: wrap;
    }

    .filters mat-form-field {
      min-width: 150px;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 60px;
      text-align: center;
    }

    .loading-container mat-spinner {
      margin-bottom: 20px;
    }

    .summary-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }

    .summary-card {
      min-height: 120px;
    }

    .summary-card .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      font-weight: 500;
      color: #666;
    }

    .summary-card .amount {
      font-size: 24px;
      font-weight: 600;
      margin-bottom: 8px;
    }

    .summary-card .change {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 14px;
    }

    .summary-card .change.positive {
      color: #4CAF50;
    }

    .summary-card .change.negative {
      color: #f44336;
    }

    .summary-card .status {
      font-size: 12px;
      font-weight: 500;
      text-transform: uppercase;
      padding: 4px 8px;
      border-radius: 12px;
      display: inline-block;
    }

    .summary-card .status.on-track {
      background: #E8F5E8;
      color: #4CAF50;
    }

    .summary-card .status.over-budget {
      background: #FFEBEE;
      color: #f44336;
    }

    .summary-card .status.warning {
      background: #FFF8E1;
      color: #FF9800;
    }

    .tab-content {
      padding: 20px 0;
    }

    .chart-container {
      height: 400px;
      margin: 20px 0;
    }

    .trends-analysis {
      margin-top: 20px;
    }

    .trends-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }

    .trend-item {
      padding: 16px;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      text-align: center;
    }

    .trend-period {
      font-size: 14px;
      color: #666;
      margin-bottom: 8px;
    }

    .trend-amount {
      font-size: 18px;
      font-weight: 600;
      margin-bottom: 8px;
    }

    .trend-change {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      font-size: 14px;
    }

    .trend-change.up {
      color: #4CAF50;
    }

    .trend-change.down {
      color: #f44336;
    }

    .trend-change.stable {
      color: #666;
    }

    .category-analysis-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }

    .category-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .category-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
    }

    .category-info h4 {
      margin: 0 0 4px 0;
      font-size: 16px;
    }

    .category-amount {
      font-size: 14px;
      color: #666;
    }

    .category-trend {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 12px;
      font-weight: 500;
    }

    .budget-summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 20px;
    }

    .budget-stat {
      display: flex;
      justify-content: space-between;
      padding: 12px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .budget-stat .label {
      font-weight: 500;
      color: #666;
    }

    .budget-stat .value {
      font-weight: 600;
    }

    .predictions-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;
      margin-top: 20px;
    }

    .prediction-card {
      min-height: 150px;
    }

    .prediction-type {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 500;
      margin-bottom: 12px;
    }

    .prediction-amount {
      font-size: 24px;
      font-weight: 600;
      margin-bottom: 8px;
    }

    .prediction-confidence, .prediction-date {
      font-size: 14px;
      color: #666;
      margin-bottom: 4px;
    }

    .anomalies-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .anomaly-item {
      display: flex;
      gap: 16px;
      padding: 20px;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      border-left: 4px solid #2196F3;
    }

    .anomaly-item.high {
      border-left-color: #f44336;
    }

    .anomaly-item.medium {
      border-left-color: #FF9800;
    }

    .anomaly-icon mat-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
    }

    .anomaly-content h4 {
      margin: 0 0 8px 0;
    }

    .anomaly-confidence {
      font-size: 14px;
      color: #666;
      margin: 8px 0;
    }

    .anomaly-actions {
      margin-top: 12px;
    }

    .no-anomalies {
      text-align: center;
      padding: 40px;
      color: #666;
    }

    .no-anomalies mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #4CAF50;
      margin-bottom: 16px;
    }

    .recommendations-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
      gap: 20px;
    }

    .recommendation-card {
      min-height: 200px;
    }

    .recommendation-avatar {
      background-color: #2196F3;
      color: white;
    }

    .recommendation-card.easy .recommendation-avatar {
      background-color: #4CAF50;
    }

    .recommendation-card.moderate .recommendation-avatar {
      background-color: #FF9800;
    }

    .recommendation-card.difficult .recommendation-avatar {
      background-color: #f44336;
    }

    .recommendation-actions h5 {
      margin: 16px 0 8px 0;
    }

    .recommendation-actions ul {
      list-style: none;
      padding: 0;
      margin: 0;
    }

    .recommendation-actions li {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      padding: 8px;
      background: #f5f5f5;
      border-radius: 4px;
    }

    .action-priority {
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 10px;
      font-weight: 500;
    }

    .action-priority.high {
      background: #FFEBEE;
      color: #f44336;
    }

    .action-priority.medium {
      background: #FFF8E1;
      color: #FF9800;
    }

    .action-priority.low {
      background: #E8F5E8;
      color: #4CAF50;
    }

    .action-time {
      font-size: 12px;
      color: #666;
      margin-left: auto;
    }

    @media (max-width: 768px) {
      .header {
        flex-direction: column;
        align-items: stretch;
      }

      .filters form {
        justify-content: center;
      }

      .category-analysis-grid {
        grid-template-columns: 1fr;
      }

      .summary-cards {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class AnalyticsComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  filtersForm!: FormGroup;
  activeTab = 0;
  
  // Chart references
  private spendingChart?: Chart;
  private categoryChart?: Chart;
  private budgetChart?: Chart;
  private predictionsChart?: Chart;

  // Data
  summaryData = {
    totalIncome: 0,
    totalExpenses: 0,
    netSavings: 0,
    budgetUtilization: 0,
    incomeChange: 0,
    expensesChange: 0,
    savingsChange: 0
  };

  spendingTrends: SpendingTrend[] = [];
  categoryInsights: CategoryInsight[] = [];
  budgetAnalysis: BudgetAnalysis | null = null;
  predictions: FinancialPrediction[] = [];
  anomalies: TransactionAnomaly[] = [];
  recommendations: FinancialRecommendation[] = [];

  // Observables
  loading$ = this.analyticsService.loading$;

  constructor(
    private fb: FormBuilder,
    private analyticsService: AnalyticsService,
    private accountService: AccountService,
    private categoryService: CategoryService
  ) {
    this.initializeForm();
  }

  ngOnInit(): void {
    this.loadAnalyticsData();
    this.subscribeToFilters();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.destroyCharts();
  }

  private initializeForm(): void {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(endDate.getMonth() - 6);

    this.filtersForm = this.fb.group({
      startDate: [startDate],
      endDate: [endDate],
      groupBy: ['month']
    });
  }

  private subscribeToFilters(): void {
    this.filtersForm.valueChanges.pipe(
      takeUntil(this.destroy$),
      debounceTime(500),
      distinctUntilChanged()
    ).subscribe(() => {
      this.updateFilters();
    });
  }

  private updateFilters(): void {
    const formValue = this.filtersForm.value;
    const filters: AnalyticsFilters = {
      dateRange: {
        startDate: formValue.startDate.toISOString().split('T')[0],
        endDate: formValue.endDate.toISOString().split('T')[0]
      },
      groupBy: formValue.groupBy
    };

    this.analyticsService.updateFilters(filters);
  }

  applyFilters(): void {
    this.updateFilters();
    this.loadAnalyticsData();
  }

  private loadAnalyticsData(): void {
    // Load insights
    this.analyticsService.insights$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(insights => {
      if (insights) {
        this.processInsights(insights);
        this.updateCharts();
      }
    });

    // Load specific data
    this.loadSpendingTrends();
    this.loadCategoryInsights();
    this.loadBudgetAnalysis();
    this.loadPredictions();
    this.loadAnomalies();
    this.loadRecommendations();
  }

  private loadSpendingTrends(): void {
    this.analyticsService.getSpendingTrends().pipe(
      takeUntil(this.destroy$)
    ).subscribe(trends => {
      this.spendingTrends = trends;
      this.updateSpendingChart();
    });
  }

  private loadCategoryInsights(): void {
    this.analyticsService.getCategoryInsights().pipe(
      takeUntil(this.destroy$)
    ).subscribe(insights => {
      this.categoryInsights = insights;
      this.updateCategoryChart();
    });
  }

  private loadBudgetAnalysis(): void {
    this.analyticsService.getBudgetAnalysis().pipe(
      takeUntil(this.destroy$)
    ).subscribe(analysis => {
      this.budgetAnalysis = analysis;
      this.updateBudgetChart();
    });
  }

  private loadPredictions(): void {
    this.analyticsService.getFinancialPredictions().pipe(
      takeUntil(this.destroy$)
    ).subscribe(predictions => {
      this.predictions = predictions;
      this.updatePredictionsChart();
    });
  }

  private loadAnomalies(): void {
    this.analyticsService.getTransactionAnomalies().pipe(
      takeUntil(this.destroy$)
    ).subscribe(anomalies => {
      this.anomalies = anomalies;
    });
  }

  private loadRecommendations(): void {
    this.analyticsService.getFinancialRecommendations().pipe(
      takeUntil(this.destroy$)
    ).subscribe(recommendations => {
      this.recommendations = recommendations;
    });
  }

  private processInsights(insights: FinancialInsights): void {
    // Process spending trends for summary
    if (insights.spending_trends.length >= 2) {
      const current = insights.spending_trends[insights.spending_trends.length - 1];
      const previous = insights.spending_trends[insights.spending_trends.length - 2];
      
      this.summaryData.totalIncome = current.total_income;
      this.summaryData.totalExpenses = current.total_spending;
      this.summaryData.netSavings = current.net_change;
      
      this.summaryData.incomeChange = (current.total_income - previous.total_income) / previous.total_income;
      this.summaryData.expensesChange = (current.total_spending - previous.total_spending) / previous.total_spending;
      this.summaryData.savingsChange = (current.net_change - previous.net_change) / Math.abs(previous.net_change || 1);
    }

    // Process budget analysis for summary
    if (insights.budget_analysis) {
      this.summaryData.budgetUtilization = insights.budget_analysis.utilization_percentage;
    }
  }

  private updateCharts(): void {
    setTimeout(() => {
      this.updateSpendingChart();
      this.updateCategoryChart();
      this.updateBudgetChart();
      this.updatePredictionsChart();
    }, 100);
  }

  private updateSpendingChart(): void {
    // Implementation would create Chart.js spending trends chart
  }

  private updateCategoryChart(): void {
    // Implementation would create Chart.js category breakdown chart
  }

  private updateBudgetChart(): void {
    // Implementation would create Chart.js budget utilization chart
  }

  private updatePredictionsChart(): void {
    // Implementation would create Chart.js predictions chart
  }

  private destroyCharts(): void {
    [this.spendingChart, this.categoryChart, this.budgetChart, this.predictionsChart].forEach(chart => {
      if (chart) {
        chart.destroy();
      }
    });
  }

  // Utility methods
  formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  }

  formatPercentage(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
  }

  formatDate(date: string): string {
    return new Date(date).toLocaleDateString();
  }

  formatPeriod(period: string): string {
    return period.replace('-', ' ');
  }

  getBudgetStatus(utilization: number): string {
    if (utilization <= 0.8) return 'on-track';
    if (utilization <= 1.0) return 'warning';
    return 'over-budget';
  }

  getBudgetStatusText(utilization: number): string {
    if (utilization <= 0.8) return 'On Track';
    if (utilization <= 1.0) return 'Warning';
    return 'Over Budget';
  }

  getTrendClass(direction: string): string {
    switch (direction) {
      case 'increasing': return 'up';
      case 'decreasing': return 'down';
      default: return 'stable';
    }
  }

  getTrendIcon(direction: string): string {
    switch (direction) {
      case 'increasing': return 'trending_up';
      case 'decreasing': return 'trending_down';
      default: return 'trending_flat';
    }
  }

  getPredictionIcon(type: string): string {
    const icons: { [key: string]: string } = {
      'spending_forecast': 'forecast',
      'income_forecast': 'paid',
      'budget_projection': 'account_balance',
      'savings_goal': 'savings'
    };
    return icons[type] || 'analytics';
  }

  formatPredictionType(type: string): string {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  getAnomalyIcon(type: string): string {
    const icons: { [key: string]: string } = {
      'unusual_amount': 'attach_money',
      'unusual_merchant': 'store',
      'unusual_category': 'category',
      'unusual_timing': 'schedule'
    };
    return icons[type] || 'warning';
  }

  formatAnomalyType(type: string): string {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  getAnomalySeverity(confidence: number): string {
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.6) return 'medium';
    return 'low';
  }

  getRecommendationIcon(type: string): string {
    const icons: { [key: string]: string } = {
      'savings_opportunity': 'savings',
      'budget_adjustment': 'tune',
      'category_optimization': 'optimization',
      'goal_setting': 'flag'
    };
    return icons[type] || 'lightbulb';
  }

  getAbsoluteValue(value: number): number {
    return Math.abs(value);
  }
}