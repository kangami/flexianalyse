import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type Language = 'en' | 'fr' | 'es';

interface LanguageContextType {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

interface LanguageProviderProps {
  children: ReactNode;
}

// Traductions
const translations: Record<Language, Record<string, string>> = {
  en: {
    // ChatPanel
    'chat.title': 'Chat',
    'chat.empty.title': 'What do you want to know?',
    'chat.empty.description': 'Start by asking a question or uploading a file to get insights.',
    
    // QueryForm
    'query.placeholder': 'What do you want to know?',
    'query.autoModel': 'Auto model selection',
    'query.research': 'Research',
    'query.local': 'Local',
    'query.file': 'File',
    'query.send': 'Send',
    'query.mobile.help': 'Press Enter to send, Shift+Enter for new line',
    
    // FileViewer
    'fileviewer.dragDrop': 'Drag and drop a file or a repository',
    'fileviewer.selectFile': 'Select File',
    'fileviewer.uploadHint': 'Upload documents to start analyzing them with AI',
    'fileviewer.directory.selected': 'Directory selected',
    'fileviewer.directory.selectFile': 'Select a file from the directory in the sidebar to start analysis',
    'fileviewer.directory.filesAvailable': 'files available',
    'fileviewer.zoom.out': 'Zoom out',
    'fileviewer.zoom.in': 'Zoom in',
    'fileviewer.page.previous': 'Previous page',
    'fileviewer.page.next': 'Next page',
    'fileviewer.page.search': 'Search',
    'fileviewer.page.of': 'of',
    'fileviewer.search.prompt': 'Search in document',
    'fileviewer.processing': 'Processing files...',
    'fileviewer.pdf.loading': 'Loading PDF...',
    'fileviewer.pdf.error': 'Error loading PDF',
    'fileviewer.docx.error': 'Error loading DOCX',
    'fileviewer.unsupported': 'Unsupported file type',
    
    // ResponseDisplay
    'response.insert': 'Insert',
    'response.insert.tooltip': 'Insert this text into the document',
    
    // Sidebar
    'sidebar.noFiles': 'No files',
    'sidebar.file': 'File',
    'sidebar.export': 'Export',
    'sidebar.model': 'Model',
    'sidebar.upload': 'Upload',
    
    // Common
    'common.pages': 'pages',
    'common.page': 'page',
    'common.file': 'file',
  },
  fr: {
    // ChatPanel
    'chat.title': 'Chat',
    'chat.empty.title': 'Que souhaitez-vous savoir ?',
    'chat.empty.description': 'Commencez par poser une question ou télécharger un fichier pour obtenir des informations.',
    
    // QueryForm
    'query.placeholder': 'Que souhaitez-vous savoir ?',
    'query.autoModel': 'Sélection automatique du modèle',
    'query.research': 'Recherche',
    'query.local': 'Local',
    'query.file': 'Fichier',
    'query.send': 'Envoyer',
    'query.mobile.help': 'Appuyez sur Entrée pour envoyer, Maj+Entrée pour une nouvelle ligne',
    
    // FileViewer
    'fileviewer.dragDrop': 'Glissez-déposez un fichier ou un répertoire',
    'fileviewer.selectFile': 'Sélectionner un fichier',
    'fileviewer.uploadHint': 'Téléchargez des documents pour commencer à les analyser avec l\'IA',
    'fileviewer.directory.selected': 'Répertoire sélectionné',
    'fileviewer.directory.selectFile': 'Sélectionnez un fichier du répertoire dans la barre latérale pour commencer l\'analyse',
    'fileviewer.directory.filesAvailable': 'fichiers disponibles',
    'fileviewer.zoom.out': 'Zoom arrière',
    'fileviewer.zoom.in': 'Zoom avant',
    'fileviewer.page.previous': 'Page précédente',
    'fileviewer.page.next': 'Page suivante',
    'fileviewer.page.search': 'Rechercher',
    'fileviewer.page.of': 'sur',
    'fileviewer.processing': 'Traitement des fichiers...',
    'fileviewer.pdf.loading': 'Chargement du PDF...',
    'fileviewer.pdf.error': 'Erreur lors du chargement du PDF',
    'fileviewer.docx.error': 'Erreur lors du chargement du DOCX',
    'fileviewer.unsupported': 'Type de fichier non supporté',
    
    // ResponseDisplay
    'response.insert': 'Insérer',
    'response.insert.tooltip': 'Insérer ce texte dans le document',
    
    // Sidebar
    'sidebar.noFiles': 'Aucun fichier',
    'sidebar.file': 'Fichier',
    'sidebar.export': 'Exporter',
    'sidebar.model': 'Modèle',
    'sidebar.upload': 'Télécharger',
    
    // Common
    'common.pages': 'pages',
    'common.page': 'page',
    'common.file': 'fichier',
  },
  es: {
    // ChatPanel
    'chat.title': 'Chat',
    'chat.empty.title': '¿Qué quieres saber?',
    'chat.empty.description': 'Comienza haciendo una pregunta o subiendo un archivo para obtener información.',
    
    // QueryForm
    'query.placeholder': '¿Qué quieres saber?',
    'query.autoModel': 'Selección automática de modelo',
    'query.research': 'Investigación',
    'query.local': 'Local',
    'query.file': 'Archivo',
    'query.send': 'Enviar',
    'query.mobile.help': 'Presiona Enter para enviar, Shift+Enter para nueva línea',
    
    // FileViewer
    'fileviewer.dragDrop': 'Arrastra y suelta un archivo o un repositorio',
    'fileviewer.selectFile': 'Seleccionar archivo',
    'fileviewer.uploadHint': 'Sube documentos para comenzar a analizarlos con IA',
    'fileviewer.directory.selected': 'Directorio seleccionado',
    'fileviewer.directory.selectFile': 'Selecciona un archivo del directorio en la barra lateral para comenzar el análisis',
    'fileviewer.directory.filesAvailable': 'archivos disponibles',
    'fileviewer.zoom.out': 'Alejar',
    'fileviewer.zoom.in': 'Acercar',
    'fileviewer.page.previous': 'Página anterior',
    'fileviewer.page.next': 'Página siguiente',
    'fileviewer.page.search': 'Buscar',
    'fileviewer.page.of': 'de',
    'fileviewer.search.prompt': 'Buscar en el documento',
    'fileviewer.processing': 'Procesando archivos...',
    'fileviewer.pdf.loading': 'Cargando PDF...',
    'fileviewer.pdf.error': 'Error al cargar el PDF',
    'fileviewer.docx.error': 'Error al cargar el DOCX',
    'fileviewer.unsupported': 'Tipo de archivo no soportado',
    
    // ResponseDisplay
    'response.insert': 'Insertar',
    'response.insert.tooltip': 'Insertar este texto en el documento',
    
    // Sidebar
    'sidebar.noFiles': 'Sin archivos',
    'sidebar.file': 'Archivo',
    'sidebar.export': 'Exportar',
    'sidebar.model': 'Modelo',
    'sidebar.upload': 'Subir',
    
    // Common
    'common.pages': 'páginas',
    'common.page': 'página',
    'common.file': 'archivo',
  },
};

export const LanguageProvider: React.FC<LanguageProviderProps> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    const savedLanguage = localStorage.getItem('app-language') as Language;
    return savedLanguage || 'en';
  });

  const setLanguage = (newLanguage: Language) => {
    setLanguageState(newLanguage);
    localStorage.setItem('app-language', newLanguage);
  };

  const t = (key: string): string => {
    return translations[language][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

