// AuthProvider.tsx - Version compatible FedCM
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AuthContextType, User, LoginCredentials, AuthState } from '../../types/auth';

declare global {
  interface Window {
    google: any;
  }
}

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

  const [googleClientId, setGoogleClientId] = useState<string>('');
  const API_URL = import.meta.env.VITE_API_URL || 'https://flexianalyse.com' //'http://localhost:5000';

  useEffect(() => {
    const initAuth = async () => {
      console.log('Initialisation de l\'authentification...');
      
      try {
        await loadGoogleConfig();
        await checkAuthStatus();
        await loadGoogleScript();
      } catch (error) {
        console.error('Erreur lors de l\'initialisation:', error);
        setAuthState(prev => ({
          ...prev,
          isAuthenticated: false,
          user: null,
          isLoading: false,
          error: 'Erreur d\'initialisation'
        }));
      }
    };
    
    initAuth();
  }, []);

  const loadGoogleConfig = async () => {
    try {
      const response = await fetch(`${API_URL}/auth/google/config`);
      if (response.ok) {
        const config = await response.json();
        setGoogleClientId(config.client_id);
        console.log('Configuration Google chargée:', config.configured);
      }
    } catch (error) {
      console.error('Erreur chargement config Google:', error);
    }
  };

  const loadGoogleScript = async () => {
    return new Promise<void>((resolve, reject) => {
      if (window.google?.accounts?.id) {
        console.log('Google Identity Services déjà chargé');
        resolve();
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      
      script.onload = () => {
        const checkGoogle = () => {
          if (window.google?.accounts?.id) {
            console.log('Google Identity Services prêt');
            resolve();
          } else {
            setTimeout(checkGoogle, 100);
          }
        };
        checkGoogle();
      };
      
      script.onerror = () => {
        reject(new Error('Impossible de charger Google Identity Services'));
      };
      
      document.head.appendChild(script);
    });
  };

  const checkAuthStatus = async () => {
    try {
      console.log('Vérification du statut d\'authentification...');
      const token = localStorage.getItem('auth_token');
      
      if (!token) {
        console.log('Aucun token trouvé, utilisateur non authentifié');
        setAuthState(prev => ({ 
          ...prev, 
          isAuthenticated: false,
          user: null,
          isLoading: false 
        }));
        return;
      }

      const response = await fetch(`${API_URL}/auth/verify`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Token valide, utilisateur authentifié:', data.user);
        
        // Assigner un plan gratuit si l'utilisateur n'en a pas
        const userWithPlan = {
          ...data.user,
          plan: data.user.plan || 'free'
        };
        
        setAuthState({
          isAuthenticated: true,
          user: userWithPlan,
          isLoading: false,
          error: null,
        });
      } else {
        console.log('Token invalide, suppression du token');
        localStorage.removeItem('auth_token');
        setAuthState({
          isAuthenticated: false,
          user: null,
          isLoading: false,
          error: null,
        });
      }
    } catch (error) {
      console.error('Erreur lors de la vérification d\'authentification:', error);
      localStorage.removeItem('auth_token');
      setAuthState({
        isAuthenticated: false,
        user: null,
        isLoading: false,
        error: null,
      });
    }
  };

  const login = async (credentials: LoginCredentials) => {
    console.log('Tentative de connexion par email...');
    setAuthState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const response = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
      });

      const data = await response.json();

      if (response.ok) {
        console.log('Connexion réussie:', data.user);
        localStorage.setItem('auth_token', data.token);
        
        // Assigner un plan gratuit si l'utilisateur n'en a pas
        const userWithPlan = {
          ...data.user,
          plan: data.user.plan || 'free'
        };
        
        setAuthState({
          isAuthenticated: true,
          user: userWithPlan,
          isLoading: false,
          error: null,
        });

        await sendEmailToMarketing(data.user.email, data.user.name, 'email');
      } else {
        console.error('Échec de la connexion:', data.error);
        setAuthState(prev => ({
          ...prev,
          isLoading: false,
          error: data.error || 'Échec de la connexion',
        }));
      }
    } catch (error) {
      console.error('Erreur de connexion:', error);
      setAuthState(prev => ({
        ...prev,
        isLoading: false,
        error: 'Erreur de connexion. Veuillez réessayer.',
      }));
    }
  };

  const loginWithGoogle = async () => {
    console.log('Initialisation de l\'authentification Google...');
    setAuthState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      if (!window.google?.accounts?.id || !googleClientId) {
        throw new Error('Google Identity Services non disponible');
      }

      // Configuration compatible FedCM selon la documentation Google
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        callback: handleGoogleResponse,
        auto_select: false,
        cancel_on_tap_outside: true,
        // Opt-in to FedCM pour éviter les avertissements
        use_fedcm_for_prompt: true,
        // Configuration pour le moment d'affichage
        moment_callback: (promptMomentNotification: any) => {
          console.log('Moment notification:', promptMomentNotification);
          
          // Gestion des différents statuts selon la documentation FedCM
          if (promptMomentNotification.isNotDisplayed()) {
            console.log('Prompt non affiché - raison:', promptMomentNotification.getNotDisplayedReason());
            
            // Si le prompt n'est pas affiché, utiliser le bouton de fallback
            showGoogleButton();
          } else if (promptMomentNotification.isSkippedMoment()) {
            console.log('Moment ignoré - raison:', promptMomentNotification.getSkippedReason());
            
            // Moment ignoré, proposer le bouton
            showGoogleButton();
          } else if (promptMomentNotification.isDismissedMoment()) {
            console.log('Moment fermé - raison:', promptMomentNotification.getDismissedReason());
            
            // L'utilisateur a fermé, on peut proposer le bouton plus tard
            setAuthState(prev => ({ ...prev, isLoading: false }));
          }
        }
      });

      // Déclencher le prompt One Tap
      window.google.accounts.id.prompt();

    } catch (error) {
      console.error('Erreur Google:', error);
      setAuthState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Service Google indisponible',
      }));
    }
  };

  const showGoogleButton = () => {
    // Créer un bouton de fallback si le One Tap ne fonctionne pas
    const existingButton = document.getElementById('google-signin-button');
    if (existingButton) {
      existingButton.remove();
    }

    const buttonDiv = document.createElement('div');
    buttonDiv.id = 'google-signin-button';
    buttonDiv.style.position = 'fixed';
    buttonDiv.style.top = '50%';
    buttonDiv.style.left = '50%';
    buttonDiv.style.transform = 'translate(-50%, -50%)';
    buttonDiv.style.zIndex = '10000';
    buttonDiv.style.backgroundColor = 'white';
    buttonDiv.style.padding = '20px';
    buttonDiv.style.borderRadius = '8px';
    buttonDiv.style.boxShadow = '0 4px 16px rgba(0,0,0,0.2)';
    
    document.body.appendChild(buttonDiv);

    window.google.accounts.id.renderButton(buttonDiv, {
      theme: 'outline',
      size: 'large',
      type: 'standard',
      text: 'signin_with',
      locale: 'fr'
    });

    // Ajouter un bouton de fermeture
    const closeButton = document.createElement('button');
    closeButton.textContent = '×';
    closeButton.style.position = 'absolute';
    closeButton.style.top = '5px';
    closeButton.style.right = '10px';
    closeButton.style.border = 'none';
    closeButton.style.background = 'none';
    closeButton.style.fontSize = '20px';
    closeButton.style.cursor = 'pointer';
    closeButton.onclick = () => {
      buttonDiv.remove();
      setAuthState(prev => ({ ...prev, isLoading: false }));
    };
    
    buttonDiv.appendChild(closeButton);
  };

  const handleGoogleResponse = async (response: any) => {
    console.log('Réponse Google reçue');
    
    try {
      const googleToken = response.credential;
      
      if (!googleToken) {
        throw new Error('Token Google manquant');
      }

      const backendResponse = await fetch(`${API_URL}/auth/google`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token: googleToken }),
      });

      const data = await backendResponse.json();

      if (backendResponse.ok && data.success) {
        console.log('Authentification Google réussie:', data.user);
        localStorage.setItem('auth_token', data.token);
        
        // Assigner un plan gratuit si l'utilisateur n'en a pas
        const userWithPlan = {
          ...data.user,
          plan: data.user.plan || 'free'
        };
        
        setAuthState({
          isAuthenticated: true,
          user: userWithPlan,
          isLoading: false,
          error: null,
        });

        await sendEmailToMarketing(data.user.email, data.user.name, 'google');
        
        // Nettoyer le bouton de fallback
        const buttonDiv = document.getElementById('google-signin-button');
        if (buttonDiv) {
          buttonDiv.remove();
        }
        
      } else {
        throw new Error(data.error || 'Échec de l\'authentification Google');
      }

    } catch (error) {
      console.error('Erreur traitement réponse Google:', error);
      setAuthState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Erreur Google. Veuillez réessayer.',
      }));
    }
  };

  const logout = async () => {
    console.log('Déconnexion...');
    
    try {
      if (window.google?.accounts?.id) {
        window.google.accounts.id.disableAutoSelect();
      }
      
      const token = localStorage.getItem('auth_token');
      if (token) {
        await fetch(`${API_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });
      }
    } catch (error) {
      console.warn('Erreur lors de la déconnexion côté serveur:', error);
    } finally {
      localStorage.removeItem('auth_token');
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

  const sendEmailToMarketing = async (email: string, name: string, provider: string) => {
    try {
      await fetch(`${API_URL}/marketing/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          name,
          provider,
          source: 'flexianalyse_signup',
          timestamp: new Date().toISOString(),
        }),
      });
    } catch (error) {
      console.error('Échec de l\'envoi email marketing:', error);
    }
  };

  const value: AuthContextType = {
    ...authState,
    login,
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

// Fix pour le HMR de Vite
if (import.meta.hot) {
  import.meta.hot.accept();
}