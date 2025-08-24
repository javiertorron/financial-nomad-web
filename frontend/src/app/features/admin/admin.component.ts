import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatBadgeModule } from '@angular/material/badge';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { LayoutComponent } from '../../shared/components/layout/layout.component';
import { WebhooksService } from '../../core/services/webhooks.service';
import { AuditService } from '../../core/services/audit.service';
import { CacheService } from '../../core/services/cache.service';
import { MigrationsService } from '../../core/services/migrations.service';
import { BackupService, BackupJob, BackupStatistics } from '../../core/services/backup.service';
import { ExportService, ExportJob, ExportStatistics } from '../../core/services/export.service';
import { 
  SystemHealth,
  WebhookConfiguration,
  AuditEvent,
  CacheStatistics,
  MigrationStatus 
} from '../../core/types/enterprise.types';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatTabsModule,
    MatTableModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatBadgeModule,
    MatProgressBarModule,
    LayoutComponent
  ],
  template: `
    <app-layout>
      <div class="admin-dashboard">
        <!-- Header -->
        <div class="header">
          <h1>
            <mat-icon>admin_panel_settings</mat-icon>
            System Administration
          </h1>
          <div class="header-actions">
            <button mat-raised-button color="primary" (click)="refreshAll()">
              <mat-icon>refresh</mat-icon>
              Refresh All
            </button>
          </div>
        </div>

        <!-- System Health Overview -->
        <div class="health-overview">
          <mat-card class="health-card" [class]="getHealthStatusClass(systemHealth?.status)">
            <mat-card-content>
              <div class="health-header">
                <mat-icon>{{ getHealthIcon(systemHealth?.status) }}</mat-icon>
                <span>System Status: {{ formatHealthStatus(systemHealth?.status) }}</span>
              </div>
              <div class="health-metrics" *ngIf="systemHealth">
                <div class="metric">
                  <span>Database:</span>
                  <mat-chip [class]="getServiceHealthClass(systemHealth.database.status)">
                    {{ systemHealth.database.status }}
                  </mat-chip>
                </div>
                <div class="metric">
                  <span>Cache:</span>
                  <mat-chip [class]="getServiceHealthClass(systemHealth.cache.status)">
                    {{ systemHealth.cache.status }}
                  </mat-chip>
                </div>
                <div class="metric">
                  <span>Response Time:</span>
                  <span>{{ systemHealth.performance_metrics.average_response_time_ms }}ms</span>
                </div>
                <div class="metric">
                  <span>Uptime:</span>
                  <span>{{ systemHealth.database.uptime_percentage }}%</span>
                </div>
              </div>
            </mat-card-content>
          </mat-card>
        </div>

        <mat-tab-group [(selectedIndex)]="activeTab">
          <!-- Webhooks Management -->
          <mat-tab label="Webhooks" [matBadge]="webhooks.length" matBadgeOverlap="false">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Webhook Management</mat-card-title>
                  <mat-card-subtitle>Configure and monitor external integrations</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <div class="actions-bar">
                    <button mat-raised-button color="primary" (click)="createWebhook()">
                      <mat-icon>add</mat-icon>
                      Add Webhook
                    </button>
                    <button mat-button (click)="testAllWebhooks()">
                      <mat-icon>play_arrow</mat-icon>
                      Test All
                    </button>
                  </div>

                  <div class="table-container">
                    <table mat-table [dataSource]="webhooks" class="webhooks-table">
                      <ng-container matColumnDef="name">
                        <th mat-header-cell *matHeaderCellDef>Name</th>
                        <td mat-cell *matCellDef="let webhook">{{ webhook.name }}</td>
                      </ng-container>

                      <ng-container matColumnDef="url">
                        <th mat-header-cell *matHeaderCellDef>URL</th>
                        <td mat-cell *matCellDef="let webhook">
                          <span class="webhook-url">{{ webhook.url }}</span>
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="events">
                        <th mat-header-cell *matHeaderCellDef>Events</th>
                        <td mat-cell *matCellDef="let webhook">
                          <mat-chip-set>
                            <mat-chip *ngFor="let event of webhook.events.slice(0, 2)">
                              {{ event.event_type }}
                            </mat-chip>
                            <mat-chip *ngIf="webhook.events.length > 2">
                              +{{ webhook.events.length - 2 }} more
                            </mat-chip>
                          </mat-chip-set>
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="status">
                        <th mat-header-cell *matHeaderCellDef>Status</th>
                        <td mat-cell *matCellDef="let webhook">
                          <mat-chip [class]="webhook.active ? 'active' : 'inactive'">
                            {{ webhook.active ? 'Active' : 'Inactive' }}
                          </mat-chip>
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="lastTriggered">
                        <th mat-header-cell *matHeaderCellDef>Last Triggered</th>
                        <td mat-cell *matCellDef="let webhook">
                          {{ webhook.last_triggered_at ? (webhook.last_triggered_at | date:'short') : 'Never' }}
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="actions">
                        <th mat-header-cell *matHeaderCellDef>Actions</th>
                        <td mat-cell *matCellDef="let webhook">
                          <button mat-icon-button (click)="testWebhook(webhook.id)">
                            <mat-icon>play_arrow</mat-icon>
                          </button>
                          <button mat-icon-button (click)="editWebhook(webhook)">
                            <mat-icon>edit</mat-icon>
                          </button>
                          <button mat-icon-button 
                                  [color]="webhook.active ? 'warn' : 'primary'"
                                  (click)="toggleWebhook(webhook)">
                            <mat-icon>{{ webhook.active ? 'pause' : 'play_arrow' }}</mat-icon>
                          </button>
                          <button mat-icon-button color="warn" (click)="deleteWebhook(webhook.id)">
                            <mat-icon>delete</mat-icon>
                          </button>
                        </td>
                      </ng-container>

                      <tr mat-header-row *matHeaderRowDef="webhookColumns"></tr>
                      <tr mat-row *matRowDef="let row; columns: webhookColumns;"></tr>
                    </table>
                  </div>
                </mat-card-content>
              </mat-card>

              <!-- Webhook Statistics -->
              <mat-card class="stats-card">
                <mat-card-header>
                  <mat-card-title>Webhook Statistics</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <div class="stats-grid" *ngIf="webhookStats">
                    <div class="stat-item">
                      <div class="stat-value">{{ webhookStats.total_webhooks }}</div>
                      <div class="stat-label">Total Webhooks</div>
                    </div>
                    <div class="stat-item">
                      <div class="stat-value">{{ webhookStats.active_webhooks }}</div>
                      <div class="stat-label">Active</div>
                    </div>
                    <div class="stat-item">
                      <div class="stat-value">{{ formatPercentage(webhookStats.success_rate) }}</div>
                      <div class="stat-label">Success Rate</div>
                    </div>
                    <div class="stat-item">
                      <div class="stat-value">{{ webhookStats.average_response_time_ms }}ms</div>
                      <div class="stat-label">Avg Response</div>
                    </div>
                  </div>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Audit & Compliance -->
          <mat-tab label="Audit" [matBadge]="recentAuditEvents.length" matBadgeOverlap="false">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Audit & Compliance</mat-card-title>
                  <mat-card-subtitle>Monitor system activities and compliance status</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <div class="actions-bar">
                    <button mat-raised-button color="primary" (click)="generateAuditReport()">
                      <mat-icon>assessment</mat-icon>
                      Generate Report
                    </button>
                    <button mat-button (click)="runComplianceCheck()">
                      <mat-icon>security</mat-icon>
                      Compliance Check
                    </button>
                  </div>

                  <!-- Compliance Status -->
                  <div class="compliance-status" *ngIf="complianceStatus">
                    <h3>Compliance Overview</h3>
                    <div class="compliance-score">
                      <mat-progress-bar mode="determinate" [value]="complianceStatus.overall_score">
                      </mat-progress-bar>
                      <span>{{ complianceStatus.overall_score }}% Compliant</span>
                    </div>
                    <div class="frameworks">
                      <div *ngFor="let framework of getComplianceFrameworks()" class="framework">
                        <span class="framework-name">{{ framework.name }}</span>
                        <mat-progress-bar mode="determinate" [value]="framework.score">
                        </mat-progress-bar>
                        <span class="framework-score">{{ framework.score }}%</span>
                      </div>
                    </div>
                  </div>

                  <!-- Recent Audit Events -->
                  <div class="audit-events">
                    <h3>Recent Events</h3>
                    <div class="table-container">
                      <table mat-table [dataSource]="recentAuditEvents" class="audit-table">
                        <ng-container matColumnDef="timestamp">
                          <th mat-header-cell *matHeaderCellDef>Time</th>
                          <td mat-cell *matCellDef="let event">
                            {{ event.timestamp | date:'short' }}
                          </td>
                        </ng-container>

                        <ng-container matColumnDef="event_type">
                          <th mat-header-cell *matHeaderCellDef>Event</th>
                          <td mat-cell *matCellDef="let event">
                            {{ formatEventType(event.event_type) }}
                          </td>
                        </ng-container>

                        <ng-container matColumnDef="user">
                          <th mat-header-cell *matHeaderCellDef>User</th>
                          <td mat-cell *matCellDef="let event">
                            {{ event.user_email || event.user_id || 'System' }}
                          </td>
                        </ng-container>

                        <ng-container matColumnDef="severity">
                          <th mat-header-cell *matHeaderCellDef>Severity</th>
                          <td mat-cell *matCellDef="let event">
                            <mat-chip [class]="'severity-' + event.severity">
                              {{ event.severity }}
                            </mat-chip>
                          </td>
                        </ng-container>

                        <ng-container matColumnDef="resource">
                          <th mat-header-cell *matHeaderCellDef>Resource</th>
                          <td mat-cell *matCellDef="let event">
                            {{ event.resource_type }}
                          </td>
                        </ng-container>

                        <tr mat-header-row *matHeaderRowDef="auditColumns"></tr>
                        <tr mat-row *matRowDef="let row; columns: auditColumns;"></tr>
                      </table>
                    </div>
                  </div>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Cache Management -->
          <mat-tab label="Cache">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Cache Management</mat-card-title>
                  <mat-card-subtitle>Monitor and manage Redis cache performance</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <div class="actions-bar">
                    <button mat-raised-button color="primary" (click)="optimizeCache()">
                      <mat-icon>tune</mat-icon>
                      Optimize
                    </button>
                    <button mat-button color="warn" (click)="flushCache()">
                      <mat-icon>clear_all</mat-icon>
                      Flush All
                    </button>
                    <button mat-button (click)="refreshCacheStats()">
                      <mat-icon>refresh</mat-icon>
                      Refresh
                    </button>
                  </div>

                  <!-- Cache Statistics -->
                  <div class="cache-stats" *ngIf="cacheStats">
                    <div class="stats-grid">
                      <div class="stat-item">
                        <div class="stat-value">{{ formatNumber(cacheStats.total_keys) }}</div>
                        <div class="stat-label">Total Keys</div>
                      </div>
                      <div class="stat-item">
                        <div class="stat-value">{{ formatBytes(cacheStats.memory_usage_mb * 1024 * 1024) }}</div>
                        <div class="stat-label">Memory Usage</div>
                      </div>
                      <div class="stat-item">
                        <div class="stat-value">{{ formatPercentage(cacheStats.hit_rate) }}</div>
                        <div class="stat-label">Hit Rate</div>
                      </div>
                      <div class="stat-item">
                        <div class="stat-value">{{ formatDuration(cacheStats.average_ttl_seconds) }}</div>
                        <div class="stat-label">Avg TTL</div>
                      </div>
                    </div>

                    <!-- Performance Metrics -->
                    <div class="performance-metrics">
                      <h3>Performance</h3>
                      <div class="metrics-row">
                        <div class="metric">
                          <span>Hit Rate:</span>
                          <mat-progress-bar mode="determinate" [value]="cacheStats.hit_rate * 100"></mat-progress-bar>
                          <span>{{ formatPercentage(cacheStats.hit_rate) }}</span>
                        </div>
                      </div>
                    </div>

                    <!-- Top Keys -->
                    <div class="top-keys" *ngIf="cacheStats.top_keys?.length">
                      <h3>Top Memory Consumers</h3>
                      <div class="keys-list">
                        <div *ngFor="let key of cacheStats.top_keys" class="key-item">
                          <div class="key-info">
                            <span class="key-name">{{ key.key }}</span>
                            <span class="key-size">{{ formatBytes(key.size_bytes) }}</span>
                          </div>
                          <div class="key-actions">
                            <button mat-icon-button (click)="viewKeyDetails(key.key)">
                              <mat-icon>info</mat-icon>
                            </button>
                            <button mat-icon-button color="warn" (click)="deleteKey(key.key)">
                              <mat-icon>delete</mat-icon>
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Database Migrations -->
          <mat-tab label="Migrations">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Database Migrations</mat-card-title>
                  <mat-card-subtitle>Manage database schema and data migrations</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <div class="actions-bar">
                    <button mat-raised-button 
                            color="primary" 
                            (click)="runPendingMigrations()"
                            [disabled]="migrationsService.isRunning$ | async">
                      <mat-icon>play_arrow</mat-icon>
                      {{ (migrationsService.isRunning$ | async) ? 'Running...' : 'Run Pending' }}
                    </button>
                    <button mat-button (click)="createMigration()">
                      <mat-icon>add</mat-icon>
                      Create Migration
                    </button>
                    <button mat-button (click)="performHealthCheck()">
                      <mat-icon>health_and_safety</mat-icon>
                      Health Check
                    </button>
                  </div>

                  <!-- Migration Status -->
                  <div class="migration-status" *ngIf="migrationStatus">
                    <div class="status-overview">
                      <div class="status-item">
                        <span class="label">Total Migrations:</span>
                        <span class="value">{{ migrationStatus.total_migrations }}</span>
                      </div>
                      <div class="status-item">
                        <span class="label">Applied:</span>
                        <span class="value">{{ migrationStatus.applied_migrations }}</span>
                      </div>
                      <div class="status-item">
                        <span class="label">Pending:</span>
                        <span class="value" [class.warning]="migrationStatus.pending_migrations > 0">
                          {{ migrationStatus.pending_migrations }}
                        </span>
                      </div>
                      <div class="status-item">
                        <span class="label">Status:</span>
                        <mat-chip [class]="'status-' + migrationStatus.status">
                          {{ migrationStatus.status.replace('_', ' ') }}
                        </mat-chip>
                      </div>
                    </div>

                    <!-- Migration Progress -->
                    <div class="migration-progress" *ngIf="migrationProgress$ | async as progress">
                      <div *ngIf="progress.status === 'running'" class="progress-info">
                        <h4>Migration in Progress</h4>
                        <mat-progress-bar mode="determinate" [value]="progress.percentage"></mat-progress-bar>
                        <div class="progress-details">
                          <span>{{ progress.completed_migrations }} of {{ progress.total_migrations }} migrations</span>
                          <span>{{ progress.percentage.toFixed(1) }}% complete</span>
                        </div>
                        <div *ngIf="progress.current_migration" class="current-migration">
                          Running: {{ progress.current_migration.name }}
                        </div>
                      </div>
                    </div>
                  </div>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Backup Management -->
          <mat-tab label="Backups" [matBadge]="backups.length" matBadgeOverlap="false">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Backup Management</mat-card-title>
                  <mat-card-subtitle>Create and manage system backups</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <div class="actions-bar">
                    <button mat-raised-button color="primary" (click)="createBackup()">
                      <mat-icon>backup</mat-icon>
                      Create Backup
                    </button>
                    <button mat-button (click)="cleanupBackups()">
                      <mat-icon>cleaning_services</mat-icon>
                      Cleanup Old
                    </button>
                    <button mat-button (click)="refreshBackups()">
                      <mat-icon>refresh</mat-icon>
                      Refresh
                    </button>
                  </div>

                  <!-- Backup Statistics -->
                  <div class="stats-grid" *ngIf="backupStats">
                    <div class="stat-item">
                      <div class="stat-value">{{ backupStats.total_backups }}</div>
                      <div class="stat-label">Total Backups</div>
                    </div>
                    <div class="stat-item">
                      <div class="stat-value">{{ backupStats.successful_backups }}</div>
                      <div class="stat-label">Successful</div>
                    </div>
                    <div class="stat-item">
                      <div class="stat-value">{{ formatBytes(backupStats.total_size_bytes) }}</div>
                      <div class="stat-label">Total Size</div>
                    </div>
                    <div class="stat-item">
                      <div class="stat-value">{{ formatDuration(backupStats.average_duration_seconds) }}</div>
                      <div class="stat-label">Avg Duration</div>
                    </div>
                  </div>

                  <!-- Backup List -->
                  <div class="table-container">
                    <table mat-table [dataSource]="backups" class="backups-table">
                      <ng-container matColumnDef="name">
                        <th mat-header-cell *matHeaderCellDef>Name</th>
                        <td mat-cell *matCellDef="let backup">
                          <div class="backup-info">
                            <mat-icon>{{ backupService.getBackupTypeIcon(backup.backup_type) }}</mat-icon>
                            <span>{{ backup.name }}</span>
                          </div>
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="type">
                        <th mat-header-cell *matHeaderCellDef>Type</th>
                        <td mat-cell *matCellDef="let backup">
                          <mat-chip>{{ backup.backup_type }}</mat-chip>
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="status">
                        <th mat-header-cell *matHeaderCellDef>Status</th>
                        <td mat-cell *matCellDef="let backup">
                          <div class="status-cell">
                            <mat-icon [style.color]="backupService.getStatusColor(backup.status)">
                              {{ backupService.getStatusIcon(backup.status) }}
                            </mat-icon>
                            <span>{{ backup.status }}</span>
                            <mat-progress-bar 
                              *ngIf="backup.status === 'running' && backup.progress_percentage"
                              mode="determinate" 
                              [value]="backup.progress_percentage">
                            </mat-progress-bar>
                          </div>
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="size">
                        <th mat-header-cell *matHeaderCellDef>Size</th>
                        <td mat-cell *matCellDef="let backup">
                          {{ backup.file_size_bytes ? formatBytes(backup.file_size_bytes) : '-' }}
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="created">
                        <th mat-header-cell *matHeaderCellDef>Created</th>
                        <td mat-cell *matCellDef="let backup">
                          {{ backup.created_at | date:'short' }}
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="actions">
                        <th mat-header-cell *matHeaderCellDef>Actions</th>
                        <td mat-cell *matCellDef="let backup">
                          <button mat-icon-button 
                                  *ngIf="backupService.canStartBackup(backup)"
                                  (click)="startBackup(backup.id)">
                            <mat-icon>play_arrow</mat-icon>
                          </button>
                          <button mat-icon-button 
                                  color="warn"
                                  *ngIf="backupService.canCancelBackup(backup)"
                                  (click)="cancelBackup(backup.id)">
                            <mat-icon>stop</mat-icon>
                          </button>
                          <button mat-icon-button 
                                  *ngIf="backup.status === 'completed' && backup.file_path"
                                  (click)="downloadBackup(backup.id)">
                            <mat-icon>download</mat-icon>
                          </button>
                          <button mat-icon-button color="warn" (click)="deleteBackup(backup.id)">
                            <mat-icon>delete</mat-icon>
                          </button>
                        </td>
                      </ng-container>

                      <tr mat-header-row *matHeaderRowDef="backupColumns"></tr>
                      <tr mat-row *matRowDef="let row; columns: backupColumns;"></tr>
                    </table>
                  </div>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Export Management -->
          <mat-tab label="Exports" [matBadge]="exports.length" matBadgeOverlap="false">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Data Export Management</mat-card-title>
                  <mat-card-subtitle>Export financial data in various formats</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <div class="actions-bar">
                    <button mat-raised-button color="primary" (click)="createExport()">
                      <mat-icon>file_download</mat-icon>
                      Create Export
                    </button>
                    <button mat-button (click)="quickExport()">
                      <mat-icon>flash_on</mat-icon>
                      Quick Export
                    </button>
                    <button mat-button (click)="manageTemplates()">
                      <mat-icon>template</mat-icon>
                      Templates
                    </button>
                    <button mat-button (click)="cleanupExports()">
                      <mat-icon>cleaning_services</mat-icon>
                      Cleanup
                    </button>
                  </div>

                  <!-- Export Statistics -->
                  <div class="stats-grid" *ngIf="exportStats">
                    <div class="stat-item">
                      <div class="stat-value">{{ exportStats.total_exports }}</div>
                      <div class="stat-label">Total Exports</div>
                    </div>
                    <div class="stat-item">
                      <div class="stat-value">{{ exportStats.successful_exports }}</div>
                      <div class="stat-label">Successful</div>
                    </div>
                    <div class="stat-item">
                      <div class="stat-value">{{ exportStats.most_popular_format?.toUpperCase() }}</div>
                      <div class="stat-label">Popular Format</div>
                    </div>
                    <div class="stat-item">
                      <div class="stat-value">{{ formatDuration(exportStats.avg_processing_time_seconds) }}</div>
                      <div class="stat-label">Avg Processing</div>
                    </div>
                  </div>

                  <!-- Export List -->
                  <div class="table-container">
                    <table mat-table [dataSource]="exports" class="exports-table">
                      <ng-container matColumnDef="name">
                        <th mat-header-cell *matHeaderCellDef>Name</th>
                        <td mat-cell *matCellDef="let exportJob">
                          <div class="export-info">
                            <mat-icon>{{ exportService.getExportTypeIcon(exportJob.export_type) }}</mat-icon>
                            <div class="export-details">
                              <span class="export-name">{{ exportJob.name }}</span>
                              <span class="export-format">{{ exportJob.format.toUpperCase() }}</span>
                            </div>
                          </div>
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="type">
                        <th mat-header-cell *matHeaderCellDef>Type</th>
                        <td mat-cell *matCellDef="let exportJob">
                          <mat-chip>{{ exportJob.export_type }}</mat-chip>
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="status">
                        <th mat-header-cell *matHeaderCellDef>Status</th>
                        <td mat-cell *matCellDef="let exportJob">
                          <div class="status-cell">
                            <mat-icon [style.color]="exportService.getStatusColor(exportJob.status)">
                              {{ exportService.getStatusIcon(exportJob.status) }}
                            </mat-icon>
                            <span>{{ exportJob.status }}</span>
                            <mat-progress-bar 
                              *ngIf="exportJob.status === 'running' && exportJob.progress_percentage"
                              mode="determinate" 
                              [value]="exportJob.progress_percentage">
                            </mat-progress-bar>
                          </div>
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="size">
                        <th mat-header-cell *matHeaderCellDef>Size / Rows</th>
                        <td mat-cell *matCellDef="let exportJob">
                          <div class="size-info">
                            <div *ngIf="exportJob.file_size_bytes">{{ formatBytes(exportJob.file_size_bytes) }}</div>
                            <div *ngIf="exportJob.row_count" class="row-count">{{ formatNumber(exportJob.row_count) }} rows</div>
                          </div>
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="created">
                        <th mat-header-cell *matHeaderCellDef>Created</th>
                        <td mat-cell *matCellDef="let exportJob">
                          {{ exportJob.created_at | date:'short' }}
                        </td>
                      </ng-container>

                      <ng-container matColumnDef="actions">
                        <th mat-header-cell *matHeaderCellDef>Actions</th>
                        <td mat-cell *matCellDef="let exportJob">
                          <button mat-icon-button 
                                  *ngIf="exportService.canStartExport(exportJob)"
                                  (click)="startExport(exportJob.id)">
                            <mat-icon>play_arrow</mat-icon>
                          </button>
                          <button mat-icon-button 
                                  color="warn"
                                  *ngIf="exportService.canCancelExport(exportJob)"
                                  (click)="cancelExport(exportJob.id)">
                            <mat-icon>stop</mat-icon>
                          </button>
                          <button mat-icon-button 
                                  *ngIf="exportService.canDownloadExport(exportJob)"
                                  (click)="downloadExport(exportJob.id)">
                            <mat-icon>download</mat-icon>
                          </button>
                          <button mat-icon-button 
                                  *ngIf="exportJob.status === 'completed'"
                                  (click)="previewExport(exportJob.id)">
                            <mat-icon>preview</mat-icon>
                          </button>
                          <button mat-icon-button color="warn" (click)="deleteExport(exportJob.id)">
                            <mat-icon>delete</mat-icon>
                          </button>
                        </td>
                      </ng-container>

                      <tr mat-header-row *matHeaderRowDef="exportColumns"></tr>
                      <tr mat-row *matRowDef="let row; columns: exportColumns;"></tr>
                    </table>
                  </div>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>
        </mat-tab-group>
      </div>
    </app-layout>
  `,
  styles: [`
    .admin-dashboard {
      padding: 20px;
      max-width: 1400px;
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

    .health-overview {
      margin-bottom: 30px;
    }

    .health-card {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }

    .health-card.healthy {
      background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
    }

    .health-card.degraded {
      background: linear-gradient(135deg, #FF9800 0%, #f57c00 100%);
    }

    .health-card.unhealthy {
      background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
    }

    .health-header {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 18px;
      font-weight: 500;
      margin-bottom: 16px;
    }

    .health-metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 16px;
    }

    .metric {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .tab-content {
      padding: 20px 0;
    }

    .actions-bar {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }

    .table-container {
      max-height: 500px;
      overflow: auto;
    }

    .webhooks-table, .audit-table, .backups-table, .exports-table {
      width: 100%;
    }

    .webhook-url {
      font-family: monospace;
      font-size: 12px;
      max-width: 200px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      display: block;
    }

    .stats-card {
      margin-top: 20px;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 20px;
    }

    .stat-item {
      text-align: center;
      padding: 16px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 600;
      color: #2196F3;
    }

    .stat-label {
      font-size: 12px;
      color: #666;
      margin-top: 4px;
    }

    .compliance-status {
      margin: 20px 0;
    }

    .compliance-score {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 20px;
    }

    .compliance-score mat-progress-bar {
      flex: 1;
      height: 8px;
    }

    .frameworks {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .framework {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .framework-name {
      min-width: 100px;
      font-weight: 500;
    }

    .framework mat-progress-bar {
      flex: 1;
      height: 6px;
    }

    .framework-score {
      min-width: 50px;
      text-align: right;
      font-weight: 500;
    }

    .audit-events {
      margin-top: 30px;
    }

    .cache-stats {
      margin: 20px 0;
    }

    .performance-metrics {
      margin: 30px 0;
    }

    .metrics-row {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .metrics-row .metric {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .metrics-row .metric mat-progress-bar {
      flex: 1;
      height: 6px;
    }

    .top-keys {
      margin: 30px 0;
    }

    .keys-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .key-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .key-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .key-name {
      font-family: monospace;
      font-size: 14px;
    }

    .key-size {
      font-size: 12px;
      color: #666;
    }

    .key-actions {
      display: flex;
      gap: 4px;
    }

    .migration-status {
      margin: 20px 0;
    }

    .status-overview {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 20px;
    }

    .status-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .status-item .label {
      font-weight: 500;
      color: #666;
    }

    .status-item .value {
      font-weight: 600;
    }

    .status-item .value.warning {
      color: #FF9800;
    }

    .migration-progress {
      margin: 20px 0;
    }

    .progress-info {
      padding: 20px;
      background: #f8f9fa;
      border-radius: 8px;
    }

    .progress-details {
      display: flex;
      justify-content: space-between;
      margin-top: 8px;
      font-size: 14px;
      color: #666;
    }

    .current-migration {
      margin-top: 12px;
      font-weight: 500;
      color: #2196F3;
    }

    /* Chip styles */
    .active {
      background-color: #E8F5E8;
      color: #4CAF50;
    }

    .inactive {
      background-color: #FFEBEE;
      color: #f44336;
    }

    .severity-low {
      background-color: #E8F5E8;
      color: #4CAF50;
    }

    .severity-medium {
      background-color: #FFF8E1;
      color: #FF9800;
    }

    .severity-high {
      background-color: #FFEBEE;
      color: #f44336;
    }

    .severity-critical {
      background-color: #F3E5F5;
      color: #9C27B0;
    }

    .status-up_to_date {
      background-color: #E8F5E8;
      color: #4CAF50;
    }

    .status-pending_migrations {
      background-color: #FFF8E1;
      color: #FF9800;
    }

    /* Backup and Export specific styles */
    .backup-info, .export-info {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .export-details {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .export-name {
      font-weight: 500;
    }

    .export-format {
      font-size: 12px;
      color: #666;
      font-weight: 600;
      text-transform: uppercase;
    }

    .status-cell {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .status-cell mat-progress-bar {
      flex: 1;
      height: 4px;
      margin-left: 8px;
    }

    .size-info {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .row-count {
      font-size: 12px;
      color: #666;
    }

    @media (max-width: 768px) {
      .header {
        flex-direction: column;
        align-items: stretch;
        gap: 16px;
      }

      .health-metrics {
        grid-template-columns: 1fr;
      }

      .stats-grid {
        grid-template-columns: repeat(2, 1fr);
      }

      .status-overview {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class AdminComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  activeTab = 0;
  
  // System Health
  systemHealth: SystemHealth | null = null;
  
  // Webhooks
  webhooks: WebhookConfiguration[] = [];
  webhookStats: any = null;
  webhookColumns = ['name', 'url', 'events', 'status', 'lastTriggered', 'actions'];
  
  // Audit
  recentAuditEvents: AuditEvent[] = [];
  complianceStatus: any = null;
  auditColumns = ['timestamp', 'event_type', 'user', 'severity', 'resource'];
  
  // Cache
  cacheStats: CacheStatistics | null = null;
  
  // Migrations
  migrationStatus: MigrationStatus | null = null;
  migrationProgress$ = this.migrationsService.progress$;
  
  // Backups
  backups: BackupJob[] = [];
  backupStats: BackupStatistics | null = null;
  backupColumns = ['name', 'type', 'status', 'size', 'created', 'actions'];
  
  // Exports
  exports: ExportJob[] = [];
  exportStats: ExportStatistics | null = null;
  exportColumns = ['name', 'type', 'status', 'size', 'created', 'actions'];

  constructor(
    private webhooksService: WebhooksService,
    private auditService: AuditService,
    private cacheService: CacheService,
    public migrationsService: MigrationsService,
    public backupService: BackupService,
    public exportService: ExportService
  ) {}

  ngOnInit(): void {
    this.loadSystemHealth();
    this.loadWebhooksData();
    this.loadAuditData();
    this.loadCacheData();
    this.loadMigrationsData();
    this.loadBackupsData();
    this.loadExportsData();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  // System Health Methods
  private loadSystemHealth(): void {
    // Mock system health data - in real implementation this would come from backend
    this.systemHealth = {
      status: 'healthy',
      database: {
        status: 'healthy',
        response_time_ms: 45,
        error_rate: 0.001,
        uptime_percentage: 99.9
      },
      cache: {
        status: 'healthy',
        response_time_ms: 2,
        error_rate: 0,
        uptime_percentage: 99.95
      },
      external_apis: {
        google: {
          status: 'healthy',
          response_time_ms: 120,
          error_rate: 0.002,
          uptime_percentage: 99.8
        }
      },
      performance_metrics: {
        cpu_usage_percent: 25,
        memory_usage_percent: 60,
        disk_usage_percent: 40,
        active_connections: 150,
        requests_per_minute: 450,
        average_response_time_ms: 85
      },
      last_checked: new Date().toISOString()
    };
  }

  // Webhooks Methods
  private loadWebhooksData(): void {
    this.webhooksService.webhooks$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(webhooks => {
      this.webhooks = webhooks;
    });

    this.webhooksService.statistics$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(stats => {
      this.webhookStats = stats;
    });
  }

  createWebhook(): void {
    // Implementation would open webhook creation dialog
    console.log('Create webhook');
  }

  editWebhook(webhook: WebhookConfiguration): void {
    // Implementation would open webhook edit dialog
    console.log('Edit webhook:', webhook);
  }

  testWebhook(webhookId: string): void {
    this.webhooksService.testWebhook(webhookId).pipe(
      takeUntil(this.destroy$)
    ).subscribe(result => {
      console.log('Webhook test result:', result);
    });
  }

  testAllWebhooks(): void {
    this.webhooks.forEach(webhook => {
      if (webhook.active) {
        this.testWebhook(webhook.id);
      }
    });
  }

  toggleWebhook(webhook: WebhookConfiguration): void {
    if (webhook.active) {
      this.webhooksService.deactivateWebhook(webhook.id).subscribe();
    } else {
      this.webhooksService.activateWebhook(webhook.id).subscribe();
    }
  }

  deleteWebhook(webhookId: string): void {
    if (confirm('Are you sure you want to delete this webhook?')) {
      this.webhooksService.deleteWebhook(webhookId).subscribe();
    }
  }

  // Audit Methods
  private loadAuditData(): void {
    this.auditService.getAuditEvents({ limit: 50 }).pipe(
      takeUntil(this.destroy$)
    ).subscribe(events => {
      this.recentAuditEvents = events;
    });

    this.auditService.complianceStatus$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(status => {
      this.complianceStatus = status;
    });
  }

  generateAuditReport(): void {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setMonth(endDate.getMonth() - 1);

    this.auditService.generateAuditReport(
      'Monthly Audit Report',
      'Automated monthly audit report',
      startDate.toISOString().split('T')[0],
      endDate.toISOString().split('T')[0]
    ).pipe(
      takeUntil(this.destroy$)
    ).subscribe(report => {
      console.log('Audit report generated:', report);
    });
  }

  runComplianceCheck(): void {
    this.auditService.runComplianceCheck().pipe(
      takeUntil(this.destroy$)
    ).subscribe(status => {
      console.log('Compliance check completed:', status);
    });
  }

  // Cache Methods
  private loadCacheData(): void {
    this.cacheService.statistics$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(stats => {
      this.cacheStats = stats;
    });
  }

  refreshCacheStats(): void {
    this.cacheService.getStatistics().subscribe();
  }

  optimizeCache(): void {
    this.cacheService.optimizeMemory().pipe(
      takeUntil(this.destroy$)
    ).subscribe(result => {
      console.log(`Freed ${result.freed_mb} MB of cache memory`);
    });
  }

  flushCache(): void {
    if (confirm('Are you sure you want to flush all cache data? This will impact performance temporarily.')) {
      this.cacheService.flushAll().pipe(
        takeUntil(this.destroy$)
      ).subscribe(() => {
        console.log('Cache flushed successfully');
      });
    }
  }

  viewKeyDetails(key: string): void {
    this.cacheService.getKeyDetails(key).pipe(
      takeUntil(this.destroy$)
    ).subscribe(details => {
      console.log('Key details:', details);
    });
  }

  deleteKey(key: string): void {
    if (confirm(`Are you sure you want to delete cache key: ${key}?`)) {
      this.cacheService.deleteKey(key).subscribe();
    }
  }

  // Migrations Methods
  private loadMigrationsData(): void {
    this.migrationsService.status$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(status => {
      this.migrationStatus = status;
    });
  }

  runPendingMigrations(): void {
    if (confirm('Are you sure you want to run all pending migrations? This action cannot be easily undone.')) {
      this.migrationsService.runMigrations({
        dry_run: false,
        force: false
      }).subscribe();
    }
  }

  createMigration(): void {
    // Implementation would open migration creation dialog
    console.log('Create migration');
  }

  performHealthCheck(): void {
    this.migrationsService.performHealthCheck().pipe(
      takeUntil(this.destroy$)
    ).subscribe(health => {
      console.log('Migration health check:', health);
    });
  }

  // Backup Methods
  private loadBackupsData(): void {
    this.backupService.backups$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(backups => {
      this.backups = backups;
    });

    this.backupService.statistics$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(stats => {
      this.backupStats = stats;
    });
  }

  createBackup(): void {
    // Implementation would open backup creation dialog
    console.log('Create backup');
  }

  startBackup(backupId: string): void {
    this.backupService.startBackup(backupId).pipe(
      takeUntil(this.destroy$)
    ).subscribe();
  }

  cancelBackup(backupId: string): void {
    if (confirm('Are you sure you want to cancel this backup?')) {
      this.backupService.cancelBackup(backupId).pipe(
        takeUntil(this.destroy$)
      ).subscribe();
    }
  }

  downloadBackup(backupId: string): void {
    this.backupService.downloadBackup(backupId).pipe(
      takeUntil(this.destroy$)
    ).subscribe(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `backup-${backupId}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    });
  }

  deleteBackup(backupId: string): void {
    if (confirm('Are you sure you want to delete this backup? This action cannot be undone.')) {
      this.backupService.deleteBackup(backupId).pipe(
        takeUntil(this.destroy$)
      ).subscribe();
    }
  }

  refreshBackups(): void {
    this.backupService.getBackups().subscribe();
  }

  cleanupBackups(): void {
    if (confirm('This will remove old backups according to retention policy. Continue?')) {
      this.backupService.cleanupOldBackups(10).pipe(
        takeUntil(this.destroy$)
      ).subscribe(result => {
        console.log(`Cleaned up ${result.deleted_count} backups`);
      });
    }
  }

  // Export Methods
  private loadExportsData(): void {
    this.exportService.exports$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(exports => {
      this.exports = exports;
    });

    this.exportService.statistics$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(stats => {
      this.exportStats = stats;
    });
  }

  createExport(): void {
    // Implementation would open export creation dialog
    console.log('Create export');
  }

  quickExport(): void {
    // Implementation would open quick export dialog
    console.log('Quick export');
  }

  manageTemplates(): void {
    // Implementation would open template management dialog
    console.log('Manage templates');
  }

  startExport(exportId: string): void {
    this.exportService.startExport(exportId).pipe(
      takeUntil(this.destroy$)
    ).subscribe();
  }

  cancelExport(exportId: string): void {
    if (confirm('Are you sure you want to cancel this export?')) {
      this.exportService.cancelExport(exportId).pipe(
        takeUntil(this.destroy$)
      ).subscribe();
    }
  }

  downloadExport(exportId: string): void {
    this.exportService.downloadExport(exportId).pipe(
      takeUntil(this.destroy$)
    ).subscribe(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `export-${exportId}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    });
  }

  previewExport(exportId: string): void {
    this.exportService.previewExport(exportId, 100).pipe(
      takeUntil(this.destroy$)
    ).subscribe(preview => {
      console.log('Export preview:', preview);
      // Implementation would open preview dialog
    });
  }

  deleteExport(exportId: string): void {
    if (confirm('Are you sure you want to delete this export?')) {
      this.exportService.deleteExport(exportId).pipe(
        takeUntil(this.destroy$)
      ).subscribe();
    }
  }

  cleanupExports(): void {
    if (confirm('This will remove expired exports. Continue?')) {
      this.exportService.cleanupExpiredExports().pipe(
        takeUntil(this.destroy$)
      ).subscribe(result => {
        console.log(`Cleaned up ${result.deleted_count} exports`);
      });
    }
  }

  // Utility Methods
  refreshAll(): void {
    this.loadSystemHealth();
    this.loadWebhooksData();
    this.loadAuditData();
    this.loadCacheData();
    this.loadMigrationsData();
    this.loadBackupsData();
    this.loadExportsData();
  }

  getHealthStatusClass(status?: string): string {
    switch (status) {
      case 'healthy': return 'healthy';
      case 'degraded': return 'degraded';
      case 'unhealthy': return 'unhealthy';
      default: return '';
    }
  }

  getHealthIcon(status?: string): string {
    switch (status) {
      case 'healthy': return 'check_circle';
      case 'degraded': return 'warning';
      case 'unhealthy': return 'error';
      default: return 'help';
    }
  }

  formatHealthStatus(status?: string): string {
    if (!status) return 'Unknown';
    return status.charAt(0).toUpperCase() + status.slice(1);
  }

  getServiceHealthClass(status: string): string {
    switch (status) {
      case 'healthy': return 'active';
      case 'degraded': return 'warning';
      case 'unhealthy': return 'inactive';
      default: return '';
    }
  }

  getComplianceFrameworks(): any[] {
    if (!this.complianceStatus?.frameworks) return [];
    
    return Object.entries(this.complianceStatus.frameworks).map(([name, data]: [string, any]) => ({
      name,
      score: data.score || 0
    }));
  }

  formatEventType(eventType: string): string {
    return eventType.split('.').map(part => 
      part.charAt(0).toUpperCase() + part.slice(1)
    ).join(' ');
  }

  formatPercentage(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
  }

  formatNumber(value: number): string {
    return new Intl.NumberFormat().format(value);
  }

  formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  formatDuration(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  }
}