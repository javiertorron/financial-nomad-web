import { Injectable } from '@angular/core';
import { SwUpdate, SwPush } from '@angular/service-worker';
import { Observable, BehaviorSubject, fromEvent } from 'rxjs';
import { map, startWith } from 'rxjs/operators';

import { NotificationService } from './notification.service';

export interface PWAInstallEvent extends Event {
  prompt(): Promise<{ outcome: 'accepted' | 'dismissed' }>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export interface PWAState {
  isInstallable: boolean;
  isInstalled: boolean;
  isOffline: boolean;
  hasUpdate: boolean;
  updateAvailable: boolean;
  notificationsEnabled: boolean;
  notificationsSupported: boolean;
  serviceWorkerActive: boolean;
}

export interface PushSubscriptionData {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
  user_id?: string;
  device_type: string;
  browser: string;
  created_at: Date;
}

@Injectable({
  providedIn: 'root'
})
export class PWAService {
  private installPromptEvent: PWAInstallEvent | null = null;
  
  private stateSubject = new BehaviorSubject<PWAState>({
    isInstallable: false,
    isInstalled: false,
    isOffline: false,
    hasUpdate: false,
    updateAvailable: false,
    notificationsEnabled: false,
    notificationsSupported: this.isPushNotificationSupported(),
    serviceWorkerActive: false
  });

  public state$ = this.stateSubject.asObservable();
  
  // Observable for online/offline status
  public online$: Observable<boolean> = fromEvent(window, 'online')
    .pipe(
      map(() => navigator.onLine),
      startWith(navigator.onLine)
    );

  public offline$: Observable<boolean> = this.online$.pipe(
    map(online => !online)
  );

  constructor(
    private swUpdate: SwUpdate,
    private swPush: SwPush,
    private notification: NotificationService
  ) {
    this.initialize();
  }

  private initialize(): void {
    this.checkInstallability();
    this.checkServiceWorkerStatus();
    this.checkUpdateAvailable();
    this.monitorOnlineStatus();
    this.checkNotificationPermission();
    this.checkInstallationStatus();
  }

  // Installation Methods
  private checkInstallability(): void {
    window.addEventListener('beforeinstallprompt', (e: Event) => {
      e.preventDefault();
      this.installPromptEvent = e as PWAInstallEvent;
      this.updateState({ isInstallable: true });
      this.notification.showInfo('App can be installed for better experience');
    });
  }

  private checkInstallationStatus(): void {
    // Check if app is running in standalone mode (installed as PWA)
    const isInstalled = window.matchMedia('(display-mode: standalone)').matches ||
                       (window.navigator as any).standalone === true ||
                       document.referrer.includes('android-app://');
    
    this.updateState({ isInstalled });

    // Listen for app installation
    window.addEventListener('appinstalled', () => {
      this.updateState({ isInstalled: true, isInstallable: false });
      this.notification.showSuccess('App installed successfully!');
      this.installPromptEvent = null;
    });
  }

  async installApp(): Promise<boolean> {
    if (!this.installPromptEvent) {
      this.notification.showWarning('Installation is not available at the moment');
      return false;
    }

    try {
      const result = await this.installPromptEvent.prompt();
      const outcome = await this.installPromptEvent.userChoice;
      
      if (outcome.outcome === 'accepted') {
        this.notification.showSuccess('App installation started');
        return true;
      } else {
        this.notification.showInfo('App installation cancelled');
        return false;
      }
    } catch (error) {
      console.error('Error during app installation:', error);
      this.notification.showError('Failed to install app');
      return false;
    } finally {
      this.installPromptEvent = null;
      this.updateState({ isInstallable: false });
    }
  }

