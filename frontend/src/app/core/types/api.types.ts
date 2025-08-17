// Tipos base para API
export interface ApiResponse<T = any> {
  data?: T;
  message?: string;
  status: 'success' | 'error';
  errors?: string[];
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface ErrorResponse {
  message: string;
  detail?: string;
  status_code: number;
  errors?: Record<string, string[]>;
}

export interface HealthCheck {
  status: 'healthy' | 'unhealthy';
  version: string;
  timestamp: string;
  services: {
    database: 'healthy' | 'unhealthy';
    auth: 'healthy' | 'unhealthy';
  };
}