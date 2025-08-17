import { Routes } from '@angular/router';

export const accountsRoutes: Routes = [
  {
    path: '',
    loadComponent: () => import('./accounts.component').then(m => m.AccountsComponent)
  }
];