import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { map, tap } from 'rxjs/operators';

import { ConfigService } from './config.service';
import {
  AuditEvent,
  AuditReport,
  ComplianceFlag,
  ComplianceStatus,
  AuditFinding
} from '../types/enterprise.types';

export interface AuditFilters {
  startDate?: string;
  endDate?: string;
  userId?: string;
  eventType?: string;
  resourceType?: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  complianceFramework?: string;
  page?: number;
  limit?: number;
}

export interface AuditStatistics {
  total_events: number;
  events_by_severity: Record<string, number>;
  events_by_type: Record<string, number>;
  recent_activity: number;
  compliance_score: number;
  critical_alerts: number;
}

export interface ComplianceFramework {
  id: string;
  name: string;
  description: string;
  requirements: ComplianceRequirement[];
  enabled: boolean;
}

export interface ComplianceRequirement {
  id: string;
  name: string;
  description: string;
  category: string;
  mandatory: boolean;
  status: 'compliant' | 'non_compliant' | 'warning' | 'not_applicable';
  last_checked: string;
  details?: string;
}

export interface DataRetentionPolicy {
  id: string;
  name: string;
  resource_types: string[];
  retention_days: number;
  archive_after_days?: number;
  delete_after_days?: number;
  enabled: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class AuditService {
  private readonly apiUrl = `${this.config.apiUrl}/audit`;

  private eventsSubject = new BehaviorSubject<AuditEvent[]>([]);
  public events$ = this.eventsSubject.asObservable();

  private statisticsSubject = new BehaviorSubject<AuditStatistics | null>(null);
  public statistics$ = this.statisticsSubject.asObservable();

  private complianceStatusSubject = new BehaviorSubject<ComplianceStatus | null>(null);
  public complianceStatus$ = this.complianceStatusSubject.asObservable();

  constructor(
    private http: HttpClient,
    private config: ConfigService
  ) {
    this.loadStatistics();
    this.loadComplianceStatus();
  }

  // Audit Events
  getAuditEvents(filters?: AuditFilters): Observable<AuditEvent[]> {
    const params = this.buildParams(filters);
    return this.http.get<AuditEvent[]>(`${this.apiUrl}/events`, { params })
      .pipe(
        tap(events => this.eventsSubject.next(events))
      );
  }

  getAuditEvent(id: string): Observable<AuditEvent> {
    return this.http.get<AuditEvent>(`${this.apiUrl}/events/${id}`);
  }

  searchAuditEvents(query: string, filters?: AuditFilters): Observable<AuditEvent[]> {
    let params = this.buildParams(filters);
    params = params.set('q', query);
    return this.http.get<AuditEvent[]>(`${this.apiUrl}/events/search`, { params });
  }

  exportAuditEvents(filters?: AuditFilters, format: 'csv' | 'excel' | 'json' = 'csv'): Observable<Blob> {
    let params = this.buildParams(filters);
    params = params.set('format', format);
    return this.http.get(`${this.apiUrl}/events/export`, {
      params,
      responseType: 'blob'
    });
  }

  // Audit Reports
  generateAuditReport(
    title: string,
    description: string,
    startDate: string,
    endDate: string,
    filters?: AuditFilters
  ): Observable<AuditReport> {
    const body = {
      title,
      description,
      period: { start_date: startDate, end_date: endDate },
      filters
    };
    return this.http.post<AuditReport>(`${this.apiUrl}/reports/generate`, body);
  }

  getAuditReports(limit = 50): Observable<AuditReport[]> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<AuditReport[]>(`${this.apiUrl}/reports`, { params });
  }

  getAuditReport(id: string): Observable<AuditReport> {
    return this.http.get<AuditReport>(`${this.apiUrl}/reports/${id}`);
  }

  downloadAuditReport(id: string, format: 'pdf' | 'excel' = 'pdf'): Observable<Blob> {
    const params = new HttpParams().set('format', format);
    return this.http.get(`${this.apiUrl}/reports/${id}/download`, {
      params,
      responseType: 'blob'
    });
  }

