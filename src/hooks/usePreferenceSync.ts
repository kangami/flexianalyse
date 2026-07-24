import { useEffect, useRef } from 'react';
import { useAuth } from '../components/auth/AuthProvider';
import { useTheme, Theme } from '../contexts/ThemeContext';
import { useLanguage, Language } from '../contexts/LanguageContext';
import { savePreferences } from '../lib/apiClient';

/**
 * Garde le thème + la langue synchronisés entre localStorage (contextes) et la
 * base : applique les préférences enregistrées à la connexion, et persiste tout
 * changement de l'utilisateur authentifié.
 */
export function usePreferenceSync() {
  const { account, isAuthenticated } = useAuth();
  const { theme, setTheme } = useTheme();
  const { language, setLanguage } = useLanguage();
  const synced = useRef<{ theme?: string; language?: string }>({});

  useEffect(() => {
    if (!account) return;
    synced.current = { theme: account.theme ?? undefined, language: account.language ?? undefined };
    if (account.theme && account.theme !== theme) setTheme(account.theme as Theme);
    if (account.language && account.language !== language) setLanguage(account.language as Language);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [account]);

  useEffect(() => {
    if (!isAuthenticated) return;
    if (theme === synced.current.theme && language === synced.current.language) return;
    synced.current = { theme, language };
    savePreferences({ theme, language }).catch(() => {});
  }, [theme, language, isAuthenticated]);
}
