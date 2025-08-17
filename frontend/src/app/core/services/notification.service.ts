import { Injectable, inject } from '@angular/core';
import { MatSnackBar, MatSnackBarConfig } from '@angular/material/snack-bar';

export interface NotificationConfig {
  duration?: number;
  action?: string;
  panelClass?: string[];
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {
  private readonly snackBar = inject(MatSnackBar);

  private readonly defaultConfig: MatSnackBarConfig = {
    duration: 5000,
    horizontalPosition: 'end',
    verticalPosition: 'top'
  };

  showSuccess(message: string, config?: NotificationConfig): void {
    this.snackBar.open(message, config?.action || 'Cerrar', {
      ...this.defaultConfig,
      duration: config?.duration || 4000,
      panelClass: ['success-snackbar', ...(config?.panelClass || [])]
    });
  }

  showError(message: string, config?: NotificationConfig): void {
    this.snackBar.open(message, config?.action || 'Cerrar', {
      ...this.defaultConfig,
      duration: config?.duration || 8000,
      panelClass: ['error-snackbar', ...(config?.panelClass || [])]
    });
  }

  showWarning(message: string, config?: NotificationConfig): void {
    this.snackBar.open(message, config?.action || 'Cerrar', {
      ...this.defaultConfig,
      duration: config?.duration || 6000,
      panelClass: ['warning-snackbar', ...(config?.panelClass || [])]
    });
  }

  showInfo(message: string, config?: NotificationConfig): void {
    this.snackBar.open(message, config?.action || 'Cerrar', {
      ...this.defaultConfig,
      duration: config?.duration || 4000,
      panelClass: ['info-snackbar', ...(config?.panelClass || [])]
    });
  }

  dismiss(): void {
    this.snackBar.dismiss();
  }
}