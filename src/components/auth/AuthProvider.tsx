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
import { provisionAccount } from '../../lib/apiClient';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    account: null,
    isLoading: true,
    error: null,
  });

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (!firebaseUser) {
        setAuthState({
          isAuthenticated: false,
          user: null,
          account: null,
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

      // Provisionne le compte backend (User + organisation par défaut) et récupère
      // son contexte. Idempotent : rejoué à chaque connexion sans rien dupliquer.
      // Remplace l'ancien appel à /users/me, qui visait une route legacy non montée
      // et échouait donc silencieusement à chaque fois.
      // displayName brut, pas mappedUser.name : ce dernier retombe sur la partie
      // locale de l'email, ce qui masquerait le nom mis en attente par le
      // formulaire d'inscription (cf. setPendingFullName).
      let account = null;
      try {
        account = await provisionAccount(firebaseUser.displayName || undefined);
      } catch (error) {
        console.warn('Provisionnement du compte échoué:', error);
      }

      setAuthState({
        isAuthenticated: true,
        user: mappedUser,
        account,
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
        account: null,
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