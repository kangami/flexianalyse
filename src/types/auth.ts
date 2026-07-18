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

/** Compte côté backend : ligne `users` + organisations dont il est membre. */
export interface Organization {
  id: string;
  name: string;
  role: string | null;
}

export interface Account {
  id: string;
  email: string;
  full_name: string | null;
  organizations: Organization[];
  organization_id: string | null;
}

export interface SignUpCredentials {
  email: string;
  password: string;
  name: string;
  phone?: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  /** Contexte backend (organisation par défaut). Null tant que non provisionné. */
  account: Account | null;
  isLoading: boolean;
  error: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  signup: (credentials: SignUpCredentials) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

export interface AccountTypeChoice {
  type: 'personal' | 'company';
}