import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';

import { ConfigService } from './config.service';
import { NotificationService } from './notification.service';
import {
  MigrationStatus,
  Migration,
  MigrationExecution,
  RunMigrationsRequest,
  CreateMigrationRequest
} from '../types/enterprise.types';

export interface MigrationFilters {
  migration_type?: string;
  status?: 'pending' | 'applied' | 'all';
  author?: string;
}

export interface MigrationPlan {
  migrations: Migration[];
  total_steps: number;
  estimated_duration_minutes: number;
  requires_downtime: boolean;
  dependencies_resolved: boolean;
  warnings: string[];
}

export interface MigrationProgress {
  current_migration?: Migration;
  completed_migrations: number;
  total_migrations: number;
  current_step: number;
  total_steps: number;
  percentage: number;
  status: 'idle' | 'running' | 'completed' | 'failed';
  error_message?: string;
}

@Injectable({
  providedIn: 'root'
})
export class MigrationsService {
  private readonly apiUrl = `${this.config.apiUrl}/migrations`;

  private statusSubject = new BehaviorSubject<MigrationStatus | null>(null);
  public status$ = this.statusSubject.asObservable();

  private migrationsSubject = new BehaviorSubject<Migration[]>([]);
  public migrations$ = this.migrationsSubject.asObservable();

  private executionsSubject = new BehaviorSubject<MigrationExecution[]>([]);
  public executions$ = this.executionsSubject.asObservable();

  private progressSubject = new BehaviorSubject<MigrationProgress>({
    completed_migrations: 0,
    total_migrations: 0,
    current_step: 0,
    total_steps: 0,
    percentage: 0,
    status: 'idle'
  });
  public progress$ = this.progressSubject.asObservable();

  private isRunningSubject = new BehaviorSubject<boolean>(false);
  public isRunning$ = this.isRunningSubject.asObservable();

  constructor(
    private http: HttpClient,
    private config: ConfigService,
    private notification: NotificationService
  ) {
    this.loadStatus();
    this.loadMigrations();
    this.loadExecutions();
  }

  // Migration Status
  getStatus(): Observable<MigrationStatus> {
    return this.http.get<MigrationStatus>(`${this.apiUrl}/status`)
      .pipe(
        tap(status => this.statusSubject.next(status)),
        catchError(error => {
          console.error('Error loading migration status:', error);
          this.notification.showError('Failed to load migration status');
          throw error;
        })
      );
  }

  // Migration Management
  getMigrations(filters?: MigrationFilters): Observable<Migration[]> {
    let params = new HttpParams();
    if (filters?.migration_type) params = params.set('migration_type', filters.migration_type);
    if (filters?.status) params = params.set('status', filters.status);
    if (filters?.author) params = params.set('author', filters.author);

    return this.http.get<Migration[]>(`${this.apiUrl}/list`, { params })
      .pipe(
        tap(migrations => this.migrationsSubject.next(migrations)),
        catchError(error => {
          console.error('Error loading migrations:', error);
          this.notification.showError('Failed to load migrations');
          throw error;
        })
      );
  }

  getMigration(id: string): Observable<Migration> {
    return this.http.get<Migration>(`${this.apiUrl}/${id}`)
      .pipe(
        catchError(error => {
          console.error('Error loading migration:', error);
          this.notification.showError('Failed to load migration details');
          throw error;
        })
      );
  }

  // Migration Execution
  runMigrations(request: RunMigrationsRequest): Observable<MigrationExecution[]> {
    this.isRunningSubject.next(true);
    this.updateProgress('running', 0, 0, 0, 0, 0);

    return this.http.post<MigrationExecution[]>(`${this.apiUrl}/run`, request)
      .pipe(
        tap(executions => {
          this.executionsSubject.next([...this.executionsSubject.value, ...executions]);
          this.isRunningSubject.next(false);
          this.updateProgress('completed', 100, executions.length, executions.length, 0, 0);
          
          const successCount = executions.filter(e => e.status === 'completed').length;
          const failureCount = executions.filter(e => e.status === 'failed').length;
          
          if (failureCount === 0) {
            this.notification.showSuccess(`Successfully executed ${successCount} migrations`);
          } else {
            this.notification.showWarning(`Executed ${successCount} migrations, ${failureCount} failed`);
          }
          
          this.loadStatus(); // Refresh status after execution
        }),
        catchError(error => {
          console.error('Error running migrations:', error);
          this.isRunningSubject.next(false);
          this.updateProgress('failed', 0, 0, 0, 0, 0, error.message);
          this.notification.showError('Failed to run migrations');
          throw error;
        })
      );
  }

  rollbackMigration(migrationId: string): Observable<MigrationExecution> {
    return this.http.post<MigrationExecution>(`${this.apiUrl}/${migrationId}/rollback`, {})
      .pipe(
        tap(execution => {
          this.executionsSubject.next([...this.executionsSubject.value, execution]);
          
          if (execution.status === 'completed') {
            this.notification.showSuccess('Migration rolled back successfully');
          } else {
            this.notification.showError('Migration rollback failed');
          }
          
          this.loadStatus(); // Refresh status after rollback
        }),
        catchError(error => {
          console.error('Error rolling back migration:', error);
          this.notification.showError('Failed to rollback migration');
          throw error;
        })
      );
  }

