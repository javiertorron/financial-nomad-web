import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { Subject, Observable, interval } from 'rxjs';
import { takeUntil, startWith, switchMap } from 'rxjs/operators';
import { MatTableDataSource } from '@angular/material/table';

import { LayoutComponent } from '../../shared/components/layout/layout.component';
import { NotificationService } from '../../core/services/notification.service';

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'debug' | 'info' | 'warn' | 'error' | 'fatal';
  message: string;
  source: string;
  user_id?: string;
  session_id?: string;
  ip_address?: string;
  user_agent?: string;
  request_id?: string;
  endpoint?: string;
  method?: string;
  status_code?: number;
  response_time_ms?: number;
  stack_trace?: string;
  metadata?: any;
}

export interface LogSearchCriteria {
  level?: string[];
  source?: string[];
  start_date?: Date;
  end_date?: Date;
  search_query?: string;
  user_id?: string;
  limit: number;
  offset: number;
}

export interface SystemMetrics {
  cpu_usage_percent: number;
  memory_usage_percent: number;
  disk_usage_percent: number;
  network_io: {
    bytes_in: number;
    bytes_out: number;
  };
  database: {
    active_connections: number;
    slow_queries_count: number;
    avg_response_time_ms: number;
  };
  api: {
    requests_per_minute: number;
    avg_response_time_ms: number;
    error_rate_percent: number;
  };
  cache: {
    hit_rate_percent: number;
    memory_usage_mb: number;
  };
  timestamp: string;
}

export interface AlertRule {
  id: string;
  name: string;
  description: string;
  metric: string;
  operator: '>' | '<' | '=' | '>=' | '<=';
  threshold: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  enabled: boolean;
  notification_channels: string[];
  created_at: string;
  last_triggered?: string;
}

