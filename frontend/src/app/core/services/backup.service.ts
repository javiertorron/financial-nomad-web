import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { map, tap } from 'rxjs/operators';

import { ConfigService } from './config.service';
import { NotificationService } from './notification.service';

export interface BackupJob {
  id: string;
  name: string;
  description?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  backup_type: 'full' | 'incremental' | 'custom';
  include_data: boolean;
  include_schema: boolean;
  include_config: boolean;
  compression_enabled: boolean;
  encryption_enabled: boolean;
  destination: 'local' | 'gcs' | 'drive';
  schedule?: {
    enabled: boolean;
    cron_expression: string;
    next_run?: string;
  };
  created_at: string;
  started_at?: string;
  completed_at?: string;
  file_path?: string;
  file_size_bytes?: number;
  error_message?: string;
  progress_percentage?: number;
}

export interface BackupStatistics {
  total_backups: number;
  successful_backups: number;
  failed_backups: number;
  total_size_bytes: number;
  average_duration_seconds: number;
  last_backup_at?: string;
  next_scheduled_backup?: string;
}

export interface BackupCreateRequest {
  name: string;
  description?: string;
  backup_type: 'full' | 'incremental' | 'custom';
  include_data: boolean;
  include_schema: boolean;
  include_config: boolean;
  compression_enabled?: boolean;
  encryption_enabled?: boolean;
  destination?: 'local' | 'gcs' | 'drive';
  schedule?: {
    enabled: boolean;
    cron_expression: string;
  };
  custom_resources?: string[];
}

export interface RestoreRequest {
  backup_id: string;
  target_environment?: 'current' | 'new';
  restore_data: boolean;
  restore_schema: boolean;
  restore_config: boolean;
  overwrite_existing: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class BackupService {
  private readonly apiUrl = `${this.config.apiUrl}/backups`;

  private backupsSubject = new BehaviorSubject<BackupJob[]>([]);
  public backups$ = this.backupsSubject.asObservable();

  private statisticsSubject = new BehaviorSubject<BackupStatistics | null>(null);
  public statistics$ = this.statisticsSubject.asObservable();

  private isLoadingSubject = new BehaviorSubject<boolean>(false);
  public isLoading$ = this.isLoadingSubject.asObservable();

  constructor(
    private http: HttpClient,
    private config: ConfigService,
    private notification: NotificationService
  ) {
    this.loadBackups();
    this.loadStatistics();
  }

  // Backup Management
  getBackups(): Observable<BackupJob[]> {
    this.isLoadingSubject.next(true);
    return this.http.get<BackupJob[]>(`${this.apiUrl}`)
      .pipe(
        tap(backups => {
          this.backupsSubject.next(backups);
          this.isLoadingSubject.next(false);
        })
      );
  }

  getBackup(backupId: string): Observable<BackupJob> {
    return this.http.get<BackupJob>(`${this.apiUrl}/${backupId}`);
  }

  createBackup(request: BackupCreateRequest): Observable<BackupJob> {
    return this.http.post<BackupJob>(`${this.apiUrl}`, request)
      .pipe(
        tap(backup => {
          const current = this.backupsSubject.value;
          this.backupsSubject.next([backup, ...current]);
          this.notification.showSuccess('Backup job created successfully');
        })
      );
  }

  deleteBackup(backupId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${backupId}`)
      .pipe(
        tap(() => {
          const current = this.backupsSubject.value;
          this.backupsSubject.next(current.filter(b => b.id !== backupId));
          this.notification.showSuccess('Backup deleted successfully');
        })
      );
  }

  // Backup Operations
  startBackup(backupId: string): Observable<BackupJob> {
    return this.http.post<BackupJob>(`${this.apiUrl}/${backupId}/start`, {})
      .pipe(
        tap(() => {
          this.notification.showInfo('Backup started');
          this.refreshBackup(backupId);
        })
      );
  }

  cancelBackup(backupId: string): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/${backupId}/cancel`, {})
      .pipe(
        tap(() => {
          this.notification.showInfo('Backup cancelled');
          this.refreshBackup(backupId);
        })
      );
  }