  // Service Worker Methods
  private checkServiceWorkerStatus(): void {
    if (this.swUpdate.isEnabled) {
      this.updateState({ serviceWorkerActive: true });
      
      // Check for available updates
      this.swUpdate.available.subscribe(() => {
        this.updateState({ updateAvailable: true });
        this.notification.showInfo('New version available. Click to update.', {
          action: 'Update',
          duration: 0
        }).onAction().subscribe(() => {
          this.updateApp();
        });
      });

      // Handle activation of new version
      this.swUpdate.activated.subscribe(() => {
        this.notification.showSuccess('App updated to latest version!');
        this.updateState({ updateAvailable: false });
      });
    }
  }

  private checkUpdateAvailable(): void {
    if (this.swUpdate.isEnabled) {
      this.swUpdate.checkForUpdate().then(hasUpdate => {
        this.updateState({ hasUpdate });
      }).catch(error => {
        console.error('Error checking for updates:', error);
      });
    }
  }

  async updateApp(): Promise<void> {
    if (!this.swUpdate.isEnabled) {
      this.notification.showWarning('Updates are not supported');
      return;
    }

    try {
      await this.swUpdate.activateUpdate();
      window.location.reload();
    } catch (error) {
      console.error('Error updating app:', error);
      this.notification.showError('Failed to update app');
    }
  }

  // Online/Offline Methods
  private monitorOnlineStatus(): void {
    this.offline$.subscribe(isOffline => {
      this.updateState({ isOffline });
      
      if (isOffline) {
        this.notification.showWarning('You are now offline. Some features may be limited.');
      } else {
        this.notification.showSuccess('You are back online!');
      }
    });
  }

  // Push Notifications
  private isPushNotificationSupported(): boolean {
    return 'Notification' in window && 
           'serviceWorker' in navigator && 
           'PushManager' in window;
  }

  private checkNotificationPermission(): void {
    if (!this.isPushNotificationSupported()) {
      this.updateState({ notificationsSupported: false });
      return;
    }

    const permission = Notification.permission;
    const notificationsEnabled = permission === 'granted';
    
    this.updateState({ 
      notificationsEnabled,
      notificationsSupported: true 
    });
  }

  async requestNotificationPermission(): Promise<boolean> {
    if (!this.isPushNotificationSupported()) {
      this.notification.showWarning('Push notifications are not supported in this browser');
      return false;
    }

    try {
      const permission = await Notification.requestPermission();
      const granted = permission === 'granted';
      
      this.updateState({ notificationsEnabled: granted });
      
      if (granted) {
        this.notification.showSuccess('Notifications enabled successfully!');
      } else {
        this.notification.showWarning('Notification permission denied');
      }
      
      return granted;
    } catch (error) {
      console.error('Error requesting notification permission:', error);
      this.notification.showError('Failed to request notification permission');
      return false;
    }
  }

  async subscribeToPush(vapidKey: string): Promise<PushSubscriptionData | null> {
    if (!this.swPush.isEnabled) {
      this.notification.showWarning('Push notifications are not supported');
      return null;
    }

    try {
      const subscription = await this.swPush.requestSubscription({
        serverPublicKey: vapidKey
      });

      const subscriptionData: PushSubscriptionData = {
        endpoint: subscription.endpoint,
        keys: {
          p256dh: this.arrayBufferToBase64(subscription.getKey('p256dh')!),
          auth: this.arrayBufferToBase64(subscription.getKey('auth')!)
        },
        device_type: this.getDeviceType(),
        browser: this.getBrowserName(),
        created_at: new Date()
      };

      this.notification.showSuccess('Successfully subscribed to push notifications!');
      return subscriptionData;
    } catch (error) {
      console.error('Error subscribing to push notifications:', error);
      this.notification.showError('Failed to subscribe to push notifications');
      return null;
    }
  }

