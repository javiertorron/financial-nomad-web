import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { ApiResponse, PaginationParams, PaginatedResponse } from '../types/api.types';

@Injectable({
  providedIn: 'root'
})
export class HttpService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  get<T>(endpoint: string, params?: Record<string, any>): Observable<ApiResponse<T>> {
    const httpParams = this.buildHttpParams(params);
    return this.http.get<ApiResponse<T>>(`${this.baseUrl}${endpoint}`, { params: httpParams });
  }

  post<T>(endpoint: string, body: any): Observable<ApiResponse<T>> {
    return this.http.post<ApiResponse<T>>(`${this.baseUrl}${endpoint}`, body);
  }

  put<T>(endpoint: string, body: any): Observable<ApiResponse<T>> {
    return this.http.put<ApiResponse<T>>(`${this.baseUrl}${endpoint}`, body);
  }

  patch<T>(endpoint: string, body: any): Observable<ApiResponse<T>> {
    return this.http.patch<ApiResponse<T>>(`${this.baseUrl}${endpoint}`, body);
  }

  delete<T>(endpoint: string): Observable<ApiResponse<T>> {
    return this.http.delete<ApiResponse<T>>(`${this.baseUrl}${endpoint}`);
  }

  getPaginated<T>(
    endpoint: string, 
    paginationParams?: PaginationParams,
    filters?: Record<string, any>
  ): Observable<ApiResponse<PaginatedResponse<T>>> {
    const params = { ...paginationParams, ...filters };
    const httpParams = this.buildHttpParams(params);
    
    return this.http.get<ApiResponse<PaginatedResponse<T>>>(
      `${this.baseUrl}${endpoint}`, 
      { params: httpParams }
    );
  }

  private buildHttpParams(params?: Record<string, any>): HttpParams {
    let httpParams = new HttpParams();
    
    if (params) {
      Object.keys(params).forEach(key => {
        const value = params[key];
        if (value !== null && value !== undefined && value !== '') {
          if (Array.isArray(value)) {
            value.forEach(item => httpParams = httpParams.append(key, item.toString()));
          } else {
            httpParams = httpParams.set(key, value.toString());
          }
        }
      });
    }
    
    return httpParams;
  }
}