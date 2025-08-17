import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { LoadingService } from './core/services/loading.service';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    MatProgressBarModule
  ],
  template: `
    <div class="app-container">
      @if (loadingService.isLoading()) {
        <mat-progress-bar mode="indeterminate" class="global-loading"></mat-progress-bar>
      }
      
      <router-outlet></router-outlet>
    </div>
  `,
  styles: [`
    .app-container {
      height: 100vh;
      display: flex;
      flex-direction: column;
      position: relative;
    }

    .global-loading {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 9999;
    }

    router-outlet {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
  `]
})
export class AppComponent implements OnInit {
  protected readonly loadingService = inject(LoadingService);
  private readonly authService = inject(AuthService);

  ngOnInit(): void {
    // Inicializar autenticación al cargar la app
    this.authService.initializeAuth();
  }
}