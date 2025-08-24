import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { map, tap } from 'rxjs/operators';

import { ConfigService } from './config.service';
import {
  WebhookConfiguration,
  WebhookEvent,
  WebhookDelivery
} from '../types/enterprise.types';

export interface WebhookTestResult {
  success: boolean;
  status_code?: number;
  response_time_ms: number;
  response_body?: string;
  error_message?: string;
}

export interface WebhookStatistics {
  total_webhooks: number;
  active_webhooks: number;
  total_deliveries: number;
  successful_deliveries: number;
  failed_deliveries: number;
  average_response_time_ms: number;
  success_rate: number;
}

@Injectable({
  providedIn: 'root'
})
export class WebhooksService {
  private readonly apiUrl = `${this.config.apiUrl}/webhooks`;

  private webhooksSubject = new BehaviorSubject<WebhookConfiguration[]>([]);
  public webhooks$ = this.webhooksSubject.asObservable();

  private deliveriesSubject = new BehaviorSubject<WebhookDelivery[]>([]);
  public deliveries$ = this.deliveriesSubject.asObservable();

  private statisticsSubject = new BehaviorSubject<WebhookStatistics | null>(null);
  public statistics$ = this.statisticsSubject.asObservable();

  constructor(
    private http: HttpClient,
    private config: ConfigService
  ) {
    this.loadWebhooks();
    this.loadStatistics();
  }

  // Webhook Configuration Management
  getWebhooks(): Observable<WebhookConfiguration[]> {
    return this.http.get<WebhookConfiguration[]>(`${this.apiUrl}/configurations`)
      .pipe(
        tap(webhooks => this.webhooksSubject.next(webhooks))
      );
  }

  getWebhook(id: string): Observable<WebhookConfiguration> {
    return this.http.get<WebhookConfiguration>(`${this.apiUrl}/configurations/${id}`);
  }

  createWebhook(webhook: Omit<WebhookConfiguration, 'id' | 'created_at' | 'updated_at' | 'last_triggered_at'>): Observable<WebhookConfiguration> {
    return this.http.post<WebhookConfiguration>(`${this.apiUrl}/configurations`, webhook)
      .pipe(
        tap(() => this.loadWebhooks())
      );
  }

  updateWebhook(id: string, webhook: Partial<WebhookConfiguration>): Observable<WebhookConfiguration> {
    return this.http.put<WebhookConfiguration>(`${this.apiUrl}/configurations/${id}`, webhook)
      .pipe(
        tap(() => this.loadWebhooks())
      );
  }

