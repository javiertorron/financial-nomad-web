import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { map, tap } from 'rxjs/operators';

import { ConfigService } from './config.service';
import {
  CacheStatistics,
  CacheKeyInfo,
  CacheOperation
} from '../types/enterprise.types';

export interface CacheConfiguration {
  default_ttl_seconds: number;
  max_memory_mb: number;
  eviction_policy: 'lru' | 'lfu' | 'fifo' | 'random';
  compression_enabled: boolean;
  persistence_enabled: boolean;
}

export interface CacheHealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime_seconds: number;
  connections: number;
  memory_usage: number;
  cpu_usage: number;
  response_time_ms: number;
  error_rate: number;
}

export interface CachePattern {
  pattern: string;
  description: string;
  example: string;
  ttl_seconds?: number;
}

export interface BulkCacheOperation {
  operation: 'delete' | 'refresh' | 'set_ttl';
  patterns: string[];
  ttl_seconds?: number;
}

@Injectable({
  providedIn: 'root'
})
export class CacheService {
  private readonly apiUrl = `${this.config.apiUrl}/cache`;

  private statisticsSubject = new BehaviorSubject<CacheStatistics | null>(null);
  public statistics$ = this.statisticsSubject.asObservable();

  private healthSubject = new BehaviorSubject<CacheHealthStatus | null>(null);
  public health$ = this.healthSubject.asObservable();

  private operationsSubject = new BehaviorSubject<CacheOperation[]>([]);
  public operations$ = this.operationsSubject.asObservable();

  private isConnected = new BehaviorSubject<boolean>(true);
  public connected$ = this.isConnected.asObservable();

  constructor(
    private http: HttpClient,
    private config: ConfigService
  ) {
    this.loadStatistics();
    this.loadHealth();
    this.startPeriodicUpdates();
  }

  // Cache Statistics
  getStatistics(): Observable<CacheStatistics> {
    return this.http.get<CacheStatistics>(`${this.apiUrl}/statistics`)
      .pipe(
        tap(stats => {
          this.statisticsSubject.next(stats);
          this.isConnected.next(true);
        })
      );
  }

  getDetailedStatistics(): Observable<any> {
    return this.http.get(`${this.apiUrl}/statistics/detailed`);
  }

  getStatisticsHistory(hours = 24): Observable<any[]> {
    const params = new HttpParams().set('hours', hours.toString());
    return this.http.get<any[]>(`${this.apiUrl}/statistics/history`, { params });
  }

  // Cache Health and Monitoring
  getHealth(): Observable<CacheHealthStatus> {
    return this.http.get<CacheHealthStatus>(`${this.apiUrl}/health`)
      .pipe(
        tap(health => {
          this.healthSubject.next(health);
          this.isConnected.next(health.status !== 'unhealthy');
        })
      );
  }

  getPerformanceMetrics(period = '1h'): Observable<any> {
    const params = new HttpParams().set('period', period);
    return this.http.get(`${this.apiUrl}/metrics`, { params });
  }

  // Key Management
  getKeys(pattern = '*', limit = 100): Observable<CacheKeyInfo[]> {
    const params = new HttpParams()
      .set('pattern', pattern)
      .set('limit', limit.toString());
    return this.http.get<CacheKeyInfo[]>(`${this.apiUrl}/keys`, { params });
  }

  getKeyDetails(key: string): Observable<CacheKeyInfo> {
    const params = new HttpParams().set('key', key);
    return this.http.get<CacheKeyInfo>(`${this.apiUrl}/keys/details`, { params });
  }

  getKeyValue(key: string): Observable<any> {
    const params = new HttpParams().set('key', key);
    return this.http.get(`${this.apiUrl}/keys/value`, { params });
  }

  setKeyValue(key: string, value: any, ttlSeconds?: number): Observable<void> {
    const body = { key, value, ttl_seconds: ttlSeconds };
    return this.http.post<void>(`${this.apiUrl}/keys/set`, body);
  }

  deleteKey(key: string): Observable<void> {
    const params = new HttpParams().set('key', key);
    return this.http.delete<void>(`${this.apiUrl}/keys`, { params });
  }

  deleteKeysByPattern(pattern: string): Observable<{ deleted_count: number }> {
    const body = { pattern };
    return this.http.post<{ deleted_count: number }>(`${this.apiUrl}/keys/delete-pattern`, body);
  }

