import { Routes } from '@angular/router';

export const legalRoutes: Routes = [
  {
    path: 'privacy-policy',
    loadComponent: () => import('./privacy-policy/privacy-policy.component').then(m => m.PrivacyPolicyComponent)
  },
  {
    path: 'terms-of-service',
    loadComponent: () => import('./terms-of-service/terms-of-service.component').then(m => m.TermsOfServiceComponent)
  }
];