  downloadBackup(backupId: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/${backupId}/download`, {
      responseType: 'blob'
    });
  }

  // Restore Operations
  restoreBackup(request: RestoreRequest): Observable<any> {
    return this.http.post(`${this.apiUrl}/restore`, request)
      .pipe(
        tap(() => {
          this.notification.showWarning('Restore operation started. Please monitor the progress.');
        })
      );
  }

  validateBackup(backupId: string): Observable<{ valid: boolean; errors: string[] }> {
    return this.http.post<{ valid: boolean; errors: string[] }>(`${this.apiUrl}/${backupId}/validate`, {});
  }

  // Schedule Management
  updateSchedule(backupId: string, schedule: { enabled: boolean; cron_expression: string }): Observable<BackupJob> {
    return this.http.patch<BackupJob>(`${this.apiUrl}/${backupId}/schedule`, { schedule })
      .pipe(
        tap(() => {
          this.notification.showSuccess('Backup schedule updated');
          this.refreshBackup(backupId);
        })
      );
  }

  testSchedule(cronExpression: string): Observable<{ next_runs: string[]; valid: boolean; error?: string }> {
    return this.http.post<{ next_runs: string[]; valid: boolean; error?: string }>(`${this.apiUrl}/test-schedule`, {
      cron_expression: cronExpression
    });
  }

  // Statistics and Monitoring
  getStatistics(): Observable<BackupStatistics> {
    return this.http.get<BackupStatistics>(`${this.apiUrl}/statistics`)
      .pipe(
        tap(stats => this.statisticsSubject.next(stats))
      );
  }

  getBackupProgress(backupId: string): Observable<{ percentage: number; status: string; message?: string }> {
    return this.http.get<{ percentage: number; status: string; message?: string }>(`${this.apiUrl}/${backupId}/progress`);
  }

  // Storage Management
  getStorageInfo(): Observable<{
    total_space_bytes: number;
    used_space_bytes: number;
    available_space_bytes: number;
    backup_count: number;
  }> {
    return this.http.get<{
      total_space_bytes: number;
      used_space_bytes: number;
      available_space_bytes: number;
      backup_count: number;
    }>(`${this.apiUrl}/storage`);
  }

  cleanupOldBackups(keepCount: number): Observable<{ deleted_count: number; freed_bytes: number }> {
    const params = new HttpParams().set('keep_count', keepCount.toString());
    return this.http.delete<{ deleted_count: number; freed_bytes: number }>(`${this.apiUrl}/cleanup`, { params })
      .pipe(
        tap(result => {
          this.notification.showSuccess(`Cleaned up ${result.deleted_count} old backups`);
          this.loadBackups();
        })
      );
  }

  // Configuration
  getBackupConfig(): Observable<{
    default_destination: string;
    compression_enabled: boolean;
    encryption_enabled: boolean;
    retention_days: number;
    max_backup_size_mb: number;
  }> {
    return this.http.get<{
      default_destination: string;
      compression_enabled: boolean;
      encryption_enabled: boolean;
      retention_days: number;
      max_backup_size_mb: number;
    }>(`${this.apiUrl}/config`);
  }

  updateBackupConfig(config: {
    default_destination?: string;
    compression_enabled?: boolean;
    encryption_enabled?: boolean;
    retention_days?: number;
    max_backup_size_mb?: number;
  }): Observable<void> {
    return this.http.patch<void>(`${this.apiUrl}/config`, config)
      .pipe(
        tap(() => {
          this.notification.showSuccess('Backup configuration updated');
        })
      );
  }

  // Utility Methods
  private loadBackups(): void {
    this.getBackups().subscribe();
  }

  private loadStatistics(): void {
    this.getStatistics().subscribe();
  }

  private refreshBackup(backupId: string): void {
    setTimeout(() => {
      this.getBackup(backupId).subscribe(backup => {
        const current = this.backupsSubject.value;
        const index = current.findIndex(b => b.id === backupId);
        if (index !== -1) {
          current[index] = backup;
          this.backupsSubject.next([...current]);
        }
      });
    }, 1000);
  }

  // Helper Methods
  formatBackupSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  formatDuration(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
  }

  getBackupTypeIcon(type: string): string {
    const icons: { [key: string]: string } = {
      'full': 'backup',
      'incremental': 'update',
      'custom': 'build'
    };
    return icons[type] || 'storage';
  }

  getStatusIcon(status: string): string {
    const icons: { [key: string]: string } = {
      'pending': 'schedule',
      'running': 'sync',
      'completed': 'check_circle',
      'failed': 'error'
    };
    return icons[status] || 'help';
  }

  getStatusColor(status: string): string {
    const colors: { [key: string]: string } = {
      'pending': '#FF9800',
      'running': '#2196F3',
      'completed': '#4CAF50',
      'failed': '#f44336'
    };
    return colors[status] || '#9E9E9E';
  }

  isBackupRunning(backup: BackupJob): boolean {
    return backup.status === 'running';
  }

  canStartBackup(backup: BackupJob): boolean {
    return backup.status === 'pending' || backup.status === 'failed';
  }

  canCancelBackup(backup: BackupJob): boolean {
    return backup.status === 'running';
  }
}