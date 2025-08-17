import { Component } from '@angular/core';
import { LayoutComponent } from '../../shared/components/layout/layout.component';

@Component({
  selector: 'app-accounts',
  standalone: true,
  imports: [LayoutComponent],
  template: `
    <app-layout>
      <h1>Cuentas</h1>
      <p>Gestión de cuentas bancarias - En desarrollo</p>
    </app-layout>
  `
})
export class AccountsComponent {}