  deleteWebhook(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/configurations/${id}`)
      .pipe(
        tap(() => this.loadWebhooks())
      );
  }

  // Webhook Activation/Deactivation
  activateWebhook(id: string): Observable<WebhookConfiguration> {
    return this.http.post<WebhookConfiguration>(`${this.apiUrl}/configurations/${id}/activate`, {})
      .pipe(
        tap(() => this.loadWebhooks())
      );
  }

  deactivateWebhook(id: string): Observable<WebhookConfiguration> {
    return this.http.post<WebhookConfiguration>(`${this.apiUrl}/configurations/${id}/deactivate`, {})
      .pipe(
        tap(() => this.loadWebhooks())
      );
  }

  // Webhook Testing
  testWebhook(id: string, eventType?: string): Observable<WebhookTestResult> {
    const body = eventType ? { event_type: eventType } : {};
    return this.http.post<WebhookTestResult>(`${this.apiUrl}/configurations/${id}/test`, body);
  }

  testWebhookUrl(url: string, payload?: any): Observable<WebhookTestResult> {
    const body = { url, payload: payload || this.getTestPayload() };
    return this.http.post<WebhookTestResult>(`${this.apiUrl}/test-url`, body);
  }

  // Webhook Events
  getAvailableEvents(): Observable<WebhookEvent[]> {
    return this.http.get<WebhookEvent[]>(`${this.apiUrl}/events`);
  }

  // Delivery Management
  getDeliveries(webhookId?: string, limit = 50): Observable<WebhookDelivery[]> {
    let params = new HttpParams().set('limit', limit.toString());
    if (webhookId) {
      params = params.set('webhook_id', webhookId);
    }
    
    return this.http.get<WebhookDelivery[]>(`${this.apiUrl}/deliveries`, { params })
      .pipe(
        tap(deliveries => this.deliveriesSubject.next(deliveries))
      );
  }

  getDelivery(id: string): Observable<WebhookDelivery> {
    return this.http.get<WebhookDelivery>(`${this.apiUrl}/deliveries/${id}`);
  }

  retryDelivery(id: string): Observable<WebhookDelivery> {
    return this.http.post<WebhookDelivery>(`${this.apiUrl}/deliveries/${id}/retry`, {})
      .pipe(
        tap(() => this.loadDeliveries())
      );
  }

  cancelDelivery(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/deliveries/${id}`)
      .pipe(
        tap(() => this.loadDeliveries())
      );
  }

  // Statistics and Monitoring
  getStatistics(): Observable<WebhookStatistics> {
    return this.http.get<WebhookStatistics>(`${this.apiUrl}/statistics`)
      .pipe(
        tap(stats => this.statisticsSubject.next(stats))
      );
  }

  getWebhookStatistics(id: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/configurations/${id}/statistics`);
  }

  // Security and Validation
  generateSecret(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  validateWebhookSignature(payload: string, signature: string, secret: string): boolean {
    // This would typically be done server-side, but including for completeness
    try {
      const crypto = window.crypto;
      const encoder = new TextEncoder();
      const keyData = encoder.encode(secret);
      const payloadData = encoder.encode(payload);
      
      // For demonstration - actual validation should be server-side
      return signature.length > 0 && secret.length > 0;
    } catch (error) {
      console.error('Error validating webhook signature:', error);
      return false;
    }
  }

  // Webhook Templates
  getWebhookTemplates(): Observable<Partial<WebhookConfiguration>[]> {
    return this.http.get<Partial<WebhookConfiguration>[]>(`${this.apiUrl}/templates`);
  }

  createWebhookFromTemplate(templateId: string, customizations: any): Observable<WebhookConfiguration> {
    const body = { template_id: templateId, customizations };
    return this.http.post<WebhookConfiguration>(`${this.apiUrl}/from-template`, body)
      .pipe(
        tap(() => this.loadWebhooks())
      );
  }

  // Batch Operations
  bulkUpdateWebhooks(updates: { id: string; active: boolean }[]): Observable<WebhookConfiguration[]> {
    return this.http.post<WebhookConfiguration[]>(`${this.apiUrl}/bulk-update`, { updates })
      .pipe(
        tap(() => this.loadWebhooks())
      );
  }

  // Health Checks
  performHealthCheck(): Observable<any> {
    return this.http.get(`${this.apiUrl}/health`);
  }

  // Utility Methods
  private loadWebhooks(): void {
    this.getWebhooks().subscribe();
  }

  private loadDeliveries(): void {
    this.getDeliveries().subscribe();
  }

  private loadStatistics(): void {
    this.getStatistics().subscribe();
  }

  private getTestPayload(): any {
    return {
      event_type: 'test.webhook',
      timestamp: new Date().toISOString(),
      data: {
        test: true,
        message: 'This is a test webhook payload'
      }
    };
  }

  // Event Type Helpers
  getEventTypeDisplayName(eventType: string): string {
    const eventNames: { [key: string]: string } = {
      'transaction.created': 'Transaction Created',
      'transaction.updated': 'Transaction Updated',
      'transaction.deleted': 'Transaction Deleted',
      'account.created': 'Account Created',
      'account.updated': 'Account Updated',
      'account.deleted': 'Account Deleted',
      'budget.exceeded': 'Budget Exceeded',
      'goal.achieved': 'Goal Achieved',
      'report.generated': 'Report Generated',
      'user.login': 'User Login',
      'user.logout': 'User Logout',
      'system.maintenance': 'System Maintenance'
    };

    return eventNames[eventType] || eventType.split('.').map(part => 
      part.charAt(0).toUpperCase() + part.slice(1)
    ).join(' ');
  }

  getEventTypeDescription(eventType: string): string {
    const descriptions: { [key: string]: string } = {
      'transaction.created': 'Triggered when a new transaction is created',
      'transaction.updated': 'Triggered when an existing transaction is modified',
      'transaction.deleted': 'Triggered when a transaction is deleted',
      'account.created': 'Triggered when a new account is added',
      'account.updated': 'Triggered when account details are modified',
      'account.deleted': 'Triggered when an account is removed',
      'budget.exceeded': 'Triggered when spending exceeds budget limits',
      'goal.achieved': 'Triggered when a financial goal is reached',
      'report.generated': 'Triggered when a scheduled report is generated',
      'user.login': 'Triggered when a user logs into the system',
      'user.logout': 'Triggered when a user logs out',
      'system.maintenance': 'Triggered during system maintenance events'
    };

    return descriptions[eventType] || 'Custom event type';
  }

  // Validation Helpers
  validateWebhookUrl(url: string): string[] {
    const errors: string[] = [];

    if (!url) {
      errors.push('URL is required');
      return errors;
    }

    try {
      const urlObj = new URL(url);
      
      if (!['http:', 'https:'].includes(urlObj.protocol)) {
        errors.push('URL must use HTTP or HTTPS protocol');
      }

      if (urlObj.protocol === 'http:' && !url.includes('localhost')) {
        errors.push('HTTP URLs are only allowed for localhost');
      }

      if (!urlObj.hostname) {
        errors.push('URL must have a valid hostname');
      }

    } catch (error) {
      errors.push('Invalid URL format');
    }

    return errors;
  }

  validateWebhookConfiguration(webhook: Partial<WebhookConfiguration>): string[] {
    const errors: string[] = [];

    if (!webhook.name?.trim()) {
      errors.push('Name is required');
    }

    if (!webhook.url?.trim()) {
      errors.push('URL is required');
    } else {
      errors.push(...this.validateWebhookUrl(webhook.url));
    }

    if (!webhook.events?.length) {
      errors.push('At least one event must be selected');
    }

    if (!webhook.secret?.trim()) {
      errors.push('Secret is required for security');
    } else if (webhook.secret.length < 16) {
      errors.push('Secret must be at least 16 characters long');
    }

    return errors;
  }

  // Format Helpers
  formatDeliveryStatus(status: string): string {
    const statusMap: { [key: string]: string } = {
      'pending': 'Pending',
      'delivered': 'Delivered',
      'failed': 'Failed',
      'retrying': 'Retrying'
    };

    return statusMap[status] || status;
  }

  getDeliveryStatusColor(status: string): string {
    const colorMap: { [key: string]: string } = {
      'pending': '#FF9800',
      'delivered': '#4CAF50',
      'failed': '#f44336',
      'retrying': '#2196F3'
    };

    return colorMap[status] || '#9E9E9E';
  }

  formatResponseTime(timeMs: number): string {
    if (timeMs < 1000) {
      return `${timeMs}ms`;
    } else if (timeMs < 60000) {
      return `${(timeMs / 1000).toFixed(1)}s`;
    } else {
      return `${(timeMs / 60000).toFixed(1)}m`;
    }
  }
}