import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { map, tap } from 'rxjs/operators';

import { ConfigService } from './config.service';
import { NotificationService } from './notification.service';

export interface ExportJob {
  id: string;
  name: string;
  description?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  export_type: 'transactions' | 'categories' | 'accounts' | 'full_backup' | 'custom';
  format: 'csv' | 'excel' | 'json' | 'pdf';
  filters: {
    start_date?: string;
    end_date?: string;
    categories?: string[];
    accounts?: string[];
    transaction_types?: string[];
    min_amount?: number;
    max_amount?: number;
  };
  options: {
    include_metadata: boolean;
    include_attachments: boolean;
    group_by_category: boolean;
    group_by_month: boolean;
    calculate_totals: boolean;
    apply_currency_conversion: boolean;
  };
  created_at: string;
  started_at?: string;
  completed_at?: string;
  file_path?: string;
  file_size_bytes?: number;
  error_message?: string;
  progress_percentage?: number;
  row_count?: number;
  download_count: number;
  expires_at?: string;
}

export interface ExportStatistics {
  total_exports: number;
  successful_exports: number;
  failed_exports: number;
  total_size_bytes: number;
  most_popular_format: string;
  most_popular_type: string;
  avg_processing_time_seconds: number;
  exports_by_format: { [format: string]: number };
  exports_by_type: { [type: string]: number };
}

export interface ExportCreateRequest {
  name: string;
  description?: string;
  export_type: 'transactions' | 'categories' | 'accounts' | 'full_backup' | 'custom';
  format: 'csv' | 'excel' | 'json' | 'pdf';
  filters?: {
    start_date?: string;
    end_date?: string;
    categories?: string[];
    accounts?: string[];
    transaction_types?: string[];
    min_amount?: number;
    max_amount?: number;
  };
  options?: {
    include_metadata?: boolean;
    include_attachments?: boolean;
    group_by_category?: boolean;
    group_by_month?: boolean;
    calculate_totals?: boolean;
    apply_currency_conversion?: boolean;
  };
  custom_query?: string;
  schedule?: {
    enabled: boolean;
    cron_expression: string;
    email_recipients?: string[];
  };
}

export interface ExportTemplate {
  id: string;
  name: string;
  description?: string;
  export_type: string;
  format: string;
  filters: any;
  options: any;
  is_default: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
}

@Injectable({
  providedIn: 'root'
})
export class ExportService {
  private readonly apiUrl = `${this.config.apiUrl}/exports`;

  private exportsSubject = new BehaviorSubject<ExportJob[]>([]);
  public exports$ = this.exportsSubject.asObservable();

  private templatesSubject = new BehaviorSubject<ExportTemplate[]>([]);
  public templates$ = this.templatesSubject.asObservable();

  private statisticsSubject = new BehaviorSubject<ExportStatistics | null>(null);
  public statistics$ = this.statisticsSubject.asObservable();

  private isLoadingSubject = new BehaviorSubject<boolean>(false);
  public isLoading$ = this.isLoadingSubject.asObservable();

  constructor(
    private http: HttpClient,
    private config: ConfigService,
    private notification: NotificationService
  ) {
    this.loadExports();
    this.loadTemplates();
    this.loadStatistics();
  }

  // Export Management
  getExports(): Observable<ExportJob[]> {
    this.isLoadingSubject.next(true);
    return this.http.get<ExportJob[]>(`${this.apiUrl}`)
      .pipe(
        tap(exports => {
          this.exportsSubject.next(exports);
          this.isLoadingSubject.next(false);
        })
      );
  }

  getExport(exportId: string): Observable<ExportJob> {
    return this.http.get<ExportJob>(`${this.apiUrl}/${exportId}`);
  }

  createExport(request: ExportCreateRequest): Observable<ExportJob> {
    return this.http.post<ExportJob>(`${this.apiUrl}`, request)
      .pipe(
        tap(exportJob => {
          const current = this.exportsSubject.value;
          this.exportsSubject.next([exportJob, ...current]);
          this.notification.showSuccess('Export job created successfully');
        })
      );
  }