@Component({
  selector: 'app-logs-monitoring',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatSelectModule,
    MatInputModule,
    MatTableModule,
    MatPaginatorModule,
    MatSortModule,
    MatChipsModule,
    MatExpansionModule,
    MatProgressSpinnerModule,
    MatDatepickerModule,
    MatNativeDateModule,
    LayoutComponent
  ],
  template: `
    <app-layout>
      <div class="logs-monitoring">
        <header class="monitoring-header">
          <div class="header-content">
            <h1>
              <mat-icon>monitor</mat-icon>
              Logs & Monitoring
            </h1>
            <p>System logs, metrics, and monitoring dashboard</p>
          </div>
          <div class="header-actions">
            <button mat-button (click)="exportLogs()">
              <mat-icon>file_download</mat-icon>
              Export Logs
            </button>
            <button mat-raised-button color="primary" (click)="refreshData()">
              <mat-icon>refresh</mat-icon>
              Refresh
            </button>
          </div>
        </header>

        <!-- System Metrics Overview -->
        <div class="metrics-overview" *ngIf="currentMetrics">
          <mat-card class="metric-card cpu">
            <mat-card-content>
              <div class="metric-header">
                <mat-icon>memory</mat-icon>
                <span>CPU Usage</span>
              </div>
              <div class="metric-value">{{ currentMetrics.cpu_usage_percent }}%</div>
              <div class="metric-bar">
                <div class="metric-fill" [style.width.%]="currentMetrics.cpu_usage_percent"
                     [class]="getMetricClass(currentMetrics.cpu_usage_percent)"></div>
              </div>
            </mat-card-content>
          </mat-card>

          <mat-card class="metric-card memory">
            <mat-card-content>
              <div class="metric-header">
                <mat-icon>storage</mat-icon>
                <span>Memory</span>
              </div>
              <div class="metric-value">{{ currentMetrics.memory_usage_percent }}%</div>
              <div class="metric-bar">
                <div class="metric-fill" [style.width.%]="currentMetrics.memory_usage_percent"
                     [class]="getMetricClass(currentMetrics.memory_usage_percent)"></div>
              </div>
            </mat-card-content>
          </mat-card>

          <mat-card class="metric-card disk">
            <mat-card-content>
              <div class="metric-header">
                <mat-icon>hard_drive</mat-icon>
                <span>Disk Usage</span>
              </div>
              <div class="metric-value">{{ currentMetrics.disk_usage_percent }}%</div>
              <div class="metric-bar">
                <div class="metric-fill" [style.width.%]="currentMetrics.disk_usage_percent"
                     [class]="getMetricClass(currentMetrics.disk_usage_percent)"></div>
              </div>
            </mat-card-content>
          </mat-card>

          <mat-card class="metric-card api">
            <mat-card-content>
              <div class="metric-header">
                <mat-icon>api</mat-icon>
                <span>API Requests</span>
              </div>
              <div class="metric-value">{{ currentMetrics.api.requests_per_minute }}/min</div>
              <div class="metric-details">
                <span>{{ currentMetrics.api.avg_response_time_ms }}ms avg</span>
                <span [class]="getErrorRateClass(currentMetrics.api.error_rate_percent)">
                  {{ currentMetrics.api.error_rate_percent }}% errors
                </span>
              </div>
            </mat-card-content>
          </mat-card>
        </div>

        <!-- Log Search and Filters -->
        <mat-card class="search-card">
          <mat-card-header>
            <mat-card-title>Log Search</mat-card-title>
            <mat-card-subtitle>Search and filter system logs</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <form [formGroup]="searchForm" class="search-form">
              <div class="search-row">
                <mat-form-field>
                  <mat-label>Search</mat-label>
                  <input matInput formControlName="search_query" placeholder="Search logs...">
                  <mat-icon matSuffix>search</mat-icon>
                </mat-form-field>

                <mat-form-field>
                  <mat-label>Log Level</mat-label>
                  <mat-select formControlName="level" multiple>
                    <mat-option value="debug">Debug</mat-option>
                    <mat-option value="info">Info</mat-option>
                    <mat-option value="warn">Warning</mat-option>
                    <mat-option value="error">Error</mat-option>
                    <mat-option value="fatal">Fatal</mat-option>
                  </mat-select>
                </mat-form-field>

                <mat-form-field>
                  <mat-label>Source</mat-label>
                  <mat-select formControlName="source" multiple>
                    <mat-option value="api">API</mat-option>
                    <mat-option value="database">Database</mat-option>
                    <mat-option value="auth">Authentication</mat-option>
                    <mat-option value="scheduler">Scheduler</mat-option>
                    <mat-option value="integrations">Integrations</mat-option>
                    <mat-option value="system">System</mat-option>
                  </mat-select>
                </mat-form-field>
              </div>

              <div class="date-row">
                <mat-form-field>
                  <mat-label>Start Date</mat-label>
                  <input matInput [matDatepicker]="startPicker" formControlName="start_date">
                  <mat-datepicker-toggle matSuffix [for]="startPicker"></mat-datepicker-toggle>
                  <mat-datepicker #startPicker></mat-datepicker>
                </mat-form-field>

                <mat-form-field>
                  <mat-label>End Date</mat-label>
                  <input matInput [matDatepicker]="endPicker" formControlName="end_date">
                  <mat-datepicker-toggle matSuffix [for]="endPicker"></mat-datepicker-toggle>
                  <mat-datepicker #endPicker></mat-datepicker>
                </mat-form-field>

                <div class="search-actions">
                  <button mat-raised-button color="primary" (click)="searchLogs()">
                    <mat-icon>search</mat-icon>
                    Search
                  </button>
                  <button mat-button (click)="clearSearch()">
                    <mat-icon>clear</mat-icon>
                    Clear
                  </button>
                </div>
              </div>
            </form>
          </mat-card-content>
        </mat-card>

        <!-- Logs Table -->
        <mat-card class="logs-card">
          <mat-card-header>
            <mat-card-title>System Logs</mat-card-title>
            <mat-card-subtitle>{{ logs.data.length }} entries found</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <div class="table-container">
              <table mat-table [dataSource]="logs" matSort class="logs-table">
                <ng-container matColumnDef="timestamp">
                  <th mat-header-cell *matHeaderCellDef mat-sort-header>Timestamp</th>
                  <td mat-cell *matCellDef="let log">
                    <div class="timestamp-cell">
                      {{ log.timestamp | date:'short' }}
                    </div>
                  </td>
                </ng-container>

                <ng-container matColumnDef="level">
                  <th mat-header-cell *matHeaderCellDef mat-sort-header>Level</th>
                  <td mat-cell *matCellDef="let log">
                    <mat-chip [class]="'level-' + log.level">
                      {{ log.level | uppercase }}
                    </mat-chip>
                  </td>
                </ng-container>

                <ng-container matColumnDef="source">
                  <th mat-header-cell *matHeaderCellDef mat-sort-header>Source</th>
                  <td mat-cell *matCellDef="let log">
                    <span class="source-badge">{{ log.source }}</span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="message">
                  <th mat-header-cell *matHeaderCellDef>Message</th>
                  <td mat-cell *matCellDef="let log">
                    <div class="message-cell">
                      {{ log.message | slice:0:100 }}{{ log.message.length > 100 ? '...' : '' }}
                    </div>
                  </td>
                </ng-container>

                <ng-container matColumnDef="user">
                  <th mat-header-cell *matHeaderCellDef>User</th>
                  <td mat-cell *matCellDef="let log">
                    <span *ngIf="log.user_id">{{ log.user_id }}</span>
                    <span *ngIf="!log.user_id" class="system-user">System</span>
                  </td>
                </ng-container>

                <ng-container matColumnDef="actions">
                  <th mat-header-cell *matHeaderCellDef>Actions</th>
                  <td mat-cell *matCellDef="let log">
                    <button mat-icon-button (click)="viewLogDetails(log)">
                      <mat-icon>info</mat-icon>
                    </button>
                    <button mat-icon-button *ngIf="log.level === 'error' || log.level === 'fatal'"
                            (click)="createAlert(log)">
                      <mat-icon>notification_add</mat-icon>
                    </button>
                  </td>
                </ng-container>

                <tr mat-header-row *matHeaderRowDef="logColumns"></tr>
                <tr mat-row *matRowDef="let row; columns: logColumns;"
                    [class]="'log-row-' + row.level"
                    (click)="viewLogDetails(row)"></tr>
              </table>

              <mat-paginator [pageSizeOptions]="[10, 25, 50, 100]"
                           showFirstLastButtons></mat-paginator>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Alert Rules -->
        <mat-card class="alerts-card">
          <mat-card-header>
            <mat-card-title>Alert Rules</mat-card-title>
            <mat-card-subtitle>Configure monitoring alerts and notifications</mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <div class="alerts-actions">
              <button mat-raised-button color="primary" (click)="createAlertRule()">
                <mat-icon>add</mat-icon>
                Create Alert Rule
              </button>
              <button mat-button (click)="testAlerts()">
                <mat-icon>play_arrow</mat-icon>
                Test Alerts
              </button>
            </div>

            <div class="alert-rules">
              <mat-expansion-panel *ngFor="let rule of alertRules" class="alert-panel">
                <mat-expansion-panel-header>
                  <mat-panel-title>
                    <div class="rule-header">
                      <span class="rule-name">{{ rule.name }}</span>
                      <mat-chip [class]="'severity-' + rule.severity">
                        {{ rule.severity | uppercase }}
                      </mat-chip>
                      <mat-chip [class]="rule.enabled ? 'enabled' : 'disabled'">
                        {{ rule.enabled ? 'Enabled' : 'Disabled' }}
                      </mat-chip>
                    </div>
                  </mat-panel-title>
                  <mat-panel-description>
                    {{ rule.description | slice:0:50 }}{{ rule.description.length > 50 ? '...' : '' }}
                  </mat-panel-description>
                </mat-expansion-panel-header>

                <div class="rule-details">
                  <div class="rule-condition">
                    <strong>Condition:</strong> {{ rule.metric }} {{ rule.operator }} {{ rule.threshold }}
                  </div>
                  
                  <div class="rule-channels">
                    <strong>Notification Channels:</strong>
                    <mat-chip-set>
                      <mat-chip *ngFor="let channel of rule.notification_channels">
                        {{ channel }}
                      </mat-chip>
                    </mat-chip-set>
                  </div>

                  <div class="rule-status" *ngIf="rule.last_triggered">
                    <strong>Last Triggered:</strong> {{ rule.last_triggered | date:'short' }}
                  </div>

                  <div class="rule-actions">
                    <button mat-button (click)="editAlertRule(rule)">
                      <mat-icon>edit</mat-icon>
                      Edit
                    </button>
                    <button mat-button 
                            [color]="rule.enabled ? 'warn' : 'primary'"
                            (click)="toggleAlertRule(rule)">
                      <mat-icon>{{ rule.enabled ? 'pause' : 'play_arrow' }}</mat-icon>
                      {{ rule.enabled ? 'Disable' : 'Enable' }}
                    </button>
                    <button mat-button color="warn" (click)="deleteAlertRule(rule.id)">
                      <mat-icon>delete</mat-icon>
                      Delete
                    </button>
                  </div>
                </div>
              </mat-expansion-panel>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Loading Overlay -->
        <div class="loading-overlay" *ngIf="isLoading">
          <mat-spinner></mat-spinner>
          <p>Loading monitoring data...</p>
        </div>
      </div>
    </app-layout>
  `,
  styles: [`
    .logs-monitoring {
      max-width: 1400px;
      margin: 0 auto;
      padding: 20px;
    }

    .monitoring-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 30px;
      flex-wrap: wrap;
      gap: 20px;
    }

    .header-content h1 {
      display: flex;
      align-items: center;
      gap: 12px;
      margin: 0 0 8px 0;
      font-size: 28px;
      font-weight: 500;
    }

    .header-content p {
      margin: 0;
      color: #666;
      font-size: 16px;
    }

    .header-actions {
      display: flex;
      gap: 12px;
    }

    /* Metrics Overview */
    .metrics-overview {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      margin-bottom: 30px;
    }

    .metric-card {
      background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    .metric-card.cpu {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }

    .metric-card.memory {
      background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
      color: white;
    }

    .metric-card.disk {
      background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
      color: white;
    }

    .metric-card.api {
      background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
      color: white;
    }

    .metric-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
    }

    .metric-value {
      font-size: 32px;
      font-weight: 600;
      margin-bottom: 12px;
    }

    .metric-bar {
      width: 100%;
      height: 6px;
      background: rgba(255, 255, 255, 0.3);
      border-radius: 3px;
      overflow: hidden;
    }

    .metric-fill {
      height: 100%;
      border-radius: 3px;
      transition: width 0.3s ease;
    }

    .metric-fill.normal {
      background: #4CAF50;
    }

    .metric-fill.warning {
      background: #FF9800;
    }

    .metric-fill.critical {
      background: #f44336;
    }

    .metric-details {
      display: flex;
      justify-content: space-between;
      font-size: 14px;
      margin-top: 8px;
    }

    .error-rate-normal {
      color: #4CAF50;
    }

    .error-rate-warning {
      color: #FF9800;
    }

    .error-rate-critical {
      color: #f44336;
    }

    /* Search Form */
    .search-card {
      margin-bottom: 30px;
    }

    .search-form {
      padding: 16px 0;
    }

    .search-row {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap: 16px;
      margin-bottom: 16px;
    }

    .date-row {
      display: grid;
      grid-template-columns: 1fr 1fr auto;
      gap: 16px;
      align-items: end;
    }

    .search-actions {
      display: flex;
      gap: 8px;
    }

    /* Logs Table */
    .logs-card {
      margin-bottom: 30px;
    }

    .table-container {
      max-height: 600px;
      overflow: auto;
    }

    .logs-table {
      width: 100%;
    }

    .timestamp-cell {
      font-family: monospace;
      font-size: 12px;
    }

    .message-cell {
      max-width: 300px;
      word-wrap: break-word;
    }

    .source-badge {
      background: #e3f2fd;
      color: #1976d2;
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 500;
    }

    .system-user {
      font-style: italic;
      color: #666;
    }

    /* Log Level Chips */
    .level-debug {
      background-color: #e8f5e8;
      color: #2e7d32;
    }

    .level-info {
      background-color: #e3f2fd;
      color: #1976d2;
    }

    .level-warn {
      background-color: #fff8e1;
      color: #f57c00;
    }

    .level-error {
      background-color: #ffebee;
      color: #c62828;
    }

    .level-fatal {
      background-color: #f3e5f5;
      color: #7b1fa2;
    }

    /* Log Row Styling */
    .log-row-error {
      background-color: rgba(244, 67, 54, 0.05);
    }

    .log-row-fatal {
      background-color: rgba(123, 31, 162, 0.05);
    }

    /* Alert Rules */
    .alerts-card {
      margin-bottom: 30px;
    }

    .alerts-actions {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
    }

    .alert-rules {
      margin-top: 16px;
    }

    .alert-panel {
      margin-bottom: 8px;
    }

    .rule-header {
      display: flex;
      align-items: center;
      gap: 12px;
      width: 100%;
    }

    .rule-name {
      font-weight: 500;
    }

    .severity-low {
      background-color: #e8f5e8;
      color: #4caf50;
    }

    .severity-medium {
      background-color: #fff8e1;
      color: #ff9800;
    }

    .severity-high {
      background-color: #ffebee;
      color: #f44336;
    }

    .severity-critical {
      background-color: #f3e5f5;
      color: #9c27b0;
    }

    .enabled {
      background-color: #e8f5e8;
      color: #4caf50;
    }

    .disabled {
      background-color: #f5f5f5;
      color: #9e9e9e;
    }

    .rule-details {
      padding: 16px 0;
    }

    .rule-condition,
    .rule-channels,
    .rule-status {
      margin-bottom: 12px;
    }

    .rule-actions {
      display: flex;
      gap: 8px;
      margin-top: 16px;
    }

    /* Loading Overlay */
    .loading-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(255, 255, 255, 0.9);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .loading-overlay p {
      margin-top: 16px;
      color: #666;
    }

    /* Responsive Design */
    @media (max-width: 768px) {
      .logs-monitoring {
        padding: 16px;
      }

      .monitoring-header {
        flex-direction: column;
        align-items: stretch;
      }

      .metrics-overview {
        grid-template-columns: 1fr;
      }

      .search-row {
        grid-template-columns: 1fr;
      }

      .date-row {
        grid-template-columns: 1fr;
      }

      .header-actions,
      .alerts-actions,
      .search-actions,
      .rule-actions {
        flex-direction: column;
      }
    }
  `]
})
export class LogsMonitoringComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  searchForm: FormGroup;
  logs = new MatTableDataSource<LogEntry>([]);
  logColumns = ['timestamp', 'level', 'source', 'message', 'user', 'actions'];

  currentMetrics: SystemMetrics | null = null;
  alertRules: AlertRule[] = [];
  isLoading = false;

  constructor(
    private fb: FormBuilder,
    private notification: NotificationService
  ) {
    this.searchForm = this.createSearchForm();
  }

  ngOnInit(): void {
    this.loadInitialData();
    this.setupAutoRefresh();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private createSearchForm(): FormGroup {
    return this.fb.group({
      search_query: [''],
      level: [[]],
      source: [[]],
      start_date: [null],
      end_date: [null]
    });
  }

  private loadInitialData(): void {
    this.loadSystemMetrics();
    this.loadLogs();
    this.loadAlertRules();
  }

  private setupAutoRefresh(): void {
    // Refresh metrics every 30 seconds
    interval(30000).pipe(
      takeUntil(this.destroy$),
      startWith(0),
      switchMap(() => this.getSystemMetrics())
    ).subscribe(metrics => {
      this.currentMetrics = metrics;
    });
  }

  private loadSystemMetrics(): void {
    this.getSystemMetrics().subscribe(metrics => {
      this.currentMetrics = metrics;
    });
  }

  private loadLogs(): void {
    this.isLoading = true;
    this.getLogEntries().subscribe(logs => {
      this.logs.data = logs;
      this.isLoading = false;
    });
  }

  private loadAlertRules(): void {
    this.getAlertRules().subscribe(rules => {
      this.alertRules = rules;
    });
  }

  // Mock data methods - in real app these would be service calls
  private getSystemMetrics(): Observable<SystemMetrics> {
    // Mock implementation - replace with actual service call
    const mockMetrics: SystemMetrics = {
      cpu_usage_percent: Math.floor(Math.random() * 100),
      memory_usage_percent: Math.floor(Math.random() * 100),
      disk_usage_percent: Math.floor(Math.random() * 100),
      network_io: {
        bytes_in: Math.floor(Math.random() * 1000000),
        bytes_out: Math.floor(Math.random() * 1000000)
      },
      database: {
        active_connections: Math.floor(Math.random() * 50),
        slow_queries_count: Math.floor(Math.random() * 10),
        avg_response_time_ms: Math.floor(Math.random() * 100)
      },
      api: {
        requests_per_minute: Math.floor(Math.random() * 1000),
        avg_response_time_ms: Math.floor(Math.random() * 500),
        error_rate_percent: Math.random() * 5
      },
      cache: {
        hit_rate_percent: 80 + Math.random() * 20,
        memory_usage_mb: Math.floor(Math.random() * 1000)
      },
      timestamp: new Date().toISOString()
    };

    return new Observable(observer => {
      setTimeout(() => {
        observer.next(mockMetrics);
        observer.complete();
      }, 100);
    });
  }

  private getLogEntries(): Observable<LogEntry[]> {
    // Mock implementation - replace with actual service call
    const mockLogs: LogEntry[] = [
      {
        id: '1',
        timestamp: new Date().toISOString(),
        level: 'info',
        message: 'User login successful',
        source: 'auth',
        user_id: 'user123',
        ip_address: '192.168.1.1'
      },
      {
        id: '2',
        timestamp: new Date(Date.now() - 60000).toISOString(),
        level: 'error',
        message: 'Database connection timeout',
        source: 'database',
        stack_trace: 'ConnectionTimeout: Unable to connect to database after 30s'
      },
      {
        id: '3',
        timestamp: new Date(Date.now() - 120000).toISOString(),
        level: 'warn',
        message: 'High CPU usage detected',
        source: 'system'
      }
    ];

    return new Observable(observer => {
      setTimeout(() => {
        observer.next(mockLogs);
        observer.complete();
      }, 500);
    });
  }

  private getAlertRules(): Observable<AlertRule[]> {
    // Mock implementation - replace with actual service call
    const mockRules: AlertRule[] = [
      {
        id: '1',
        name: 'High CPU Usage',
        description: 'Alert when CPU usage exceeds 80%',
        metric: 'cpu_usage_percent',
        operator: '>',
        threshold: 80,
        severity: 'high',
        enabled: true,
        notification_channels: ['email', 'slack'],
        created_at: new Date().toISOString()
      },
      {
        id: '2',
        name: 'Database Errors',
        description: 'Alert on database connection failures',
        metric: 'database_errors',
        operator: '>',
        threshold: 0,
        severity: 'critical',
        enabled: true,
        notification_channels: ['email', 'sms'],
        created_at: new Date().toISOString(),
        last_triggered: new Date(Date.now() - 3600000).toISOString()
      }
    ];

    return new Observable(observer => {
      setTimeout(() => {
        observer.next(mockRules);
        observer.complete();
      }, 300);
    });
  }

  // UI Action Methods
  searchLogs(): void {
    const searchCriteria = this.searchForm.value;
    console.log('Searching logs with criteria:', searchCriteria);
    this.loadLogs(); // In real app, pass criteria to service
  }

  clearSearch(): void {
    this.searchForm.reset();
    this.loadLogs();
  }

  refreshData(): void {
    this.loadInitialData();
    this.notification.showInfo('Data refreshed');
  }

  exportLogs(): void {
    // Implementation would export current logs
    this.notification.showInfo('Exporting logs...');
  }

  viewLogDetails(log: LogEntry): void {
    // Implementation would open log details dialog
    console.log('View log details:', log);
  }

  createAlert(log: LogEntry): void {
    // Implementation would open alert creation dialog based on log
    console.log('Create alert from log:', log);
  }

  createAlertRule(): void {
    // Implementation would open alert rule creation dialog
    console.log('Create new alert rule');
  }

  editAlertRule(rule: AlertRule): void {
    // Implementation would open alert rule edit dialog
    console.log('Edit alert rule:', rule);
  }

  toggleAlertRule(rule: AlertRule): void {
    rule.enabled = !rule.enabled;
    this.notification.showInfo(`Alert rule ${rule.enabled ? 'enabled' : 'disabled'}`);
  }

  deleteAlertRule(ruleId: string): void {
    if (confirm('Are you sure you want to delete this alert rule?')) {
      this.alertRules = this.alertRules.filter(rule => rule.id !== ruleId);
      this.notification.showSuccess('Alert rule deleted');
    }
  }

  testAlerts(): void {
    this.notification.showInfo('Testing alert notifications...');
  }

  // Utility Methods
  getMetricClass(percentage: number): string {
    if (percentage < 70) return 'normal';
    if (percentage < 85) return 'warning';
    return 'critical';
  }

  getErrorRateClass(errorRate: number): string {
    if (errorRate < 1) return 'error-rate-normal';
    if (errorRate < 5) return 'error-rate-warning';
    return 'error-rate-critical';
  }
}