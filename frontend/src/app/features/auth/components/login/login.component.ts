import { Component, inject, OnInit, signal, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatTabsModule } from '@angular/material/tabs';

import { AuthService } from '../../../../core/services/auth.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { environment } from '../../../../../environments/environment';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    MatCardModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatDividerModule,
    MatFormFieldModule,
    MatInputModule,
    MatTabsModule
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
              <p>{{ currentMode() === 'register' ? 'Registrando...' : 'Iniciando sesión...' }}</p>
            </div>
          } @else {
            <mat-tab-group [(selectedIndex)]="selectedTabIndex" (selectedTabChange)="onTabChange($event)">
              <mat-tab label="Iniciar Sesión">
                <div class="tab-content">
                  <form [formGroup]="loginForm" (ngSubmit)="onLogin()" class="auth-form">
                    <mat-form-field appearance="outline">
                      <mat-label>Email</mat-label>
                      <input matInput type="email" formControlName="email" required>
                      <mat-icon matSuffix>email</mat-icon>
                      @if (loginForm.get('email')?.hasError('required') && loginForm.get('email')?.touched) {
                        <mat-error>El email es obligatorio</mat-error>
                      }
                      @if (loginForm.get('email')?.hasError('email') && loginForm.get('email')?.touched) {
                        <mat-error>Introduce un email válido</mat-error>
                      }
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Contraseña</mat-label>
                      <input matInput [type]="hidePassword ? 'password' : 'text'" formControlName="password" required>
                      <button mat-icon-button matSuffix (click)="hidePassword = !hidePassword" type="button">
                        <mat-icon>{{ hidePassword ? 'visibility_off' : 'visibility' }}</mat-icon>
                      </button>
                      @if (loginForm.get('password')?.hasError('required') && loginForm.get('password')?.touched) {
                        <mat-error>La contraseña es obligatoria</mat-error>
                      }
                    </mat-form-field>

                    <button mat-raised-button color="primary" type="submit" 
                            [disabled]="loginForm.invalid || isLoading()" class="submit-btn">
                      Iniciar Sesión
                    </button>
                  </form>
                </div>
              </mat-tab>

              <mat-tab label="Registro">
                <div class="tab-content">
                  <form [formGroup]="registerForm" (ngSubmit)="onRegister()" class="auth-form">
                    <mat-form-field appearance="outline">
                      <mat-label>Nombre</mat-label>
                      <input matInput formControlName="name" required>
                      <mat-icon matSuffix>person</mat-icon>
                      @if (registerForm.get('name')?.hasError('required') && registerForm.get('name')?.touched) {
                        <mat-error>El nombre es obligatorio</mat-error>
                      }
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Email</mat-label>
                      <input matInput type="email" formControlName="email" required>
                      <mat-icon matSuffix>email</mat-icon>
                      @if (registerForm.get('email')?.hasError('required') && registerForm.get('email')?.touched) {
                        <mat-error>El email es obligatorio</mat-error>
                      }
                      @if (registerForm.get('email')?.hasError('email') && registerForm.get('email')?.touched) {
                        <mat-error>Introduce un email válido</mat-error>
                      }
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Contraseña</mat-label>
                      <input matInput [type]="hideRegisterPassword ? 'password' : 'text'" formControlName="password" required>
                      <button mat-icon-button matSuffix (click)="hideRegisterPassword = !hideRegisterPassword" type="button">
                        <mat-icon>{{ hideRegisterPassword ? 'visibility_off' : 'visibility' }}</mat-icon>
                      </button>
                      @if (registerForm.get('password')?.hasError('required') && registerForm.get('password')?.touched) {
                        <mat-error>La contraseña es obligatoria</mat-error>
                      }
                      @if (registerForm.get('password')?.hasError('minlength') && registerForm.get('password')?.touched) {
                        <mat-error>La contraseña debe tener al menos 8 caracteres</mat-error>
                      }
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Código de Invitación</mat-label>
                      <input matInput formControlName="invitationCode" required>
                      <mat-icon matSuffix>confirmation_number</mat-icon>
                      @if (registerForm.get('invitationCode')?.hasError('required') && registerForm.get('invitationCode')?.touched) {
                        <mat-error>El código de invitación es obligatorio</mat-error>
                      }
                    </mat-form-field>

                    <button mat-raised-button color="primary" type="submit" 
                            [disabled]="registerForm.invalid || isLoading()" class="submit-btn">
                      Registrarse
                    </button>
                  </form>
                </div>
              </mat-tab>
            </mat-tab-group>

            <mat-divider style="margin: 24px 0;"></mat-divider>

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
          }
        </mat-card-content>
      </mat-card>

      @if (!environment.production) {
        <div class="dev-info">
          <small>Entorno de desarrollo</small>
          <br>
          <small>API: {{ environment.apiUrl }}</small>
          <br>
          <button mat-stroked-button (click)="initMasterUser()" style="margin-top: 8px; font-size: 10px;">
            Inicializar Usuario Maestro
          </button>
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
      max-width: 500px;
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
      padding: 24px;
    }

    .loading-container {
      text-align: center;
      padding: 32px;
    }

    .loading-container p {
      margin-top: 16px;
      color: #666;
    }

    .tab-content {
      padding: 24px 0;
    }

    .auth-form {
      display: flex;
      flex-direction: column;
      gap: 16px;
      max-width: 400px;
      margin: 0 auto;
    }

    .submit-btn {
      height: 48px;
      font-size: 16px;
      margin-top: 8px;
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
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);

  protected readonly environment = environment;
  protected readonly isLoading = this.authService.isLoading;
  protected readonly currentMode = signal<'login' | 'register'>('login');

  // Form controls
  loginForm: FormGroup;
  registerForm: FormGroup;
  selectedTabIndex = 0;
  hidePassword = true;
  hideRegisterPassword = true;

  constructor() {
    // Inicializar formularios
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required]]
    });

    this.registerForm = this.fb.group({
      name: ['', [Validators.required]],
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      invitationCode: ['', [Validators.required]]
    });

    // Redirigir si ya está autenticado
    effect(() => {
      if (this.authService.isAuthenticated()) {
        this.router.navigate(['/dashboard']);
      }
    });
  }

  ngOnInit(): void {
    // Ya no necesitamos inicializar Google Auth
  }

  onTabChange(event: any): void {
    this.selectedTabIndex = event.index;
    this.currentMode.set(event.index === 0 ? 'login' : 'register');
  }

  onLogin(): void {
    if (this.loginForm.valid) {
      const { email, password } = this.loginForm.value;
      
      this.authService.login(email, password).subscribe({
        next: (response) => {
          this.notificationService.showSuccess('¡Bienvenido a Financial Nomad!');
          this.router.navigate(['/dashboard']);
        },
        error: (error) => {
          console.error('Error en login:', error);
          this.notificationService.showError(
            error.error?.message || 'Error al iniciar sesión'
          );
        }
      });
    }
  }

  onRegister(): void {
    if (this.registerForm.valid) {
      const { email, password, name, invitationCode } = this.registerForm.value;
      
      this.authService.register(email, password, name, invitationCode).subscribe({
        next: (response) => {
          this.notificationService.showSuccess('¡Registro exitoso! Ahora puedes iniciar sesión.');
          this.selectedTabIndex = 0; // Cambiar a tab de login
          this.registerForm.reset();
        },
        error: (error) => {
          console.error('Error en registro:', error);
          this.notificationService.showError(
            error.error?.message || 'Error en el registro'
          );
        }
      });
    }
  }

  initMasterUser(): void {
    this.authService.initMasterUser().subscribe({
      next: (response) => {
        this.notificationService.showSuccess('Usuario maestro inicializado correctamente');
        console.log('Master user:', response);
      },
      error: (error) => {
        console.error('Error inicializando usuario maestro:', error);
        this.notificationService.showError(
          error.error?.message || 'Error al inicializar usuario maestro'
        );
      }
    });
  }
}