  deleteExport(exportId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${exportId}`)
      .pipe(
        tap(() => {
          const current = this.exportsSubject.value;
          this.exportsSubject.next(current.filter(e => e.id !== exportId));
          this.notification.showSuccess('Export deleted successfully');
        })
      );
  }

  // Export Operations
  startExport(exportId: string): Observable<ExportJob> {
    return this.http.post<ExportJob>(`${this.apiUrl}/${exportId}/start`, {})
      .pipe(
        tap(() => {
          this.notification.showInfo('Export started');
          this.refreshExport(exportId);
        })
      );
  }

  cancelExport(exportId: string): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/${exportId}/cancel`, {})
      .pipe(
        tap(() => {
          this.notification.showInfo('Export cancelled');
          this.refreshExport(exportId);
        })
      );
  }

  downloadExport(exportId: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/${exportId}/download`, {
      responseType: 'blob'
    }).pipe(
      tap(() => {
        // Update download count
        this.refreshExport(exportId);
      })
    );
  }

  previewExport(exportId: string, limit = 100): Observable<{
    headers: string[];
    rows: any[][];
    total_rows: number;
  }> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<{
      headers: string[];
      rows: any[][];
      total_rows: number;
    }>(`${this.apiUrl}/${exportId}/preview`, { params });
  }

  // Quick Export (without job creation)
  quickExport(request: Omit<ExportCreateRequest, 'name'>): Observable<Blob> {
    return this.http.post(`${this.apiUrl}/quick`, request, {
      responseType: 'blob'
    }).pipe(
      tap(() => {
        this.notification.showSuccess('Export completed');
      })
    );
  }

  // Templates
  getTemplates(): Observable<ExportTemplate[]> {
    return this.http.get<ExportTemplate[]>(`${this.apiUrl}/templates`)
      .pipe(
        tap(templates => this.templatesSubject.next(templates))
      );
  }

  createTemplate(template: Omit<ExportTemplate, 'id' | 'usage_count' | 'created_at' | 'updated_at'>): Observable<ExportTemplate> {
    return this.http.post<ExportTemplate>(`${this.apiUrl}/templates`, template)
      .pipe(
        tap(newTemplate => {
          const current = this.templatesSubject.value;
          this.templatesSubject.next([...current, newTemplate]);
          this.notification.showSuccess('Template created successfully');
        })
      );
  }

  updateTemplate(templateId: string, updates: Partial<ExportTemplate>): Observable<ExportTemplate> {
    return this.http.patch<ExportTemplate>(`${this.apiUrl}/templates/${templateId}`, updates)
      .pipe(
        tap(updatedTemplate => {
          const current = this.templatesSubject.value;
          const index = current.findIndex(t => t.id === templateId);
          if (index !== -1) {
            current[index] = updatedTemplate;
            this.templatesSubject.next([...current]);
          }
          this.notification.showSuccess('Template updated successfully');
        })
      );
  }

  deleteTemplate(templateId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/templates/${templateId}`)
      .pipe(
        tap(() => {
          const current = this.templatesSubject.value;
          this.templatesSubject.next(current.filter(t => t.id !== templateId));
          this.notification.showSuccess('Template deleted successfully');
        })
      );
  }

  createExportFromTemplate(templateId: string, overrides?: Partial<ExportCreateRequest>): Observable<ExportJob> {
    return this.http.post<ExportJob>(`${this.apiUrl}/templates/${templateId}/create-export`, overrides || {})
      .pipe(
        tap(exportJob => {
          const current = this.exportsSubject.value;
          this.exportsSubject.next([exportJob, ...current]);
          this.notification.showSuccess('Export created from template');
        })
      );
  }

  // Progress and Status
  getExportProgress(exportId: string): Observable<{
    percentage: number;
    status: string;
    current_step: string;
    estimated_completion?: string;
    rows_processed?: number;
    total_rows?: number;
  }> {
    return this.http.get<{
      percentage: number;
      status: string;
      current_step: string;
      estimated_completion?: string;
      rows_processed?: number;
      total_rows?: number;
    }>(`${this.apiUrl}/${exportId}/progress`);
  }

  // Statistics
  getStatistics(): Observable<ExportStatistics> {
    return this.http.get<ExportStatistics>(`${this.apiUrl}/statistics`)
      .pipe(
        tap(stats => this.statisticsSubject.next(stats))
      );
  }

  getUsageAnalytics(period: 'week' | 'month' | 'year' = 'month'): Observable<{
    exports_by_day: { date: string; count: number }[];
    formats_usage: { format: string; count: number; percentage: number }[];
    types_usage: { type: string; count: number; percentage: number }[];
    avg_file_size_mb: number;
    peak_usage_day: string;
    total_data_exported_gb: number;
  }> {
    const params = new HttpParams().set('period', period);
    return this.http.get<{
      exports_by_day: { date: string; count: number }[];
      formats_usage: { format: string; count: number; percentage: number }[];
      types_usage: { type: string; count: number; percentage: number }[];
      avg_file_size_mb: number;
      peak_usage_day: string;
      total_data_exported_gb: number;
    }>(`${this.apiUrl}/analytics`, { params });
  }

  // Schedule Management
  updateSchedule(exportId: string, schedule: {
    enabled: boolean;
    cron_expression: string;
    email_recipients?: string[];
  }): Observable<ExportJob> {
    return this.http.patch<ExportJob>(`${this.apiUrl}/${exportId}/schedule`, { schedule })
      .pipe(
        tap(() => {
          this.notification.showSuccess('Export schedule updated');
          this.refreshExport(exportId);
        })
      );
  }

  testSchedule(cronExpression: string): Observable<{
    next_runs: string[];
    valid: boolean;
    error?: string;
  }> {
    return this.http.post<{
      next_runs: string[];
      valid: boolean;
      error?: string;
    }>(`${this.apiUrl}/test-schedule`, { cron_expression: cronExpression });
  }

  getScheduledExports(): Observable<ExportJob[]> {
    return this.http.get<ExportJob[]>(`${this.apiUrl}/scheduled`);
  }

  // Cleanup and Maintenance
  cleanupExpiredExports(): Observable<{
    deleted_count: number;
    freed_bytes: number;
  }> {
    return this.http.delete<{
      deleted_count: number;
      freed_bytes: number;
    }>(`${this.apiUrl}/cleanup`)
      .pipe(
        tap(result => {
          this.notification.showSuccess(`Cleaned up ${result.deleted_count} expired exports`);
          this.loadExports();
        })
      );
  }

  // Utility Methods
  private loadExports(): void {
    this.getExports().subscribe();
  }

  private loadTemplates(): void {
    this.getTemplates().subscribe();
  }

  private loadStatistics(): void {
    this.getStatistics().subscribe();
  }

  private refreshExport(exportId: string): void {
    setTimeout(() => {
      this.getExport(exportId).subscribe(exportJob => {
        const current = this.exportsSubject.value;
        const index = current.findIndex(e => e.id === exportId);
        if (index !== -1) {
          current[index] = exportJob;
          this.exportsSubject.next([...current]);
        }
      });
    }, 1000);
  }

  // Helper Methods
  formatFileSize(bytes: number): string {
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

  getExportTypeIcon(type: string): string {
    const icons: { [key: string]: string } = {
      'transactions': 'receipt',
      'categories': 'category',
      'accounts': 'account_balance',
      'full_backup': 'backup',
      'custom': 'build'
    };
    return icons[type] || 'description';
  }

  getFormatIcon(format: string): string {
    const icons: { [key: string]: string } = {
      'csv': 'table_view',
      'excel': 'grid_on',
      'json': 'code',
      'pdf': 'picture_as_pdf'
    };
    return icons[format] || 'description';
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

  isExportRunning(exportJob: ExportJob): boolean {
    return exportJob.status === 'running';
  }

  canStartExport(exportJob: ExportJob): boolean {
    return exportJob.status === 'pending' || exportJob.status === 'failed';
  }

  canCancelExport(exportJob: ExportJob): boolean {
    return exportJob.status === 'running';
  }

  canDownloadExport(exportJob: ExportJob): boolean {
    return exportJob.status === 'completed' && !!exportJob.file_path;
  }

  isExportExpired(exportJob: ExportJob): boolean {
    if (!exportJob.expires_at) return false;
    return new Date(exportJob.expires_at) < new Date();
  }
}