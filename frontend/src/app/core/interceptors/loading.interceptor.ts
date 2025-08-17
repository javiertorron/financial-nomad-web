import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { finalize } from 'rxjs';

import { LoadingService } from '../services/loading.service';

export const loadingInterceptor: HttpInterceptorFn = (req, next) => {
  const loadingService = inject(LoadingService);
  
  // No mostrar loading para ciertos endpoints
  const skipLoadingEndpoints = ['/health', '/auth/refresh'];
  const shouldSkipLoading = skipLoadingEndpoints.some(endpoint => 
    req.url.includes(endpoint)
  );

  if (shouldSkipLoading) {
    return next(req);
  }

  // Mostrar loading
  loadingService.show();

  return next(req).pipe(
    finalize(() => {
      // Ocultar loading cuando termine la request
      loadingService.hide();
    })
  );
};