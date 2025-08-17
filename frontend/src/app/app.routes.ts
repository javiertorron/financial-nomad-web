import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/dashboard',
    pathMatch: 'full'
  },
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.routes').then(m => m.authRoutes)
  },
  {
    path: 'dashboard',
    canActivate: [authGuard],
    loadChildren: () => import('./features/dashboard/dashboard.routes').then(m => m.dashboardRoutes)
  },
  {
    path: 'accounts',
    canActivate: [authGuard],
    loadChildren: () => import('./features/accounts/accounts.routes').then(m => m.accountsRoutes)
  },
  {
    path: 'transactions',
    canActivate: [authGuard],
    loadChildren: () => import('./features/transactions/transactions.routes').then(m => m.transactionsRoutes)
  },
  {
    path: 'categories',
    canActivate: [authGuard],
    loadChildren: () => import('./features/categories/categories.routes').then(m => m.categoriesRoutes)
  },
  {
    path: 'budgets',
    canActivate: [authGuard],
    loadChildren: () => import('./features/budgets/budgets.routes').then(m => m.budgetsRoutes)
  },
  {
    path: 'reports',
    canActivate: [authGuard],
    loadChildren: () => import('./features/reports/reports.routes').then(m => m.reportsRoutes)
  },
  {
    path: 'settings',
    canActivate: [authGuard],
    loadChildren: () => import('./features/settings/settings.routes').then(m => m.settingsRoutes)
  },
  {
    path: '**',
    redirectTo: '/dashboard'
  }
];