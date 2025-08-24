import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTabsModule } from '@angular/material/tabs';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { LayoutComponent } from '../../shared/components/layout/layout.component';
import { ConfigService } from '../../core/services/config.service';
import { NotificationService } from '../../core/services/notification.service';

export interface SystemConfiguration {
  // Application Settings
  app_name: string;
  app_version: string;
  environment: 'development' | 'staging' | 'production';
  debug_mode: boolean;
  maintenance_mode: boolean;
  
  // Database Settings
  database: {
    connection_timeout: number;
    max_connections: number;
    enable_query_logging: boolean;
    backup_retention_days: number;
  };
  
  // Security Settings
  security: {
    session_timeout_minutes: number;
    password_requirements: {
      min_length: number;
      require_uppercase: boolean;
      require_lowercase: boolean;
      require_numbers: boolean;
      require_special_chars: boolean;
    };
    max_login_attempts: number;
    lockout_duration_minutes: number;
    enable_2fa: boolean;
    allowed_origins: string[];
  };
  
  // Email Settings
  email: {
    smtp_host: string;
    smtp_port: number;
    smtp_username: string;
    smtp_password: string;
    from_address: string;
    from_name: string;
    enable_ssl: boolean;
    enable_notifications: boolean;
  };
  
  // File Storage Settings
  storage: {
    max_upload_size_mb: number;
    allowed_file_types: string[];
    storage_path: string;
    enable_compression: boolean;
    auto_cleanup: boolean;
    cleanup_interval_days: number;
  };
  
  // API Settings
  api: {
    rate_limit_per_minute: number;
    enable_cors: boolean;
    cors_origins: string[];
    api_version: string;
    enable_swagger: boolean;
    request_timeout_seconds: number;
  };
  
  // Logging Settings
  logging: {
    log_level: 'debug' | 'info' | 'warn' | 'error';
    enable_file_logging: boolean;
    log_retention_days: number;
    max_log_size_mb: number;
    enable_remote_logging: boolean;
    remote_logging_endpoint?: string;
  };
  
  // Backup Settings
  backup: {
    auto_backup_enabled: boolean;
    backup_frequency_hours: number;
    backup_retention_count: number;
    backup_location: 'local' | 'cloud';
    cloud_provider?: 'gcs' | 'aws' | 'azure';
    encrypt_backups: boolean;
  };
  
  // Integration Settings
  integrations: {
    google: {
      client_id?: string;
      client_secret?: string;
      enabled: boolean;
    };
    asana: {
      client_id?: string;
      client_secret?: string;
      enabled: boolean;
    };
    webhooks: {
      enabled: boolean;
      timeout_seconds: number;
      retry_attempts: number;
      signature_secret?: string;
    };
  };
  
  // Feature Flags
  features: {
    advanced_analytics: boolean;
    export_functionality: boolean;
    multi_currency: boolean;
    budget_forecasting: boolean;
    bill_reminders: boolean;
    investment_tracking: boolean;
    expense_categorization_ai: boolean;
    dark_mode: boolean;
  };
}

