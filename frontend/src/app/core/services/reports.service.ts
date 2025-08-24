import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { saveAs } from 'file-saver';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import * as XLSX from 'xlsx';

import { ConfigService } from './config.service';
import { 
  ReportConfiguration, 
  ReportExecution, 
  ReportParameters,
  ReportSchedule,
  FinancialInsights 
} from '../types/enterprise.types';

@Injectable({
  providedIn: 'root'
})
export class ReportsService {
  private readonly apiUrl = `${this.config.apiUrl}/reports`;
  
  private currentReportSubject = new BehaviorSubject<ReportConfiguration | null>(null);
  public currentReport$ = this.currentReportSubject.asObservable();

  private executionsSubject = new BehaviorSubject<ReportExecution[]>([]);
  public executions$ = this.executionsSubject.asObservable();

  constructor(
    private http: HttpClient,
    private config: ConfigService
  ) {}

  // Report Configuration Management
  getReportConfigurations(): Observable<ReportConfiguration[]> {
    return this.http.get<ReportConfiguration[]>(`${this.apiUrl}/configurations`);
  }

  getReportConfiguration(id: string): Observable<ReportConfiguration> {
    return this.http.get<ReportConfiguration>(`${this.apiUrl}/configurations/${id}`);
  }

  createReportConfiguration(config: Omit<ReportConfiguration, 'id' | 'created_at' | 'updated_at'>): Observable<ReportConfiguration> {
    return this.http.post<ReportConfiguration>(`${this.apiUrl}/configurations`, config);
  }

  updateReportConfiguration(id: string, config: Partial<ReportConfiguration>): Observable<ReportConfiguration> {
    return this.http.put<ReportConfiguration>(`${this.apiUrl}/configurations/${id}`, config);
  }

  deleteReportConfiguration(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/configurations/${id}`);
  }

  // Report Generation
  generateReport(configId: string, parameters?: ReportParameters): Observable<ReportExecution> {
    const body = { configuration_id: configId, parameters };
    return this.http.post<ReportExecution>(`${this.apiUrl}/generate`, body);
  }

  getReportStatus(executionId: string): Observable<ReportExecution> {
    return this.http.get<ReportExecution>(`${this.apiUrl}/executions/${executionId}`);
  }

  getReportExecutions(limit = 50): Observable<ReportExecution[]> {
    const params = new HttpParams().set('limit', limit.toString());
    return this.http.get<ReportExecution[]>(`${this.apiUrl}/executions`, { params });
  }

  downloadReport(executionId: string): Observable<Blob> {
    return this.http.get(`${this.apiUrl}/executions/${executionId}/download`, {
      responseType: 'blob'
    });
  }

  // Quick Report Generation (without configuration)
  generateQuickReport(parameters: ReportParameters, format: 'pdf' | 'excel' | 'csv'): Observable<ReportExecution> {
    const body = { parameters, format };
    return this.http.post<ReportExecution>(`${this.apiUrl}/quick-generate`, body);
  }

  // Report Templates
  getReportTemplates(): Observable<Partial<ReportConfiguration>[]> {
    return this.http.get<Partial<ReportConfiguration>[]>(`${this.apiUrl}/templates`);
  }

  // Financial Insights
  getFinancialInsights(parameters: ReportParameters): Observable<FinancialInsights> {
    return this.http.post<FinancialInsights>(`${this.apiUrl}/insights`, parameters);
  }

  // Client-side PDF Generation
  async generatePDFFromElement(element: HTMLElement, filename = 'report.pdf'): Promise<void> {
    try {
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        allowTaint: true
      });

      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      
      const imgWidth = 210;
      const pageHeight = 295;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let heightLeft = imgHeight;
      
      let position = 0;

      // Add first page
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;

      // Add additional pages if needed
      while (heightLeft >= 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }

      pdf.save(filename);
    } catch (error) {
      console.error('Error generating PDF:', error);
      throw new Error('Failed to generate PDF');
    }
  }

  // Client-side Excel Generation
  generateExcelFromData(data: any[], filename = 'report.xlsx', sheetName = 'Report'): void {
    try {
      const worksheet = XLSX.utils.json_to_sheet(data);
      const workbook = XLSX.utils.book_new();
      
      // Add worksheet to workbook
      XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);
      
      // Generate buffer
      const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
      
      // Save file
      const blob = new Blob([excelBuffer], { 
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
      });
      
      saveAs(blob, filename);
    } catch (error) {
      console.error('Error generating Excel file:', error);
      throw new Error('Failed to generate Excel file');
    }
  }

  // Schedule Management
  scheduleReport(configId: string, schedule: ReportSchedule): Observable<ReportConfiguration> {
    return this.http.post<ReportConfiguration>(`${this.apiUrl}/configurations/${configId}/schedule`, schedule);
  }

  updateReportSchedule(configId: string, schedule: ReportSchedule): Observable<ReportConfiguration> {
    return this.http.put<ReportConfiguration>(`${this.apiUrl}/configurations/${configId}/schedule`, schedule);
  }

  disableReportSchedule(configId: string): Observable<ReportConfiguration> {
    return this.http.delete<ReportConfiguration>(`${this.apiUrl}/configurations/${configId}/schedule`);
  }

  // Utility methods
  setCurrentReport(report: ReportConfiguration | null): void {
    this.currentReportSubject.next(report);
  }

  getCurrentReport(): ReportConfiguration | null {
    return this.currentReportSubject.value;
  }

  updateExecutions(executions: ReportExecution[]): void {
    this.executionsSubject.next(executions);
  }

  // Download helpers
  async downloadReportFile(executionId: string, filename?: string): Promise<void> {
    try {
      const blob = await this.downloadReport(executionId).toPromise();
      if (blob) {
        const reportFilename = filename || `report_${executionId}.pdf`;
        saveAs(blob, reportFilename);
      }
    } catch (error) {
      console.error('Error downloading report:', error);
      throw new Error('Failed to download report');
    }
  }

  // Report validation
  validateReportParameters(parameters: ReportParameters): string[] {
    const errors: string[] = [];

    if (!parameters.date_range.start_date) {
      errors.push('Start date is required');
    }

    if (!parameters.date_range.end_date) {
      errors.push('End date is required');
    }

    if (parameters.date_range.start_date && parameters.date_range.end_date) {
      const startDate = new Date(parameters.date_range.start_date);
      const endDate = new Date(parameters.date_range.end_date);
      
      if (startDate >= endDate) {
        errors.push('Start date must be before end date');
      }

      const daysDiff = (endDate.getTime() - startDate.getTime()) / (1000 * 3600 * 24);
      if (daysDiff > 365) {
        errors.push('Date range cannot exceed 365 days');
      }
    }

    return errors;
  }

  // Format helpers
  formatCurrency(amount: number, currency = 'USD'): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency
    }).format(amount);
  }

  formatPercentage(value: number, decimals = 2): string {
    return `${(value * 100).toFixed(decimals)}%`;
  }

  formatDate(date: string | Date, format = 'short'): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    
    switch (format) {
      case 'short':
        return dateObj.toLocaleDateString();
      case 'long':
        return dateObj.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        });
      case 'time':
        return dateObj.toLocaleString();
      default:
        return dateObj.toLocaleDateString();
    }
  }
}