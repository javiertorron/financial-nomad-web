import { Component } from '@angular/core';
import { LayoutComponent } from '../../shared/components/layout/layout.component';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [LayoutComponent],
  template: `
    <app-layout>
      <h1>Reportes</h1>
      <p>Generación de reportes - En desarrollo</p>
    </app-layout>
  `
})
export class ReportsComponent {}