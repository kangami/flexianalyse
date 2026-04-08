import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import {
  createUserWithEmailAndPassword,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
  updateProfile,
} from 'firebase/auth';
import { AuthContextType, User, LoginCredentials, AuthState, SignUpCredentials } from '../../types/auth';
import { auth, googleProvider } from '../../lib/firebase';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (!firebaseUser) {
        setAuthState({
          isAuthenticated: false,
          user: null,
          isLoading: false,
          error: null,
        });
        return;
      }

      const providerId = firebaseUser.providerData[0]?.providerId;
      const mappedUser: User = {
        id: firebaseUser.uid,
        email: firebaseUser.email || '',
        name: firebaseUser.displayName || firebaseUser.email?.split('@')[0] || 'User',
        provider: providerId === 'google.com' ? 'google' : 'email',
        avatar: firebaseUser.photoURL || undefined,
        plan: 'free',
        createdAt: firebaseUser.metadata.creationTime || undefined,
      };

      try {
        const token = await firebaseUser.getIdToken();
        const backendUrl = import.meta.env.VITE_API_URL || 'https://flexianalyse.com';
        await fetch(`${backendUrl}/users/me`, {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
      } catch (error) {
        console.warn('Backend user sync failed:', error);
      }

      setAuthState({
        isAuthenticated: true,
        user: mappedUser,
        isLoading: false,
        error: null,
      });
    });

    return () => unsubscribe();
  }, []);

  const login = async (credentials: LoginCredentials) => {
    setAuthState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      await signInWithEmailAndPassword(auth, credentials.email, credentials.password);
    } catch (error) {
      setAuthState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Erreur de connexion. Veuillez réessayer.',
      }));
    }
  };

  const signup = async (credentials: SignUpCredentials) => {
    setAuthState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await createUserWithEmailAndPassword(auth, credentials.email, credentials.password);
      if (credentials.name) {
        await updateProfile(result.user, { displayName: credentials.name });
      }
    } catch (error) {
      setAuthState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Erreur lors de la création du compte.',
      }));
    }
  };

  const loginWithGoogle = async () => {
    setAuthState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      await signInWithPopup(auth, googleProvider);
    } catch (error) {
      setAuthState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Service Google indisponible',
      }));
    }
  };

  const logout = async () => {
    try {
      await signOut(auth);
    } catch (error) {
      console.warn('Erreur lors de la déconnexion:', error);
    } finally {
      setAuthState({
        isAuthenticated: false,
        user: null,
        isLoading: false,
        error: null,
      });
    }
  };

  const clearError = () => {
    setAuthState(prev => ({ ...prev, error: null }));
  };

  const value: AuthContextType = {
    ...authState,
    login,
    signup,
    loginWithGoogle,
    logout,
    clearError,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};