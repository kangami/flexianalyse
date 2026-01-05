import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type Language = 'en' | 'fr' | 'es';

interface LanguageContextType {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
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
    
    // Status messages
    'status.extracting.pdf': 'Extracting text from PDF {fileName}...',
    'status.extracting.docx': 'Extracting text from document {fileName}...',
    'status.reading.file': 'Reading file {fileName}...',
    'status.analyzing.document': 'Analyzing document {fileName}...',
    'status.sending.server': 'Sending to server for analysis...',
    'status.ai.analyzing': 'AI analyzing...',
    'status.generating.summary': 'Generating summary...',
    'status.extracting.content': 'Extracting content from {count} file{plural}...',
    'status.analyzing.repository': 'Analyzing repository ({count} file{plural})...',
    'status.generating.repo.summary': 'Generating repository summary...',
    'status.processing.file': 'Processing {fileName}...',
    'status.processing.files': 'Processing {count} files...',
    'status.extracting.files': 'Extracting files...',
    'status.analyzing.question': 'Analyzing your question...',
    'status.processing.request': 'Processing your request...',
    'status.analyzing.file': 'Analyzing file {fileName}...',
    'status.searching.documents': 'Searching in documents...',
    'status.searching.online': 'Searching for information online...',
    'status.generating.response': 'Generating response...',
    'status.extracting.structured': 'Extracting structured data...',
    'status.indexing.extracting': 'Extracting content from {count} files...',
    'status.indexing.processing': 'Processing {fileName} ({current}/{total})...',
    'status.indexing.on.server': 'Indexing on server ({count} files)...',
    'status.indexing.documents': 'Indexing documents...',
    
    // Error messages
    'error.page.limit.exceeded': '⚠️ The file "{fileName}" has {pageCount} pages. The limit is 100 pages per document.',
    'error.page.limit.exceeded.ignored': '⚠️ The file "{fileName}" has {pageCount} pages. The limit is 100 pages per document. This file will be ignored.',
    'error.page.limit.exceeded.generic': '⚠️ The file "{fileName}" exceeds the limit of 100 pages.',
    'error.page.limit.exceeded.query': '⚠️ The file "{fileName}" has {pageCount} pages. The limit is 100 pages per document. Please select another file to ask questions.',
    'error.page.limit.exceeded.query.generic': '⚠️ The file "{fileName}" exceeds the limit of 100 pages. Please select another file to ask questions.',
    
    // Reasoning animation
    'reasoning.analyzing.question': '🧠 Analyzing your question...',
    'reasoning.analyzing.description': 'Understanding the context and requirements',
    'reasoning.gathering.info': '🔍 Gathering relevant information...',
    'reasoning.gathering.description': 'Searching through file contents and structure',
    'reasoning.processing': '⚡ Processing with advanced reasoning...',
    'reasoning.processing.description': 'GPT-5 is thinking deeply about your request',
    'reasoning.formulating': '🎯 Formulating comprehensive response...',
    'reasoning.formulating.description': 'Crafting a detailed and accurate answer',
    'reasoning.finalizing': '✨ Finalizing response...',
    'reasoning.finalizing.description': 'Adding final touches and formatting',
    'reasoning.step': 'Step {current} of {total}',
    'reasoning.powered.by': 'Powered by',
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
    
    // Status messages
    'status.extracting.pdf': 'Extraction du texte du PDF {fileName}...',
    'status.extracting.docx': 'Extraction du texte du document {fileName}...',
    'status.reading.file': 'Lecture du fichier {fileName}...',
    'status.analyzing.document': 'Analyse du document {fileName}...',
    'status.sending.server': 'Envoi au serveur pour analyse...',
    'status.ai.analyzing': 'Analyse en cours par l\'IA...',
    'status.generating.summary': 'Génération du résumé...',
    'status.extracting.content': 'Extraction du contenu de {count} fichier{plural}...',
    'status.analyzing.repository': 'Analyse du répertoire ({count} fichier{plural})...',
    'status.generating.repo.summary': 'Génération du résumé du répertoire...',
    'status.processing.file': 'Traitement de {fileName}...',
    'status.processing.files': 'Traitement de {count} fichiers...',
    'status.extracting.files': 'Extraction des fichiers...',
    'status.analyzing.question': 'Analyse de votre question...',
    'status.processing.request': 'Traitement de votre requête...',
    'status.analyzing.file': 'Analyse du fichier {fileName}...',
    'status.searching.documents': 'Recherche dans les documents...',
    'status.searching.online': 'Recherche d\'informations en ligne...',
    'status.generating.response': 'Génération de la réponse...',
    'status.extracting.structured': 'Extraction des données structurées en cours...',
    'status.indexing.extracting': 'Extraction du contenu de {count} fichiers...',
    'status.indexing.processing': 'Traitement de {fileName} ({current}/{total})...',
    'status.indexing.on.server': 'Indexation sur le serveur ({count} fichiers)...',
    'status.indexing.documents': 'Indexation des documents en cours...',
    
