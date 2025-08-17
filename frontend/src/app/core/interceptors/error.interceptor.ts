import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { NotificationService } from '../services/notification.service';
import { ErrorResponse } from '../types/api.types';
import { environment } from '../../../environments/environment';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const notificationService = inject(NotificationService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      let errorMessage = 'Ha ocurrido un error inesperado';

      if (error.error instanceof ErrorEvent) {
        // Error del lado del cliente
        errorMessage = `Error: ${error.error.message}`;
      } else {
        // Error del lado del servidor
        const errorResponse: ErrorResponse = error.error;
        
        switch (error.status) {
          case 400:
            errorMessage = errorResponse?.message || 'Solicitud inválida';
            break;
          case 401:
            errorMessage = 'No autorizado. Por favor, inicia sesión nuevamente';
            break;
          case 403:
            errorMessage = 'No tienes permisos para realizar esta acción';
            break;
          case 404:
            errorMessage = 'Recurso no encontrado';
            break;
          case 409:
            errorMessage = errorResponse?.message || 'Conflicto en los datos';
            break;
          case 422:
            errorMessage = 'Datos de entrada inválidos';
            // Mostrar errores de validación específicos
            if (errorResponse?.errors) {
              const validationErrors = Object.values(errorResponse.errors)
                .flat()
                .join(', ');
              errorMessage += `: ${validationErrors}`;
            }
            break;
          case 429:
            errorMessage = 'Demasiadas solicitudes. Intenta nuevamente más tarde';
            break;
          case 500:
            errorMessage = 'Error interno del servidor';
            break;
          case 503:
            errorMessage = 'Servicio no disponible temporalmente';
            break;
          default:
            errorMessage = errorResponse?.message || `Error ${error.status}: ${error.statusText}`;
        }
      }

      // Solo mostrar notificación si no es un error 401 (se maneja en auth interceptor)
      if (error.status !== 401) {
        notificationService.showError(errorMessage);
      }

      // Loggear error en desarrollo
      if (!environment.production) {
        console.error('HTTP Error:', error);
      }

      return throwError(() => ({
        ...error,
        userMessage: errorMessage
      }));
    })
  );
};