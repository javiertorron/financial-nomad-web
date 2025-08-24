import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';

export const adminRoutes: Routes = [
  {
    path: '',
    canActivate: [authGuard],
    data: { requiresAdmin: true },
    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      },
      {
        path: 'dashboard',
        loadComponent: () => import('./admin.component').then(m => m.AdminComponent),
        title: 'Admin Panel - Financial Nomad'
      },
      {
        path: 'logs',
        loadComponent: () => import('./logs-monitoring.component').then(m => m.LogsMonitoringComponent),
        title: 'Logs & Monitoring - Financial Nomad'
      }
    ]
  }
];