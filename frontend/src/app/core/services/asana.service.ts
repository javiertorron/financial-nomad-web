import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { map, tap } from 'rxjs/operators';

import { ConfigService } from './config.service';
import { NotificationService } from './notification.service';
import {
  AsanaIntegration,
  AsanaTaskMapping,
  AsanaIntegrationResponse,
  AsanaIntegrationConfigRequest,
  AsanaTaskMappingResponse,
  AsanaTaskMappingCreateRequest,
  AsanaSyncRequest,
  AsanaSyncResponse,
  AsanaIntegrationState,
  AsanaWorkspace,
  AsanaProject,
  AsanaUser,
  AsanaOAuthConfig,
  AsanaOAuthToken,
  AsanaTask
} from '../types/asana.types';

@Injectable({
  providedIn: 'root'
})
export class AsanaService {
  private readonly apiUrl = `${this.config.apiUrl}/asana`;

  private stateSubject = new BehaviorSubject<AsanaIntegrationState>({
    integration: null,
    workspaces: [],
    projects: [],
    users: [],
    taskMappings: [],
    syncHistory: [],
    isLoading: false,
    isConfiguring: false,
    isSyncing: false,
    error: null,
    oauthInProgress: false
  });

  public state$ = this.stateSubject.asObservable();

  constructor(
    private http: HttpClient,
    private config: ConfigService,
    private notification: NotificationService
  ) {
    this.loadIntegration();
  }

  // Integration Management
  getIntegration(): Observable<AsanaIntegrationResponse> {
    this.updateState({ isLoading: true });
    return this.http.get<AsanaIntegrationResponse>(`${this.apiUrl}/integration`)
      .pipe(
        tap(response => {
          this.updateState({
            integration: response.integration,
            workspaces: response.workspaces,
            projects: response.projects,
            users: response.users,
            isLoading: false,
            error: null
          });
        }),
        tap({
          error: (error) => {
            this.updateState({ 
              isLoading: false, 
              error: error.message || 'Failed to load integration'
            });
          }
        })
      );
  }

  configureIntegration(config: AsanaIntegrationConfigRequest): Observable<AsanaIntegrationResponse> {
    this.updateState({ isConfiguring: true });
    return this.http.post<AsanaIntegrationResponse>(`${this.apiUrl}/integration/configure`, config)
      .pipe(
        tap(response => {
          this.updateState({
            integration: response.integration,
            workspaces: response.workspaces,
            projects: response.projects,
            users: response.users,
            isConfiguring: false,
            error: null
          });
          this.notification.showSuccess('Asana integration configured successfully');
        }),
        tap({
          error: (error) => {
            this.updateState({ 
              isConfiguring: false, 
              error: error.message || 'Failed to configure integration'
            });
            this.notification.showError('Failed to configure Asana integration');
          }
        })
      );
  }

