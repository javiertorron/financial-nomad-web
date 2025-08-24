import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';

export const settingsRoutes: Routes = [
  {
    path: '',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        redirectTo: 'profile',
        pathMatch: 'full'
      },
      {
        path: 'profile',
        loadComponent: () => import('./settings.component').then(m => m.SettingsComponent),
        title: 'Profile Settings - Financial Nomad'
      },
      {
        path: 'pwa',
        loadComponent: () => import('./pwa-settings.component').then(m => m.PWASettingsComponent),
        title: 'PWA Settings - Financial Nomad'
      },
      {
        path: 'system',
        loadComponent: () => import('./system-config.component').then(m => m.SystemConfigComponent),
        title: 'System Configuration - Financial Nomad'
      }
    ]
  }
];