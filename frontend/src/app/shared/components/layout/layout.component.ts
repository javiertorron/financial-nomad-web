import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterOutlet } from '@angular/router';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';

import { AuthService } from '../../../core/services/auth.service';

interface NavigationItem {
  label: string;
  icon: string;
  route: string;
  badge?: number;
}

@Component({
  selector: 'app-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    MatSidenavModule,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatListModule,
    MatMenuModule,
    MatDividerModule
  ],
  template: `
    <mat-sidenav-container class="sidenav-container">
      <!-- Sidebar -->
      <mat-sidenav 
        #drawer 
        class="sidenav"
        fixedInViewport
        [attr.role]="isHandset() ? 'dialog' : 'navigation'"
        [mode]="isHandset() ? 'over' : 'side'"
        [opened]="!isHandset()"
      >
        <mat-toolbar class="sidenav-header">
          <mat-icon class="app-icon">account_balance_wallet</mat-icon>
          <span class="app-name">Financial Nomad</span>
        </mat-toolbar>

        <mat-nav-list>
          @for (item of navigationItems; track item.route) {
            <a 
              mat-list-item 
              [routerLink]="item.route"
              routerLinkActive="active-nav-item"
              (click)="isHandset() && drawer.close()"
            >
              <mat-icon matListIcon>{{ item.icon }}</mat-icon>
              <span matLine>{{ item.label }}</span>
              @if (item.badge) {
                <span class="nav-badge">{{ item.badge }}</span>
              }
            </a>
          }
        </mat-nav-list>

        <mat-divider></mat-divider>

        <mat-nav-list>
          <a mat-list-item routerLink="/settings" routerLinkActive="active-nav-item">
            <mat-icon matListIcon>settings</mat-icon>
            <span matLine>Configuración</span>
          </a>
        </mat-nav-list>
      </mat-sidenav>

      <!-- Main content -->
      <mat-sidenav-content>
        <!-- Top toolbar -->
        <mat-toolbar color="primary" class="main-toolbar">
          <button
            type="button"
            aria-label="Toggle sidenav"
            mat-icon-button
            (click)="drawer.toggle()"
            *ngIf="isHandset()"
          >
            <mat-icon aria-label="Side nav toggle icon">menu</mat-icon>
          </button>

          <span class="spacer"></span>

          <!-- User menu -->
          <button mat-icon-button [matMenuTriggerFor]="userMenu">
            @if (user()?.picture) {
              <img 
                [src]="user()!.picture" 
                [alt]="user()!.name"
                class="user-avatar"
              >
            } @else {
              <mat-icon>account_circle</mat-icon>
            }
          </button>

          <mat-menu #userMenu="matMenu">
            <div class="user-info">
              <div class="user-name">{{ user()?.name }}</div>
              <div class="user-email">{{ user()?.email }}</div>
            </div>
            <mat-divider></mat-divider>
            <button mat-menu-item routerLink="/settings">
              <mat-icon>settings</mat-icon>
              <span>Configuración</span>
            </button>
            <button mat-menu-item (click)="logout()">
              <mat-icon>logout</mat-icon>
              <span>Cerrar sesión</span>
            </button>
          </mat-menu>
        </mat-toolbar>

        <!-- Page content -->
        <div class="main-content">
          <router-outlet></router-outlet>
        </div>
      </mat-sidenav-content>
    </mat-sidenav-container>
  `,
  styles: [`
    .sidenav-container {
      height: 100vh;
    }

    .sidenav {
      width: 250px;
      background: #fafafa;
    }

    .sidenav-header {
      background: #1976d2;
      color: white;
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 16px;
    }

    .app-icon {
      font-size: 28px;
      width: 28px;
      height: 28px;
    }

    .app-name {
      font-size: 18px;
      font-weight: 500;
    }

    .active-nav-item {
      background: rgba(25, 118, 210, 0.1) !important;
      color: #1976d2 !important;
    }

    .active-nav-item .mat-icon {
      color: #1976d2 !important;
    }

    .nav-badge {
      background: #f44336;
      color: white;
      border-radius: 10px;
      padding: 2px 6px;
      font-size: 12px;
      min-width: 18px;
      text-align: center;
    }

    .main-toolbar {
      position: sticky;
      top: 0;
      z-index: 1000;
    }

    .spacer {
      flex: 1 1 auto;
    }

    .user-avatar {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      object-fit: cover;
    }

    .user-info {
      padding: 12px 16px;
      border-bottom: 1px solid #eee;
    }

    .user-name {
      font-weight: 500;
      margin-bottom: 4px;
    }

    .user-email {
      font-size: 12px;
      color: #666;
    }

    .main-content {
      padding: 24px;
      min-height: calc(100vh - 64px);
      background: #f5f5f5;
    }

    @media (max-width: 768px) {
      .main-content {
        padding: 16px;
      }
    }
  `]
})
export class LayoutComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly breakpointObserver = inject(BreakpointObserver);

  protected readonly user = this.authService.user;
  
  protected readonly isHandset = computed(() => 
    this.breakpointObserver.isMatched(Breakpoints.Handset)
  );

  protected readonly navigationItems: NavigationItem[] = [
    {
      label: 'Dashboard',
      icon: 'dashboard',
      route: '/dashboard'
    },
    {
      label: 'Cuentas',
      icon: 'account_balance',
      route: '/accounts'
    },
    {
      label: 'Transacciones',
      icon: 'receipt_long',
      route: '/transactions'
    },
    {
      label: 'Categorías',
      icon: 'category',
      route: '/categories'
    },
    {
      label: 'Presupuestos',
      icon: 'pie_chart',
      route: '/budgets'
    },
    {
      label: 'Reportes',
      icon: 'assessment',
      route: '/reports'
    }
  ];

  logout(): void {
    this.authService.logout();
  }
}