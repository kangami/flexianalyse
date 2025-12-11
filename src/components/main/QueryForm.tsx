import React, { useState, useRef, useEffect } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import { useAuth } from '../auth/AuthProvider';

interface SuggestedAction {
  id: string;
  title: string;
  description: string;
  sample_prompt: string;
}

interface QueryFormProps {
    isFileContentVisible: boolean;
    setIsFileContentVisible: (visible: boolean) => void;
    onQuerySubmit: (query: string, mode: 'online' | 'local') => void;
    loading: boolean;
    selectedModel: string;
    researchMode: 'online' | 'local';
    setResearchMode: React.Dispatch<React.SetStateAction<'online' | 'local'>>;
    suggestedActions?: SuggestedAction[];
    onSuggestedActionClick?: (action: SuggestedAction) => void;
    language?: 'en' | 'fr' | 'es';
}

const QueryForm: React.FC<QueryFormProps> = ({ 
    isFileContentVisible, 
    setIsFileContentVisible, 
    onQuerySubmit, 
    loading, 
    selectedModel,
    researchMode, 
    setResearchMode,
    suggestedActions = [],
    onSuggestedActionClick,
    language = 'en'
}) => {
    const { t } = useLanguage();
    const { isAuthenticated } = useAuth();
    const [query, setQuery] = useState<string>('');
    const [isMobile, setIsMobile] = useState(false);
    const [alertMessage, setAlertMessage] = useState<string>('');
    
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    
    // Faire disparaître automatiquement l'alerte après 5 secondes
    useEffect(() => {
      if (alertMessage) {
        const timer = setTimeout(() => {
          setAlertMessage('');
        }, 5000);
        return () => clearTimeout(timer);
      }
    }, [alertMessage]);
    
    // Fonction pour vérifier la limite de requêtes
    const checkQueryLimit = (): boolean => {
      if (isAuthenticated) return true;
      
      const today = new Date().toDateString();
      const stored = localStorage.getItem('daily_queries');
      if (!stored) return true;
      
      try {
        const data = JSON.parse(stored);
        if (data.date === today) {
          return (data.count || 0) < 5;
        }
      } catch (e) {
        console.error('Error reading daily queries:', e);
      }
      return true;
    };
    
    // Détection mobile
    useEffect(() => {
        const checkIfMobile = () => {
            setIsMobile(window.innerWidth < 768);
        };

        checkIfMobile();
        window.addEventListener('resize', checkIfMobile);
        return () => window.removeEventListener('resize', checkIfMobile);
    }, []);
    
    // Auto-resize textarea based on content
    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = `${Math.min(textarea.scrollHeight, isMobile ? 120 : 128)}px`;
        }
    }, [query, isMobile]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (query.trim() && !loading) {
            // Vérifier la limite de requêtes pour les utilisateurs non connectés
            if (!isAuthenticated && !checkQueryLimit()) {
                setAlertMessage('You have reached the limit of 5 queries per day. Please sign in to continue using FlexiAnalyse.');
                return;
            }           
            onQuerySubmit(query, researchMode);
            setQuery('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            // Vérifier la limite avant de soumettre
            if (query.trim() && !loading) {
                if (!isAuthenticated && !checkQueryLimit()) {
                    setAlertMessage('You have reached the limit of 5 queries per day. Please sign in to continue using FlexiAnalyse.');
                    return;
                }
            }
            handleSubmit(e);
        }
    };

    return (
    <div className={`
      w-full bg-white
      ${isMobile 
        ? 'px-3 pt-2 pb-3' 
        : 'px-4 pb-4'
      }
    `}>
      <div className={`
        w-full bg-white shadow-lg rounded-xl border
        ${isMobile ? 'max-w-none' : 'max-w-full mx-auto'}
      `}>
        {/* Mobile handle */}
        {isMobile && (
          <div className="flex justify-center pt-2">
            <div className="w-12 h-1 bg-gray-300 rounded-full"></div>
          </div>
        )}

        <div className="p-3 sm:p-4">
          {/* Alerte temporaire pour les limitations */}
          {alertMessage && (
            <div className="mb-3 bg-yellow-500 text-white px-4 py-3 rounded-lg shadow-lg animate-slide-in-right">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2 flex-1">
                  <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <p className="text-sm font-medium">{alertMessage}</p>
                </div>
                <button
                  onClick={() => setAlertMessage('')}
                  className="text-white hover:text-gray-200 transition-colors flex-shrink-0"
                >
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          )}
          
          {/* Panneau d'actions suggérées avec scroll horizontal */}
          {suggestedActions.length > 0 && onSuggestedActionClick && (
            <div className="mb-2 pb-2 border-b border-gray-200">
              <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
                {suggestedActions.map((action) => (
                  <button
                    key={action.id}
                    onClick={() => onSuggestedActionClick(action)}
                    className="flex-shrink-0 bg-white hover:bg-blue-50 text-gray-800 border border-gray-200 rounded-md px-2 py-1 text-[10px] leading-tight transition-colors shadow-sm hover:shadow whitespace-nowrap"
                    title={action.description}
                  >
                    {action.title}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t('query.placeholder')}
            className={`
              w-full bg-transparent outline-none text-gray-700 placeholder-gray-400
              resize-none overflow-y-auto whitespace-pre-wrap
              scrollbar-thin scrollbar-track-transparent scrollbar-thumb-gray-300
              ${isMobile ? 'min-h-[44px] text-base' : 'min-h-[40px] text-sm'}
            `}
            disabled={loading}
            rows={1}
          />

          {/* Controls */}
          <div className={`
            flex flex-col sm:flex-row justify-between items-start sm:items-center
            gap-3 mt-3
          `}>
            {/* Left controls */}
            <div className="flex flex-wrap gap-2">
              {/* Model badge */}
              <span
                className={`
                  bg-gray-100 text-gray-700 rounded-full px-3 py-1 text-xs
                  ${isMobile ? 'font-medium' : 'font-normal'}
                `}
              >
                {selectedModel === 'auto' ? t('query.autoModel') : selectedModel}
              </span>

              {/* File toggle */}
              {!isFileContentVisible && (
                <button
                  onClick={() => setIsFileContentVisible(true)}
                  className={`
                    bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full px-3 py-1
                    flex items-center gap-1 text-xs transition-colors
                  `}
                >
                  <span>📄</span>
                  <span>{t('query.file')}</span>
                </button>
              )}

              {/* Research mode toggle */}
              <button
                onClick={() => setResearchMode(researchMode === 'online' ? 'local' : 'online')}
                className={`
                  ${researchMode === 'online' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}
                  rounded-full px-3 py-1 text-xs flex items-center gap-1 transition-colors
                `}
              >
                {researchMode === 'online' ? (
                  <>
                    <svg 
                      xmlns="http://www.w3.org/2000/svg" 
                      viewBox="0 0 20 20" 
                      fill="currentColor" 
                      className="w-3 h-3"
                    >
                      <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clipRule="evenodd" />
                    </svg>
                    {t('query.research')}
                  </>
                ) : (
                  <>
                    <svg 
                      xmlns="http://www.w3.org/2000/svg" 
                      viewBox="0 0 20 20" 
                      fill="currentColor" 
                      className="w-3 h-3"
                    >
                      <path fillRule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5z" clipRule="evenodd" />
                    </svg>
                    {t('query.local')}
                  </>
                )}
              </button>
            </div>

            {/* Submit button */}
            <button
              onClick={handleSubmit}
              disabled={loading || !query.trim()}
              className={`
                self-end sm:self-center rounded-full p-2 sm:p-2
                ${loading 
                  ? 'bg-gray-300 cursor-not-allowed' 
                  : 'bg-blue-500 hover:bg-blue-600 active:scale-95'
                }
                text-white transition-all
              `}
            >
              {loading ? (
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
                  <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" className="opacity-75"/>
                </svg>
              ) : (
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                </svg>
              )}
            </button>
          </div>

          {/* Mobile helper text */}
          {isMobile && (
            <div className="mt-2 text-xs text-gray-500 text-center">
              {t('query.mobile.help')}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default QueryForm;