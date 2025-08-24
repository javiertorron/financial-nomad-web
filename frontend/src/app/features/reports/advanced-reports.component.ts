import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatChipsModule } from '@angular/material/chips';
import { Subject, Observable, combineLatest } from 'rxjs';
import { takeUntil, debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { saveAs } from 'file-saver';

import { ReportsService } from '../../core/services/reports.service';
import { AccountService } from '../../core/services/account.service';
import { CategoryService } from '../../core/services/category.service';
import { NotificationService } from '../../core/services/notification.service';
import { 
  ReportConfiguration, 
  ReportExecution, 
  ReportParameters,
  FinancialInsights 
} from '../../core/types/enterprise.types';
// import { Account } from '../../core/types/financial.types';

@Component({
  selector: 'app-advanced-reports',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatCheckboxModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatDialogModule,
    MatSnackBarModule,
    MatChipsModule
  ],
  template: `
    <div class="advanced-reports">
      <!-- Header -->
      <div class="header">
        <h1>
          <mat-icon>assessment</mat-icon>
          Advanced Reports
        </h1>
        <div class="header-actions">
          <button mat-raised-button color="primary" (click)="generateQuickReport()">
            <mat-icon>flash_on</mat-icon>
            Quick Report
          </button>
          <button mat-raised-button color="accent" (click)="createNewReport()">
            <mat-icon>add</mat-icon>
            New Report
          </button>
        </div>
      </div>

      <mat-tab-group [(selectedIndex)]="activeTab">
        <!-- Report Builder Tab -->
        <mat-tab label="Report Builder">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Create New Report</mat-card-title>
                <mat-card-subtitle>Configure your custom financial report</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <form [formGroup]="reportForm" (ngSubmit)="onGenerateReport()">
                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Report Name</mat-label>
                      <input matInput formControlName="name" placeholder="Enter report name">
                    </mat-form-field>
                    
                    <mat-form-field appearance="outline">
                      <mat-label>Report Type</mat-label>
                      <mat-select formControlName="type">
                        <mat-option value="financial_summary">Financial Summary</mat-option>
                        <mat-option value="transaction_analysis">Transaction Analysis</mat-option>
                        <mat-option value="budget_performance">Budget Performance</mat-option>
                        <mat-option value="category_breakdown">Category Breakdown</mat-option>
                        <mat-option value="custom">Custom Report</mat-option>
                      </mat-select>
                    </mat-form-field>
                  </div>

                  <div class="form-row">
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
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Accounts</mat-label>
                      <mat-select formControlName="accounts" multiple>
                        <mat-option *ngFor="let account of accounts" [value]="account.id">
                          {{ account.name }}
                        </mat-option>
                      </mat-select>
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Categories</mat-label>
                      <mat-select formControlName="categories" multiple>
                        <mat-option *ngFor="let category of categories" [value]="category.id">
                          {{ category.name }}
                        </mat-option>
                      </mat-select>
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Format</mat-label>
                      <mat-select formControlName="format">
                        <mat-option value="pdf">PDF</mat-option>
                        <mat-option value="excel">Excel</mat-option>
                        <mat-option value="csv">CSV</mat-option>
                      </mat-select>
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
                  </div>

                  <div class="checkbox-group">
                    <mat-checkbox formControlName="includeCharts">Include Charts</mat-checkbox>
                  </div>
                </form>
              </mat-card-content>
              <mat-card-actions>
                <button 
                  mat-raised-button 
                  color="primary" 
                  (click)="onGenerateReport()"
                  [disabled]="reportForm.invalid || isGenerating">
                  <mat-icon>play_arrow</mat-icon>
                  {{ isGenerating ? 'Generating...' : 'Generate Report' }}
                </button>
                <button 
                  mat-button 
                  color="accent" 
                  (click)="saveAsTemplate()"
                  [disabled]="reportForm.invalid">
                  <mat-icon>bookmark</mat-icon>
                  Save as Template
                </button>
              </mat-card-actions>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Saved Reports Tab -->
        <mat-tab label="Saved Reports">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Report Configurations</mat-card-title>
                <mat-card-subtitle>Manage your saved report templates</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <div class="table-container">
                  <table mat-table [dataSource]="reportConfigurations" class="reports-table">
                    <ng-container matColumnDef="name">
                      <th mat-header-cell *matHeaderCellDef>Name</th>
                      <td mat-cell *matCellDef="let config">{{ config.name }}</td>
                    </ng-container>

                    <ng-container matColumnDef="type">
                      <th mat-header-cell *matHeaderCellDef>Type</th>
                      <td mat-cell *matCellDef="let config">
                        <span class="report-type">{{ formatReportType(config.type) }}</span>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="format">
                      <th mat-header-cell *matHeaderCellDef>Format</th>
                      <td mat-cell *matCellDef="let config">
                        <mat-chip-set>
                          <mat-chip>{{ config.format.toUpperCase() }}</mat-chip>
                        </mat-chip-set>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="updated">
                      <th mat-header-cell *matHeaderCellDef>Updated</th>
                      <td mat-cell *matCellDef="let config">
                        {{ config.updated_at | date:'short' }}
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="actions">
                      <th mat-header-cell *matHeaderCellDef>Actions</th>
                      <td mat-cell *matCellDef="let config">
                        <button mat-icon-button (click)="runSavedReport(config)">
                          <mat-icon>play_arrow</mat-icon>
                        </button>
                        <button mat-icon-button (click)="editReport(config)">
                          <mat-icon>edit</mat-icon>
                        </button>
                        <button mat-icon-button color="warn" (click)="deleteReport(config.id)">
                          <mat-icon>delete</mat-icon>
                        </button>
                      </td>
                    </ng-container>

                    <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
                    <tr mat-row *matRowDef="let row; columns: displayedColumns;"></tr>
                  </table>
                </div>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Execution History Tab -->
        <mat-tab label="History">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Report Execution History</mat-card-title>
                <mat-card-subtitle>View and download previously generated reports</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <div class="table-container">
                  <table mat-table [dataSource]="reportExecutions" class="executions-table">
                    <ng-container matColumnDef="report">
                      <th mat-header-cell *matHeaderCellDef>Report</th>
                      <td mat-cell *matCellDef="let execution">{{ execution.report_name || execution.id }}</td>
                    </ng-container>

                    <ng-container matColumnDef="status">
                      <th mat-header-cell *matHeaderCellDef>Status</th>
                      <td mat-cell *matCellDef="let execution">
                        <mat-chip [class]="'status-' + execution.status">
                          <mat-icon>{{ getStatusIcon(execution.status) }}</mat-icon>
                          {{ formatStatus(execution.status) }}
                        </mat-chip>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="started">
                      <th mat-header-cell *matHeaderCellDef>Started</th>
                      <td mat-cell *matCellDef="let execution">
                        {{ execution.started_at | date:'short' }}
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="duration">
                      <th mat-header-cell *matHeaderCellDef>Duration</th>
                      <td mat-cell *matCellDef="let execution">
                        <span *ngIf="execution.completed_at">
                          {{ getDuration(execution.started_at, execution.completed_at) }}
                        </span>
                        <span *ngIf="!execution.completed_at && execution.status === 'generating'">
                          <mat-spinner diameter="16"></mat-spinner>
                        </span>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="size">
                      <th mat-header-cell *matHeaderCellDef>Size</th>
                      <td mat-cell *matCellDef="let execution">
                        <span *ngIf="execution.file_size">{{ formatFileSize(execution.file_size) }}</span>
                      </td>
                    </ng-container>

                    <ng-container matColumnDef="actions">
                      <th mat-header-cell *matHeaderCellDef>Actions</th>
                      <td mat-cell *matCellDef="let execution">
                        <button 
                          mat-icon-button 
                          *ngIf="execution.status === 'completed' && execution.file_url"
                          (click)="downloadReport(execution)">
                          <mat-icon>download</mat-icon>
                        </button>
                        <button 
                          mat-icon-button 
                          color="warn" 
                          (click)="deleteExecution(execution.id)">
                          <mat-icon>delete</mat-icon>
                        </button>
                      </td>
                    </ng-container>

                    <tr mat-header-row *matHeaderRowDef="executionColumns"></tr>
                    <tr mat-row *matRowDef="let row; columns: executionColumns;"></tr>
                  </table>
                </div>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Insights Tab -->
        <mat-tab label="Insights">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Financial Insights</mat-card-title>
                <mat-card-subtitle>AI-powered financial analysis and recommendations</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <div *ngIf="financialInsights; else loadingInsights">
                  <!-- Insights content would go here -->
                  <div class="insights-grid">
                    <div class="insight-card" *ngFor="let recommendation of financialInsights.recommendations">
                      <h3>{{ recommendation.title }}</h3>
                      <p>{{ recommendation.description }}</p>
                      <div class="impact">
                        Impact: <strong>{{ formatCurrency(recommendation.potential_impact) }}</strong>
                      </div>
                    </div>
                  </div>
                </div>
                <ng-template #loadingInsights>
                  <div class="loading-container">
                    <mat-spinner></mat-spinner>
                    <p>Analyzing your financial data...</p>
                  </div>
                </ng-template>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .advanced-reports {
      padding: 20px;
      max-width: 1200px;
      margin: 0 auto;
    }

    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .header h1 {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 0;
      font-size: 28px;
      font-weight: 500;
    }

    .header-actions {
      display: flex;
      gap: 12px;
    }

    .tab-content {
      padding: 20px 0;
    }

    .form-row {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
    }

    .form-row mat-form-field {
      flex: 1;
    }

    .checkbox-group {
      margin: 20px 0;
    }

    .table-container {
      max-height: 500px;
      overflow: auto;
    }

    .reports-table, .executions-table {
      width: 100%;
    }

    .report-type {
      font-weight: 500;
      text-transform: capitalize;
    }

    .status-queued { 
      background-color: #fff3cd;
      color: #856404;
    }

    .status-generating { 
      background-color: #d1ecf1;
      color: #0c5460;
    }

    .status-completed { 
      background-color: #d4edda;
      color: #155724;
    }

    .status-failed { 
      background-color: #f8d7da;
      color: #721c24;
    }

    .insights-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;
      margin-top: 20px;
    }

    .insight-card {
      padding: 20px;
      border: 1px solid #e0e0e0;
      border-radius: 8px;
      background: #f9f9f9;
    }

    .insight-card h3 {
      margin: 0 0 10px 0;
      color: #333;
    }

    .impact {
      margin-top: 10px;
      font-size: 14px;
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 40px;
    }

    .loading-container mat-spinner {
      margin-bottom: 20px;
    }
  `]
})
export class AdvancedReportsComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  reportForm!: FormGroup;
  activeTab = 0;
  isGenerating = false;
  
  accounts: any[] = [];
  categories: any[] = [];
  reportConfigurations: ReportConfiguration[] = [];
  reportExecutions: ReportExecution[] = [];
  financialInsights: FinancialInsights | null = null;

  displayedColumns = ['name', 'type', 'format', 'updated', 'actions'];
  executionColumns = ['report', 'status', 'started', 'duration', 'size', 'actions'];

  constructor(
    private fb: FormBuilder,
    private reportsService: ReportsService,
    private accountService: AccountService,
    private categoryService: CategoryService,
    private notification: NotificationService,
    private dialog: MatDialog
  ) {
    this.initializeForm();
  }

  ngOnInit(): void {
    this.loadInitialData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private initializeForm(): void {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(endDate.getMonth() - 1);

    this.reportForm = this.fb.group({
      name: ['Monthly Report', Validators.required],
      type: ['financial_summary', Validators.required],
      startDate: [startDate, Validators.required],
      endDate: [endDate, Validators.required],
      accounts: [[]],
      categories: [[]],
      format: ['pdf', Validators.required],
      groupBy: ['month', Validators.required],
      includeCharts: [true]
    });
  }

  private loadInitialData(): void {
    // Load accounts
    this.accountService.getAccounts().pipe(
      takeUntil(this.destroy$)
    ).subscribe(accounts => {
      this.accounts = accounts;
    });

    // Load categories
    this.categoryService.getCategories().pipe(
      takeUntil(this.destroy$)
    ).subscribe(categories => {
      this.categories = categories;
    });

    // Load report configurations
    this.loadReportConfigurations();

    // Load execution history
    this.loadExecutionHistory();

    // Load financial insights
    this.loadFinancialInsights();
  }

  private loadReportConfigurations(): void {
    this.reportsService.getReportConfigurations().pipe(
      takeUntil(this.destroy$)
    ).subscribe(configs => {
      this.reportConfigurations = configs;
    });
  }

  private loadExecutionHistory(): void {
    this.reportsService.getReportExecutions().pipe(
      takeUntil(this.destroy$)
    ).subscribe(executions => {
      this.reportExecutions = executions;
    });
  }

  private loadFinancialInsights(): void {
    const params = this.buildReportParameters();
    this.reportsService.getFinancialInsights(params).pipe(
      takeUntil(this.destroy$)
    ).subscribe(insights => {
      this.financialInsights = insights;
    });
  }

  onGenerateReport(): void {
    if (this.reportForm.valid) {
      this.isGenerating = true;
      const params = this.buildReportParameters();
      const format = this.reportForm.get('format')?.value;

      this.reportsService.generateQuickReport(params, format).pipe(
        takeUntil(this.destroy$)
      ).subscribe({
        next: (execution) => {
          this.isGenerating = false;
          this.notification.showSuccess('Report generation started');
          this.reportExecutions.unshift(execution);
          this.pollReportStatus(execution.id);
        },
        error: (error) => {
          this.isGenerating = false;
          this.notification.showError('Failed to generate report');
          console.error('Report generation error:', error);
        }
      });
    }
  }

  generateQuickReport(): void {
    this.onGenerateReport();
  }

  createNewReport(): void {
    this.reportForm.reset();
    this.initializeForm();
    this.activeTab = 0;
  }

  saveAsTemplate(): void {
    if (this.reportForm.valid) {
      const formValue = this.reportForm.value;
      const config: Omit<ReportConfiguration, 'id' | 'created_at' | 'updated_at'> = {
        name: formValue.name,
        description: `Generated report: ${formValue.name}`,
        type: formValue.type,
        format: formValue.format,
        parameters: this.buildReportParameters()
      };

      this.reportsService.createReportConfiguration(config).pipe(
        takeUntil(this.destroy$)
      ).subscribe({
        next: (savedConfig) => {
          this.reportConfigurations.unshift(savedConfig);
          this.notification.showSuccess('Report template saved successfully');
        },
        error: (error) => {
          this.notification.showError('Failed to save report template');
          console.error('Save template error:', error);
        }
      });
    }
  }

  runSavedReport(config: ReportConfiguration): void {
    this.reportsService.generateReport(config.id, config.parameters).pipe(
      takeUntil(this.destroy$)
    ).subscribe({
      next: (execution) => {
        this.reportExecutions.unshift(execution);
        this.notification.showSuccess('Report generation started');
        this.pollReportStatus(execution.id);
      },
      error: (error) => {
        this.notification.showError('Failed to run report');
        console.error('Run report error:', error);
      }
    });
  }

  editReport(config: ReportConfiguration): void {
    // Populate form with config data
    this.reportForm.patchValue({
      name: config.name,
      type: config.type,
      format: config.format,
      startDate: new Date(config.parameters.date_range.start_date),
      endDate: new Date(config.parameters.date_range.end_date),
      accounts: config.parameters.accounts || [],
      categories: config.parameters.categories || [],
      groupBy: config.parameters.group_by || 'month',
      includeCharts: config.parameters.include_charts
    });
    this.activeTab = 0;
  }

  deleteReport(configId: string): void {
    if (confirm('Are you sure you want to delete this report configuration?')) {
      this.reportsService.deleteReportConfiguration(configId).pipe(
        takeUntil(this.destroy$)
      ).subscribe({
        next: () => {
          this.reportConfigurations = this.reportConfigurations.filter(c => c.id !== configId);
          this.notification.showSuccess('Report configuration deleted');
        },
        error: (error) => {
          this.notification.showError('Failed to delete report configuration');
          console.error('Delete report error:', error);
        }
      });
    }
  }

  downloadReport(execution: ReportExecution): void {
    this.reportsService.downloadReportFile(execution.id).catch(error => {
      this.notification.showError('Failed to download report');
      console.error('Download error:', error);
    });
  }

  deleteExecution(executionId: string): void {
    if (confirm('Are you sure you want to delete this report execution?')) {
      // Note: This would need to be implemented in the backend
      this.reportExecutions = this.reportExecutions.filter(e => e.id !== executionId);
      this.notification.showSuccess('Report execution deleted');
    }
  }

  private buildReportParameters(): ReportParameters {
    const formValue = this.reportForm.value;
    return {
      date_range: {
        start_date: formValue.startDate.toISOString().split('T')[0],
        end_date: formValue.endDate.toISOString().split('T')[0]
      },
      accounts: formValue.accounts.length > 0 ? formValue.accounts : undefined,
      categories: formValue.categories.length > 0 ? formValue.categories : undefined,
      include_charts: formValue.includeCharts,
      group_by: formValue.groupBy
    };
  }

  private pollReportStatus(executionId: string): void {
    const poll = () => {
      this.reportsService.getReportStatus(executionId).pipe(
        takeUntil(this.destroy$)
      ).subscribe(execution => {
        const index = this.reportExecutions.findIndex(e => e.id === executionId);
        if (index >= 0) {
          this.reportExecutions[index] = execution;
        }

        if (execution.status === 'completed') {
          this.notification.showSuccess('Report generated successfully');
        } else if (execution.status === 'failed') {
          this.notification.showError('Report generation failed');
        } else {
          // Continue polling
          setTimeout(poll, 2000);
        }
      });
    };
    
    setTimeout(poll, 1000);
  }

  // Utility methods
  formatReportType(type: string): string {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  formatStatus(status: string): string {
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  getStatusIcon(status: string): string {
    const icons: { [key: string]: string } = {
      'queued': 'schedule',
      'generating': 'sync',
      'completed': 'check_circle',
      'failed': 'error'
    };
    return icons[status] || 'help';
  }

  getDuration(start: string, end: string): string {
    const startTime = new Date(start).getTime();
    const endTime = new Date(end).getTime();
    const duration = Math.round((endTime - startTime) / 1000);
    
    if (duration < 60) return `${duration}s`;
    if (duration < 3600) return `${Math.floor(duration / 60)}m ${duration % 60}s`;
    return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`;
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  }
}