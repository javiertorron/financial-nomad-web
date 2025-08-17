import { Component } from '@angular/core';
import { LayoutComponent } from '../../shared/components/layout/layout.component';

@Component({
  selector: 'app-budgets',
  standalone: true,
  imports: [LayoutComponent],
  template: `
    <app-layout>
      <h1>Presupuestos</h1>
      <p>Gestión de presupuestos - En desarrollo</p>
    </app-layout>
  `
})
export class BudgetsComponent {}