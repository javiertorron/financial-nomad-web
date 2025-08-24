import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { LayoutComponent } from '../../shared/components/layout/layout.component';
import { AsanaService } from '../../core/services/asana.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  AsanaIntegrationState,
  AsanaIntegration,
  AsanaWorkspace,
  AsanaProject,
  AsanaUser,
  AsanaTaskMapping,
  AsanaSyncResponse,
  AsanaIntegrationConfigRequest
} from '../../core/types/asana.types';

@Component({
  selector: 'app-asana-integration',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, LayoutComponent],
  template: `
    <app-layout>
      <div class="asana-integration">
        <header class="integration-header">
          <div class="header-content">
            <div class="title-section">
              <h1>
                <i class="fas fa-tasks"></i>
                Asana Integration
              </h1>
              <p>Connect your Asana workspace to automatically manage financial tasks</p>
            </div>
            <div class="status-badge" [class]="getStatusClass()">
              {{ getStatusText() }}
            </div>
          </div>
        </header>

        <!-- OAuth Flow -->
        <div class="oauth-section" *ngIf="!state.integration && !state.oauthInProgress">
          <div class="oauth-card">
            <div class="oauth-content">
              <i class="fab fa-asana fa-3x"></i>
              <h2>Connect to Asana</h2>
              <p>Authorize Financial Nomad to access your Asana workspace to sync tasks and manage financial projects.</p>
              
              <div class="oauth-features">
                <div class="feature">
                  <i class="fas fa-sync"></i>
                  <span>Automatic task synchronization</span>
                </div>
                <div class="feature">
                  <i class="fas fa-dollar-sign"></i>
                  <span>Convert tasks to financial transactions</span>
                </div>
                <div class="feature">
                  <i class="fas fa-chart-line"></i>
                  <span>Budget tracking from project data</span>
                </div>
                <div class="feature">
                  <i class="fas fa-bell"></i>
                  <span>Real-time webhook notifications</span>
                </div>
              </div>

              <button 
                class="btn btn-primary btn-large"
                (click)="initiateOAuth()"
                [disabled]="state.isLoading">
                <i class="fab fa-asana"></i>
                Connect to Asana
              </button>
            </div>
          </div>
        </div>

        <!-- OAuth in Progress -->
        <div class="oauth-progress" *ngIf="state.oauthInProgress">
          <div class="progress-card">
            <div class="spinner"></div>
            <h3>Connecting to Asana...</h3>
            <p>Please complete the authorization in the popup window</p>
          </div>
        </div>

        <!-- Integration Configuration -->
        <div class="integration-content" *ngIf="state.integration">
          
          <!-- Integration Info -->
          <div class="integration-info">
            <div class="info-card">
              <h3>
                <i class="fas fa-info-circle"></i>
                Integration Status
              </h3>
              <div class="info-grid">
                <div class="info-item">
                  <label>Workspace:</label>
                  <span>{{ state.integration.workspace_name }}</span>
                </div>
                <div class="info-item">
                  <label>Last Sync:</label>
                  <span>{{ getLastSyncText() }}</span>
                </div>
                <div class="info-item">
                  <label>Auto Sync:</label>
                  <span class="sync-status" [class.enabled]="state.integration.auto_sync_enabled">
                    {{ state.integration.auto_sync_enabled ? 'Enabled' : 'Disabled' }}
                  </span>
                </div>
                <div class="info-item">
                  <label>Sync Interval:</label>
                  <span>{{ asanaService.getSyncIntervalText() }}</span>
                </div>
              </div>
            </div>

            <!-- Quick Actions -->
            <div class="actions-card">
              <h3>
                <i class="fas fa-bolt"></i>
                Quick Actions
              </h3>
              <div class="action-buttons">
                <button 
                  class="btn btn-primary"
                  (click)="syncNow()"
                  [disabled]="state.isSyncing">
                  <i class="fas fa-sync" [class.fa-spin]="state.isSyncing"></i>
                  {{ state.isSyncing ? 'Syncing...' : 'Sync Now' }}
                </button>
                <button 
                  class="btn btn-secondary"
                  (click)="showConfiguration = !showConfiguration">
                  <i class="fas fa-cog"></i>
                  Configure
                </button>
                <button 
                  class="btn btn-secondary"
                  (click)="refreshData()">
                  <i class="fas fa-redo"></i>
                  Refresh
                </button>
                <button 
                  class="btn btn-danger"
                  (click)="disconnectAsana()">
                  <i class="fas fa-unlink"></i>
                  Disconnect
                </button>
              </div>
            </div>
          </div>

          <!-- Configuration Form -->
          <div class="config-section" *ngIf="showConfiguration">
            <div class="config-card">
              <h3>
                <i class="fas fa-cog"></i>
                Integration Configuration
              </h3>
              
              <form [formGroup]="configForm" (ngSubmit)="saveConfiguration()">
                <div class="form-grid">
                  
                  <!-- Project Configuration -->
                  <div class="form-section">
                    <h4>Project Mapping</h4>
                    
                    <div class="form-group">
                      <label for="pending_project">Pending Tasks Project</label>
                      <select 
                        id="pending_project"
                        formControlName="pending_project_gid"
                        class="form-control">
                        <option value="">Select project for pending tasks</option>
                        <option 
                          *ngFor="let project of state.projects" 
                          [value]="project.gid">
                          {{ project.name }}
                        </option>
                      </select>
                    </div>

                    <div class="form-group">
                      <label for="processed_project">Processed Tasks Project</label>
                      <select 
                        id="processed_project"
                        formControlName="processed_project_gid"
                        class="form-control">
                        <option value="">Select project for processed tasks</option>
                        <option 
                          *ngFor="let project of state.projects" 
                          [value]="project.gid">
                          {{ project.name }}
                        </option>
                      </select>
                    </div>

                    <div class="form-group">
                      <label for="default_assignee">Default Assignee</label>
                      <select 
                        id="default_assignee"
                        formControlName="default_assignee_gid"
                        class="form-control">
                        <option value="">No default assignee</option>
                        <option 
                          *ngFor="let user of state.users" 
                          [value]="user.gid">
                          {{ user.name }}
                        </option>
                      </select>
                    </div>
                  </div>

                  <!-- Sync Configuration -->
                  <div class="form-section">
                    <h4>Sync Settings</h4>
                    
                    <div class="form-group">
                      <label for="sync_interval">Sync Interval (hours)</label>
                      <select 
                        id="sync_interval"
                        formControlName="sync_interval_hours"
                        class="form-control">
                        <option [value]="1">Every hour</option>
                        <option [value]="4">Every 4 hours</option>
                        <option [value]="8">Every 8 hours</option>
                        <option [value]="12">Every 12 hours</option>
                        <option [value]="24">Once daily</option>
                        <option [value]="48">Every 2 days</option>
                        <option [value]="168">Weekly</option>
                      </select>
                    </div>

                    <div class="form-group checkbox-group">
                      <label>
                        <input 
                          type="checkbox"
                          formControlName="auto_sync_enabled">
                        <span class="checkmark"></span>
                        Enable automatic synchronization
                      </label>
                    </div>

                    <div class="form-group checkbox-group">
                      <label>
                        <input 
                          type="checkbox"
                          formControlName="sync_completed_tasks">
                        <span class="checkmark"></span>
                        Sync completed tasks
                      </label>
                    </div>

                    <div class="form-group checkbox-group">
                      <label>
                        <input 
                          type="checkbox"
                          formControlName="create_transactions_from_tasks">
                        <span class="checkmark"></span>
                        Create transactions from tasks
                      </label>
                    </div>

                    <div class="form-group checkbox-group">
                      <label>
                        <input 
                          type="checkbox"
                          formControlName="archive_processed_tasks">
                        <span class="checkmark"></span>
                        Archive processed tasks
                      </label>
                    </div>
                  </div>
                </div>

                <div class="form-actions">
                  <button 
                    type="submit"
                    class="btn btn-primary"
                    [disabled]="!configForm.valid || state.isConfiguring">
                    <i class="fas fa-save"></i>
                    {{ state.isConfiguring ? 'Saving...' : 'Save Configuration' }}
                  </button>
                  <button 
                    type="button"
                    class="btn btn-secondary"
                    (click)="showConfiguration = false">
                    <i class="fas fa-times"></i>
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>

          <!-- Task Mappings -->
          <div class="mappings-section">
            <div class="mappings-card">
              <h3>
                <i class="fas fa-link"></i>
                Task Mappings
                <span class="count">({{ state.taskMappings.length }})</span>
              </h3>

              <div class="mappings-list" *ngIf="state.taskMappings.length > 0">
                <div 
                  class="mapping-item"
                  *ngFor="let mapping of state.taskMappings"
                  [class]="'status-' + mapping.status">
                  
                  <div class="mapping-info">
                    <div class="task-name">{{ mapping.task_name }}</div>
                    <div class="task-meta">
                      <span class="status-badge" [style.background-color]="asanaService.getTaskStatusColor(mapping.status)">
                        {{ asanaService.formatTaskStatus(mapping.status) }}
                      </span>
                      <span class="amount" *ngIf="mapping.extracted_amount">
                        €{{ mapping.extracted_amount | number:'1.2-2' }}
                      </span>
                      <span class="category" *ngIf="mapping.extracted_category">
                        {{ mapping.extracted_category }}
                      </span>
                    </div>
                    <div class="task-notes" *ngIf="mapping.task_notes">
                      {{ mapping.task_notes | slice:0:100 }}{{ mapping.task_notes.length > 100 ? '...' : '' }}
                    </div>
                  </div>

                  <div class="mapping-actions">
                    <button 
                      class="btn btn-sm btn-secondary"
                      (click)="reprocessMapping(mapping.id)"
                      *ngIf="mapping.status === 'failed'">
                      <i class="fas fa-redo"></i>
                      Retry
                    </button>
                    <button 
                      class="btn btn-sm btn-danger"
                      (click)="deleteMapping(mapping.id)">
                      <i class="fas fa-trash"></i>
                      Delete
                    </button>
                  </div>
                </div>
              </div>

              <div class="empty-state" *ngIf="state.taskMappings.length === 0">
                <i class="fas fa-tasks fa-2x"></i>
                <p>No task mappings found</p>
                <p class="help-text">Run a sync to create task mappings from your Asana projects</p>
              </div>
            </div>
          </div>

          <!-- Sync History -->
          <div class="history-section">
            <div class="history-card">
              <h3>
                <i class="fas fa-history"></i>
                Sync History
              </h3>

              <div class="history-list" *ngIf="state.syncHistory.length > 0">
                <div 
                  class="history-item"
                  *ngFor="let sync of state.syncHistory">
                  
                  <div class="sync-info">
                    <div class="sync-header">
                      <span class="sync-date">
                        {{ formatDate(sync.started_at) }}
                      </span>
                      <span class="sync-status" [class]="'status-' + sync.status">
                        {{ sync.status }}
                      </span>
                    </div>
                    <div class="sync-summary">
                      <span>{{ sync.tasks_processed }} tasks processed</span>
                      <span>{{ sync.transactions_created }} transactions created</span>
                      <span *ngIf="sync.errors.length > 0" class="error-count">
                        {{ sync.errors.length }} errors
                      </span>
                    </div>
                  </div>

                  <div class="sync-details" *ngIf="sync.summary">
                    <div class="detail-grid">
                      <div class="detail-item">
                        <span class="label">New:</span>
                        <span>{{ sync.summary.new_tasks }}</span>
                      </div>
                      <div class="detail-item">
                        <span class="label">Updated:</span>
                        <span>{{ sync.summary.updated_tasks }}</span>
                      </div>
                      <div class="detail-item">
                        <span class="label">Completed:</span>
                        <span>{{ sync.summary.completed_tasks }}</span>
                      </div>
                      <div class="detail-item">
                        <span class="label">Failed:</span>
                        <span>{{ sync.summary.failed_tasks }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="empty-state" *ngIf="state.syncHistory.length === 0">
                <i class="fas fa-history fa-2x"></i>
                <p>No sync history available</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Error Display -->
        <div class="error-message" *ngIf="state.error">
          <i class="fas fa-exclamation-triangle"></i>
          {{ state.error }}
        </div>

        <!-- Loading Overlay -->
        <div class="loading-overlay" *ngIf="state.isLoading">
          <div class="spinner"></div>
          <p>Loading integration data...</p>
        </div>
      </div>
    </app-layout>
  `,
  styles: [`
    .asana-integration {
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
    }

    .integration-header {
      margin-bottom: 30px;
    }

    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 20px;
    }

    .title-section h1 {
      margin: 0 0 10px 0;
      color: #333;
    }

    .title-section h1 i {
      margin-right: 10px;
      color: #f06a6a;
    }

    .title-section p {
      margin: 0;
      color: #666;
      font-size: 16px;
    }

    .status-badge {
      padding: 8px 16px;
      border-radius: 20px;
      font-weight: 500;
      font-size: 14px;
    }

    .status-badge.active {
      background: #e8f5e8;
      color: #2e7d32;
    }

    .status-badge.inactive {
      background: #fff3e0;
      color: #f57c00;
    }

    .status-badge.error {
      background: #ffebee;
      color: #c62828;
    }

    /* OAuth Section */
    .oauth-section {
      text-align: center;
      margin-bottom: 40px;
    }

    .oauth-card {
      background: white;
      border-radius: 12px;
      padding: 40px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.1);
      max-width: 600px;
      margin: 0 auto;
    }

    .oauth-content i.fab {
      color: #f06a6a;
      margin-bottom: 20px;
    }

    .oauth-content h2 {
      margin: 0 0 15px 0;
      color: #333;
    }

    .oauth-features {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
      margin: 30px 0;
    }

    .feature {
      display: flex;
      align-items: center;
      gap: 10px;
      text-align: left;
    }

    .feature i {
      color: #4CAF50;
      width: 20px;
    }

    .btn-large {
      padding: 15px 30px;
      font-size: 16px;
      margin-top: 20px;
    }

    /* Progress */
    .oauth-progress {
      text-align: center;
      margin: 40px 0;
    }

    .progress-card {
      background: white;
      border-radius: 12px;
      padding: 40px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }

    /* Integration Content */
    .integration-info {
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
      margin-bottom: 30px;
    }

    .info-card, .actions-card {
      background: white;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .info-card h3, .actions-card h3 {
      margin: 0 0 15px 0;
      display: flex;
      align-items: center;
      gap: 8px;
      color: #333;
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 15px;
    }

    .info-item {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .info-item label {
      font-weight: 500;
      color: #666;
      font-size: 14px;
    }

    .info-item span {
      font-size: 16px;
      color: #333;
    }

    .sync-status.enabled {
      color: #4CAF50;
      font-weight: 500;
    }

    .action-buttons {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    /* Configuration */
    .config-section {
      margin-bottom: 30px;
    }

    .config-card {
      background: white;
      border-radius: 8px;
      padding: 25px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
      gap: 30px;
    }

    .form-section h4 {
      margin: 0 0 20px 0;
      color: #333;
      border-bottom: 2px solid #f0f0f0;
      padding-bottom: 10px;
    }

    .form-group {
      margin-bottom: 20px;
    }

    .form-group label {
      display: block;
      margin-bottom: 8px;
      font-weight: 500;
      color: #333;
    }

    .form-control {
      width: 100%;
      padding: 12px;
      border: 2px solid #e0e0e0;
      border-radius: 6px;
      font-size: 14px;
      transition: border-color 0.2s;
    }

    .form-control:focus {
      outline: none;
      border-color: #2196F3;
    }

    .checkbox-group {
      display: flex;
      align-items: center;
    }

    .checkbox-group label {
      display: flex;
      align-items: center;
      cursor: pointer;
      margin-bottom: 0;
    }

    .checkbox-group input[type="checkbox"] {
      margin-right: 10px;
    }

    .form-actions {
      display: flex;
      gap: 15px;
      margin-top: 25px;
      padding-top: 20px;
      border-top: 1px solid #eee;
    }

    /* Task Mappings */
    .mappings-card, .history-card {
      background: white;
      border-radius: 8px;
      padding: 20px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      margin-bottom: 20px;
    }

    .mappings-card h3, .history-card h3 {
      margin: 0 0 20px 0;
      display: flex;
      align-items: center;
      gap: 8px;
      color: #333;
    }

    .count {
      background: #e3f2fd;
      color: #1976d2;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 500;
      margin-left: 10px;
    }

    .mapping-item, .history-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 15px;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      margin-bottom: 10px;
      transition: box-shadow 0.2s;
    }

    .mapping-item:hover, .history-item:hover {
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .mapping-info, .sync-info {
      flex: 1;
    }

    .task-name {
      font-weight: 500;
      margin-bottom: 5px;
      color: #333;
    }

    .task-meta, .sync-summary {
      display: flex;
      gap: 15px;
      margin-bottom: 5px;
    }

    .status-badge {
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
      color: white;
      font-weight: 500;
    }

    .amount {
      color: #4CAF50;
      font-weight: 500;
    }

    .category {
      color: #666;
      font-style: italic;
    }

    .task-notes {
      font-size: 13px;
      color: #666;
      line-height: 1.4;
    }

    .mapping-actions {
      display: flex;
      gap: 8px;
    }

    /* Sync History */
    .sync-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }

    .sync-date {
      font-weight: 500;
      color: #333;
    }

    .sync-status {
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
    }

    .sync-status.status-completed {
      background: #e8f5e8;
      color: #2e7d32;
    }

    .sync-status.status-failed {
      background: #ffebee;
      color: #c62828;
    }

    .sync-summary {
      font-size: 14px;
      color: #666;
    }

    .error-count {
      color: #f44336;
      font-weight: 500;
    }

    .sync-details {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid #f0f0f0;
    }

    .detail-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
      gap: 15px;
    }

    .detail-item {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
    }

    .detail-item .label {
      color: #666;
    }

    /* Empty States */
    .empty-state {
      text-align: center;
      padding: 40px 20px;
      color: #666;
    }

    .empty-state i {
      color: #bbb;
      margin-bottom: 15px;
    }

    .help-text {
      font-size: 14px;
      color: #999;
    }

    /* Common Elements */
    .btn {
      padding: 8px 16px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 14px;
      font-weight: 500;
      transition: all 0.2s;
    }

    .btn-primary {
      background: #2196F3;
      color: white;
    }

    .btn-secondary {
      background: #f5f5f5;
      color: #333;
    }

    .btn-danger {
      background: #f44336;
      color: white;
    }

    .btn-sm {
      padding: 4px 8px;
      font-size: 12px;
    }

    .btn:hover:not(:disabled) {
      opacity: 0.9;
      transform: translateY(-1px);
    }

    .btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .spinner {
      width: 32px;
      height: 32px;
      border: 3px solid #f3f3f3;
      border-top: 3px solid #2196F3;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin: 0 auto 15px;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .loading-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(255,255,255,0.9);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .error-message {
      background: #ffebee;
      color: #c62828;
      padding: 15px;
      border-radius: 6px;
      margin: 20px 0;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    @media (max-width: 768px) {
      .integration-info {
        grid-template-columns: 1fr;
      }
      
      .form-grid {
        grid-template-columns: 1fr;
      }
      
      .action-buttons {
        flex-direction: column;
      }
      
      .mapping-item, .history-item {
        flex-direction: column;
        align-items: stretch;
        gap: 15px;
      }
    }
  `]
})
export class AsanaIntegrationComponent implements OnInit, OnDestroy {
  state: AsanaIntegrationState = {
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
  };

