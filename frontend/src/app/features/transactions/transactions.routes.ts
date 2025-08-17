import { Routes } from '@angular/router';

export const transactionsRoutes: Routes = [
  {
    path: '',
    loadComponent: () => import('./transactions.component').then(m => m.TransactionsComponent)
  }
];