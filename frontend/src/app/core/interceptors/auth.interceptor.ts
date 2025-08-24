import { HttpInterceptorFn, HttpRequest, HttpHandlerFn, HttpEvent } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req: HttpRequest<any>, next: HttpHandlerFn): Observable<HttpEvent<any>> => {
  const authService = inject(AuthService);
  const token = authService.getStoredToken();

  // No agregar token a endpoints públicos
  const publicEndpoints = ['/auth/login', '/auth/register', '/auth/init-master', '/health'];
  const isPublicEndpoint = publicEndpoints.some(endpoint => req.url.includes(endpoint));

  if (isPublicEndpoint || !token) {
    return next(req);
  }

  // Clonar request y agregar token
  const authReq = req.clone({
    setHeaders: {
      Authorization: `Bearer ${token}`
    }
  });

  return next(authReq).pipe(
    catchError(error => {
      // Si recibimos 401, hacer logout automático
      if (error.status === 401) {
        authService.logout();
      }

      return throwError(() => error);
    })
  );
};