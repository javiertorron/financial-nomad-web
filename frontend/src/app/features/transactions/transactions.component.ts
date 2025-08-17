import { Component } from '@angular/core';
import { LayoutComponent } from '../../shared/components/layout/layout.component';

@Component({
  selector: 'app-transactions',
  standalone: true,
  imports: [LayoutComponent],
  template: `
    <app-layout>
      <h1>Transacciones</h1>
      <p>Gestión de transacciones - En desarrollo</p>
    </app-layout>
  `
})
export class TransactionsComponent {}