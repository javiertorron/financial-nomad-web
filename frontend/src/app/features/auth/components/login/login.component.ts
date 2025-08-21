import { Component, inject, OnInit, signal, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';

import { AuthService } from '../../../../core/services/auth.service';
import { ConfigService } from '../../../../core/services/config.service';
import { GoogleAuthService } from '../../services/google-auth.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { environment } from '../../../../../environments/environment';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatDividerModule
  ],
  template: `
    <div class="login-container">
      <mat-card class="login-card">
        <mat-card-header class="login-header">
          <div class="logo-container">
            <mat-icon class="logo-icon">account_balance_wallet</mat-icon>
            <h1>Financial Nomad</h1>
          </div>
          <p class="subtitle">Controla tus finanzas de forma simple y efectiva</p>
        </mat-card-header>

        <mat-card-content class="login-content">
          @if (isLoading()) {
            <div class="loading-container">
              <mat-progress-spinner mode="indeterminate" diameter="40"></mat-progress-spinner>
              <p>Iniciando sesión...</p>
            </div>
          } @else {
            <div class="login-methods">
              <button 
                mat-raised-button 
                color="primary" 
                class="google-signin-btn"
                (click)="signInWithGoogle()"
                [disabled]="!googleAuthAvailable()"
              >
                <mat-icon>account_circle</mat-icon>
                Continuar con Google
              </button>

              @if (!googleAuthAvailable()) {
                <div class="google-unavailable">
                  <mat-icon color="warn">warning</mat-icon>
                  <p>Google Auth no está disponible en este momento</p>
                  <small>Verifique la configuración del Client ID</small>
                </div>
              }

              <mat-divider></mat-divider>

              <div class="app-info">
                <h3>¿Qué puedes hacer con Financial Nomad?</h3>
                <ul>
                  <li>Gestionar múltiples cuentas bancarias</li>
                  <li>Categorizar tus transacciones</li>
                  <li>Crear y seguir presupuestos</li>
                  <li>Generar reportes detallados</li>
                  <li>Exportar datos a diferentes formatos</li>
                </ul>
              </div>

              <div class="legal-links">
                <p>Al continuar, aceptas nuestros</p>
                <div class="links">
                  <a routerLink="/legal/terms-of-service" target="_blank">Términos de Servicio</a>
                  <span>y</span>
                  <a routerLink="/legal/privacy-policy" target="_blank">Política de Privacidad</a>
                </div>
              </div>
            </div>
          }
        </mat-card-content>
      </mat-card>

      @if (!environment.production) {
        <div class="dev-info">
          <small>Entorno de desarrollo</small>
          <br>
          <small>API: {{ environment.apiUrl }}</small>
        </div>
      }
    </div>
  `,
  styles: [`
    .login-container {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding: 16px;
    }

    .login-card {
      max-width: 450px;
      width: 100%;
      padding: 0;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }

    .login-header {
      text-align: center;
      padding: 32px 24px 16px;
      background: linear-gradient(135deg, #1976d2 0%, #1565c0 100%);
      color: white;
    }

    .logo-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }

    .logo-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
    }

    .login-header h1 {
      margin: 0;
      font-size: 28px;
      font-weight: 300;
    }

    .subtitle {
      margin: 8px 0 0;
      opacity: 0.9;
      font-size: 14px;
    }

    .login-content {
      padding: 32px 24px;
    }

    .loading-container {
      text-align: center;
      padding: 32px;
    }

    .loading-container p {
      margin-top: 16px;
      color: #666;
    }

    .login-methods {
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .google-signin-btn {
      height: 48px;
      font-size: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .google-unavailable {
      text-align: center;
      padding: 16px;
      background: #fff3cd;
      border-radius: 4px;
      color: #856404;
    }

    .google-unavailable mat-icon {
      margin-bottom: 8px;
    }

    .google-unavailable p {
      margin: 0 0 4px;
      font-weight: 500;
    }

    .google-unavailable small {
      font-size: 12px;
    }

    .app-info {
      text-align: center;
    }

    .app-info h3 {
      margin: 0 0 16px;
      color: #333;
    }

    .app-info ul {
      text-align: left;
      margin: 0;
      padding-left: 20px;
      color: #666;
    }

    .app-info li {
      margin-bottom: 8px;
    }

    .legal-links {
      text-align: center;
      margin-top: 16px;
      font-size: 12px;
      color: #666;
    }

    .legal-links p {
      margin: 0 0 8px;
    }

    .legal-links .links {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .legal-links a {
      color: #1976d2;
      text-decoration: none;
    }

    .legal-links a:hover {
      text-decoration: underline;
    }

    .dev-info {
      position: fixed;
      bottom: 16px;
      right: 16px;
      background: rgba(0, 0, 0, 0.7);
      color: white;
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 12px;
      text-align: right;
    }
  `]
})
export class LoginComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly configService = inject(ConfigService);
  private readonly googleAuthService = inject(GoogleAuthService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  protected readonly environment = environment;
  protected readonly isLoading = signal(false);
  protected readonly googleAuthAvailable = signal(false);

  constructor() {
    // Redirigir si ya está autenticado
    effect(() => {
      if (this.authService.isAuthenticated()) {
        this.router.navigate(['/dashboard']);
      }
    });
  }

  async ngOnInit(): Promise<void> {
    // Primero cargar configuración del servidor
    await this.loadConfiguration();
    // Luego inicializar Google Auth
    await this.initializeGoogleAuth();
  }

  private async loadConfiguration(): Promise<void> {
    try {
      // Cargar configuración del backend
      await this.configService.loadConfig().toPromise();
      console.log('Configuración cargada:', this.configService.config());
    } catch (error) {
      console.warn('No se pudo cargar configuración del servidor, usando valores por defecto:', error);
    }
  }

  private async initializeGoogleAuth(): Promise<void> {
    try {
      const googleClientId = this.configService.getGoogleClientId();
      if (!googleClientId) {
        console.warn('Google Client ID no configurado');
        return;
      }

      await this.googleAuthService.initialize();
      this.googleAuthAvailable.set(this.googleAuthService.isAvailable());
    } catch (error) {
      console.error('Error inicializando Google Auth:', error);
      this.notificationService.showWarning(
        'La autenticación con Google no está disponible'
      );
    }
  }

  async signInWithGoogle(): Promise<void> {
    if (!this.googleAuthService.isAvailable()) {
      this.notificationService.showError('Google Auth no está disponible');
      return;
    }

    this.isLoading.set(true);

    try {
      // Obtener token de Google
      const googleToken = await this.googleAuthService.signInWithPopup();
      
      // Enviar token al backend
      this.authService.loginWithGoogle(googleToken).subscribe({
        next: (response) => {
          this.notificationService.showSuccess('¡Bienvenido a Financial Nomad!');
          this.router.navigate(['/dashboard']);
        },
        error: (error) => {
          console.error('Error en login:', error);
          this.notificationService.showError(
            error.userMessage || 'Error al iniciar sesión'
          );
        },
        complete: () => {
          this.isLoading.set(false);
        }
      });
    } catch (error) {
      console.error('Error con Google Auth:', error);
      this.notificationService.showError('Error al conectar con Google');
      this.isLoading.set(false);
    }
  }
}