  // Migration Execution History
  getExecutions(limit = 50): Observable<MigrationExecution[]> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<MigrationExecution[]>(`${this.apiUrl}/executions`, { params })
      .pipe(
        tap(executions => this.executionsSubject.next(executions)),
        catchError(error => {
          console.error('Error loading executions:', error);
          this.notification.showError('Failed to load migration history');
          throw error;
        })
      );
  }

  getExecution(id: string): Observable<MigrationExecution> {
    return this.http.get<MigrationExecution>(`${this.apiUrl}/executions/${id}`)
      .pipe(
        catchError(error => {
          console.error('Error loading execution:', error);
          this.notification.showError('Failed to load execution details');
          throw error;
        })
      );
  }

  // Migration Creation
  createMigration(request: CreateMigrationRequest): Observable<Migration> {
    return this.http.post<Migration>(`${this.apiUrl}/create`, request)
      .pipe(
        tap(migration => {
          this.migrationsSubject.next([...this.migrationsSubject.value, migration]);
          this.notification.showSuccess(`Migration template "${migration.name}" created successfully`);
        }),
        catchError(error => {
          console.error('Error creating migration:', error);
          this.notification.showError('Failed to create migration template');
          throw error;
        })
      );
  }

  // Migration Planning
  getMigrationPlan(targetVersion?: string): Observable<MigrationPlan> {
    let params = new HttpParams();
    if (targetVersion) params = params.set('target_version', targetVersion);

    return this.http.get<MigrationPlan>(`${this.apiUrl}/plan`, { params })
      .pipe(
        catchError(error => {
          console.error('Error loading migration plan:', error);
          this.notification.showError('Failed to load migration plan');
          throw error;
        })
      );
  }

  validateMigrationPlan(targetVersion?: string): Observable<{ valid: boolean; errors: string[] }> {
    let params = new HttpParams();
    if (targetVersion) params = params.set('target_version', targetVersion);

    return this.http.get<{ valid: boolean; errors: string[] }>(`${this.apiUrl}/validate-plan`, { params });
  }

  // Data Export/Import (for migrations)
  exportData(resourceTypes: string[], format: 'json' | 'csv' = 'json'): Observable<Blob> {
    const body = { resource_types: resourceTypes, format };
    return this.http.post(`${this.apiUrl}/export-data`, body, {
      responseType: 'blob'
    }).pipe(
      catchError(error => {
        console.error('Error exporting data:', error);
        this.notification.showError('Failed to export data');
        throw error;
      })
    );
  }

  importData(file: File, options: { overwrite?: boolean; validate?: boolean } = {}): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('options', JSON.stringify(options));

    return this.http.post(`${this.apiUrl}/import-data`, formData)
      .pipe(
        tap(result => {
          this.notification.showSuccess('Data imported successfully');
        }),
        catchError(error => {
          console.error('Error importing data:', error);
          this.notification.showError('Failed to import data');
          throw error;
        })
      );
  }

  validateImportData(file: File): Observable<{ valid: boolean; errors: string[]; warnings: string[] }> {
    const formData = new FormData();
    formData.append('file', file);

    return this.http.post<{ valid: boolean; errors: string[]; warnings: string[] }>(
      `${this.apiUrl}/validate-import`, formData
    );
  }

  // Backup and Restore
  createBackup(name: string, includeData = true): Observable<{ backup_id: string; file_url: string }> {
    const body = { name, include_data: includeData };
    return this.http.post<{ backup_id: string; file_url: string }>(`${this.apiUrl}/backup`, body)
      .pipe(
        tap(() => {
          this.notification.showSuccess('Backup created successfully');
        }),
        catchError(error => {
          console.error('Error creating backup:', error);
          this.notification.showError('Failed to create backup');
          throw error;
        })
      );
  }

  restoreFromBackup(backupId: string, options: { 
    confirm_destructive?: boolean; 
    target_version?: string; 
  } = {}): Observable<MigrationExecution[]> {
    const body = { backup_id: backupId, ...options };
    return this.http.post<MigrationExecution[]>(`${this.apiUrl}/restore`, body)
      .pipe(
        tap(() => {
          this.notification.showSuccess('Restore completed successfully');
          this.loadStatus();
        }),
        catchError(error => {
          console.error('Error restoring backup:', error);
          this.notification.showError('Failed to restore backup');
          throw error;
        })
      );
  }

  getBackups(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/backups`);
  }

  deleteBackup(backupId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/backups/${backupId}`)
      .pipe(
        tap(() => {
          this.notification.showSuccess('Backup deleted successfully');
        }),
        catchError(error => {
          console.error('Error deleting backup:', error);
          this.notification.showError('Failed to delete backup');
          throw error;
        })
      );
  }

  // System Health Checks
  performHealthCheck(): Observable<{ 
    database_accessible: boolean; 
    migrations_table_exists: boolean; 
    pending_migrations: number; 
    schema_version: string;
  }> {
    return this.http.get<{
      database_accessible: boolean; 
      migrations_table_exists: boolean; 
      pending_migrations: number; 
      schema_version: string;
    }>(`${this.apiUrl}/health-check`);
  }

  repairMigrationState(): Observable<{ repaired: boolean; issues_found: string[]; issues_fixed: string[] }> {
    return this.http.post<{
      repaired: boolean; 
      issues_found: string[]; 
      issues_fixed: string[];
    }>(`${this.apiUrl}/repair`, {})
      .pipe(
        tap(result => {
          if (result.repaired) {
            this.notification.showSuccess('Migration state repaired successfully');
            this.loadStatus();
          } else {
            this.notification.showInfo('No migration issues found');
          }
        }),
        catchError(error => {
          console.error('Error repairing migration state:', error);
          this.notification.showError('Failed to repair migration state');
          throw error;
        })
      );
  }

  // Utility Methods
  private loadStatus(): void {
    this.getStatus().subscribe();
  }

  private loadMigrations(): void {
    this.getMigrations().subscribe();
  }

  private loadExecutions(): void {
    this.getExecutions().subscribe();
  }

  private updateProgress(
    status: 'idle' | 'running' | 'completed' | 'failed',
    percentage: number,
    completedMigrations: number,
    totalMigrations: number,
    currentStep: number,
    totalSteps: number,
    errorMessage?: string,
    currentMigration?: Migration
  ): void {
    this.progressSubject.next({
      status,
      percentage,
      completed_migrations: completedMigrations,
      total_migrations: totalMigrations,
      current_step: currentStep,
      total_steps: totalSteps,
      error_message: errorMessage,
      current_migration: currentMigration
    });
  }

  // Format Helpers
  formatMigrationType(type: string): string {
    const typeMap: { [key: string]: string } = {
      'schema': 'Schema',
      'data': 'Data',
      'index': 'Index',
      'cleanup': 'Cleanup',
      'performance': 'Performance',
      'security': 'Security',
      'feature': 'Feature'
    };
    return typeMap[type] || type;
  }

  formatMigrationStatus(status: string): string {
    const statusMap: { [key: string]: string } = {
      'pending': 'Pending',
      'running': 'Running',
      'completed': 'Completed',
      'failed': 'Failed',
      'rolled_back': 'Rolled Back',
      'skipped': 'Skipped'
    };
    return statusMap[status] || status;
  }

  getMigrationStatusColor(status: string): string {
    const colorMap: { [key: string]: string } = {
      'pending': '#FF9800',
      'running': '#2196F3',
      'completed': '#4CAF50',
      'failed': '#f44336',
      'rolled_back': '#9C27B0',
      'skipped': '#9E9E9E'
    };
    return colorMap[status] || '#9E9E9E';
  }

  formatDuration(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  }

  formatVersion(version: string): string {
    // Ensure version follows semantic versioning format
    const parts = version.split('.');
    if (parts.length === 3) {
      return `v${version}`;
    }
    return version;
  }

  // Validation Helpers
  validateMigrationRequest(request: RunMigrationsRequest): string[] {
    const errors: string[] = [];

    if (request.target_version) {
      const versionRegex = /^\d+\.\d+\.\d+$/;
      if (!versionRegex.test(request.target_version)) {
        errors.push('Target version must follow semantic versioning format (x.y.z)');
      }
    }

    return errors;
  }

  validateCreateMigrationRequest(request: CreateMigrationRequest): string[] {
    const errors: string[] = [];

    if (!request.name?.trim()) {
      errors.push('Migration name is required');
    } else if (request.name.length > 100) {
      errors.push('Migration name must be 100 characters or less');
    }

    if (!request.description?.trim()) {
      errors.push('Migration description is required');
    }

    if (!request.author?.trim()) {
      errors.push('Migration author is required');
    }

    const validTypes = ['schema', 'data', 'index', 'cleanup', 'performance', 'security', 'feature'];
    if (!validTypes.includes(request.migration_type)) {
      errors.push(`Migration type must be one of: ${validTypes.join(', ')}`);
    }

    return errors;
  }

  // Safety Checks
  requiresConfirmation(operation: 'run' | 'rollback' | 'restore' | 'repair'): boolean {
    return ['rollback', 'restore', 'repair'].includes(operation);
  }

  getOperationWarning(operation: 'run' | 'rollback' | 'restore' | 'repair'): string {
    const warnings: { [key: string]: string } = {
      'run': 'Running migrations will modify your database schema and/or data. This action cannot be easily undone.',
      'rollback': 'Rolling back a migration may result in data loss. Ensure you have a backup before proceeding.',
      'restore': 'Restoring from backup will overwrite existing data. This action is destructive and cannot be undone.',
      'repair': 'Repairing migration state will modify migration tracking tables. Only proceed if you understand the implications.'
    };
    return warnings[operation] || '';
  }

  // Real-time Updates (would integrate with WebSocket/SSE)
  subscribeToMigrationProgress(): Observable<MigrationProgress> {
    // This would connect to real-time updates from the backend
    // For now, return the current progress subject
    return this.progress$;
  }
}