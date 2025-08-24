import { Routes } from '@angular/router';
import { AuthGuard } from '../../core/guards/auth.guard';

export const integrationsRoutes: Routes = [
  {
    path: '',
    canActivate: [AuthGuard],
    children: [
      {
        path: '',
        redirectTo: 'asana',
        pathMatch: 'full'
      },
      {
        path: 'asana',
        loadComponent: () => import('./asana-integration.component').then(m => m.AsanaIntegrationComponent),
        title: 'Asana Integration - Financial Nomad'
      }
    ]
  }
];