// src/types/auth.ts
export interface User {
  id: string;
  email: string;
  name: string;
  provider: 'email' | 'google';
  avatar?: string;
  plan?: 'free' | 'premium' | 'enterprise';
  phone?: string;
  createdAt?: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  isLoading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => void;
  clearError: () => void;
}