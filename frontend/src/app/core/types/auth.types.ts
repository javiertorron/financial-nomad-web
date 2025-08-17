// Tipos para autenticación
export interface User {
  id: string;
  email: string;
  name: string;
  picture?: string;
  created_at: string;
  updated_at: string;
  is_active: boolean;
}

export interface LoginRequest {
  google_token: string;
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

export interface GoogleUser {
  id: string;
  email: string;
  name: string;
  picture: string;
  email_verified: boolean;
}

export interface TokenInfo {
  access_token: string;
  expires_at: number;
  user: User;
}