  deleteIntegration(): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/integration`)
      .pipe(
        tap(() => {
          this.updateState({
            integration: null,
            workspaces: [],
            projects: [],
            users: [],
            taskMappings: [],
            syncHistory: []
          });
          this.notification.showSuccess('Asana integration removed successfully');
        }),
        tap({
          error: (error) => {
            this.notification.showError('Failed to remove Asana integration');
          }
        })
      );
  }

  // OAuth Flow
  initiateOAuth(): Observable<{ auth_url: string; state: string }> {
    this.updateState({ oauthInProgress: true });
    return this.http.post<{ auth_url: string; state: string }>(`${this.apiUrl}/oauth/initiate`, {})
      .pipe(
        tap(() => {
          // OAuth progress will be handled by redirect
        }),
        tap({
          error: (error) => {
            this.updateState({ 
              oauthInProgress: false,
              error: error.message || 'Failed to initiate OAuth'
            });
          }
        })
      );
  }

  completeOAuth(code: string, state: string): Observable<AsanaIntegrationResponse> {
    return this.http.post<AsanaIntegrationResponse>(`${this.apiUrl}/oauth/callback`, {
      code,
      state
    }).pipe(
      tap(response => {
        this.updateState({
          integration: response.integration,
          workspaces: response.workspaces,
          projects: response.projects,
          users: response.users,
          oauthInProgress: false,
          error: null
        });
        this.notification.showSuccess('Successfully connected to Asana!');
      }),
      tap({
        error: (error) => {
          this.updateState({ 
            oauthInProgress: false,
            error: error.message || 'Failed to complete OAuth'
          });
          this.notification.showError('Failed to connect to Asana');
        }
      })
    );
  }

  refreshToken(): Observable<AsanaIntegration> {
    return this.http.post<AsanaIntegration>(`${this.apiUrl}/oauth/refresh`, {})
      .pipe(
        tap(integration => {
          this.updateState({ integration });
        })
      );
  }

  // Synchronization
  syncTasks(request: AsanaSyncRequest = {}): Observable<AsanaSyncResponse> {
    this.updateState({ isSyncing: true });
    return this.http.post<AsanaSyncResponse>(`${this.apiUrl}/sync`, request)
      .pipe(
        tap(response => {
          const currentHistory = this.stateSubject.value.syncHistory;
          this.updateState({
            syncHistory: [response, ...currentHistory],
            isSyncing: false,
            error: null
          });
          
          if (response.errors.length === 0) {
            this.notification.showSuccess(`Sync completed: ${response.tasks_processed} tasks processed`);
          } else {
            this.notification.showWarning(`Sync completed with ${response.errors.length} errors`);
          }
        }),
        tap({
          error: (error) => {
            this.updateState({ 
              isSyncing: false,
              error: error.message || 'Sync failed'
            });
            this.notification.showError('Task sync failed');
          }
        })
      );
  }

  getSyncHistory(): Observable<AsanaSyncResponse[]> {
    return this.http.get<AsanaSyncResponse[]>(`${this.apiUrl}/sync/history`)
      .pipe(
        tap(history => {
          this.updateState({ syncHistory: history });
        })
      );
  }

  getSyncStatus(syncId: string): Observable<AsanaSyncResponse> {
    return this.http.get<AsanaSyncResponse>(`${this.apiUrl}/sync/${syncId}/status`);
  }

  // Task Mappings
  getTaskMappings(limit = 50, offset = 0): Observable<AsanaTaskMapping[]> {
    const params = new HttpParams()
      .set('limit', limit.toString())
      .set('offset', offset.toString());

    return this.http.get<AsanaTaskMapping[]>(`${this.apiUrl}/task-mappings`, { params })
      .pipe(
        tap(mappings => {
          this.updateState({ taskMappings: mappings });
        })
      );
  }

  createTaskMapping(request: AsanaTaskMappingCreateRequest): Observable<AsanaTaskMappingResponse> {
    return this.http.post<AsanaTaskMappingResponse>(`${this.apiUrl}/task-mappings`, request)
      .pipe(
        tap(() => {
          // Refresh task mappings
          this.getTaskMappings().subscribe();
        })
      );
  }

  deleteTaskMapping(mappingId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/task-mappings/${mappingId}`)
      .pipe(
        tap(() => {
          // Refresh task mappings
          this.getTaskMappings().subscribe();
        })
      );
  }

  reprocessTask(mappingId: string): Observable<AsanaTaskMappingResponse> {
    return this.http.post<AsanaTaskMappingResponse>(`${this.apiUrl}/task-mappings/${mappingId}/reprocess`, {})
      .pipe(
        tap(() => {
          // Refresh task mappings
          this.getTaskMappings().subscribe();
        })
      );
  }

  // Asana Data
  getWorkspaces(): Observable<AsanaWorkspace[]> {
    return this.http.get<AsanaWorkspace[]>(`${this.apiUrl}/workspaces`);
  }

  getProjects(workspaceGid: string): Observable<AsanaProject[]> {
    return this.http.get<AsanaProject[]>(`${this.apiUrl}/workspaces/${workspaceGid}/projects`);
  }

  getUsers(workspaceGid: string): Observable<AsanaUser[]> {
    return this.http.get<AsanaUser[]>(`${this.apiUrl}/workspaces/${workspaceGid}/users`);
  }

  getTasks(projectGid: string, limit = 50): Observable<AsanaTask[]> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<AsanaTask[]>(`${this.apiUrl}/projects/${projectGid}/tasks`, { params });
  }

  // Webhooks
  setupWebhooks(): Observable<void> {
    return this.http.post<void>(`${this.apiUrl}/webhooks/setup`, {})
      .pipe(
        tap(() => {
          this.notification.showSuccess('Webhooks configured successfully');
        }),
        tap({
          error: () => {
            this.notification.showError('Failed to configure webhooks');
          }
        })
      );
  }

  removeWebhooks(): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/webhooks`)
      .pipe(
        tap(() => {
          this.notification.showSuccess('Webhooks removed successfully');
        })
      );
  }

  // Utility Methods
  private updateState(updates: Partial<AsanaIntegrationState>): void {
    const currentState = this.stateSubject.value;
    this.stateSubject.next({ ...currentState, ...updates });
  }

  private loadIntegration(): void {
    this.getIntegration().subscribe({
      error: () => {
        // Integration doesn't exist yet, which is fine
        this.updateState({ isLoading: false });
      }
    });
  }

  // Helper methods for UI
  isIntegrationActive(): boolean {
    return this.stateSubject.value.integration?.status === 'active';
  }

  getIntegrationStatus(): string {
    const integration = this.stateSubject.value.integration;
    if (!integration) return 'Not configured';
    return integration.status;
  }

  getLastSyncTime(): string | null {
    const integration = this.stateSubject.value.integration;
    if (!integration?.last_sync_at) return null;
    
    const lastSync = new Date(integration.last_sync_at);
    return lastSync.toLocaleString();
  }

  getSyncIntervalText(): string {
    const integration = this.stateSubject.value.integration;
    if (!integration) return 'Not configured';
    
    const hours = integration.sync_interval_hours;
    if (hours < 24) {
      return `Every ${hours} hour${hours !== 1 ? 's' : ''}`;
    } else {
      const days = Math.floor(hours / 24);
      return `Every ${days} day${days !== 1 ? 's' : ''}`;
    }
  }

  formatTaskStatus(status: string): string {
    const statusMap: { [key: string]: string } = {
      'pending': 'Pending',
      'processing': 'Processing',
      'completed': 'Completed',
      'failed': 'Failed',
      'skipped': 'Skipped'
    };
    return statusMap[status] || status;
  }

  getTaskStatusColor(status: string): string {
    const colorMap: { [key: string]: string } = {
      'pending': '#FF9800',
      'processing': '#2196F3',
      'completed': '#4CAF50',
      'failed': '#f44336',
      'skipped': '#9E9E9E'
    };
    return colorMap[status] || '#9E9E9E';
  }
}