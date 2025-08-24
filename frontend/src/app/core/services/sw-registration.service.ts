import { Injectable } from '@angular/core';
import { SwUpdate } from '@angular/service-worker';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class SwRegistrationService {
  constructor(private swUpdate: SwUpdate) {}

  async registerServiceWorker(): Promise<void> {
    if (!('serviceWorker' in navigator) || !environment.production) {
      console.log('Service worker not supported or not in production');
      return;
    }

    try {
      const registration = await navigator.serviceWorker.register('/ngsw-worker.js');
      console.log('Service Worker registered successfully:', registration);

      // Handle service worker updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              console.log('New service worker installed, prompting user to refresh');
              this.promptUserToRefresh();
            }
          });
        }
      });

      // Listen for messages from service worker
      navigator.serviceWorker.addEventListener('message', (event) => {
        this.handleServiceWorkerMessage(event);
      });

    } catch (error) {
      console.error('Service Worker registration failed:', error);
    }
  }

  private promptUserToRefresh(): void {
    if (confirm('A new version of the app is available. Refresh to update?')) {
      window.location.reload();
    }
  }

  private handleServiceWorkerMessage(event: MessageEvent): void {
    console.log('Message from service worker:', event.data);
    
    // Handle different types of messages from service worker
    switch (event.data.type) {
      case 'CACHE_UPDATED':
        console.log('Cache has been updated');
        break;
      case 'OFFLINE':
        console.log('App is now offline');
        break;
      case 'ONLINE':
        console.log('App is now online');
        break;
      default:
        console.log('Unknown message type:', event.data.type);
    }
  }

  async unregisterServiceWorker(): Promise<void> {
    if (!('serviceWorker' in navigator)) {
      return;
    }

    try {
      const registrations = await navigator.serviceWorker.getRegistrations();
      for (const registration of registrations) {
        await registration.unregister();
        console.log('Service Worker unregistered:', registration);
      }
    } catch (error) {
      console.error('Service Worker unregistration failed:', error);
    }
  }

  async skipWaiting(): Promise<void> {
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'SKIP_WAITING' });
    }
  }
}