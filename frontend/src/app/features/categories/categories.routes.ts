import { Routes } from '@angular/router';

export const categoriesRoutes: Routes = [
  {
    path: '',
    loadComponent: () => import('./categories.component').then(m => m.CategoriesComponent)
  }
];