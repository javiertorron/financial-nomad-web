import { Injectable, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, throwError, of, EMPTY } from 'rxjs';
import { map, tap, catchError, switchMap } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { 
  User, 
  LoginRequest, 
  LoginResponse, 
  RegisterRequest,
  RegisterResponse,
  TokenInfo
} from '../types/auth.types';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly baseUrl = environment.apiUrl;

  // Signals para estado reactivo
  private readonly _user = signal<User | null>(null);
  private readonly _isLoading = signal(false);
  private readonly _error = signal<string | null>(null);

  // Getters públicos readonly
  readonly user = this._user.asReadonly();
  readonly isLoading = this._isLoading.asReadonly();
  readonly error = this._error.asReadonly();
  readonly isAuthenticated = computed(() => this._user() !== null);

  // Constantes
  private readonly TOKEN_KEY = 'financial_nomad_token';
  private readonly USER_KEY = 'financial_nomad_user';

  constructor() {
    this.loadStoredAuth();
  }

  initializeAuth(): void {
    this.loadStoredAuth();
    
    // Verificar si el token sigue siendo válido
    if (this.getStoredToken()) {
      this.validateToken().subscribe({
        next: (user) => {
          this._user.set(user);
          this._error.set(null);
        },
        error: () => {
          this.logout();
        }
      });
    }
  }

  register(email: string, password: string, name: string, invitationCode: string): Observable<RegisterResponse> {
    this._isLoading.set(true);
    this._error.set(null);

    const registerRequest: RegisterRequest = { 
      email, 
      password, 
      name, 
      invitation_code: invitationCode 
    };

    return this.http.post<RegisterResponse>(`${this.baseUrl}/auth/register`, registerRequest).pipe(
      tap(() => {
        this._isLoading.set(false);
      }),
      catchError(error => {
        this._error.set(error.message || 'Error en el registro');
        this._isLoading.set(false);
        return throwError(() => error);
      })
    );
  }

  login(email: string, password: string): Observable<LoginResponse> {
    this._isLoading.set(true);
    this._error.set(null);

    const loginRequest: LoginRequest = { email, password };

    return this.http.post<LoginResponse>(`${this.baseUrl}/auth/login`, loginRequest).pipe(
      tap(loginResponse => {
        this.setAuthData(loginResponse);
        this._user.set(loginResponse.user);
        this._isLoading.set(false);
      }),
      catchError(error => {
        this._error.set(error.message || 'Error en la autenticación');
        this._isLoading.set(false);
        return throwError(() => error);
      })
    );
  }

  logout(): void {
    // Llamar al endpoint de logout en el backend
    const token = this.getStoredToken();
    if (token) {
      this.http.post(`${this.baseUrl}/auth/logout`, {}).subscribe({
        complete: () => {
          this.clearAuthData();
          this._user.set(null);
          this._error.set(null);
          this.router.navigate(['/auth/login']);
        },
        error: () => {
          // Incluso si el logout falla en el backend, limpiar el frontend
          this.clearAuthData();
          this._user.set(null);
          this._error.set(null);
          this.router.navigate(['/auth/login']);
        }
      });
    } else {
      this.clearAuthData();
      this._user.set(null);
      this._error.set(null);
      this.router.navigate(['/auth/login']);
    }
  }

  private validateToken(): Observable<User> {
    return this.http.get<any>(`${this.baseUrl}/auth/verify`).pipe(
      catchError(() => throwError(() => new Error('Token validation failed')))
    );
  }

  private setAuthData(loginResponse: LoginResponse): void {
    const tokenInfo: TokenInfo = {
      access_token: loginResponse.access_token,
      expires_at: Date.now() + (loginResponse.expires_in * 1000),
      user: loginResponse.user
    };

    localStorage.setItem(this.TOKEN_KEY, JSON.stringify(tokenInfo));
    localStorage.setItem(this.USER_KEY, JSON.stringify(loginResponse.user));
  }

  private clearAuthData(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  }

  private loadStoredAuth(): void {
    try {
      const tokenData = localStorage.getItem(this.TOKEN_KEY);
      const userData = localStorage.getItem(this.USER_KEY);

      if (tokenData && userData) {
        const tokenInfo: TokenInfo = JSON.parse(tokenData);
        const user: User = JSON.parse(userData);

        // Verificar si el token no ha expirado
        if (tokenInfo.expires_at > Date.now()) {
          this._user.set(user);
        } else {
          this.clearAuthData();
        }
      }
    } catch (error) {
      console.error('Error loading stored auth:', error);
      this.clearAuthData();
    }
  }

  getStoredToken(): string | null {
    try {
      const tokenData = localStorage.getItem(this.TOKEN_KEY);
      if (tokenData) {
        const tokenInfo: TokenInfo = JSON.parse(tokenData);
        
        // Verificar si el token no ha expirado
        if (tokenInfo.expires_at > Date.now()) {
          return tokenInfo.access_token;
        } else {
          this.clearAuthData();
        }
      }
    } catch (error) {
      console.error('Error getting stored token:', error);
      this.clearAuthData();
    }
    
    return null;
  }

  isTokenExpired(): boolean {
    try {
      const tokenData = localStorage.getItem(this.TOKEN_KEY);
      if (tokenData) {
        const tokenInfo: TokenInfo = JSON.parse(tokenData);
        return tokenInfo.expires_at <= Date.now();
      }
    } catch (error) {
      console.error('Error checking token expiration:', error);
    }
    
    return true;
  }

  // Método para inicializar el usuario maestro (solo para desarrollo)
  initMasterUser(): Observable<any> {
    return this.http.post(`${this.baseUrl}/auth/init-master`, {});
  }
}