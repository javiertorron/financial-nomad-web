// Tipos para autenticación
export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  role: 'admin' | 'user' | 'guest';
  status: 'active' | 'inactive' | 'suspended' | 'pending';
  locale: string;
  timezone: string;
  currency: string;
  last_login?: string;
  has_asana_integration: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
  invitation_code: string;
}

export interface RegisterResponse {
  message: string;
  user_id: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface TokenInfo {
  access_token: string;
  expires_at: number;
  user: User;
}