  configForm: FormGroup;
  showConfiguration = false;
  private destroy$ = new Subject<void>();

  constructor(
    public asanaService: AsanaService,
    private fb: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private notification: NotificationService
  ) {
    this.configForm = this.createConfigForm();
  }

  ngOnInit() {
    // Subscribe to Asana service state
    this.asanaService.state$
      .pipe(takeUntil(this.destroy$))
      .subscribe(state => {
        this.state = state;
        this.updateConfigForm();
      });

    // Handle OAuth callback
    this.route.queryParams.subscribe(params => {
      if (params['code'] && params['state']) {
        this.completeOAuth(params['code'], params['state']);
      }
    });

    // Load initial data
    this.loadData();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private createConfigForm(): FormGroup {
    return this.fb.group({
      workspace_gid: ['', Validators.required],
      pending_project_gid: [''],
      processed_project_gid: [''],
      default_assignee_gid: [''],
      expense_tag_gids: [[]],
      income_tag_gids: [[]],
      budget_custom_field_gid: [''],
      amount_custom_field_gid: [''],
      category_custom_field_gid: [''],
      sync_interval_hours: [24, [Validators.required, Validators.min(1)]],
      auto_sync_enabled: [true],
      sync_completed_tasks: [false],
      create_transactions_from_tasks: [true],
      archive_processed_tasks: [false]
    });
  }

  private updateConfigForm(): void {
    if (this.state.integration) {
      this.configForm.patchValue({
        workspace_gid: this.state.integration.workspace_gid,
        pending_project_gid: this.state.integration.pending_project_gid,
        processed_project_gid: this.state.integration.processed_project_gid,
        default_assignee_gid: this.state.integration.default_assignee_gid,
        expense_tag_gids: this.state.integration.expense_tag_gids,
        income_tag_gids: this.state.integration.income_tag_gids,
        budget_custom_field_gid: this.state.integration.budget_custom_field_gid,
        amount_custom_field_gid: this.state.integration.amount_custom_field_gid,
        category_custom_field_gid: this.state.integration.category_custom_field_gid,
        sync_interval_hours: this.state.integration.sync_interval_hours,
        auto_sync_enabled: this.state.integration.auto_sync_enabled,
        sync_completed_tasks: this.state.integration.sync_completed_tasks,
        create_transactions_from_tasks: this.state.integration.create_transactions_from_tasks,
        archive_processed_tasks: this.state.integration.archive_processed_tasks
      });
    }
  }

  private loadData(): void {
    if (this.state.integration) {
      this.asanaService.getTaskMappings().subscribe();
      this.asanaService.getSyncHistory().subscribe();
    }
  }

  // OAuth Flow
  initiateOAuth(): void {
    this.asanaService.initiateOAuth().subscribe(response => {
      window.location.href = response.auth_url;
    });
  }

  completeOAuth(code: string, state: string): void {
    this.asanaService.completeOAuth(code, state).subscribe({
      next: () => {
        this.router.navigate([], { 
          relativeTo: this.route,
          queryParams: {}
        });
        this.loadData();
      }
    });
  }

  // Actions
  syncNow(): void {
    this.asanaService.syncTasks().subscribe({
      next: () => {
        this.loadData();
      }
    });
  }

  refreshData(): void {
    this.asanaService.getIntegration().subscribe({
      next: () => {
        this.loadData();
      }
    });
  }

  disconnectAsana(): void {
    if (confirm('Are you sure you want to disconnect from Asana? This will remove all configuration and task mappings.')) {
      this.asanaService.deleteIntegration().subscribe({
        next: () => {
          this.showConfiguration = false;
        }
      });
    }
  }

  saveConfiguration(): void {
    if (this.configForm.valid) {
      const config: AsanaIntegrationConfigRequest = this.configForm.value;
      this.asanaService.configureIntegration(config).subscribe({
        next: () => {
          this.showConfiguration = false;
        }
      });
    }
  }

  // Task Mapping Actions
  reprocessMapping(mappingId: string): void {
    this.asanaService.reprocessTask(mappingId).subscribe();
  }

  deleteMapping(mappingId: string): void {
    if (confirm('Are you sure you want to delete this task mapping?')) {
      this.asanaService.deleteTaskMapping(mappingId).subscribe();
    }
  }

  // Utility Methods
  getStatusClass(): string {
    if (!this.state.integration) return 'inactive';
    return this.state.integration.status;
  }

  getStatusText(): string {
    return this.asanaService.getIntegrationStatus();
  }

  getLastSyncText(): string {
    return this.asanaService.getLastSyncTime() || 'Never';
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleString();
  }
}