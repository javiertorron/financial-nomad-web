import { Routes } from '@angular/router';
import { publicGuard } from '../../core/guards/auth.guard';

export const authRoutes: Routes = [
  {
    path: '',
    redirectTo: 'login',
    pathMatch: 'full'
  },
  {
    path: 'login',
    canActivate: [publicGuard],
    loadComponent: () => import('./components/login/login.component').then(m => m.LoginComponent)
  }
];