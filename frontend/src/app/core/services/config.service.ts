import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, of } from 'rxjs';
import { tap, catchError } from 'rxjs/operators';

export interface AppConfig {
  googleClientId: string;
  apiUrl: string;
  environment: string;
  version: string;
  features: {
    enableAsanaIntegration: boolean;
    enableExportFeatures: boolean;
    enablePwaFeatures: boolean;
    enableOfflineMode: boolean;
  };
}

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  private readonly http = inject(HttpClient);
  
  private readonly _config = signal<AppConfig | null>(null);
  private readonly _isLoaded = signal(false);
  private readonly configSubject = new BehaviorSubject<AppConfig | null>(null);

  readonly config = this._config.asReadonly();
  readonly isLoaded = this._isLoaded.asReadonly();
  readonly config$ = this.configSubject.asObservable();

  // Configuración por defecto para fallback
  private readonly defaultConfig: AppConfig = {
    googleClientId: '783748328773-l80u4vhcmh90oa5d1fhf0mfhrvhppfhe.apps.googleusercontent.com',
    apiUrl: 'http://localhost:8080/api/v1',
    environment: 'development',
    version: '1.0.0',
    features: {
      enableAsanaIntegration: true,
      enableExportFeatures: true,
      enablePwaFeatures: true,
      enableOfflineMode: false
    }
  };

  loadConfig(): Observable<AppConfig> {
    return this.http.get<AppConfig>('http://localhost:8080/api/v1/config').pipe(
      tap(config => {
        this._config.set(config);
        this._isLoaded.set(true);
        this.configSubject.next(config);
        console.log('Config loaded:', config);
      }),
      catchError(error => {
        console.warn('Failed to load config from server, using defaults:', error);
        this._config.set(this.defaultConfig);
        this._isLoaded.set(true);
        this.configSubject.next(this.defaultConfig);
        return of(this.defaultConfig);
      })
    );
  }

  getGoogleClientId(): string {
    const config = this._config();
    return config?.googleClientId || this.defaultConfig.googleClientId;
  }

  getApiUrl(): string {
    const config = this._config();
    return config?.apiUrl || this.defaultConfig.apiUrl;
  }

  isFeatureEnabled(feature: keyof AppConfig['features']): boolean {
    const config = this._config();
    return config?.features[feature] || this.defaultConfig.features[feature];
  }
}