  deleteAuditReport(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/reports/${id}`);
  }

  // Compliance Management
  getComplianceStatus(): Observable<ComplianceStatus> {
    return this.http.get<ComplianceStatus>(`${this.apiUrl}/compliance/status`)
      .pipe(
        tap(status => this.complianceStatusSubject.next(status))
      );
  }

  getComplianceFrameworks(): Observable<ComplianceFramework[]> {
    return this.http.get<ComplianceFramework[]>(`${this.apiUrl}/compliance/frameworks`);
  }

  getComplianceFramework(frameworkId: string): Observable<ComplianceFramework> {
    return this.http.get<ComplianceFramework>(`${this.apiUrl}/compliance/frameworks/${frameworkId}`);
  }

  updateComplianceFramework(frameworkId: string, enabled: boolean): Observable<ComplianceFramework> {
    return this.http.patch<ComplianceFramework>(`${this.apiUrl}/compliance/frameworks/${frameworkId}`, {
      enabled
    });
  }

  runComplianceCheck(frameworkId?: string): Observable<ComplianceStatus> {
    const body = frameworkId ? { framework_id: frameworkId } : {};
    return this.http.post<ComplianceStatus>(`${this.apiUrl}/compliance/check`, body)
      .pipe(
        tap(status => this.complianceStatusSubject.next(status))
      );
  }

  getComplianceFindings(frameworkId?: string, severity?: string): Observable<AuditFinding[]> {
    let params = new HttpParams();
    if (frameworkId) params = params.set('framework_id', frameworkId);
    if (severity) params = params.set('severity', severity);
    
    return this.http.get<AuditFinding[]>(`${this.apiUrl}/compliance/findings`, { params });
  }

  resolveComplianceFinding(findingId: string, resolution: string): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/compliance/findings/${findingId}/resolve`, {
      resolution
    });
  }

  // Data Privacy and GDPR
  getDataSubjectRequests(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/privacy/data-subject-requests`);
  }

  createDataExportRequest(userId: string, requestType: 'export' | 'deletion'): Observable<any> {
    return this.http.post(`${this.apiUrl}/privacy/data-subject-requests`, {
      user_id: userId,
      request_type: requestType
    });
  }

  processDataDeletion(userId: string, deleteAll = false): Observable<any> {
    return this.http.post(`${this.apiUrl}/privacy/delete-user-data`, {
      user_id: userId,
      delete_all: deleteAll
    });
  }

  getDataProcessingActivities(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/privacy/processing-activities`);
  }

  // Data Retention
  getRetentionPolicies(): Observable<DataRetentionPolicy[]> {
    return this.http.get<DataRetentionPolicy[]>(`${this.apiUrl}/retention/policies`);
  }

  createRetentionPolicy(policy: Omit<DataRetentionPolicy, 'id'>): Observable<DataRetentionPolicy> {
    return this.http.post<DataRetentionPolicy>(`${this.apiUrl}/retention/policies`, policy);
  }

  updateRetentionPolicy(id: string, policy: Partial<DataRetentionPolicy>): Observable<DataRetentionPolicy> {
    return this.http.patch<DataRetentionPolicy>(`${this.apiUrl}/retention/policies/${id}`, policy);
  }

  deleteRetentionPolicy(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/retention/policies/${id}`);
  }

  runRetentionCleanup(policyId?: string): Observable<any> {
    const body = policyId ? { policy_id: policyId } : {};
    return this.http.post(`${this.apiUrl}/retention/cleanup`, body);
  }

  getRetentionStatistics(): Observable<any> {
    return this.http.get(`${this.apiUrl}/retention/statistics`);
  }

  // Security Monitoring
  getSecurityAlerts(severity?: string): Observable<any[]> {
    let params = new HttpParams();
    if (severity) params = params.set('severity', severity);
    
    return this.http.get<any[]>(`${this.apiUrl}/security/alerts`, { params });
  }

  dismissSecurityAlert(alertId: string): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/security/alerts/${alertId}/dismiss`, {});
  }

  getSecurityMetrics(): Observable<any> {
    return this.http.get(`${this.apiUrl}/security/metrics`);
  }

  // Access Control Audit
  getUserAccessHistory(userId: string, days = 30): Observable<any[]> {
    const params = new HttpParams()
      .set('user_id', userId)
      .set('days', days.toString());
    
    return this.http.get<any[]>(`${this.apiUrl}/access/user-history`, { params });
  }

  getResourceAccessHistory(resourceType: string, resourceId: string): Observable<any[]> {
    const params = new HttpParams()
      .set('resource_type', resourceType)
      .set('resource_id', resourceId);
    
    return this.http.get<any[]>(`${this.apiUrl}/access/resource-history`, { params });
  }

  getUnusualAccessPatterns(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/access/unusual-patterns`);
  }

  // Statistics and Analytics
  getAuditStatistics(period?: 'day' | 'week' | 'month' | 'year'): Observable<AuditStatistics> {
    let params = new HttpParams();
    if (period) params = params.set('period', period);
    
    return this.http.get<AuditStatistics>(`${this.apiUrl}/statistics`, { params })
      .pipe(
        tap(stats => this.statisticsSubject.next(stats))
      );
  }

  getAuditTrends(startDate: string, endDate: string, groupBy: 'day' | 'week' | 'month' = 'day'): Observable<any[]> {
    const params = new HttpParams()
      .set('start_date', startDate)
      .set('end_date', endDate)
      .set('group_by', groupBy);
    
    return this.http.get<any[]>(`${this.apiUrl}/trends`, { params });
  }

  // Utility Methods
  private buildParams(filters?: AuditFilters): HttpParams {
    let params = new HttpParams();
    
    if (!filters) return params;

    if (filters.startDate) params = params.set('start_date', filters.startDate);
    if (filters.endDate) params = params.set('end_date', filters.endDate);
    if (filters.userId) params = params.set('user_id', filters.userId);
    if (filters.eventType) params = params.set('event_type', filters.eventType);
    if (filters.resourceType) params = params.set('resource_type', filters.resourceType);
    if (filters.severity) params = params.set('severity', filters.severity);
    if (filters.complianceFramework) params = params.set('compliance_framework', filters.complianceFramework);
    if (filters.page) params = params.set('page', filters.page.toString());
    if (filters.limit) params = params.set('limit', filters.limit.toString());

    return params;
  }

  private loadStatistics(): void {
    this.getAuditStatistics().subscribe();
  }

  private loadComplianceStatus(): void {
    this.getComplianceStatus().subscribe();
  }

  // Format Helpers
  formatEventType(eventType: string): string {
    return eventType.split('.').map(part => 
      part.charAt(0).toUpperCase() + part.slice(1)
    ).join(' ');
  }

  formatSeverity(severity: string): string {
    const severityMap: { [key: string]: string } = {
      'low': 'Low',
      'medium': 'Medium',
      'high': 'High',
      'critical': 'Critical'
    };
    return severityMap[severity] || severity;
  }

  getSeverityColor(severity: string): string {
    const colorMap: { [key: string]: string } = {
      'low': '#4CAF50',
      'medium': '#FF9800',
      'high': '#f44336',
      'critical': '#9C27B0'
    };
    return colorMap[severity] || '#9E9E9E';
  }

  getComplianceScoreColor(score: number): string {
    if (score >= 95) return '#4CAF50';
    if (score >= 80) return '#8BC34A';
    if (score >= 60) return '#FF9800';
    if (score >= 40) return '#f44336';
    return '#9C27B0';
  }

  formatComplianceStatus(status: string): string {
    const statusMap: { [key: string]: string } = {
      'compliant': 'Compliant',
      'non_compliant': 'Non-Compliant',
      'warning': 'Warning',
      'not_applicable': 'N/A'
    };
    return statusMap[status] || status;
  }

  getComplianceStatusColor(status: string): string {
    const colorMap: { [key: string]: string } = {
      'compliant': '#4CAF50',
      'non_compliant': '#f44336',
      'warning': '#FF9800',
      'not_applicable': '#9E9E9E'
    };
    return colorMap[status] || '#9E9E9E';
  }

  // Validation Helpers
  validateDateRange(startDate: string, endDate: string): string[] {
    const errors: string[] = [];
    
    if (!startDate) {
      errors.push('Start date is required');
    }
    
    if (!endDate) {
      errors.push('End date is required');
    }
    
    if (startDate && endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      
      if (start >= end) {
        errors.push('Start date must be before end date');
      }
      
      const daysDiff = (end.getTime() - start.getTime()) / (1000 * 3600 * 24);
      if (daysDiff > 365) {
        errors.push('Date range cannot exceed 365 days');
      }
    }
    
    return errors;
  }

  // Configuration Helpers
  getDefaultFilters(): AuditFilters {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - 30); // Last 30 days

    return {
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0],
      page: 1,
      limit: 50
    };
  }

  // Real-time Updates
  subscribeToAuditEvents(): Observable<AuditEvent> {
    // This would integrate with WebSocket or Server-Sent Events
    // For now, return a mock observable
    return new Observable(observer => {
      // Implementation would depend on real-time service
    });
  }
}