@Component({
  selector: 'app-system-config',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTabsModule,
    MatChipsModule,
    MatExpansionModule,
    LayoutComponent
  ],
  template: `
    <app-layout>
      <div class="system-config">
        <header class="config-header">
          <div class="header-content">
            <h1>
              <mat-icon>settings</mat-icon>
              System Configuration
            </h1>
            <p>Configure system-wide settings and preferences</p>
          </div>
          <div class="header-actions">
            <button mat-button (click)="resetToDefaults()" color="warn">
              <mat-icon>restore</mat-icon>
              Reset to Defaults
            </button>
            <button mat-raised-button (click)="saveConfiguration()" color="primary" [disabled]="!hasChanges">
              <mat-icon>save</mat-icon>
              Save Configuration
            </button>
          </div>
        </header>

        <mat-tab-group [(selectedIndex)]="activeTab">
          <!-- Application Settings -->
          <mat-tab label="Application">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Application Settings</mat-card-title>
                  <mat-card-subtitle>Basic application configuration</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <form [formGroup]="appForm" class="config-form">
                    <div class="form-row">
                      <mat-form-field>
                        <mat-label>Application Name</mat-label>
                        <input matInput formControlName="app_name" placeholder="Financial Nomad">
                      </mat-form-field>
                      
                      <mat-form-field>
                        <mat-label>Environment</mat-label>
                        <mat-select formControlName="environment">
                          <mat-option value="development">Development</mat-option>
                          <mat-option value="staging">Staging</mat-option>
                          <mat-option value="production">Production</mat-option>
                        </mat-select>
                      </mat-form-field>
                    </div>

                    <div class="form-toggles">
                      <div class="toggle-item">
                        <mat-slide-toggle formControlName="debug_mode">
                          Debug Mode
                        </mat-slide-toggle>
                        <span class="toggle-description">Enable detailed logging and error reporting</span>
                      </div>
                      
                      <div class="toggle-item">
                        <mat-slide-toggle formControlName="maintenance_mode">
                          Maintenance Mode
                        </mat-slide-toggle>
                        <span class="toggle-description">Temporarily disable public access</span>
                      </div>
                    </div>
                  </form>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Security Settings -->
          <mat-tab label="Security">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Security Configuration</mat-card-title>
                  <mat-card-subtitle>Authentication and security policies</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <form [formGroup]="securityForm" class="config-form">
                    <div class="form-section">
                      <h3>Session Management</h3>
                      <div class="form-row">
                        <mat-form-field>
                          <mat-label>Session Timeout (minutes)</mat-label>
                          <input matInput type="number" formControlName="session_timeout_minutes" min="5" max="1440">
                        </mat-form-field>
                        
                        <mat-form-field>
                          <mat-label>Max Login Attempts</mat-label>
                          <input matInput type="number" formControlName="max_login_attempts" min="1" max="10">
                        </mat-form-field>
                        
                        <mat-form-field>
                          <mat-label>Lockout Duration (minutes)</mat-label>
                          <input matInput type="number" formControlName="lockout_duration_minutes" min="1" max="60">
                        </mat-form-field>
                      </div>
                    </div>

                    <div class="form-section">
                      <h3>Password Requirements</h3>
                      <div formGroupName="password_requirements">
                        <div class="form-row">
                          <mat-form-field>
                            <mat-label>Minimum Length</mat-label>
                            <input matInput type="number" formControlName="min_length" min="6" max="50">
                          </mat-form-field>
                        </div>
                        
                        <div class="form-toggles">
                          <div class="toggle-item">
                            <mat-slide-toggle formControlName="require_uppercase">
                              Require Uppercase Letters
                            </mat-slide-toggle>
                          </div>
                          
                          <div class="toggle-item">
                            <mat-slide-toggle formControlName="require_lowercase">
                              Require Lowercase Letters
                            </mat-slide-toggle>
                          </div>
                          
                          <div class="toggle-item">
                            <mat-slide-toggle formControlName="require_numbers">
                              Require Numbers
                            </mat-slide-toggle>
                          </div>
                          
                          <div class="toggle-item">
                            <mat-slide-toggle formControlName="require_special_chars">
                              Require Special Characters
                            </mat-slide-toggle>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div class="form-section">
                      <div class="toggle-item">
                        <mat-slide-toggle formControlName="enable_2fa">
                          Enable Two-Factor Authentication
                        </mat-slide-toggle>
                        <span class="toggle-description">Require 2FA for all user accounts</span>
                      </div>
                    </div>
                  </form>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Database Settings -->
          <mat-tab label="Database">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Database Configuration</mat-card-title>
                  <mat-card-subtitle>Database connection and performance settings</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <form [formGroup]="databaseForm" class="config-form">
                    <div class="form-row">
                      <mat-form-field>
                        <mat-label>Connection Timeout (seconds)</mat-label>
                        <input matInput type="number" formControlName="connection_timeout" min="5" max="300">
                      </mat-form-field>
                      
                      <mat-form-field>
                        <mat-label>Max Connections</mat-label>
                        <input matInput type="number" formControlName="max_connections" min="1" max="1000">
                      </mat-form-field>
                      
                      <mat-form-field>
                        <mat-label>Backup Retention (days)</mat-label>
                        <input matInput type="number" formControlName="backup_retention_days" min="1" max="365">
                      </mat-form-field>
                    </div>

                    <div class="form-toggles">
                      <div class="toggle-item">
                        <mat-slide-toggle formControlName="enable_query_logging">
                          Enable Query Logging
                        </mat-slide-toggle>
                        <span class="toggle-description">Log database queries for debugging (impacts performance)</span>
                      </div>
                    </div>
                  </form>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- API Settings -->
          <mat-tab label="API">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>API Configuration</mat-card-title>
                  <mat-card-subtitle>API security and performance settings</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <form [formGroup]="apiForm" class="config-form">
                    <div class="form-row">
                      <mat-form-field>
                        <mat-label>Rate Limit (requests/minute)</mat-label>
                        <input matInput type="number" formControlName="rate_limit_per_minute" min="10" max="10000">
                      </mat-form-field>
                      
                      <mat-form-field>
                        <mat-label>Request Timeout (seconds)</mat-label>
                        <input matInput type="number" formControlName="request_timeout_seconds" min="5" max="300">
                      </mat-form-field>
                      
                      <mat-form-field>
                        <mat-label>API Version</mat-label>
                        <input matInput formControlName="api_version" placeholder="v1">
                      </mat-form-field>
                    </div>

                    <div class="form-toggles">
                      <div class="toggle-item">
                        <mat-slide-toggle formControlName="enable_cors">
                          Enable CORS
                        </mat-slide-toggle>
                        <span class="toggle-description">Allow cross-origin requests</span>
                      </div>
                      
                      <div class="toggle-item">
                        <mat-slide-toggle formControlName="enable_swagger">
                          Enable Swagger Documentation
                        </mat-slide-toggle>
                        <span class="toggle-description">Provide API documentation endpoint</span>
                      </div>
                    </div>

                    <mat-form-field class="full-width" *ngIf="apiForm.get('enable_cors')?.value">
                      <mat-label>Allowed Origins (comma-separated)</mat-label>
                      <textarea matInput formControlName="cors_origins_text" rows="3"
                                placeholder="https://example.com, https://app.example.com"></textarea>
                    </mat-form-field>
                  </form>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Storage Settings -->
          <mat-tab label="Storage">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>File Storage Configuration</mat-card-title>
                  <mat-card-subtitle>File upload and storage management</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <form [formGroup]="storageForm" class="config-form">
                    <div class="form-row">
                      <mat-form-field>
                        <mat-label>Max Upload Size (MB)</mat-label>
                        <input matInput type="number" formControlName="max_upload_size_mb" min="1" max="1000">
                      </mat-form-field>
                      
                      <mat-form-field>
                        <mat-label>Storage Path</mat-label>
                        <input matInput formControlName="storage_path" placeholder="/uploads">
                      </mat-form-field>
                      
                      <mat-form-field>
                        <mat-label>Cleanup Interval (days)</mat-label>
                        <input matInput type="number" formControlName="cleanup_interval_days" min="1" max="365">
                      </mat-form-field>
                    </div>

                    <mat-form-field class="full-width">
                      <mat-label>Allowed File Types (comma-separated)</mat-label>
                      <textarea matInput formControlName="allowed_file_types_text" rows="2"
                                placeholder="jpg, png, pdf, csv, xlsx"></textarea>
                    </mat-form-field>

                    <div class="form-toggles">
                      <div class="toggle-item">
                        <mat-slide-toggle formControlName="enable_compression">
                          Enable File Compression
                        </mat-slide-toggle>
                        <span class="toggle-description">Compress uploaded files to save storage space</span>
                      </div>
                      
                      <div class="toggle-item">
                        <mat-slide-toggle formControlName="auto_cleanup">
                          Enable Auto Cleanup
                        </mat-slide-toggle>
                        <span class="toggle-description">Automatically remove temporary files</span>
                      </div>
                    </div>
                  </form>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>

          <!-- Feature Flags -->
          <mat-tab label="Features">
            <div class="tab-content">
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Feature Configuration</mat-card-title>
                  <mat-card-subtitle>Enable or disable application features</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <form [formGroup]="featuresForm" class="config-form">
                    <div class="features-grid">
                      <div class="feature-item">
                        <mat-slide-toggle formControlName="advanced_analytics">
                          Advanced Analytics
                        </mat-slide-toggle>
                        <span class="feature-description">Detailed financial analytics and insights</span>
                      </div>
                      
                      <div class="feature-item">
                        <mat-slide-toggle formControlName="export_functionality">
                          Export Functionality
                        </mat-slide-toggle>
                        <span class="feature-description">Data export in various formats</span>
                      </div>
                      
                      <div class="feature-item">
                        <mat-slide-toggle formControlName="multi_currency">
                          Multi-Currency Support
                        </mat-slide-toggle>
                        <span class="feature-description">Support for multiple currencies</span>
                      </div>
                      
                      <div class="feature-item">
                        <mat-slide-toggle formControlName="budget_forecasting">
                          Budget Forecasting
                        </mat-slide-toggle>
                        <span class="feature-description">Predictive budget analysis</span>
                      </div>
                      
                      <div class="feature-item">
                        <mat-slide-toggle formControlName="bill_reminders">
                          Bill Reminders
                        </mat-slide-toggle>
                        <span class="feature-description">Automated bill payment reminders</span>
                      </div>
                      
                      <div class="feature-item">
                        <mat-slide-toggle formControlName="investment_tracking">
                          Investment Tracking
                        </mat-slide-toggle>
                        <span class="feature-description">Portfolio and investment management</span>
                      </div>
                      
                      <div class="feature-item">
                        <mat-slide-toggle formControlName="expense_categorization_ai">
                          AI Expense Categorization
                        </mat-slide-toggle>
                        <span class="feature-description">Automatic expense categorization using AI</span>
                      </div>
                      
                      <div class="feature-item">
                        <mat-slide-toggle formControlName="dark_mode">
                          Dark Mode
                        </mat-slide-toggle>
                        <span class="feature-description">Dark theme for better user experience</span>
                      </div>
                    </div>
                  </form>
                </mat-card-content>
              </mat-card>
            </div>
          </mat-tab>
        </mat-tab-group>
      </div>
    </app-layout>
  `,
  styles: [`
    .system-config {
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
    }

    .config-header {
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

    .tab-content {
      padding: 20px 0;
    }

    .config-form {
      margin: 16px 0;
    }

    .form-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
      margin-bottom: 20px;
    }

    .form-section {
      margin-bottom: 30px;
      padding-bottom: 20px;
      border-bottom: 1px solid #eee;
    }

    .form-section:last-child {
      border-bottom: none;
    }

    .form-section h3 {
      margin: 0 0 16px 0;
      color: #333;
      font-size: 18px;
      font-weight: 500;
    }

    .form-toggles {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .toggle-item {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .toggle-description {
      font-size: 14px;
      color: #666;
      margin-left: 32px;
    }

    .features-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;
    }

    .feature-item {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 16px;
      background: #f8f9fa;
      border-radius: 8px;
    }

    .feature-description {
      font-size: 14px;
      color: #666;
      margin-left: 32px;
    }

    .full-width {
      width: 100%;
    }

    mat-form-field {
      width: 100%;
    }

    mat-card {
      margin-bottom: 24px;
    }

    mat-card-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    @media (max-width: 768px) {
      .system-config {
        padding: 16px;
      }

      .config-header {
        flex-direction: column;
        align-items: stretch;
      }

      .header-actions {
        justify-content: stretch;
      }

      .form-row {
        grid-template-columns: 1fr;
      }

      .features-grid {
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class SystemConfigComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  
  activeTab = 0;
  hasChanges = false;
  
  // Form groups for different configuration sections
  appForm: FormGroup;
  securityForm: FormGroup;
  databaseForm: FormGroup;
  apiForm: FormGroup;
  storageForm: FormGroup;
  featuresForm: FormGroup;
  
  // Current system configuration
  currentConfig: SystemConfiguration | null = null;

  constructor(
    private fb: FormBuilder,
    private configService: ConfigService,
    private notification: NotificationService
  ) {
    this.createForms();
  }

  ngOnInit(): void {
    this.loadConfiguration();
    this.setupFormChangeListeners();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private createForms(): void {
    this.appForm = this.fb.group({
      app_name: ['Financial Nomad', Validators.required],
      environment: ['production', Validators.required],
      debug_mode: [false],
      maintenance_mode: [false]
    });

    this.securityForm = this.fb.group({
      session_timeout_minutes: [30, [Validators.required, Validators.min(5), Validators.max(1440)]],
      max_login_attempts: [5, [Validators.required, Validators.min(1), Validators.max(10)]],
      lockout_duration_minutes: [15, [Validators.required, Validators.min(1), Validators.max(60)]],
      enable_2fa: [false],
      password_requirements: this.fb.group({
        min_length: [8, [Validators.required, Validators.min(6), Validators.max(50)]],
        require_uppercase: [true],
        require_lowercase: [true],
        require_numbers: [true],
        require_special_chars: [false]
      })
    });

    this.databaseForm = this.fb.group({
      connection_timeout: [30, [Validators.required, Validators.min(5), Validators.max(300)]],
      max_connections: [100, [Validators.required, Validators.min(1), Validators.max(1000)]],
      backup_retention_days: [30, [Validators.required, Validators.min(1), Validators.max(365)]],
      enable_query_logging: [false]
    });

    this.apiForm = this.fb.group({
      rate_limit_per_minute: [100, [Validators.required, Validators.min(10), Validators.max(10000)]],
      request_timeout_seconds: [30, [Validators.required, Validators.min(5), Validators.max(300)]],
      api_version: ['v1', Validators.required],
      enable_cors: [true],
      enable_swagger: [false],
      cors_origins_text: ['']
    });

    this.storageForm = this.fb.group({
      max_upload_size_mb: [10, [Validators.required, Validators.min(1), Validators.max(1000)]],
      storage_path: ['/uploads', Validators.required],
      cleanup_interval_days: [7, [Validators.required, Validators.min(1), Validators.max(365)]],
      enable_compression: [true],
      auto_cleanup: [true],
      allowed_file_types_text: ['jpg,png,pdf,csv,xlsx']
    });

    this.featuresForm = this.fb.group({
      advanced_analytics: [true],
      export_functionality: [true],
      multi_currency: [false],
      budget_forecasting: [true],
      bill_reminders: [true],
      investment_tracking: [false],
      expense_categorization_ai: [false],
      dark_mode: [true]
    });
  }

  private setupFormChangeListeners(): void {
    const allForms = [
      this.appForm,
      this.securityForm,
      this.databaseForm,
      this.apiForm,
      this.storageForm,
      this.featuresForm
    ];

    allForms.forEach(form => {
      form.valueChanges.pipe(
        takeUntil(this.destroy$)
      ).subscribe(() => {
        this.hasChanges = true;
      });
    });
  }

  private loadConfiguration(): void {
    // In a real application, this would load from backend
    // For now, using mock data
    this.currentConfig = this.getDefaultConfiguration();
    this.populateFormsWithConfig(this.currentConfig);
  }

  private getDefaultConfiguration(): SystemConfiguration {
    return {
      app_name: 'Financial Nomad',
      app_version: '1.0.0',
      environment: 'production',
      debug_mode: false,
      maintenance_mode: false,
      database: {
        connection_timeout: 30,
        max_connections: 100,
        enable_query_logging: false,
        backup_retention_days: 30
      },
      security: {
        session_timeout_minutes: 30,
        password_requirements: {
          min_length: 8,
          require_uppercase: true,
          require_lowercase: true,
          require_numbers: true,
          require_special_chars: false
        },
        max_login_attempts: 5,
        lockout_duration_minutes: 15,
        enable_2fa: false,
        allowed_origins: ['https://financial-nomad.com']
      },
      email: {
        smtp_host: '',
        smtp_port: 587,
        smtp_username: '',
        smtp_password: '',
        from_address: '',
        from_name: 'Financial Nomad',
        enable_ssl: true,
        enable_notifications: true
      },
      storage: {
        max_upload_size_mb: 10,
        allowed_file_types: ['jpg', 'png', 'pdf', 'csv', 'xlsx'],
        storage_path: '/uploads',
        enable_compression: true,
        auto_cleanup: true,
        cleanup_interval_days: 7
      },
      api: {
        rate_limit_per_minute: 100,
        enable_cors: true,
        cors_origins: ['*'],
        api_version: 'v1',
        enable_swagger: false,
        request_timeout_seconds: 30
      },
      logging: {
        log_level: 'info',
        enable_file_logging: true,
        log_retention_days: 30,
        max_log_size_mb: 100,
        enable_remote_logging: false
      },
      backup: {
        auto_backup_enabled: true,
        backup_frequency_hours: 24,
        backup_retention_count: 7,
        backup_location: 'local',
        encrypt_backups: true
      },
      integrations: {
        google: {
          enabled: true
        },
        asana: {
          enabled: false
        },
        webhooks: {
          enabled: true,
          timeout_seconds: 30,
          retry_attempts: 3
        }
      },
      features: {
        advanced_analytics: true,
        export_functionality: true,
        multi_currency: false,
        budget_forecasting: true,
        bill_reminders: true,
        investment_tracking: false,
        expense_categorization_ai: false,
        dark_mode: true
      }
    };
  }

  private populateFormsWithConfig(config: SystemConfiguration): void {
    this.appForm.patchValue({
      app_name: config.app_name,
      environment: config.environment,
      debug_mode: config.debug_mode,
      maintenance_mode: config.maintenance_mode
    });

    this.securityForm.patchValue({
      session_timeout_minutes: config.security.session_timeout_minutes,
      max_login_attempts: config.security.max_login_attempts,
      lockout_duration_minutes: config.security.lockout_duration_minutes,
      enable_2fa: config.security.enable_2fa,
      password_requirements: config.security.password_requirements
    });

    this.databaseForm.patchValue(config.database);

    this.apiForm.patchValue({
      ...config.api,
      cors_origins_text: config.api.cors_origins.join(', ')
    });

    this.storageForm.patchValue({
      ...config.storage,
      allowed_file_types_text: config.storage.allowed_file_types.join(',')
    });

    this.featuresForm.patchValue(config.features);

    this.hasChanges = false;
  }

  saveConfiguration(): void {
    if (!this.validateAllForms()) {
      this.notification.showError('Please correct the validation errors before saving');
      return;
    }

    const updatedConfig = this.buildConfigurationFromForms();
    
    // In a real application, this would send to backend
    console.log('Saving configuration:', updatedConfig);
    
    this.currentConfig = updatedConfig;
    this.hasChanges = false;
    
    this.notification.showSuccess('System configuration saved successfully');
  }

  resetToDefaults(): void {
    if (confirm('Are you sure you want to reset all settings to default values? This action cannot be undone.')) {
      const defaultConfig = this.getDefaultConfiguration();
      this.populateFormsWithConfig(defaultConfig);
      this.notification.showInfo('Configuration reset to default values');
    }
  }

  private validateAllForms(): boolean {
    const forms = [
      this.appForm,
      this.securityForm,
      this.databaseForm,
      this.apiForm,
      this.storageForm,
      this.featuresForm
    ];

    let allValid = true;
    forms.forEach(form => {
      form.markAllAsTouched();
      if (!form.valid) {
        allValid = false;
      }
    });

    return allValid;
  }

  private buildConfigurationFromForms(): SystemConfiguration {
    const apiFormValue = this.apiForm.value;
    const storageFormValue = this.storageForm.value;
    
    return {
      ...this.currentConfig!,
      ...this.appForm.value,
      security: {
        ...this.currentConfig!.security,
        ...this.securityForm.value
      },
      database: {
        ...this.currentConfig!.database,
        ...this.databaseForm.value
      },
      api: {
        ...this.currentConfig!.api,
        ...apiFormValue,
        cors_origins: apiFormValue.cors_origins_text
          ? apiFormValue.cors_origins_text.split(',').map((s: string) => s.trim())
          : []
      },
      storage: {
        ...this.currentConfig!.storage,
        ...storageFormValue,
        allowed_file_types: storageFormValue.allowed_file_types_text
          ? storageFormValue.allowed_file_types_text.split(',').map((s: string) => s.trim())
          : []
      },
      features: {
        ...this.currentConfig!.features,
        ...this.featuresForm.value
      }
    };
  }
}