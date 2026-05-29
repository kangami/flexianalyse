import React from 'react';
import { useLanguage, type Language } from '../../contexts/LanguageContext';
import { Globe } from 'lucide-react';

export function LanguageSwitcher() {
  const { language, setLanguage, t } = useLanguage();
  const languages: Language[] = ['en', 'fr', 'es'];

  return (
    <div className="flex items-center gap-1 p-1 bg-gray-100 rounded-lg">
      <Globe size={16} className="text-gray-600" />
      {languages.map(lang => (
        <button
          key={lang}
          onClick={() => setLanguage(lang)}
          title={t(`lang.${lang === 'en' ? 'english' : lang === 'fr' ? 'french' : 'spanish'}`)}
          className={`px-2 py-1 text-xs font-medium rounded transition-colors ${
            language === lang
              ? 'bg-purple-600 text-white shadow-md'
              : 'bg-white text-gray-700 hover:bg-gray-200'
          }`}
        >
          {lang.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