  async unsubscribeFromPush(): Promise<boolean> {
    if (!this.swPush.isEnabled) {
      return false;
    }

    try {
      const subscription = await this.swPush.subscription.toPromise();
      if (subscription) {
        const unsubscribed = await subscription.unsubscribe();
        if (unsubscribed) {
          this.notification.showSuccess('Unsubscribed from push notifications');
          return true;
        }
      }
      return false;
    } catch (error) {
      console.error('Error unsubscribing from push notifications:', error);
      this.notification.showError('Failed to unsubscribe from push notifications');
      return false;
    }
  }

  // Push notification message handling
  get pushMessages$(): Observable<any> {
    return this.swPush.messages;
  }

  get pushNotificationClicks$(): Observable<any> {
    return this.swPush.notificationClicks;
  }

  // Local Notifications
  async showLocalNotification(
    title: string,
    options: NotificationOptions = {}
  ): Promise<void> {
    if (!this.isPushNotificationSupported()) {
      console.warn('Local notifications are not supported');
      return;
    }

    if (Notification.permission !== 'granted') {
      const granted = await this.requestNotificationPermission();
      if (!granted) return;
    }

    try {
      const notification = new Notification(title, {
        icon: '/assets/icons/icon-192x192.png',
        badge: '/assets/icons/icon-96x96.png',
        ...options
      });

      notification.onclick = () => {
        window.focus();
        notification.close();
      };
    } catch (error) {
      console.error('Error showing local notification:', error);
    }
  }

  // Cache Management
  async clearCache(): Promise<void> {
    if ('caches' in window) {
      try {
        const cacheNames = await caches.keys();
        await Promise.all(
          cacheNames.map(cacheName => caches.delete(cacheName))
        );
        this.notification.showSuccess('App cache cleared successfully');
      } catch (error) {
        console.error('Error clearing cache:', error);
        this.notification.showError('Failed to clear app cache');
      }
    }
  }

  async getCacheSize(): Promise<number> {
    if (!('storage' in navigator) || !('estimate' in navigator.storage)) {
      return 0;
    }

    try {
      const estimate = await navigator.storage.estimate();
      return estimate.usage || 0;
    } catch (error) {
      console.error('Error getting cache size:', error);
      return 0;
    }
  }

  // Offline Data Sync
  async syncOfflineData(): Promise<void> {
    // This would sync any offline data when coming back online
    // Implementation would depend on your specific offline storage strategy
    console.log('Syncing offline data...');
    this.notification.showInfo('Syncing offline changes...');
    
    // Simulate sync process
    setTimeout(() => {
      this.notification.showSuccess('Offline data synced successfully!');
    }, 2000);
  }

  // Utility Methods
  private updateState(updates: Partial<PWAState>): void {
    const currentState = this.stateSubject.value;
    this.stateSubject.next({ ...currentState, ...updates });
  }

  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  private getDeviceType(): string {
    const userAgent = navigator.userAgent.toLowerCase();
    if (/android/.test(userAgent)) return 'android';
    if (/iphone|ipad|ipod/.test(userAgent)) return 'ios';
    if (/windows phone/.test(userAgent)) return 'windows-phone';
    return 'desktop';
  }

  private getBrowserName(): string {
    const userAgent = navigator.userAgent.toLowerCase();
    if (userAgent.includes('chrome')) return 'chrome';
    if (userAgent.includes('firefox')) return 'firefox';
    if (userAgent.includes('safari')) return 'safari';
    if (userAgent.includes('edge')) return 'edge';
    return 'unknown';
  }

  // Public getters for current state
  get isInstallable(): boolean {
    return this.stateSubject.value.isInstallable;
  }

  get isInstalled(): boolean {
    return this.stateSubject.value.isInstalled;
  }

  get isOffline(): boolean {
    return this.stateSubject.value.isOffline;
  }

  get hasUpdate(): boolean {
    return this.stateSubject.value.updateAvailable;
  }

  get notificationsEnabled(): boolean {
    return this.stateSubject.value.notificationsEnabled;
  }

  get serviceWorkerActive(): boolean {
    return this.stateSubject.value.serviceWorkerActive;
  }
}