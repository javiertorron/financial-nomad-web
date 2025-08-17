import { Routes } from '@angular/router';

export const budgetsRoutes: Routes = [
  {
    path: '',
    loadComponent: () => import('./budgets.component').then(m => m.BudgetsComponent)
  }
];