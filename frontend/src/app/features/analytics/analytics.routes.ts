import { Routes } from '@angular/router';

export const analyticsRoutes: Routes = [
  {
    path: '',
    loadComponent: () => import('./analytics.component').then(m => m.AnalyticsComponent),
    title: 'Analytics - Financial Nomad'
  }
];