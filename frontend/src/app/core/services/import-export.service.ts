import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { HttpService } from './http.service';
import {
  YAMLImportRequest,
  YAMLImportResponse,
  YAMLExportRequest,
  YAMLExportResponse
} from '../types/financial.types';

@Injectable({
  providedIn: 'root'
})
export class ImportExportService {
  private readonly baseUrl = '/import-export/transactions';

  constructor(private httpService: HttpService) {}

  /**
   * Import transactions from YAML data
   */
  importTransactionsYAML(request: YAMLImportRequest): Observable<YAMLImportResponse> {
    return this.httpService.post<YAMLImportResponse>(`${this.baseUrl}/import/yaml`, request).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Import transactions from YAML file
   */
  importTransactionsYAMLFile(
    file: File,
    options?: {
      dryRun?: boolean;
      createMissingCategories?: boolean;
      defaultCategoryType?: string;
    }
  ): Observable<YAMLImportResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (options?.dryRun !== undefined) {
      formData.append('dry_run', options.dryRun.toString());
    }
    if (options?.createMissingCategories !== undefined) {
      formData.append('create_missing_categories', options.createMissingCategories.toString());
    }
    if (options?.defaultCategoryType) {
      formData.append('default_category_type', options.defaultCategoryType);
    }

    return this.httpService.post<YAMLImportResponse>(`${this.baseUrl}/import/yaml/file`, formData).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Export transactions to YAML format
   */
  exportTransactionsYAML(request: YAMLExportRequest): Observable<YAMLExportResponse> {
    return this.httpService.post<YAMLExportResponse>(`${this.baseUrl}/export/yaml`, request).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Download transactions as YAML file
   */
  downloadTransactionsYAML(request: YAMLExportRequest): Observable<Blob> {
    return this.httpService.post<Blob>(`${this.baseUrl}/export/yaml/download`, request).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Get YAML import template
   */
  getYAMLTemplate(): Observable<Blob> {
    return this.httpService.get<Blob>(`${this.baseUrl}/template/yaml`).pipe(
      map(response => response.data!)
    );
  }

  /**
   * Download YAML template file
   */
  downloadYAMLTemplate(): void {
    this.getYAMLTemplate().subscribe(blob => {
      this.downloadBlob(blob, 'transaction_import_template.yaml');
    });
  }

  /**
   * Download YAML export file
   */
  downloadYAMLExport(request: YAMLExportRequest, filename?: string): void {
    this.downloadTransactionsYAML(request).subscribe(blob => {
      const finalFilename = filename || this.generateExportFilename();
      this.downloadBlob(blob, finalFilename);
    });
  }

  /**
   * Validate YAML file before import
   */
  validateYAMLFile(file: File): Observable<YAMLImportResponse> {
    return this.importTransactionsYAMLFile(file, { dryRun: true });
  }

  /**
   * Check if file is valid YAML format
   */
  isValidYAMLFile(file: File): boolean {
    const validExtensions = ['.yaml', '.yml'];
    const fileName = file.name.toLowerCase();
    return validExtensions.some(ext => fileName.endsWith(ext));
  }

  /**
   * Generate export filename with timestamp
   */
  private generateExportFilename(): string {
    const now = new Date();
    const timestamp = now.toISOString().slice(0, 19).replace(/[:]/g, '-');
    return `transactions_export_${timestamp}.yaml`;
  }

  /**
   * Download blob as file
   */
  private downloadBlob(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  /**
   * Parse YAML import response for display
   */
  parseImportResponse(response: YAMLImportResponse): {
    isSuccess: boolean;
    message: string;
    successCount: number;
    errorCount: number;
    totalCount: number;
    errors: string[];
    createdCategories: number;
  } {
    const errors = response.summary.errors.map(error => 
      `Fila ${error.row_index + 1}: ${error.error}`
    );

    return {
      isSuccess: response.success,
      message: response.message,
      successCount: response.summary.successful_imports,
      errorCount: response.summary.failed_imports,
      totalCount: response.summary.total_transactions,
      errors,
      createdCategories: response.summary.created_categories || 0
    };
  }

  /**
   * Format import summary for user display
   */
  formatImportSummary(response: YAMLImportResponse): string {
    const parsed = this.parseImportResponse(response);
    let summary = `${parsed.successCount} de ${parsed.totalCount} transacciones procesadas`;
    
    if (parsed.errorCount > 0) {
      summary += `, ${parsed.errorCount} con errores`;
    }
    
    if (parsed.createdCategories > 0) {
      summary += `, ${parsed.createdCategories} categorías creadas`;
    }

    return summary;
  }

  /**
   * Get file size in human readable format
   */
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  /**
   * Validate import options
   */
  validateImportOptions(options: {
    dryRun?: boolean;
    createMissingCategories?: boolean;
    defaultCategoryType?: string;
  }): string[] {
    const errors: string[] = [];
    
    if (options.defaultCategoryType && 
        !['income', 'expense', 'transfer'].includes(options.defaultCategoryType)) {
      errors.push('Tipo de categoría por defecto debe ser: income, expense o transfer');
    }

    return errors;
  }
}