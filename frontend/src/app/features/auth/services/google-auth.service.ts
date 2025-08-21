import { Injectable, inject } from '@angular/core';
import { Observable, fromEvent, map, take } from 'rxjs';

import { ConfigService } from '../../../core/services/config.service';
import { GoogleUser } from '../../../core/types/auth.types';

declare global {
  interface Window {
    google: any;
    gapi: any;
  }
}

@Injectable({
  providedIn: 'root'
})
export class GoogleAuthService {
  private readonly configService = inject(ConfigService);
  private isInitialized = false;
  private auth2: any;

  async initialize(): Promise<void> {
    if (this.isInitialized) {
      return;
    }

    try {
      // Cargar Google Identity Services
      await this.loadGoogleScript();
      
      // Obtener client ID del servicio de configuración
      const googleClientId = this.configService.getGoogleClientId();
      
      // Inicializar con el client ID
      if (window.google && googleClientId) {
        window.google.accounts.id.initialize({
          client_id: googleClientId,
          callback: () => {} // Se manejará en el componente
        });
        
        this.isInitialized = true;
        console.log('Google Auth initialized with Client ID:', googleClientId);
      } else {
        throw new Error('Google Auth no está disponible o Client ID no configurado');
      }
    } catch (error) {
      console.error('Error inicializando Google Auth:', error);
      throw error;
    }
  }

  private loadGoogleScript(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (window.google) {
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      
      script.onload = () => {
        // Esperar a que Google Identity Services esté disponible
        const checkGoogleLoaded = () => {
          if (window.google && window.google.accounts) {
            resolve();
          } else {
            setTimeout(checkGoogleLoaded, 100);
          }
        };
        checkGoogleLoaded();
      };
      
      script.onerror = () => reject(new Error('Error cargando Google Auth script'));
      
      document.head.appendChild(script);
    });
  }

  renderSignInButton(elementId: string): void {
    if (!this.isInitialized) {
      throw new Error('Google Auth no está inicializado');
    }

    window.google.accounts.id.renderButton(
      document.getElementById(elementId),
      {
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        logo_alignment: 'left',
        width: 300
      }
    );
  }

  signInWithPopup(): Promise<string> {
    return new Promise((resolve, reject) => {
      if (!this.isInitialized) {
        reject(new Error('Google Auth no está inicializado'));
        return;
      }

      // Configurar callback temporal para el popup
      const originalCallback = window.google.accounts.id.callback;
      
      window.google.accounts.id.initialize({
        client_id: this.configService.getGoogleClientId(),
        callback: (response: any) => {
          // Restaurar callback original
          window.google.accounts.id.callback = originalCallback;
          
          if (response.credential) {
            resolve(response.credential);
          } else {
            reject(new Error('No se recibió credential de Google'));
          }
        }
      });

      // Mostrar prompt de One Tap
      window.google.accounts.id.prompt((notification: any) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
          // Si One Tap no se muestra, usar popup
          this.fallbackToPopup().then(resolve).catch(reject);
        }
      });
    });
  }

  private fallbackToPopup(): Promise<string> {
    return new Promise((resolve, reject) => {
      // Crear un botón temporal oculto para triggear el popup
      const tempDiv = document.createElement('div');
      tempDiv.style.position = 'absolute';
      tempDiv.style.top = '-9999px';
      tempDiv.id = 'temp-google-signin';
      document.body.appendChild(tempDiv);

      const originalCallback = window.google.accounts.id.callback;
      
      window.google.accounts.id.initialize({
        client_id: this.configService.getGoogleClientId(),
        callback: (response: any) => {
          window.google.accounts.id.callback = originalCallback;
          document.body.removeChild(tempDiv);
          
          if (response.credential) {
            resolve(response.credential);
          } else {
            reject(new Error('Login cancelado o falló'));
          }
        }
      });

      window.google.accounts.id.renderButton(tempDiv, {
        theme: 'outline',
        size: 'large'
      });

      // Simular click en el botón
      setTimeout(() => {
        const button = tempDiv.querySelector('div[role="button"]') as HTMLElement;
        if (button) {
          button.click();
        } else {
          document.body.removeChild(tempDiv);
          reject(new Error('No se pudo crear el botón de Google'));
        }
      }, 100);
    });
  }

  signOut(): Promise<void> {
    return new Promise((resolve) => {
      if (window.google && window.google.accounts) {
        window.google.accounts.id.disableAutoSelect();
      }
      resolve();
    });
  }

  isAvailable(): boolean {
    return this.isInitialized && !!window.google && !!this.configService.getGoogleClientId();
  }
}