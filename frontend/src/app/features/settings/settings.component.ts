import { Component } from '@angular/core';
import { LayoutComponent } from '../../shared/components/layout/layout.component';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [LayoutComponent],
  template: `
    <app-layout>
      <h1>Configuración</h1>
      <p>Configuración de la aplicación - En desarrollo</p>
    </app-layout>
  `
})
export class SettingsComponent {}