  setKeyTTL(key: string, ttlSeconds: number): Observable<void> {
    const body = { key, ttl_seconds: ttlSeconds };
    return this.http.post<void>(`${this.apiUrl}/keys/ttl`, body);
  }

  // Cache Operations
  flushCache(pattern?: string): Observable<{ cleared_count: number }> {
    const body = pattern ? { pattern } : {};
    return this.http.post<{ cleared_count: number }>(`${this.apiUrl}/flush`, body)
      .pipe(
        tap(() => this.loadStatistics())
      );
  }

  flushAll(): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/flush-all`, {})
      .pipe(
        tap(() => this.loadStatistics())
      );
  }

  warmupCache(patterns?: string[]): Observable<{ warmed_count: number }> {
    const body = { patterns: patterns || [] };
    return this.http.post<{ warmed_count: number }>(`${this.apiUrl}/warmup`, body);
  }

  refreshCache(patterns?: string[]): Observable<{ refreshed_count: number }> {
    const body = { patterns: patterns || [] };
    return this.http.post<{ refreshed_count: number }>(`${this.apiUrl}/refresh`, body);
  }

  // Bulk Operations
  bulkOperation(operation: BulkCacheOperation): Observable<{ affected_count: number }> {
    return this.http.post<{ affected_count: number }>(`${this.apiUrl}/bulk`, operation)
      .pipe(
        tap(() => this.loadStatistics())
      );
  }

  // Configuration Management
  getConfiguration(): Observable<CacheConfiguration> {
    return this.http.get<CacheConfiguration>(`${this.apiUrl}/config`);
  }

  updateConfiguration(config: Partial<CacheConfiguration>): Observable<CacheConfiguration> {
    return this.http.put<CacheConfiguration>(`${this.apiUrl}/config`, config);
  }

  resetConfiguration(): Observable<CacheConfiguration> {
    return this.http.post<CacheConfiguration>(`${this.apiUrl}/config/reset`, {});
  }

  // Cache Patterns and Templates
  getCachePatterns(): Observable<CachePattern[]> {
    return this.http.get<CachePattern[]>(`${this.apiUrl}/patterns`);
  }

  createCachePattern(pattern: CachePattern): Observable<CachePattern> {
    return this.http.post<CachePattern>(`${this.apiUrl}/patterns`, pattern);
  }

  deleteCachePattern(pattern: string): Observable<void> {
    const params = new HttpParams().set('pattern', pattern);
    return this.http.delete<void>(`${this.apiUrl}/patterns`, { params });
  }

  // Operation History
  getOperationHistory(limit = 100): Observable<CacheOperation[]> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<CacheOperation[]>(`${this.apiUrl}/operations`, { params })
      .pipe(
        tap(operations => this.operationsSubject.next(operations))
      );
  }

  clearOperationHistory(): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/operations`);
  }

  // Memory Management
  getMemoryUsage(): Observable<any> {
    return this.http.get(`${this.apiUrl}/memory`);
  }

  optimizeMemory(): Observable<{ freed_mb: number }> {
    return this.http.post<{ freed_mb: number }>(`${this.apiUrl}/memory/optimize`, {})
      .pipe(
        tap(() => this.loadStatistics())
      );
  }

  getTopMemoryConsumers(limit = 20): Observable<CacheKeyInfo[]> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<CacheKeyInfo[]>(`${this.apiUrl}/memory/top-consumers`, { params });
  }

  // Search and Analysis
  searchKeys(query: string, searchIn: 'key' | 'value' | 'both' = 'key'): Observable<CacheKeyInfo[]> {
    const params = new HttpParams()
      .set('query', query)
      .set('search_in', searchIn);
    return this.http.get<CacheKeyInfo[]>(`${this.apiUrl}/search`, { params });
  }

  analyzeKeyPatterns(): Observable<any> {
    return this.http.get(`${this.apiUrl}/analysis/patterns`);
  }

  getKeyUsageStats(pattern?: string): Observable<any> {
    const params = pattern ? new HttpParams().set('pattern', pattern) : new HttpParams();
    return this.http.get(`${this.apiUrl}/analysis/usage`, { params });
  }

  // Export and Import
  exportCache(pattern = '*', format: 'json' | 'redis' = 'json'): Observable<Blob> {
    const params = new HttpParams()
      .set('pattern', pattern)
      .set('format', format);
    return this.http.get(`${this.apiUrl}/export`, {
      params,
      responseType: 'blob'
    });
  }

  importCache(data: any, overwrite = false): Observable<{ imported_count: number }> {
    const body = { data, overwrite };
    return this.http.post<{ imported_count: number }>(`${this.apiUrl}/import`, body)
      .pipe(
        tap(() => this.loadStatistics())
      );
  }

  // Monitoring and Alerts
  setMemoryAlert(threshold: number): Observable<void> {
    const body = { threshold_mb: threshold };
    return this.http.post<void>(`${this.apiUrl}/alerts/memory`, body);
  }

  setHitRateAlert(threshold: number): Observable<void> {
    const body = { threshold_percentage: threshold };
    return this.http.post<void>(`${this.apiUrl}/alerts/hit-rate`, body);
  }

  getAlerts(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/alerts`);
  }

  dismissAlert(alertId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/alerts/${alertId}`);
  }

  // Utility Methods
  private loadStatistics(): void {
    this.getStatistics().subscribe({
      error: () => this.isConnected.next(false)
    });
  }

  private loadHealth(): void {
    this.getHealth().subscribe({
      error: () => this.isConnected.next(false)
    });
  }

  private startPeriodicUpdates(): void {
    // Update statistics every 30 seconds
    setInterval(() => {
      if (this.isConnected.value) {
        this.loadStatistics();
        this.loadHealth();
      }
    }, 30000);
  }

  // Format Helpers
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
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
    return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
  }

  formatPercentage(value: number, decimals = 1): string {
    return `${value.toFixed(decimals)}%`;
  }

  formatNumber(value: number): string {
    return new Intl.NumberFormat().format(value);
  }

  // Validation Helpers
  validatePattern(pattern: string): string[] {
    const errors: string[] = [];
    
    if (!pattern.trim()) {
      errors.push('Pattern cannot be empty');
    }
    
    // Check for potentially dangerous patterns
    if (pattern === '*' || pattern === '**') {
      errors.push('Use caution with wildcard patterns as they may affect many keys');
    }
    
    return errors;
  }

  validateKey(key: string): string[] {
    const errors: string[] = [];
    
    if (!key.trim()) {
      errors.push('Key cannot be empty');
    }
    
    if (key.length > 512) {
      errors.push('Key length should not exceed 512 characters');
    }
    
    return errors;
  }

  validateTTL(ttl: number): string[] {
    const errors: string[] = [];
    
    if (ttl < 0) {
      errors.push('TTL cannot be negative');
    }
    
    if (ttl > 2147483647) { // Max 32-bit int
      errors.push('TTL value is too large');
    }
    
    return errors;
  }

  // Connection Management
  testConnection(): Observable<boolean> {
    return this.http.get(`${this.apiUrl}/ping`).pipe(
      map(() => {
        this.isConnected.next(true);
        return true;
      }),
      tap(() => {}, () => this.isConnected.next(false))
    );
  }

  reconnect(): Observable<boolean> {
    return this.testConnection();
  }

  // Cache Strategy Helpers
  getRecommendedTTL(keyPattern: string): number {
    const ttlRecommendations: { [key: string]: number } = {
      'user:*': 3600,        // 1 hour
      'session:*': 1800,     // 30 minutes  
      'transaction:*': 7200, // 2 hours
      'account:*': 3600,     // 1 hour
      'category:*': 86400,   // 1 day
      'budget:*': 3600,      // 1 hour
      'report:*': 1800,      // 30 minutes
      'analytics:*': 900,    // 15 minutes
      'temp:*': 300          // 5 minutes
    };

    for (const [pattern, ttl] of Object.entries(ttlRecommendations)) {
      if (keyPattern.startsWith(pattern.replace('*', ''))) {
        return ttl;
      }
    }

    return 3600; // Default 1 hour
  }

  getCacheHealthStatus(): 'healthy' | 'warning' | 'critical' {
    const stats = this.statisticsSubject.value;
    const health = this.healthSubject.value;

    if (!stats || !health) return 'critical';

    if (health.status === 'unhealthy') return 'critical';
    if (health.memory_usage > 90) return 'critical';
    if (stats.hit_rate < 0.5) return 'warning';
    if (health.error_rate > 0.05) return 'warning';

    return 'healthy';
  }
}