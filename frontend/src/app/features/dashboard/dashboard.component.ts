import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

import { LayoutComponent } from '../../shared/components/layout/layout.component';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    LayoutComponent,
    MatCardModule,
    MatIconModule,
    MatButtonModule
  ],
  template: `
    <app-layout>
      <div class="dashboard-container">
        <div class="welcome-section">
          <h1>¡Bienvenido{{ user()?.name ? ', ' + user()!.name.split(' ')[0] : '' }}!</h1>
          <p class="welcome-subtitle">
            Aquí tienes un resumen de tus finanzas
          </p>
        </div>

        <div class="stats-grid">
          <mat-card class="stat-card">
            <mat-card-content>
              <div class="stat-content">
                <div class="stat-icon income">
                  <mat-icon>trending_up</mat-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">€0.00</div>
                  <div class="stat-label">Balance Total</div>
                </div>
              </div>
            </mat-card-content>
          </mat-card>

          <mat-card class="stat-card">
            <mat-card-content>
              <div class="stat-content">
                <div class="stat-icon expense">
                  <mat-icon>trending_down</mat-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">€0.00</div>
                  <div class="stat-label">Gastos del Mes</div>
                </div>
              </div>
            </mat-card-content>
          </mat-card>

          <mat-card class="stat-card">
            <mat-card-content>
              <div class="stat-content">
                <div class="stat-icon budget">
                  <mat-icon>pie_chart</mat-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">0</div>
                  <div class="stat-label">Presupuestos Activos</div>
                </div>
              </div>
            </mat-card-content>
          </mat-card>

          <mat-card class="stat-card">
            <mat-card-content>
              <div class="stat-content">
                <div class="stat-icon accounts">
                  <mat-icon>account_balance</mat-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">0</div>
                  <div class="stat-label">Cuentas</div>
                </div>
              </div>
            </mat-card-content>
          </mat-card>
        </div>

        <div class="actions-section">
          <mat-card class="action-card">
            <mat-card-header>
              <mat-card-title>Primeros Pasos</mat-card-title>
              <mat-card-subtitle>
                Configura tu cuenta para empezar a gestionar tus finanzas
              </mat-card-subtitle>
            </mat-card-header>
            <mat-card-content>
              <div class="action-buttons">
                <button mat-raised-button color="primary">
                  <mat-icon>add</mat-icon>
                  Crear Primera Cuenta
                </button>
                <button mat-stroked-button>
                  <mat-icon>category</mat-icon>
                  Configurar Categorías
                </button>
                <button mat-stroked-button>
                  <mat-icon>receipt_long</mat-icon>
                  Añadir Transacción
                </button>
              </div>
            </mat-card-content>
          </mat-card>
        </div>
      </div>
    </app-layout>
  `,
  styles: [`
    .dashboard-container {
      max-width: 1200px;
      margin: 0 auto;
    }

    .welcome-section {
      margin-bottom: 32px;
    }

    .welcome-section h1 {
      margin: 0;
      font-size: 32px;
      font-weight: 300;
      color: #333;
    }

    .welcome-subtitle {
      margin: 8px 0 0;
      color: #666;
      font-size: 16px;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 16px;
      margin-bottom: 32px;
    }

    .stat-card {
      padding: 0;
    }

    .stat-content {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 16px;
    }

    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
    }

    .stat-icon.income {
      background: linear-gradient(135deg, #4caf50, #45a049);
    }

    .stat-icon.expense {
      background: linear-gradient(135deg, #f44336, #d32f2f);
    }

    .stat-icon.budget {
      background: linear-gradient(135deg, #ff9800, #f57c00);
    }

    .stat-icon.accounts {
      background: linear-gradient(135deg, #2196f3, #1976d2);
    }

    .stat-info {
      flex: 1;
    }

    .stat-value {
      font-size: 24px;
      font-weight: 500;
      color: #333;
      margin-bottom: 4px;
    }

    .stat-label {
      font-size: 14px;
      color: #666;
    }

    .actions-section {
      margin-bottom: 32px;
    }

    .action-card {
      padding: 0;
    }

    .action-buttons {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .action-buttons button {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    @media (max-width: 768px) {
      .welcome-section h1 {
        font-size: 24px;
      }

      .stats-grid {
        grid-template-columns: 1fr;
      }

      .action-buttons {
        flex-direction: column;
      }

      .action-buttons button {
        width: 100%;
        justify-content: center;
      }
    }
  `]
})
export class DashboardComponent implements OnInit {
  private readonly authService = inject(AuthService);
  
  protected readonly user = this.authService.user;

  ngOnInit(): void {
    // TODO: Cargar datos del dashboard
  }
}