import { Component } from '@angular/core';
import { LayoutComponent } from '../../shared/components/layout/layout.component';
import { AdvancedReportsComponent } from './advanced-reports.component';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [LayoutComponent, AdvancedReportsComponent],
  template: `
    <app-layout>
      <app-advanced-reports></app-advanced-reports>
    </app-layout>
  `
})
export class ReportsComponent {}