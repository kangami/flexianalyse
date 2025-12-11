import React, { useState, useEffect, useRef } from 'react';
import ResponseDisplay from './ResponseDisplay';
import { franc } from 'franc-min';
import { useTheme } from '../../contexts/ThemeContext';
import { useLanguage } from '../../contexts/LanguageContext';

interface ChatMessage {
  id: string;
  userQuery: string;
  aiResponse: string;
  displayedAiResponse?: string;
}

interface SuggestedAction {
  id: string;
  title: string;
  description: string;
  sample_prompt: string;
}

interface EditableFile {
  file: File;
  content: string | ArrayBuffer;
  type: 'code' | 'docx';
}

interface ChatPanelProps {
  chatHistory: ChatMessage[];
  loading: boolean;
  onQuerySubmit: (query: string, mode: 'online' | 'local') => void;
  selectedModel: string;
  researchMode: 'online' | 'local';
  setResearchMode: React.Dispatch<React.SetStateAction<'online' | 'local'>>;
  suggestedActions?: SuggestedAction[];
  onSuggestedActionClick?: (action: SuggestedAction) => void;
  editableFiles?: EditableFile[];
  onTextSelect?: (text: string) => void;
  getEditableFiles?: () => Promise<EditableFile[]>;
  isSearchingOnline?: boolean;
  currentStatus?: string;
  isFileContentVisible?: boolean;
  setIsFileContentVisible?: (visible: boolean) => void;
  isProcessingDrop?: boolean;
}

const ChatPanel: React.FC<ChatPanelProps> = ({
  chatHistory,
  loading,
  onQuerySubmit,
  selectedModel,
  researchMode,
  setResearchMode,
  suggestedActions = [],
  onSuggestedActionClick,
  editableFiles = [],
  onTextSelect,
  getEditableFiles,
  isSearchingOnline = false,
  currentStatus = '',
  isFileContentVisible = false,
  setIsFileContentVisible,
  isProcessingDrop = false
}) => {
  const { theme, setTheme } = useTheme();
  const { language, setLanguage, t } = useLanguage();
  const [isThemeDropdownOpen, setIsThemeDropdownOpen] = useState<boolean>(false);
  const themeDropdownRef = useRef<HTMLDivElement>(null);
  const languageOptions = [
    { code: 'en', name: 'English', flag: '🇬🇧' },
    { code: 'fr', name: 'Français', flag: '🇫🇷' },
    { code: 'es', name: 'Español', flag: '🇪🇸' }
  ];
  
  const themeOptions = [
    { value: 'white', label: 'White', color: 'bg-white' },
    { value: 'dark', label: 'Dark', color: 'bg-gray-900' },
    { value: 'dark-blue', label: 'Dark Blue', color: 'bg-blue-950' }
  ];

  // Détection automatique de la langue désactivée pour permettre à l'utilisateur de changer manuellement
  // L'utilisateur peut maintenant changer la langue à tout moment via le sélecteur
  // La langue de l'interface reste celle choisie par l'utilisateur, indépendamment du contenu

  const handleLanguageChange = (langCode: string) => {
    setLanguage(langCode as 'en' | 'fr' | 'es');
  };

  const handleQuerySubmitWithLanguage = (query: string, mode: 'online' | 'local') => {
    // Le modèle répondra dans la langue du prompt, pas besoin de changer la langue de l'interface
    // La langue de l'interface reste celle choisie par l'utilisateur
    onQuerySubmit(query, mode);
  };

  // Fermer le dropdown de thème quand on clique en dehors
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (themeDropdownRef.current && !themeDropdownRef.current.contains(event.target as Node)) {
        setIsThemeDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header avec sélecteur de thème et langue */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center shadow-md">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <span className="text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            FlexiAnalyse
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* Sélecteur de thème */}
          <div className="relative" ref={themeDropdownRef}>
            <button
              onClick={() => setIsThemeDropdownOpen(!isThemeDropdownOpen)}
              className="w-6 h-6 rounded-full border-2 border-blue-500 flex items-center justify-center bg-white hover:bg-blue-50 transition-all shadow-md hover:shadow-lg active:scale-95"
              style={{
                boxShadow: '0 2px 4px rgba(59, 130, 246, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.5), inset 0 -1px 0 rgba(59, 130, 246, 0.2)'
              }}
              title="Changer le thème"
            >
              <div className={`w-3 h-3 rounded-full ${themeOptions.find(t => t.value === theme)?.color || 'bg-white'}`}></div>
            </button>
            {isThemeDropdownOpen && (
              <div className="absolute right-0 mt-2 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                {themeOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => {
                      setTheme(option.value as 'white' | 'dark' | 'dark-blue');
                      setIsThemeDropdownOpen(false);
                    }}
                    className={`w-full px-4 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-100 transition-colors ${
                      theme === option.value ? 'bg-blue-50' : ''
                    }`}
                  >
                    <div className={`w-4 h-4 rounded-full ${option.color} border border-gray-300`}></div>
                    <span className="text-gray-700">{option.label}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          
          {/* Sélecteur de langue */}
          <select
            value={language}
            onChange={(e) => handleLanguageChange(e.target.value)}
            className={`px-3 py-1.5 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors ${
              theme === 'dark' 
                ? 'bg-gray-800 border-gray-600 text-gray-200 hover:bg-gray-700' 
                : theme === 'dark-blue'
                ? 'bg-blue-900 border-blue-700 text-blue-100 hover:bg-blue-800'
                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {languageOptions.map(lang => (
              <option key={lang.code} value={lang.code}>
                {lang.flag} {lang.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Zone de chat avec QueryForm intégré */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <ResponseDisplay
          chatHistory={chatHistory}
          loading={loading}
          editableFiles={editableFiles}
          onTextSelect={onTextSelect}
          getEditableFiles={getEditableFiles}
          isSearchingOnline={isSearchingOnline}
          currentStatus={currentStatus}
          onQuerySubmit={handleQuerySubmitWithLanguage}
          selectedModel={selectedModel}
          researchMode={researchMode}
          setResearchMode={setResearchMode}
          suggestedActions={suggestedActions}
          onSuggestedActionClick={onSuggestedActionClick}
          isFileContentVisible={isFileContentVisible}
          setIsFileContentVisible={setIsFileContentVisible}
        />
      </div>
    </div>
  );
};

export default ChatPanel;