    // Error messages
    'error.page.limit.exceeded': '⚠️ Le fichier "{fileName}" a {pageCount} pages. La limite est de 100 pages par document.',
    'error.page.limit.exceeded.ignored': '⚠️ Le fichier "{fileName}" a {pageCount} pages. La limite est de 100 pages par document. Ce fichier sera ignoré.',
    'error.page.limit.exceeded.generic': '⚠️ Le fichier "{fileName}" dépasse la limite de 100 pages.',
    'error.page.limit.exceeded.query': '⚠️ Le fichier "{fileName}" a {pageCount} pages. La limite est de 100 pages par document. Veuillez sélectionner un autre fichier pour poser des questions.',
    'error.page.limit.exceeded.query.generic': '⚠️ Le fichier "{fileName}" dépasse la limite de 100 pages. Veuillez sélectionner un autre fichier pour poser des questions.',
    
    // Reasoning animation
    'reasoning.analyzing.question': '🧠 Analyse de votre question...',
    'reasoning.analyzing.description': 'Compréhension du contexte et des exigences',
    'reasoning.gathering.info': '🔍 Collecte d\'informations pertinentes...',
    'reasoning.gathering.description': 'Recherche dans le contenu et la structure des fichiers',
    'reasoning.processing': '⚡ Traitement avec raisonnement avancé...',
    'reasoning.processing.description': 'GPT-5 réfléchit profondément à votre demande',
    'reasoning.formulating': '🎯 Formulation d\'une réponse complète...',
    'reasoning.formulating.description': 'Création d\'une réponse détaillée et précise',
    'reasoning.finalizing': '✨ Finalisation de la réponse...',
    'reasoning.finalizing.description': 'Ajout des touches finales et formatage',
    'reasoning.step': 'Étape {current} sur {total}',
    'reasoning.powered.by': 'Propulsé par',
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
    
    // Status messages
    'status.extracting.pdf': 'Extrayendo texto del PDF {fileName}...',
    'status.extracting.docx': 'Extrayendo texto del documento {fileName}...',
    'status.reading.file': 'Leyendo archivo {fileName}...',
    'status.analyzing.document': 'Analizando documento {fileName}...',
    'status.sending.server': 'Enviando al servidor para análisis...',
    'status.ai.analyzing': 'IA analizando...',
    'status.generating.summary': 'Generando resumen...',
    'status.extracting.content': 'Extrayendo contenido de {count} archivo{plural}...',
    'status.analyzing.repository': 'Analizando repositorio ({count} archivo{plural})...',
    'status.generating.repo.summary': 'Generando resumen del repositorio...',
    'status.processing.file': 'Procesando {fileName}...',
    'status.processing.files': 'Procesando {count} archivos...',
    'status.extracting.files': 'Extrayendo archivos...',
    'status.analyzing.question': 'Analizando tu pregunta...',
    'status.processing.request': 'Procesando tu solicitud...',
    'status.analyzing.file': 'Analizando archivo {fileName}...',
    'status.searching.documents': 'Buscando en documentos...',
    'status.searching.online': 'Buscando información en línea...',
    'status.generating.response': 'Generando respuesta...',
    'status.extracting.structured': 'Extrayendo datos estructurados...',
    'status.indexing.extracting': 'Extrayendo contenido de {count} archivos...',
    'status.indexing.processing': 'Procesando {fileName} ({current}/{total})...',
    'status.indexing.on.server': 'Indexando en el servidor ({count} archivos)...',
    'status.indexing.documents': 'Indexando documentos...',
    
    // Error messages
    'error.page.limit.exceeded': '⚠️ El archivo "{fileName}" tiene {pageCount} páginas. El límite es de 100 páginas por documento.',
    'error.page.limit.exceeded.ignored': '⚠️ El archivo "{fileName}" tiene {pageCount} páginas. El límite es de 100 páginas por documento. Este archivo será ignorado.',
    'error.page.limit.exceeded.generic': '⚠️ El archivo "{fileName}" excede el límite de 100 páginas.',
    'error.page.limit.exceeded.query': '⚠️ El archivo "{fileName}" tiene {pageCount} páginas. El límite es de 100 páginas por documento. Por favor, seleccione otro archivo para hacer preguntas.',
    'error.page.limit.exceeded.query.generic': '⚠️ El archivo "{fileName}" excede el límite de 100 páginas. Por favor, seleccione otro archivo para hacer preguntas.',
    
    // Reasoning animation
    'reasoning.analyzing.question': '🧠 Analizando tu pregunta...',
    'reasoning.analyzing.description': 'Comprendiendo el contexto y los requisitos',
    'reasoning.gathering.info': '🔍 Reuniendo información relevante...',
    'reasoning.gathering.description': 'Buscando en el contenido y la estructura de los archivos',
    'reasoning.processing': '⚡ Procesando con razonamiento avanzado...',
    'reasoning.processing.description': 'GPT-5 está pensando profundamente en tu solicitud',
    'reasoning.formulating': '🎯 Formulando una respuesta completa...',
    'reasoning.formulating.description': 'Creando una respuesta detallada y precisa',
    'reasoning.finalizing': '✨ Finalizando respuesta...',
    'reasoning.finalizing.description': 'Añadiendo los toques finales y formateo',
    'reasoning.step': 'Paso {current} de {total}',
    'reasoning.powered.by': 'Impulsado por',
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

  const t = (key: string, params?: Record<string, string | number>): string => {
    let text = translations[language][key] || key;
    
    // Replace placeholders if params provided
    if (params) {
      Object.entries(params).forEach(([paramKey, value]) => {
        text = text.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), String(value));
      });
    }
    
    return text;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

