import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

import { LayoutComponent } from '../../shared/components/layout/layout.component';
import { PWAService, PWAState } from '../../core/services/pwa.service';
import { NotificationService } from '../../core/services/notification.service';

@Component({
  selector: 'app-pwa-settings',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatSlideToggleModule,
    MatProgressBarModule,
    MatChipsModule,
    MatExpansionModule,
    LayoutComponent
  ],
  template: `
    <app-layout>
      <div class="pwa-settings">
        <header class="settings-header">
          <div class="header-content">
            <h1>
              <mat-icon>settings_applications</mat-icon>
              PWA Settings
            </h1>
            <p>Configure Progressive Web App features and offline capabilities</p>
          </div>
        </header>

        <!-- PWA Status Overview -->
        <mat-card class="status-card">
          <mat-card-header>
            <mat-card-title>
              <mat-icon>info</mat-icon>
              App Status
            </mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="status-grid">
              <div class="status-item">
                <mat-icon [class]="pwaState.isInstalled ? 'status-enabled' : 'status-disabled'">
                  {{ pwaState.isInstalled ? 'check_circle' : 'radio_button_unchecked' }}
                </mat-icon>
                <div class="status-info">
                  <span class="status-label">Installed as PWA</span>
                  <span class="status-description">
                    {{ pwaState.isInstalled ? 'App is installed on device' : 'App runs in browser only' }}
                  </span>
                </div>
              </div>

              <div class="status-item">
                <mat-icon [class]="pwaState.serviceWorkerActive ? 'status-enabled' : 'status-disabled'">
                  {{ pwaState.serviceWorkerActive ? 'check_circle' : 'radio_button_unchecked' }}
                </mat-icon>
                <div class="status-info">
                  <span class="status-label">Service Worker</span>
                  <span class="status-description">
                    {{ pwaState.serviceWorkerActive ? 'Active and caching resources' : 'Not available' }}
                  </span>
                </div>
              </div>

              <div class="status-item">
                <mat-icon [class]="!pwaState.isOffline ? 'status-enabled' : 'status-disabled'">
                  {{ !pwaState.isOffline ? 'wifi' : 'wifi_off' }}
                </mat-icon>
                <div class="status-info">
                  <span class="status-label">Network Status</span>
                  <span class="status-description">
                    {{ !pwaState.isOffline ? 'Online' : 'Offline' }}
                  </span>
                </div>
              </div>

              <div class="status-item">
                <mat-icon [class]="pwaState.notificationsEnabled ? 'status-enabled' : 'status-disabled'">
                  {{ pwaState.notificationsEnabled ? 'notifications_active' : 'notifications_off' }}
                </mat-icon>
                <div class="status-info">
                  <span class="status-label">Notifications</span>
                  <span class="status-description">
                    {{ pwaState.notificationsEnabled ? 'Enabled' : 'Disabled or not supported' }}
                  </span>
                </div>
              </div>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Installation Section -->
        <mat-card class="installation-card" *ngIf="!pwaState.isInstalled">
          <mat-card-header>
            <mat-card-title>
              <mat-icon>get_app</mat-icon>
              Install App
            </mat-card-title>
            <mat-card-subtitle>
              Install Financial Nomad as a native app for better performance and offline access
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <div class="installation-benefits">
              <div class="benefit">
                <mat-icon>flash_on</mat-icon>
                <span>Faster loading and better performance</span>
              </div>
              <div class="benefit">
                <mat-icon>offline_bolt</mat-icon>
                <span>Work offline with cached data</span>
              </div>
              <div class="benefit">
                <mat-icon>home</mat-icon>
                <span>Quick access from home screen</span>
              </div>
              <div class="benefit">
                <mat-icon>notifications</mat-icon>
                <span>Push notifications for important updates</span>
              </div>
            </div>
          </mat-card-content>
          <mat-card-actions>
            <button 
              mat-raised-button 
              color="primary"
              [disabled]="!pwaState.isInstallable"
              (click)="installApp()">
              <mat-icon>get_app</mat-icon>
              {{ pwaState.isInstallable ? 'Install App' : 'Installation Not Available' }}
            </button>
          </mat-card-actions>
        </mat-card>

        <!-- Update Section -->
        <mat-card class="update-card" *ngIf="pwaState.updateAvailable">
          <mat-card-header>
            <mat-card-title>
              <mat-icon>system_update</mat-icon>
              Update Available
            </mat-card-title>
            <mat-card-subtitle>
              A new version of Financial Nomad is ready to install
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <p>Update now to get the latest features, improvements, and security fixes.</p>
          </mat-card-content>
          <mat-card-actions>
            <button mat-raised-button color="primary" (click)="updateApp()">
              <mat-icon>system_update</mat-icon>
              Update Now
            </button>
            <button mat-button (click)="checkForUpdates()">
              <mat-icon>refresh</mat-icon>
              Check for Updates
            </button>
          </mat-card-actions>
        </mat-card>

        <!-- Notifications Section -->
        <mat-card class="notifications-card">
          <mat-card-header>
            <mat-card-title>
              <mat-icon>notifications</mat-icon>
              Push Notifications
            </mat-card-title>
            <mat-card-subtitle>
              Configure notifications for financial updates and reminders
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <div class="notification-settings">
              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-label">Enable Push Notifications</span>
                  <span class="setting-description">
                    Receive notifications about transactions, budgets, and reminders
                  </span>
                </div>
                <mat-slide-toggle
                  [checked]="pwaState.notificationsEnabled"
                  [disabled]="!pwaState.notificationsSupported"
                  (change)="toggleNotifications($event.checked)">
                </mat-slide-toggle>
              </div>

              <div class="notification-types" *ngIf="pwaState.notificationsEnabled">
                <h4>Notification Types</h4>
                <form [formGroup]="notificationForm">
                  <div class="notification-type">
                    <mat-slide-toggle formControlName="transactionAlerts">
                      Transaction Alerts
                    </mat-slide-toggle>
                    <span class="type-description">New transactions and payment confirmations</span>
                  </div>
                  
                  <div class="notification-type">
                    <mat-slide-toggle formControlName="budgetWarnings">
                      Budget Warnings
                    </mat-slide-toggle>
                    <span class="type-description">When approaching or exceeding budget limits</span>
                  </div>
                  
                  <div class="notification-type">
                    <mat-slide-toggle formControlName="billReminders">
                      Bill Reminders
                    </mat-slide-toggle>
                    <span class="type-description">Upcoming bills and payment due dates</span>
                  </div>
                  
                  <div class="notification-type">
                    <mat-slide-toggle formControlName="monthlyReports">
                      Monthly Reports
                    </mat-slide-toggle>
                    <span class="type-description">Monthly financial summaries and insights</span>
                  </div>
                  
                  <div class="notification-type">
                    <mat-slide-toggle formControlName="securityAlerts">
                      Security Alerts
                    </mat-slide-toggle>
                    <span class="type-description">Login attempts and security-related notifications</span>
                  </div>
                </form>
              </div>
            </div>

            <div class="notification-test" *ngIf="pwaState.notificationsEnabled">
              <button mat-button (click)="testNotification()">
                <mat-icon>test_tube</mat-icon>
                Test Notification
              </button>
            </div>
          </mat-card-content>
        </mat-card>

        <!-- Offline & Cache Section -->
        <mat-card class="offline-card">
          <mat-card-header>
            <mat-card-title>
              <mat-icon>offline_bolt</mat-icon>
              Offline & Cache
            </mat-card-title>
            <mat-card-subtitle>
              Manage offline functionality and cached data
            </mat-card-subtitle>
          </mat-card-header>
          <mat-card-content>
            <div class="cache-info">
              <div class="cache-stat">
                <span class="cache-label">Cache Size</span>
                <span class="cache-value">{{ formatBytes(cacheSize) }}</span>
              </div>
              <div class="cache-stat">
                <span class="cache-label">Offline Status</span>
                <mat-chip [class]="!pwaState.isOffline ? 'online-chip' : 'offline-chip'">
                  {{ !pwaState.isOffline ? 'Online' : 'Offline' }}
                </mat-chip>
              </div>
            </div>

            <mat-expansion-panel>
              <mat-expansion-panel-header>
                <mat-panel-title>
                  <mat-icon>storage</mat-icon>
                  Cached Data
                </mat-panel-title>
                <mat-panel-description>
                  View and manage offline data storage
                </mat-panel-description>
              </mat-expansion-panel-header>
              
              <div class="cached-data-info">
                <p>The following data is cached for offline access:</p>
                <ul class="cached-items">
                  <li><mat-icon>account_balance</mat-icon> Account balances and basic information</li>
                  <li><mat-icon>receipt</mat-icon> Recent transactions (last 30 days)</li>
                  <li><mat-icon>category</mat-icon> Categories and budget information</li>
                  <li><mat-icon>settings</mat-icon> App settings and preferences</li>
                  <li><mat-icon>person</mat-icon> User profile data</li>
                </ul>
                
                <div class="cache-actions">
                  <button mat-button (click)="syncOfflineData()" [disabled]="pwaState.isOffline">
                    <mat-icon>sync</mat-icon>
                    Sync Offline Changes
                  </button>
                  <button mat-button color="warn" (click)="clearCache()">
                    <mat-icon>clear_all</mat-icon>
                    Clear All Cache
                  </button>
                </div>
              </div>
            </mat-expansion-panel>
          </mat-card-content>
        </mat-card>

        <!-- Advanced Settings -->
        <mat-card class="advanced-card">
          <mat-card-header>
            <mat-card-title>
              <mat-icon>tune</mat-icon>
              Advanced Settings
            </mat-card-title>
          </mat-card-header>
          <mat-card-content>
            <div class="advanced-settings">
              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-label">Background Sync</span>
                  <span class="setting-description">
                    Sync data automatically when connection is restored
                  </span>
                </div>
                <mat-slide-toggle
                  [checked]="backgroundSyncEnabled"
                  (change)="toggleBackgroundSync($event.checked)">
                </mat-slide-toggle>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-label">Offline Mode</span>
                  <span class="setting-description">
                    Allow app to function when internet is unavailable
                  </span>
                </div>
                <mat-slide-toggle
                  [checked]="offlineModeEnabled"
                  (change)="toggleOfflineMode($event.checked)">
                </mat-slide-toggle>
              </div>

              <div class="setting-item">
                <div class="setting-info">
                  <span class="setting-label">Auto Updates</span>
                  <span class="setting-description">
                    Automatically install app updates when available
                  </span>
                </div>
                <mat-slide-toggle
                  [checked]="autoUpdatesEnabled"
                  (change)="toggleAutoUpdates($event.checked)">
                </mat-slide-toggle>
              </div>
            </div>
          </mat-card-content>
        </mat-card>
      </div>
    </app-layout>
  `,
  styles: [`
    .pwa-settings {
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
    }

    .settings-header {
      margin-bottom: 30px;
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

    mat-card {
      margin-bottom: 24px;
    }

    mat-card-title {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* Status Grid */
    .status-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 20px;
    }

    .status-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
      background: #f8f9fa;
      border-radius: 8px;
    }

    .status-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .status-label {
      font-weight: 500;
      color: #333;
    }

    .status-description {
      font-size: 14px;
      color: #666;
    }

    .status-enabled {
      color: #4CAF50;
    }

    .status-disabled {
      color: #9e9e9e;
    }

    /* Installation Benefits */
    .installation-benefits {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
      margin: 20px 0;
    }

    .benefit {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #4CAF50;
    }

    .benefit mat-icon {
      font-size: 20px;
      width: 20px;
      height: 20px;
    }

    /* Notification Settings */
    .notification-settings {
      margin: 16px 0;
    }

    .setting-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 0;
      border-bottom: 1px solid #eee;
    }

    .setting-item:last-child {
      border-bottom: none;
    }

    .setting-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
      flex: 1;
    }

    .setting-label {
      font-weight: 500;
      color: #333;
    }

    .setting-description {
      font-size: 14px;
      color: #666;
    }

    .notification-types {
      margin-top: 20px;
      padding-top: 20px;
      border-top: 1px solid #eee;
    }

    .notification-types h4 {
      margin: 0 0 16px 0;
      color: #333;
    }

    .notification-type {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: 16px;
    }

    .type-description {
      font-size: 14px;
      color: #666;
      margin-left: 32px;
    }

    .notification-test {
      margin-top: 16px;
      padding-top: 16px;
      border-top: 1px solid #eee;
    }

    /* Cache Info */
    .cache-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .cache-stat {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .cache-label {
      font-size: 14px;
      color: #666;
    }

    .cache-value {
      font-weight: 500;
      color: #333;
    }

    .online-chip {
      background-color: #E8F5E8;
      color: #4CAF50;
    }

    .offline-chip {
      background-color: #FFEBEE;
      color: #f44336;
    }

    .cached-data-info {
      padding: 16px 0;
    }

    .cached-items {
      list-style: none;
      padding: 0;
      margin: 16px 0;
    }

    .cached-items li {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 0;
      color: #666;
    }

    .cached-items mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
      color: #4CAF50;
    }

    .cache-actions {
      display: flex;
      gap: 12px;
      margin-top: 20px;
    }

    /* Advanced Settings */
    .advanced-settings {
      margin: 16px 0;
    }

    @media (max-width: 768px) {
      .pwa-settings {
        padding: 16px;
      }

      .status-grid {
        grid-template-columns: 1fr;
      }

      .installation-benefits {
        grid-template-columns: 1fr;
      }

      .cache-info {
        flex-direction: column;
        align-items: stretch;
        gap: 16px;
      }

      .cache-actions {
        flex-direction: column;
      }
    }
  `]
})
export class PWASettingsComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  pwaState: PWAState = {
    isInstallable: false,
    isInstalled: false,
    isOffline: false,
    hasUpdate: false,
    updateAvailable: false,
    notificationsEnabled: false,
    notificationsSupported: false,
    serviceWorkerActive: false
  };

  notificationForm: FormGroup;
  cacheSize = 0;
  backgroundSyncEnabled = true;
  offlineModeEnabled = true;
  autoUpdatesEnabled = false;

  constructor(
    private pwaService: PWAService,
    private notification: NotificationService,
    private fb: FormBuilder
  ) {
    this.notificationForm = this.createNotificationForm();
  }

  ngOnInit(): void {
    this.loadPWAState();
    this.loadCacheSize();
    this.loadSettings();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private createNotificationForm(): FormGroup {
    return this.fb.group({
      transactionAlerts: [true],
      budgetWarnings: [true],
      billReminders: [true],
      monthlyReports: [false],
      securityAlerts: [true]
    });
  }

  private loadPWAState(): void {
    this.pwaService.state$.pipe(
      takeUntil(this.destroy$)
    ).subscribe(state => {
      this.pwaState = state;
    });
  }

  private async loadCacheSize(): Promise<void> {
    this.cacheSize = await this.pwaService.getCacheSize();
  }

  private loadSettings(): void {
    // Load settings from localStorage or service
    const settings = localStorage.getItem('pwa-settings');
    if (settings) {
      const parsed = JSON.parse(settings);
      this.backgroundSyncEnabled = parsed.backgroundSync ?? true;
      this.offlineModeEnabled = parsed.offlineMode ?? true;
      this.autoUpdatesEnabled = parsed.autoUpdates ?? false;
    }

    // Load notification preferences
    const notificationSettings = localStorage.getItem('notification-settings');
    if (notificationSettings) {
      this.notificationForm.patchValue(JSON.parse(notificationSettings));
    }
  }

  private saveSettings(): void {
    const settings = {
      backgroundSync: this.backgroundSyncEnabled,
      offlineMode: this.offlineModeEnabled,
      autoUpdates: this.autoUpdatesEnabled
    };
    localStorage.setItem('pwa-settings', JSON.stringify(settings));
  }

  private saveNotificationSettings(): void {
    localStorage.setItem('notification-settings', JSON.stringify(this.notificationForm.value));
  }

  // PWA Actions
  async installApp(): Promise<void> {
    await this.pwaService.installApp();
  }

  async updateApp(): Promise<void> {
    await this.pwaService.updateApp();
  }

  async checkForUpdates(): Promise<void> {
    // Force check for updates
    if (this.pwaService.serviceWorkerActive) {
      this.notification.showInfo('Checking for updates...');
      // Implementation would trigger update check
    }
  }

  // Notification Actions
  async toggleNotifications(enabled: boolean): Promise<void> {
    if (enabled) {
      const granted = await this.pwaService.requestNotificationPermission();
      if (granted) {
        // Subscribe to push notifications
        const vapidKey = 'YOUR_VAPID_KEY'; // This should come from config
        await this.pwaService.subscribeToPush(vapidKey);
      }
    } else {
      await this.pwaService.unsubscribeFromPush();
    }
    
    this.saveNotificationSettings();
  }

  async testNotification(): Promise<void> {
    await this.pwaService.showLocalNotification(
      'Test Notification',
      {
        body: 'This is a test notification from Financial Nomad',
        icon: '/assets/icons/icon-192x192.png',
        tag: 'test-notification'
      }
    );
  }

  // Cache Actions
  async syncOfflineData(): Promise<void> {
    await this.pwaService.syncOfflineData();
  }

  async clearCache(): Promise<void> {
    if (confirm('This will clear all cached data and you may need to reload the app. Continue?')) {
      await this.pwaService.clearCache();
      this.cacheSize = 0;
    }
  }

  // Settings Actions
  toggleBackgroundSync(enabled: boolean): void {
    this.backgroundSyncEnabled = enabled;
    this.saveSettings();
    this.notification.showInfo(`Background sync ${enabled ? 'enabled' : 'disabled'}`);
  }

  toggleOfflineMode(enabled: boolean): void {
    this.offlineModeEnabled = enabled;
    this.saveSettings();
    this.notification.showInfo(`Offline mode ${enabled ? 'enabled' : 'disabled'}`);
  }

  toggleAutoUpdates(enabled: boolean): void {
    this.autoUpdatesEnabled = enabled;
    this.saveSettings();
    this.notification.showInfo(`Auto updates ${enabled ? 'enabled' : 'disabled'}`);
  }

  // Utility Methods
  formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
}