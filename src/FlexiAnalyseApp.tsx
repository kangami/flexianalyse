// App.tsx - Modifications nécessaires

import React, { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "./components/main/Sidebar";
import FileViewer from "./components/main/FileViewer";
import ChatPanel from "./components/main/ChatPanel";
import StructuredDataDisplay from "./components/main/StructuredDataDisplay";
import InsertTextModal from "./components/main/InsertTextModal";
import mammoth from 'mammoth';
import * as pdfjslib from 'pdfjs-dist/legacy/build/pdf';
import pdfWorker from 'pdfjs-dist/legacy/build/pdf.worker?url';
import { franc } from 'franc-min';
import { useAuth } from './components/auth/AuthProvider';
import { useTheme } from './contexts/ThemeContext';
import { useLanguage } from './contexts/LanguageContext';

interface FileDetails {
  content: string | ArrayBuffer;
  description: string;
}

interface ChatMessage {
  id: string;
  userQuery: string;
  aiResponse: string;
}

interface SuggestedAction {
  id: string;
  title: string;
  description: string;
  sample_prompt: string;
}

pdfjslib.GlobalWorkerOptions.workerSrc = pdfWorker;

// Auto model selection helper
const AUTO_MODEL_ID = 'auto';

const chooseModelForQuery = (query: string): string => {
  const normalized = query.toLowerCase();
  const length = query.length;

  const isCodeOrDebugQuery = /bug|error|exception|stack trace|stacktrace|traceback|optimiz|refactor|performance|memory leak|crash/.test(normalized);
  const isHighReasoningQuery = /architecture|design pattern|scalability|security|threat model|strategy|roadmap|system design/.test(normalized);
  const isMultilingualHint = /translate|traduire|traduction|multi[- ]language|multilingual/.test(normalized);

  if (length > 1500 || isHighReasoningQuery || isMultilingualHint) {
    return 'gpt-5';
  }

  if (isCodeOrDebugQuery || length > 600) {
    return 'gpt-4o';
  }

  return 'gpt-3.5-turbo';
};

const FlexiAnalyseApp: React.FC = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const { theme } = useTheme();
  const { language, t } = useLanguage();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileDetails, setFileDetails] = useState<FileDetails | null>(null);
  const [isFileContentVisible, setIsFileContentVisible] = useState<boolean>(true);
  const [responses, setResponses] = useState([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [repoStructure, setRepoStructure] = useState<string>('');
  const [directoryFiles, setDirectoryFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [isSearchingOnline, setIsSearchingOnline] = useState<boolean>(false);
  const [currentStatus, setCurrentStatus] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>(AUTO_MODEL_ID);
  const [researchMode, setResearchMode] = useState<'online' | 'local'>('online');
  const [isMobile, setIsMobile] = useState(false);
  
  // NOUVEAU: États pour gérer l'indexation backend
  const [isDirectoryIndexed, setIsDirectoryIndexed] = useState<boolean>(false);
  const [indexingStatus, setIndexingStatus] = useState<string>('');
  const [sessionId] = useState(() => Math.random().toString(36).substr(2, 9));
  const [suggestedActions, setSuggestedActions] = useState<SuggestedAction[]>([]);
  
  // États pour l'extraction structurée
  const [structuredData, setStructuredData] = useState<any>(null);
  const [showStructuredData, setShowStructuredData] = useState<boolean>(false);
  const [extracting, setExtracting] = useState<boolean>(false);
  
  // États pour l'insertion de texte
  const [showInsertModal, setShowInsertModal] = useState<boolean>(false);
  const [selectedTextToInsert, setSelectedTextToInsert] = useState<string>('');
  
  // État pour l'animation de chargement lors du drop
  const [isProcessingDrop, setIsProcessingDrop] = useState<boolean>(false);
  
  // État pour savoir si un répertoire est sélectionné
  const [selectedDirectory, setSelectedDirectory] = useState<File[] | null>(null);
  
  // État pour l'infobulle de limitation
  const [showLimitInfo, setShowLimitInfo] = useState<boolean>(false);
  const [limitMessage, setLimitMessage] = useState<string>('');

  // Ref pour tracker les derniers fichiers indexés
  const lastIndexedFilesRef = useRef<File[]>([]);
  
  // Fonctions utilitaires pour gérer les limitations des utilisateurs non connectés
  const getDailyQueries = useCallback((): number => {
    const today = new Date().toDateString();
    const stored = localStorage.getItem('daily_queries');
    if (!stored) return 0;
    
    try {
      const data = JSON.parse(stored);
      if (data.date === today) {
        return data.count || 0;
      }
    } catch (e) {
      console.error('Error reading daily queries:', e);
    }
    return 0;
  }, []);
  
  const incrementDailyQueries = useCallback(() => {
    const today = new Date().toDateString();
    const currentCount = getDailyQueries();
    localStorage.setItem('daily_queries', JSON.stringify({
      date: today,
      count: currentCount + 1
    }));
  }, [getDailyQueries]);
  
  const getUploadedFilesCount = useCallback((): number => {
    const stored = localStorage.getItem('uploaded_files');
    if (!stored) return 0;
    
    try {
      const data = JSON.parse(stored);
      return data.count || 0;
    } catch (e) {
      console.error('Error reading uploaded files:', e);
    }
    return 0;
  }, []);
  
  const incrementUploadedFiles = useCallback(() => {
    const currentCount = getUploadedFilesCount();
    localStorage.setItem('uploaded_files', JSON.stringify({
      count: currentCount + 1
    }));
  }, [getUploadedFilesCount]);
  
  const checkQueryLimit = useCallback((): boolean => {
    if (isAuthenticated) return true;
    const queryCount = getDailyQueries();
    return queryCount < 5;
  }, [isAuthenticated, getDailyQueries]);
  
  const checkFileUploadLimit = useCallback((): boolean => {
    if (isAuthenticated) return true;
    const fileCount = getUploadedFilesCount();
    return fileCount < 1;
  }, [isAuthenticated, getUploadedFilesCount]);
  
  // Fonction pour afficher l'infobulle de limitation
  const showLimitInfoBubble = useCallback((message: string) => {
    setLimitMessage(message);
    setShowLimitInfo(true);
    setTimeout(() => setShowLimitInfo(false), 5000);
  }, []);

  // Détection mobile (reste identique)
  useEffect(() => {
    const checkIfMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkIfMobile();
    window.addEventListener('resize', checkIfMobile);
    return () => window.removeEventListener('resize', checkIfMobile);
  }, []);

  // Fermer la sidebar automatiquement sur mobile après sélection (reste identique)
  useEffect(() => {
    if (isMobile && selectedFile) {
      setIsSidebarOpen(false);
    }
  }, [selectedFile, isMobile]);

  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen);

  // Fonction pour ajouter un fichier à la sidebar
  const addFileToSidebar = useCallback((file: File) => {
    // Utiliser la fonction exposée par la Sidebar si elle existe
    if ((window as any).__addFileToSidebar) {
      (window as any).__addFileToSidebar(file);
    }
  }, []);

  const handleFileSelect = async (file: File, details: FileDetails) => {
    const clonedContent = details.content instanceof ArrayBuffer ? details.content.slice(0) : details.content;
    setSelectedFile(file);
    setFileDetails({ ...details, content: clonedContent });
    setIsFileContentVisible(true);
    // Désactiver la recherche web et forcer le mode "local" dès qu'un fichier est importé
    setResearchMode('local');
    
    // Ajouter le fichier à directoryFiles s'il n'y est pas déjà pour déclencher l'indexation
    setDirectoryFiles(prevFiles => {
      const fileExists = prevFiles.some(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified);
      if (!fileExists) {
        return [...prevFiles, file];
      }
      return prevFiles;
    });

    // Ajouter le fichier à la sidebar
    addFileToSidebar(file);
    
    // Afficher le statut initial avant de commencer l'analyse
    setLoading(true);
    
    // Si le fichier fait partie d'un répertoire, régénérer les suggested actions en arrière-plan (non-bloquant)
    if (selectedDirectory && selectedDirectory.length > 1) {
      regenerateSuggestedActionsForFile(file).catch(err => {
        console.error('Error regenerating suggested actions:', err);
      });
    }
    
    // Générer automatiquement un résumé avec animation de typing (se lance immédiatement, ne bloque pas les actions suggérées)
    await generateFileSummaryWithStreaming(file, clonedContent);
  };
  

  // Gestion du drag & drop pour FileViewer
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);
  
  const apiUrl = 'http://127.0.0.1:5000'; // 'http://127.0.0.1:5000' 'https://flexianalyse.com';

  // Fonctions d'extraction de texte (doivent être définies avant generateFileSummary)
  const extractTextFromDocx = async (content: ArrayBuffer): Promise<string> => {
    try {
      if (content.byteLength === 0) {
        console.error('Error: DOCX file is empty');
        return 'Error: Le fichier DOCX est vide ou corrompu.';
      }
      const result = await mammoth.extractRawText({ arrayBuffer: content });
      if (!result || !result.value || result.value.trim().length === 0) {
        return 'Le fichier DOCX ne contient pas de texte extractible.';
      }
      return result.value;
    } catch (error) {
      console.error('Error extracting text from .docx:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      if (errorMessage.includes('Corrupted zip') || errorMessage.includes('data length = 0')) {
        return 'Error: Le fichier DOCX est corrompu ou invalide. Veuillez vérifier le fichier.';
      }
      return `Error extracting text from .docx: ${errorMessage}`;
    }
  };

  const extractTextFromPdf = async (arrayBuffer: ArrayBuffer): Promise<string> => {
    try {
      const bufferCopy = arrayBuffer.slice(0);
      const pdf = await pdfjslib.getDocument({ data: bufferCopy }).promise;
      let text = '';
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const content = await page.getTextContent();
        const strings = content.items.map((item: any) => item.str).join(' ');
        text += strings + '\n';
      }
      return text;
    } catch (error) {
      console.error('Error extracting text from PDF:', error);
      return 'Error extracting text from PDF';
    }
  };

  // Fonction pour générer un résumé d'un fichier avec streaming et animation de typing
  const generateFileSummaryWithStreaming = useCallback(async (file: File, content: string | ArrayBuffer) => {
    try {
      let fileContent: string;
      const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      
      // Afficher le statut d'extraction selon le type de fichier
      if (extension === '.pdf') {
        setCurrentStatus(t('status.extracting.pdf', { fileName: file.name }));
        fileContent = await extractTextFromPdf(content as ArrayBuffer);
      } else if (extension === '.docx') {
        setCurrentStatus(t('status.extracting.docx', { fileName: file.name }));
        fileContent = await extractTextFromDocx(content as ArrayBuffer);
      } else {
        setCurrentStatus(t('status.reading.file', { fileName: file.name }));
        fileContent = typeof content === 'string' ? content : new TextDecoder().decode(new Uint8Array(content as ArrayBuffer));
      }
      
      // Limiter le contenu pour la requête
      const limitedContent = fileContent.substring(0, 2000);
      
      // Créer un message dans le chat history pour le résumé
      const messageId = Math.random().toString(36).substr(2, 9);
      const summaryMessage: ChatMessage = {
        id: messageId,
        userQuery: `📄 ${file.name}`,
        aiResponse: ''
      };
      
      // Ajouter le message à l'historique
      setChatHistory((prev) => [...prev, summaryMessage]);
      setLoading(true);
      
      // Mettre à jour le statut pour l'analyse
      setCurrentStatus(t('status.analyzing.document', { fileName: file.name }));
      
      // Utiliser le streaming pour le résumé
      setCurrentStatus(t('status.sending.server'));
      const response = await fetch(`${apiUrl}/summarize_file_stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_name: file.name,
          file_content: limitedContent,
          language: language
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unable to read error message');
        console.error('❌ Erreur résumé fichier:', {
          status: response.status,
          statusText: response.statusText,
          error: errorText,
          url: `${apiUrl}/summarize_file_stream`,
          method: 'POST'
        });
        
        // Si c'est une erreur 405, c'est probablement un problème de configuration serveur
        if (response.status === 405) {
          throw new Error(`Endpoint non accessible (405). Vérifiez que le backend de production a bien l'endpoint /summarize_file_stream déployé et que la méthode POST est autorisée.`);
        }
        
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }
      
      // Mettre à jour le statut pendant l'attente de la réponse
      setCurrentStatus(t('status.ai.analyzing'));
      
      // Lire le stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = '';
      
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          // Décoder le chunk
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            // Traiter les lignes SSE (format: "data: {...}")
            if (line.startsWith('data: ')) {
              try {
                const jsonData = JSON.parse(line.slice(6));
                
                // Mettre à jour le statut si fourni par le backend
                if (jsonData.status) {
                  setCurrentStatus(jsonData.status);
                }
                
                if (jsonData.content) {
                  // Ajouter le contenu à la réponse accumulée
                  accumulatedResponse += jsonData.content;
                  
                  // Mettre à jour le statut si on commence à recevoir du contenu
                  if (accumulatedResponse.length > 0 && !jsonData.status) {
                    setCurrentStatus(t('status.generating.summary'));
                  }
                  
                  // Limiter à 4 lignes maximum
                  const lines = accumulatedResponse.split('\n').filter(l => l.trim());
                  const limitedResponse = lines.slice(0, 4).join('\n');
                  
                  // Mettre à jour l'interface en temps réel
                  setChatHistory((prev) => 
                    prev.map(msg => 
                      msg.id === messageId 
                        ? { ...msg, aiResponse: limitedResponse }
                        : msg
                    )
                  );
                }
                
                if (jsonData.done) {
                  console.log('✅ Résumé terminé');
                  setLoading(false);
                  setCurrentStatus('');
                }
                
                if (jsonData.error) {
                  console.error('❌ Erreur streaming:', jsonData.error);
                  setLoading(false);
                  throw new Error(jsonData.error);
                }
                
              } catch (e) {
                // Ignorer les erreurs de parsing pour les lignes vides
                if (line.trim() !== 'data: ') {
                  console.error('Erreur parsing SSE:', e);
                }
              }
            }
          }
        }
      }
      
      setLoading(false);
      setCurrentStatus('');
    } catch (error) {
      console.error('❌ Error generating file summary:', error);
      setCurrentStatus('');
      // Afficher un message d'erreur dans le chat si le résumé échoue
      setChatHistory((prev) => {
        const lastMessage = prev[prev.length - 1];
        if (lastMessage && lastMessage.userQuery === `📄 ${file.name}`) {
          return prev.map(msg => 
            msg.id === lastMessage.id 
              ? { ...msg, aiResponse: `⚠️ Impossible de générer le résumé automatique. Erreur: ${error instanceof Error ? error.message : 'Erreur inconnue'}` }
              : msg
          );
        }
        return prev;
      });
      setLoading(false);
    }
  }, [apiUrl, extractTextFromPdf, extractTextFromDocx, language]);

  // Fonction pour générer un résumé d'un fichier (ancienne version, gardée pour compatibilité)
  const generateFileSummary = useCallback(async (file: File, content: string | ArrayBuffer) => {
    await generateFileSummaryWithStreaming(file, content);
  }, [generateFileSummaryWithStreaming]);

  // Fonction pour générer un résumé de répertoire avec streaming
  const generateRepositorySummaryWithStreaming = useCallback(async (files: File[]) => {
    try {
      // Afficher le statut d'extraction
      const filePlural = files.length > 1 ? 's' : '';
      setCurrentStatus(t('status.extracting.content', { count: files.length, plural: filePlural }));
      
      // Créer un message dans le chat history pour le résumé
      const messageId = Math.random().toString(36).substr(2, 9);
      const repoMessage: ChatMessage = {
        id: messageId,
        userQuery: `📁 Répertoire (${files.length} fichier${files.length > 1 ? 's' : ''})`,
        aiResponse: ''
      };
      
      // Ajouter le message à l'historique
      setChatHistory((prev) => [...prev, repoMessage]);
      setLoading(true);
      
      // Mettre à jour le statut pour l'analyse
      const repoFilePlural = files.length > 1 ? 's' : '';
      setCurrentStatus(t('status.analyzing.repository', { count: files.length, plural: repoFilePlural }));
      
      // Utiliser le streaming pour le résumé du répertoire
      const response = await fetch(`${apiUrl}/summarize_repository_stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          files: files.slice(0, 20).map(file => ({
            name: file.name,
            // Extraire juste le nom du fichier sans le chemin
            display_name: file.name.split('/').pop() || file.name
          })),
          language: language
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unable to read error message');
        console.error('❌ Erreur résumé répertoire:', {
          status: response.status,
          statusText: response.statusText,
          error: errorText,
          url: `${apiUrl}/summarize_repository_stream`,
          method: 'POST'
        });
        
        // Si c'est une erreur 405, c'est probablement un problème de configuration serveur
        if (response.status === 405) {
          throw new Error(`Endpoint non accessible (405). Vérifiez que le backend de production a bien l'endpoint /summarize_repository_stream déployé et que la méthode POST est autorisée.`);
        }
        
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }
      
      // Lire le stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = '';
      
      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          // Décoder le chunk
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            // Traiter les lignes SSE (format: "data: {...}")
            if (line.startsWith('data: ')) {
              try {
                const jsonData = JSON.parse(line.slice(6));
                
                // Mettre à jour le statut si fourni par le backend
                if (jsonData.status) {
                  setCurrentStatus(jsonData.status);
                }
                
                if (jsonData.content) {
                  // Ajouter le contenu à la réponse accumulée
                  accumulatedResponse += jsonData.content;
                  
                  // Mettre à jour le statut si on commence à recevoir du contenu
                  if (accumulatedResponse.length > 0 && !jsonData.status) {
                    setCurrentStatus(t('status.generating.repo.summary'));
                  }
                  
                  // Mettre à jour l'interface en temps réel
                  setChatHistory((prev) => 
                    prev.map(msg => 
                      msg.id === messageId 
                        ? { ...msg, aiResponse: accumulatedResponse }
                        : msg
                    )
                  );
                }
                
                if (jsonData.done) {
                  console.log('✅ Résumé du répertoire terminé');
                  setLoading(false);
                  setCurrentStatus('');
                }
                
                if (jsonData.error) {
                  console.error('❌ Erreur streaming:', jsonData.error);
                  setLoading(false);
                  throw new Error(jsonData.error);
                }
                
              } catch (e) {
                // Ignorer les erreurs de parsing pour les lignes vides
                if (line.trim() !== 'data: ') {
                  console.error('Erreur parsing SSE:', e);
                }
              }
            }
          }
        }
      }
      
      setLoading(false);
      setCurrentStatus('');
    } catch (error) {
      console.error('❌ Error generating repository summary:', error);
      setCurrentStatus('');
      // Afficher un message d'erreur dans le chat si le résumé échoue
      setChatHistory((prev) => {
        const lastMessage = prev[prev.length - 1];
        if (lastMessage && lastMessage.userQuery.includes('Répertoire')) {
          return prev.map(msg => 
            msg.id === lastMessage.id 
              ? { ...msg, aiResponse: `⚠️ Impossible de générer le résumé automatique du répertoire. Erreur: ${error instanceof Error ? error.message : 'Erreur inconnue'}` }
              : msg
          );
        }
        return prev;
      });
      setLoading(false);
    }
  }, [apiUrl, language]);
  
  // Fonction pour régénérer les suggested actions pour un fichier spécifique
  const regenerateSuggestedActionsForFile = useCallback(async (file: File) => {
    try {
      const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      let fileContent: string;
      
      if (extension === '.pdf') {
        const arrayBuffer = await file.arrayBuffer();
        fileContent = await extractTextFromPdf(arrayBuffer);
      } else if (extension === '.docx') {
        const arrayBuffer = await file.arrayBuffer();
        fileContent = await extractTextFromDocx(arrayBuffer);
      } else {
        fileContent = await file.text();
      }
      
      const limitedContent = fileContent.substring(0, 2000);
      
      const response = await fetch(`${apiUrl}/infer-corpus-actions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          documents: [{
            file_name: file.name,
            content: limitedContent
          }],
          language: language
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.suggested_actions) {
          setSuggestedActions(result.suggested_actions);
        }
      }
    } catch (error) {
      console.error('Error regenerating suggested actions:', error);
    }
  }, [apiUrl, extractTextFromPdf, extractTextFromDocx, language]);
  
  // Fonction pour gérer l'import d'un répertoire
  const handleDirectorySelect = useCallback(async (files: File[]) => {
    // Bloquer l'import de répertoires pour les utilisateurs non connectés
    /*if (!isAuthenticated) {
      showLimitInfoBubble('Repository upload is only available for signed-in users. Please sign in to upload multiple files.');
      return;
    }*/
    
    // Ajouter tous les fichiers à directoryFiles
    setDirectoryFiles(prevFiles => {
      const newFiles: File[] = [];
      for (const file of files) {
        const fileExists = prevFiles.some(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified);
        if (!fileExists) {
          newFiles.push(file);
        }
      }
      // Ne retourner que si de nouveaux fichiers ont été ajoutés pour éviter les boucles
      if (newFiles.length === 0) {
        return prevFiles; // Pas de changement, retourner la même référence
      }
      return [...prevFiles, ...newFiles];
    });
    
    // Les fichiers sont déjà ajoutés à la sidebar dans handleFolderChange,
    // donc pas besoin de les ajouter à nouveau ici pour éviter les doublons
    
    // Marquer qu'un répertoire est sélectionné
    setSelectedDirectory(files);
    
    // Réinitialiser le fichier sélectionné pour afficher le message de sélection
    setSelectedFile(null);
    setFileDetails(null);
    
    // Générer automatiquement un résumé du répertoire avec streaming
    await generateRepositorySummaryWithStreaming(files);
  }, [generateRepositorySummaryWithStreaming, isAuthenticated, showLimitInfoBubble]);
  
  // Fonction pour générer des descriptions pour un répertoire (ancienne version, gardée pour compatibilité)
  const generateRepositorySummaries = useCallback(async (files: File[]) => {
    await generateRepositorySummaryWithStreaming(files);
  }, [generateRepositorySummaryWithStreaming]);

  // Fonction helper pour extraire tous les fichiers d'un répertoire
  const extractFilesFromDirectory = async (entry: FileSystemEntry | null, path: string = ''): Promise<File[]> => {
    const files: File[] = [];
    
    if (!entry) return files;
    
    if (entry.isFile) {
      const fileEntry = entry as FileSystemFileEntry;
      return new Promise((resolve) => {
        fileEntry.file((file: File) => {
          // Créer le chemin relatif complet
          const relativePath = path ? `${path}/${file.name}` : file.name;
          
          // Créer un nouveau File avec le chemin complet dans le nom
          const fileWithPath = new File([file], file.name, { type: file.type });
          
          // Ajouter webkitRelativePath pour que buildFileTree puisse l'utiliser
          (fileWithPath as any).webkitRelativePath = relativePath;
          
          resolve([fileWithPath]);
        });
      });
    } else if (entry.isDirectory) {
      const dirEntry = entry as FileSystemDirectoryEntry;
      const reader = dirEntry.createReader();
      const entries = await new Promise<FileSystemEntry[]>((resolve) => {
        reader.readEntries((entries) => resolve(Array.from(entries)));
      });
      
      for (const subEntry of entries) {
        const subPath = path ? `${path}/${subEntry.name}` : subEntry.name;
        const subFiles = await extractFilesFromDirectory(subEntry, subPath);
        files.push(...subFiles);
      }
    }
    
    return files;
  };

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    setIsProcessingDrop(true);
    setCurrentStatus(t('status.extracting.files'));
    
    try {
      const items = Array.from(e.dataTransfer.items);
      const allFiles: File[] = [];
      
      // Traiter chaque item (peut être un fichier ou un répertoire)
      for (const item of items) {
        const entry = item.webkitGetAsEntry();
        if (entry) {
          const files = await extractFilesFromDirectory(entry);
          allFiles.push(...files);
        }
      }
      
      // Si aucun fichier n'a été trouvé via webkitGetAsEntry, essayer avec files
      if (allFiles.length === 0) {
        const files = Array.from(e.dataTransfer.files);
        allFiles.push(...files);
      }
      
      if (allFiles.length === 0) {
        setIsProcessingDrop(false);
        setCurrentStatus('');
        return;
      }
      
      const allowedExtensions = [
        '.java', '.py', '.cs', '.js', '.ts', '.cpp', '.c', '.h',
        '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx',
        '.tsx', '.sql', '.docx', '.pdf', '.json', '.xml', '.md', '.txt'
      ];
      
      // Filtrer les fichiers supportés
      const supportedFiles = allFiles.filter(file => {
        const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        return allowedExtensions.includes(extension);
      });
      
      if (supportedFiles.length === 0) {
        alert('Aucun fichier supporté trouvé');
        setIsProcessingDrop(false);
        setCurrentStatus('');
        return;
      }
      
      // Vérifier les limitations pour les utilisateurs non connectés
      /*if (!isAuthenticated) {
        // Bloquer l'upload de répertoires pour les non connectés
        if (supportedFiles.length > 1) {
          showLimitInfoBubble('Repository upload is only available for signed-in users. Please sign in to upload multiple files.');
          setIsProcessingDrop(false);
          setCurrentStatus('');
          return;
        }
        
        // Vérifier la limite d'upload de fichiers
        if (!checkFileUploadLimit()) {
          showLimitInfoBubble('You have reached the limit of 1 file upload. Please sign in to upload more files.');
          setIsProcessingDrop(false);
          setCurrentStatus('');
          return;
        }
      }*/
      
      // Si c'est un seul fichier, traiter comme avant
      if (supportedFiles.length === 1) {
        const file = supportedFiles[0];
        const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        
        setCurrentStatus(t('status.processing.file', { fileName: file.name }));
        
        let content: string | ArrayBuffer;
        if (extension === '.pdf' || extension === '.docx') {
          content = await file.arrayBuffer();
        } else {
          content = await file.text();
        }
        
        // Réinitialiser isProcessingDrop avant d'appeler handleFileSelect
        // car handleFileSelect peut prendre du temps avec le streaming
        setIsProcessingDrop(false);
        
        // Incrémenter le compteur de fichiers uploadés pour les non connectés
        /*if (!isAuthenticated) {
          incrementUploadedFiles();
        }*/
        
        // handleFileSelect appellera automatiquement generateFileSummaryWithStreaming
        // Ne pas attendre pour éviter de bloquer si le streaming échoue
        handleFileSelect(file, { content, description: file.name }).catch(error => {
          console.error('Error in handleFileSelect:', error);
          setCurrentStatus('');
        });
      } else {
        // C'est un répertoire avec plusieurs fichiers
        // Réinitialiser isProcessingDrop avant d'appeler handleDirectorySelect
        setIsProcessingDrop(false);
        setCurrentStatus(t('status.processing.files', { count: supportedFiles.length }));
        
        // Gérer l'import du répertoire
        // Ne pas attendre pour éviter de bloquer si le streaming échoue
        handleDirectorySelect(supportedFiles).catch(error => {
          console.error('Error in handleDirectorySelect:', error);
          setCurrentStatus('');
        });
      }
    } catch (error) {
      console.error('Error handling drop:', error);
      alert('Erreur lors du traitement des fichiers: ' + (error instanceof Error ? error.message : 'Erreur inconnue'));
      setIsProcessingDrop(false);
      setCurrentStatus('');
    }
  }, [handleFileSelect, handleDirectorySelect, isAuthenticated, checkFileUploadLimit, incrementUploadedFiles, showLimitInfoBubble]);

  const detectLanguage = (text: string): string => {
    const langCode = franc(text);
    if(langCode === 'fra') return 'fr';
    if(langCode === 'eng') return 'en';
    if(langCode === 'spa') return 'es';
    return 'en';
  };

  const extractTextFromFile = async (file: File): Promise<string> => {
    const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    const arrayBufferOriginal = await file.arrayBuffer();
    const arrayBuffer = arrayBufferOriginal.slice(0);
    
    if (extension === '.docx') {
      return await extractTextFromDocx(arrayBuffer);
    } else if (extension === '.pdf') {
      return await extractTextFromPdf(arrayBuffer);
    } else if (['.txt', '.md', '.java', '.py', '.js', '.ts', '.cpp', '.c', '.h', '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx', '.tsx', '.sql'].includes(extension)) {
      return new TextDecoder().decode(new Uint8Array(arrayBuffer));
    } else {
      return 'Unsupported file type';
    }
  };

  // NOUVELLE FONCTION: Indexation côté backend
  const indexDirectoryContentOnBackend = async (files: File[]) => {
    try {
      console.log('=== ENVOI DES FICHIERS AU BACKEND POUR INDEXATION ===');
      console.log('Fichiers à indexer:', files.length);
      
      setIndexingStatus(t('status.indexing.extracting', { count: files.length }));
      
      // Extraire le contenu de tous les fichiers
      const fileContents: { fileName: string; content: string }[] = [];
      
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        console.log(`Traitement du fichier ${i + 1}/${files.length}: ${file.name}`);
        setIndexingStatus(t('status.indexing.processing', { fileName: file.name, current: i + 1, total: files.length }));
        
        const text = await extractTextFromFile(file);
        if (text && text !== 'Unsupported file type') {
          fileContents.push({
            fileName: file.name,
            content: text
          });
          console.log(`✅ Fichier traité: ${file.name} (${text.length} caractères)`);
        } else {
          console.log(`❌ Fichier ignoré: ${file.name} - type non supporté`);
        }
      }

      console.log(`📤 Envoi de ${fileContents.length} fichiers au backend...`);
      setIndexingStatus(t('status.indexing.on.server', { count: fileContents.length }));

      // Envoyer au backend pour indexation
      const response = await fetch(`${apiUrl}/index-directory`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Session-ID': sessionId
        },
        body: JSON.stringify({
          files: fileContents,
          language: language
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Échec de l\'indexation sur le serveur');
      }

      const data = await response.json();
      console.log('✅ Indexation terminée sur le backend:', data);
      
      setIsDirectoryIndexed(true);
      setIndexingStatus('');

      // Mettre à jour les actions suggérées renvoyées par le backend
      if (Array.isArray(data.suggested_actions)) {
        setSuggestedActions(data.suggested_actions);
      } else {
        setSuggestedActions([]);
      }
      
      console.log(`📚 ${data.indexed_files_count} fichiers indexés avec ${data.chunks_count} chunks`);
      
    } catch (error) {
      console.error("❌ Erreur lors de l'indexation côté backend:", error);
      setIsDirectoryIndexed(false);
      setIndexingStatus('');
      
      // Afficher une notification d'erreur à l'utilisateur
      //alert(`Erreur lors de l'indexation: ${error instanceof Error ? error.message : 'Erreur inconnue'}`);
    }
  };

  // NOUVEAU useEffect: Indexation automatique des fichiers du répertoire
  useEffect(() => {
    const loadDirectoryFiles = async () => {
      // Comparer les fichiers par nom, taille et lastModified pour détecter les vrais changements
      const currentFileKeys = directoryFiles.map(f => `${f.name}-${f.size}-${f.lastModified}`).sort();
      const lastFileKeys = lastIndexedFilesRef.current.map(f => `${f.name}-${f.size}-${f.lastModified}`).sort();
      const hasFilesChanged =
        directoryFiles.length !== lastIndexedFilesRef.current.length ||
        currentFileKeys.length !== lastFileKeys.length ||
        currentFileKeys.some((key, index) => key !== lastFileKeys[index]);

      console.log('=== VÉRIFICATION DES FICHIERS DU RÉPERTOIRE ===');
      console.log('Fichiers actuels:', directoryFiles.length);
      console.log('Derniers fichiers indexés:', lastIndexedFilesRef.current.length);
      console.log('Changements détectés:', hasFilesChanged);

      if (directoryFiles.length > 0 && hasFilesChanged) {
        console.log('🔄 Démarrage de l\'indexation backend...');
        await indexDirectoryContentOnBackend(directoryFiles);
        // Mettre à jour la référence avec une copie pour éviter les problèmes de référence
        lastIndexedFilesRef.current = [...directoryFiles];
      } else if (directoryFiles.length > 0 && !hasFilesChanged) {
        console.log('ℹ️ Fichiers déjà indexés, pas de changement');
        setIsDirectoryIndexed(true);
      } else if (directoryFiles.length === 0) {
        console.log('📂 Aucun fichier de répertoire à indexer');
        setIsDirectoryIndexed(false);
        lastIndexedFilesRef.current = [];
      }
    };

    loadDirectoryFiles();
  }, [directoryFiles, sessionId]);

  // Fonction principale de gestion des requêtes utilisateur
  const handleQuerySubmit = async (query: string, mode: 'online' | 'local') => {
    // Vérifier la limite de requêtes pour les utilisateurs non connectés
    /*if (!isAuthenticated && !checkQueryLimit()) {
      showLimitInfoBubble('You have reached the limit of 5 queries per day. Please sign in to continue using FlexiAnalyse.');
      return;
    }
    
    // Incrémenter le compteur de requêtes pour les non connectés
    if (!isAuthenticated) {
      incrementDailyQueries();
    }*/
    
    //setResearchMode(mode);
    
    // Ajouter la requête à l'historique de recherche
    if ((window as any).__addToSearchHistory) {
      (window as any).__addToSearchHistory(query);
    }
    
    // Utiliser la langue de l'interface pour les suggested actions, mais le modèle répondra dans la langue du prompt
    console.log(`Mode de recherche: ${mode}, Langue interface: ${language}`);
    
    const messageId = Math.random().toString(36).substr(2, 9);
    const newMessage: ChatMessage = { 
      id: messageId,
      userQuery: query, 
      aiResponse: '' 
    };
    setChatHistory((prev) => [...prev, newMessage]);
    setLoading(true);
    setCurrentStatus(mode === 'local' ? t('status.analyzing.question') : t('status.processing.request'));

    try {
      // Détermination automatique du mode si aucun fichier n'est sélectionné
      let effectiveMode = mode;
      if (!selectedFile && mode === 'local') {
        console.log('Aucun fichier sélectionné, basculement automatique vers le mode online');
        effectiveMode = 'online';
        //setResearchMode('online');
      }

      // Préparation des données selon le mode
      const effectiveModel =
        selectedModel === AUTO_MODEL_ID ? chooseModelForQuery(query) : selectedModel;

      // Construire un petit historique de conversation (les 6 derniers échanges)
      const conversationHistory = chatHistory.slice(-6).flatMap((msg) => [
        { role: 'user', content: msg.userQuery },
        { role: 'assistant', content: msg.aiResponse },
      ]);

      // Le modèle répondra dans la langue du prompt, pas besoin de passer la langue de l'interface
      let requestPayload: any = {
        user_query: query,
        selected_model: effectiveModel,
        research_mode: effectiveMode,
        conversation_history: conversationHistory,
      };

      if (effectiveMode === 'local') {
        // S'assurer que le vector store backend est prêt avant la première requête locale
        if (directoryFiles.length > 0 && !isDirectoryIndexed) {
          console.log('📚 Vector store non prêt, démarrage indexation avant la requête locale...');
          setIndexingStatus(t('status.indexing.documents'));
          try {
            await indexDirectoryContentOnBackend(directoryFiles);
            lastIndexedFilesRef.current = directoryFiles;
          } finally {
            setIndexingStatus('');
          }
        }

        // MODE LOCAL: Utilisation de l'indexation backend
        if (!selectedFile || !fileDetails) {
          throw new Error('Mode local nécessite un fichier sélectionné');
        }

        // Mettre à jour le statut pour l'analyse du fichier
        setCurrentStatus(t('status.analyzing.file', { fileName: selectedFile.name }));

        // Traitement du fichier actuel
        const extension = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
        const isBinary = ['.docx', '.pdf'].includes(extension);
        let currentFileContent: string;

        if (isBinary) {
          if (fileDetails.content instanceof ArrayBuffer) {
            const contentCopy = fileDetails.content.slice(0); 
            if (extension === '.docx') {
              currentFileContent = await extractTextFromDocx(contentCopy);
            } else if (extension === '.pdf') {
              currentFileContent = await extractTextFromPdf(contentCopy);
            } else {
              currentFileContent = 'Type de fichier binaire non supporté';
            }
          } else {
            currentFileContent = 'Erreur: Contenu binaire non disponible';
          }
        } else {
          currentFileContent = typeof fileDetails.content === 'string' ? fileDetails.content : '';
        }

        // Payload pour mode local avec indexation backend
        requestPayload = {
          ...requestPayload,
          file_name: selectedFile.name,
          file_content: currentFileContent,
          directory_content: [], // Vide: le backend gérera via son vector store
          repo_structure: repoStructure,
          is_binary: isBinary,
          disable_online_search: true,
          use_backend_vectorstore: isDirectoryIndexed, // Nouveau flag
        };

        console.log(`🚀 Envoi de la requête en mode local:`, {
          mode: effectiveMode,
          fileName: requestPayload.file_name,
          hasFileContent: !!requestPayload.file_content,
          useBackendVectorstore: requestPayload.use_backend_vectorstore,
          selectedModel: effectiveModel,
          directoryIndexed: isDirectoryIndexed,
        });

      } else {
        // MODE ONLINE: reste identique
        requestPayload = {
          ...requestPayload,
          file_name: null,
          file_content: null,
          directory_content: [],
          repo_structure: null,
          is_binary: false,
          enable_online_search: true,
        };
      }

      // Détecter si une recherche en ligne sera nécessaire
      const needsOnlineSearch = effectiveMode === 'online' || 
        (effectiveMode === 'local' && requestPayload.enable_auto_online_search !== false);
      
      // Démarrer l'indicateur de recherche après un court délai
      let searchTimeout: NodeJS.Timeout | null = null;
      if (needsOnlineSearch) {
        searchTimeout = setTimeout(() => {
          setIsSearchingOnline(true);
        }, 1500); // Afficher après 1.5 secondes si la recherche prend du temps
      }

      console.log(`📡 Envoi de la requête au backend...`, {
        effectiveModel,
        researchMode: effectiveMode,
      });

      // Mettre à jour le statut selon le mode
      if (effectiveMode === 'local') {
        setCurrentStatus(t('status.searching.documents'));
      } else {
        setCurrentStatus(t('status.searching.online'));
      }

      const response = await fetch(`${apiUrl}/query`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Session-ID': sessionId // Important: inclure l'ID de session
        },
        body: JSON.stringify(requestPayload),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        if (searchTimeout) clearTimeout(searchTimeout);
        setIsSearchingOnline(false);
        throw new Error(errorData.error || 'Échec du traitement de la requête');
      }

      const data = await response.json();
      
      // Arrêter l'indicateur de recherche
      if (searchTimeout) clearTimeout(searchTimeout);
      setIsSearchingOnline(false);
      setCurrentStatus(t('status.generating.response'));
      const aiResponse = data.response;

      console.log('📨 Réponse reçue du backend:', {
        mode: data.mode,
        contextInfo: data.context_info,
      });

      // Mise à jour de l'historique
      setChatHistory((prev) => {
        return prev.map(msg => 
          msg.id === messageId 
            ? { ...msg, aiResponse }
            : msg
        );
      });

      // Traitement des modifications de fichier (reste identique)
      if (effectiveMode === 'local' && selectedFile && !requestPayload.is_binary) {
        const modifiedContentMatch = aiResponse.match(/```modified-file-content\n([\s\S]*?)\n```/);
        let updatedContent: string | null = null;

        if (modifiedContentMatch && modifiedContentMatch[1]) {
          updatedContent = modifiedContentMatch[1].trim();
        } else {
          // Logique de détection alternative du contenu modifié
          const lines = aiResponse.split('\n');
          const currentFileContent = requestPayload.file_content;
          const originalLines = currentFileContent.split('\n').filter(line => line.trim());
          let potentialContent: string[] = [];
          let isCollecting = false;

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!isCollecting && (
              trimmedLine === currentFileContent.split('\n')[0]?.trim() || 
              trimmedLine.includes('def ') || 
              trimmedLine.includes('function ') || 
              trimmedLine.includes('class ')
            )) {
              isCollecting = true;
              potentialContent.push(line);
            } else if (isCollecting) {
              if (trimmedLine === '' && potentialContent.length > 0) {
                break;
              }
              potentialContent.push(line);
            }
          }

          if (potentialContent.length > 0 && potentialContent.length >= originalLines.length * 0.5) {
            updatedContent = potentialContent.join('\n').trim();
          }
        }

        if (updatedContent) {
          console.log('Mise à jour du contenu du fichier détectée');
          setFileDetails((prev) => prev ? { ...prev, content: updatedContent } : null);
        }
      }

    } catch (error) {
      console.error('Erreur lors de la soumission de la requête:', error);
      const errorMessage = error instanceof Error ? error.message : 'Erreur lors du traitement de votre requête.';
      
      setChatHistory((prev) => {
        return prev.map(msg => 
          msg.id === messageId 
            ? { ...msg, aiResponse: `Erreur: ${errorMessage}` }
            : msg
        );
      });
    } finally {
      setLoading(false);
      setCurrentStatus('');
    }
  };

  // Nouvelle fonction pour gérer les requêtes avec streaming
  const handleQuerySubmitWithStream = async (query: string, mode: 'online' | 'local') => {
    // Vérifier la limite de requêtes pour les utilisateurs non connectés
    /*if (!isAuthenticated && !checkQueryLimit()) {
      showLimitInfoBubble('You have reached the limit of 5 queries per day. Please sign in to continue using FlexiAnalyse.');
      return;
    }
    
    // Incrémenter le compteur de requêtes pour les non connectés
    if (!isAuthenticated) {
      incrementDailyQueries();
    }*/
    
    // Si mode local, utiliser l'ancienne méthode pour l'instant
    if (mode === 'local') {
      return handleQuerySubmit(query, mode);
    }

    const language = detectLanguage(query);
    const effectiveModel =
      selectedModel === AUTO_MODEL_ID ? chooseModelForQuery(query) : selectedModel;
    console.log(`🚀 Mode streaming activé - Mode: ${mode}, Langue: ${language}`);
    
    const messageId = Math.random().toString(36).substr(2, 9);
    const newMessage: ChatMessage = { 
      id: messageId,
      userQuery: query, 
      aiResponse: '' 
    };
    
    // Ajouter le message à l'historique
    setChatHistory((prev) => [...prev, newMessage]);
    setLoading(true);
    setCurrentStatus(mode === 'local' ? t('status.analyzing.question') : t('status.processing.request'));

    try {
      // Mettre à jour le statut selon le mode
      if (mode === 'local' && selectedFile) {
        setCurrentStatus(t('status.analyzing.file', { fileName: selectedFile.name }));
      } else {
        setCurrentStatus(t('status.searching.online'));
      }

      const response = await fetch(`${apiUrl}/query-stream`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Session-ID': sessionId
        },
        body: JSON.stringify({
          user_query: query,
          selected_model: effectiveModel,
          language: language,
          research_mode: mode,
          // on peut aussi donner un peu de contexte pour améliorer la cohérence
          conversation_history: chatHistory.slice(-6).flatMap((msg) => [
            { role: 'user', content: msg.userQuery },
            { role: 'assistant', content: msg.aiResponse },
          ]),
          enable_online_search: mode === 'online'
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Lire le stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedResponse = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          // Décoder le chunk
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');
          
          for (const line of lines) {
            // Traiter les lignes SSE (format: "data: {...}")
            if (line.startsWith('data: ')) {
              try {
                const jsonData = JSON.parse(line.slice(6));
                
                // Mettre à jour le statut si fourni par le backend
                if (jsonData.status) {
                  setCurrentStatus(jsonData.status);
                }
                
                if (jsonData.content) {
                  // Ajouter le contenu à la réponse accumulée
                  accumulatedResponse += jsonData.content;
                  
                  // Mettre à jour le statut si on commence à recevoir du contenu
                  if (accumulatedResponse.length > 0 && !jsonData.status) {
                    setCurrentStatus(t('status.generating.response'));
                  }
                  
                  // Mettre à jour l'interface en temps réel
                  setChatHistory((prev) => 
                    prev.map(msg => 
                      msg.id === messageId 
                        ? { ...msg, aiResponse: accumulatedResponse }
                        : msg
                    )
                  );
                }
                
                if (jsonData.done) {
                  console.log('✅ Streaming terminé');
                }
                
                if (jsonData.error) {
                  console.error('❌ Erreur streaming:', jsonData.error);
                  throw new Error(jsonData.error);
                }
                
              } catch (e) {
                // Ignorer les erreurs de parsing pour les lignes vides
                if (line.trim() !== 'data: ') {
                  console.error('Erreur parsing SSE:', e);
                }
              }
            }
          }
        }
      }

    } catch (error) {
      console.error('Erreur lors du streaming:', error);
      const errorMessage = error instanceof Error ? error.message : 'Erreur lors du traitement de votre requête.';
      
      setChatHistory((prev) => {
        return prev.map(msg => 
          msg.id === messageId 
            ? { ...msg, aiResponse: `Erreur: ${errorMessage}` }
            : msg
        );
      });
    } finally {
      setLoading(false);
      setCurrentStatus('');
    }
  };


  const getRepoStructure = useCallback((structureFn: () => string, files: File[]) => {
    const structure = structureFn();
    setRepoStructure(structure);
    // Ne pas modifier directoryFiles ici pour éviter les boucles infinies
    // directoryFiles est déjà géré par handleDirectorySelect et handleFileSelect
  }, []);

  // Fonction pour extraire les données structurées
  const handleExtractStructured = useCallback(async () => {
    if (!selectedFile || !fileDetails) {
      console.error('Aucun fichier sélectionné pour l\'extraction');
      return;
    }

    // Vérifier d'abord si l'endpoint est accessible
    try {
      const healthCheck = await fetch(`${apiUrl}/test-endpoints`);
      if (healthCheck.ok) {
        const healthData = await healthCheck.json();
        console.log('📊 Endpoints disponibles:', healthData);
        if (healthData.endpoints && healthData.endpoints['/extract-structured'] && !healthData.endpoints['/extract-structured'].exists) {
          alert(`⚠️ L'endpoint /extract-structured n'est pas disponible sur le serveur de production.\n\nVérifiez que le backend a bien été déployé avec tous les endpoints nécessaires.`);
          return;
        }
      }
    } catch (healthError) {
      console.warn('⚠️ Impossible de vérifier les endpoints:', healthError);
    }

    setExtracting(true);
    try {
      // Extraire le texte du fichier
      const fileContent = typeof fileDetails.content === 'string' 
        ? fileDetails.content 
        : await extractTextFromFile(selectedFile);

      // Déterminer le modèle à utiliser
      const effectiveModel = selectedModel === AUTO_MODEL_ID 
        ? chooseModelForQuery('extract structured data') 
        : selectedModel;

      // Appeler l'endpoint d'extraction
      const response = await fetch(`${apiUrl}/extract-structured`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_name: selectedFile.name,
          file_content: fileContent,
          selected_model: effectiveModel,
          language: language
        })
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unable to read error message');
        console.error('❌ Erreur extraction structurée:', {
          status: response.status,
          statusText: response.statusText,
          error: errorText,
          url: `${apiUrl}/extract-structured`,
          method: 'POST'
        });
        
        // Si c'est une erreur 405, c'est probablement un problème de configuration serveur
        if (response.status === 405) {
          throw new Error(`Endpoint non accessible (405). Vérifiez que le backend de production a bien l'endpoint /extract-structured déployé et que la méthode POST est autorisée.`);
        }
        
        throw new Error(`Erreur HTTP: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      
      if (result.success && result.data) {
        setStructuredData(result.data);
        setShowStructuredData(true);
      } else {
        console.error('Erreur lors de l\'extraction:', result.error);
        alert('Erreur lors de l\'extraction des données structurées: ' + (result.error || 'Erreur inconnue'));
      }
    } catch (error) {
      console.error('Erreur lors de l\'extraction structurée:', error);
      alert('Erreur lors de l\'extraction: ' + (error instanceof Error ? error.message : 'Erreur inconnue'));
    } finally {
      setExtracting(false);
    }
  }, [selectedFile, fileDetails, selectedModel, apiUrl]);

  const handleSuggestedActionClick = useCallback(
    (action: SuggestedAction) => {
      // Détecter si c'est une action d'extraction structurée
      const isExtractionAction = action.id.includes('extract') || 
                                 action.id.includes('structured') ||
                                 action.title.toLowerCase().includes('extraire') ||
                                 action.title.toLowerCase().includes('extract');
      
      if (isExtractionAction && selectedFile) {
        // Appeler l'extraction structurée
        handleExtractStructured();
      } else {
        // Comportement normal : envoyer le prompt
        const defaultMode: 'online' | 'local' = selectedFile ? 'local' : 'online';
        handleQuerySubmitWithStream(action.sample_prompt, defaultMode);
      }
    },
    [selectedFile, handleQuerySubmitWithStream, handleExtractStructured]
  );

  // Fonction pour obtenir les fichiers éditables
  const getEditableFiles = useCallback(async () => {
    const codeExtensions = [
      '.java', '.py', '.cs', '.js', '.ts', '.cpp', '.c', '.h',
      '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx',
      '.tsx', '.sql', '.json', '.xml', '.md', '.txt'
    ];
    
    const editableFiles: Array<{ file: File; content: string | ArrayBuffer; type: 'code' | 'docx' }> = [];
    
    // Ajouter le fichier sélectionné s'il est éditable
    if (selectedFile && fileDetails) {
      const extension = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase();
      if (codeExtensions.includes(extension) && typeof fileDetails.content === 'string') {
        editableFiles.push({
          file: selectedFile,
          content: fileDetails.content,
          type: 'code'
        });
      } else if (extension === '.docx' && fileDetails.content instanceof ArrayBuffer) {
        editableFiles.push({
          file: selectedFile,
          content: fileDetails.content,
          type: 'docx'
        });
      }
    }
    
    // Charger le contenu des fichiers du répertoire qui sont éditables
    for (const file of directoryFiles) {
      const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      
      // Vérifier si le fichier n'est pas déjà dans la liste
      if (!editableFiles.some(ef => ef.file.name === file.name)) {
        if (codeExtensions.includes(extension)) {
          // Fichier code : charger le contenu texte
          try {
            const arrayBuffer = await file.arrayBuffer();
            const content = new TextDecoder().decode(new Uint8Array(arrayBuffer));
            editableFiles.push({
              file: file,
              content: content,
              type: 'code'
            });
          } catch (err) {
            console.error(`Erreur lors du chargement de ${file.name}:`, err);
          }
        } else if (extension === '.docx') {
          // Fichier DOCX : charger l'ArrayBuffer
          try {
            const arrayBuffer = await file.arrayBuffer();
            editableFiles.push({
              file: file,
              content: arrayBuffer,
              type: 'docx'
            });
          } catch (err) {
            console.error(`Erreur lors du chargement de ${file.name}:`, err);
          }
        }
      }
    }
    
    return editableFiles;
  }, [selectedFile, fileDetails, directoryFiles]);

  // Fonction pour gérer la sélection de texte
  const handleTextSelect = useCallback(async (text: string) => {
    console.log('handleTextSelect called with text:', text.substring(0, 50));
    const editableFiles = await getEditableFiles();
    console.log('Editable files found:', editableFiles.length);
    if (editableFiles.length === 0) {
      alert('Aucun fichier éditable disponible. Veuillez d\'abord sélectionner un fichier code ou DOCX dans la sidebar.');
      return;
    }
    setSelectedTextToInsert(text);
    setShowInsertModal(true);
  }, [getEditableFiles]);

  // Fonction pour insérer du texte dans un fichier
  const handleInsertText = useCallback(async (file: File, text: string, lineNumber?: number) => {
    console.log('handleInsertText called:', { fileName: file.name, textLength: text.length, lineNumber });
    
    // Trouver le fichier dans les fichiers éditables
    const editableFiles = await getEditableFiles();
    const fileData = editableFiles.find(ef => ef.file.name === file.name);
    
    if (!fileData) {
      alert('Fichier non trouvé dans les fichiers éditables');
      return;
    }

    const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    const codeExtensions = [
      '.java', '.py', '.cs', '.js', '.ts', '.cpp', '.c', '.h',
      '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx',
      '.tsx', '.sql', '.json', '.xml', '.md', '.txt'
    ];

    if (codeExtensions.includes(extension) && typeof fileData.content === 'string') {
      const lines = fileData.content.split('\n');
      
      if (lineNumber !== undefined && lineNumber > 0) {
        // Mode manuel : insérer à la ligne spécifiée
        if (lineNumber <= lines.length) {
          lines.splice(lineNumber - 1, 0, text);
        } else {
          // Si le numéro de ligne est au-delà de la fin, ajouter des lignes vides puis le texte
          while (lines.length < lineNumber - 1) {
            lines.push('');
          }
          lines.push(text);
        }
      } else {
        // Mode auto : ajouter à la fin
        lines.push(text);
      }
      
      const newContent = lines.join('\n');
      
      // Si c'est le fichier sélectionné, mettre à jour fileDetails
      if (selectedFile && selectedFile.name === file.name && fileDetails) {
        setFileDetails({
          ...fileDetails,
          content: newContent
        });
      } else {
        // Sinon, sélectionner ce fichier et mettre à jour
        setSelectedFile(file);
        setFileDetails({
          content: newContent,
          description: file.name
        });
        setIsFileContentVisible(true);
      }
      
      console.log('Texte inséré avec succès');
    } else if (extension === '.docx' && fileData.content instanceof ArrayBuffer) {
      // Pour DOCX, on convertit en HTML, ajoute le texte, puis reconvertit en DOCX
      mammoth.convertToHtml({ arrayBuffer: fileData.content })
        .then(async (result) => {
          let htmlContent = result.value;
          
          // Ajouter le texte au HTML
          if (lineNumber !== undefined && lineNumber > 0) {
            // Mode manuel : insérer à une position approximative
            const htmlLines = htmlContent.split('</p>');
            if (lineNumber <= htmlLines.length) {
              const insertIndex = lineNumber - 1;
              htmlLines[insertIndex] = htmlLines[insertIndex] + `<p>${text}</p>`;
              htmlContent = htmlLines.join('</p>');
            } else {
              htmlContent = htmlContent + `<p>${text}</p>`;
            }
          } else {
            // Mode auto : ajouter à la fin
            htmlContent = htmlContent + `<p>${text}</p>`;
          }
          
          // Convertir le HTML en paragraphes DOCX
          const { Document, Paragraph, TextRun, Packer } = await import('docx');
          const { saveAs } = await import('file-saver');
          
          // Parser le HTML en paragraphes
          const tempDiv = document.createElement('div');
          tempDiv.innerHTML = htmlContent;
          const paragraphs: any[] = [];
          
          tempDiv.querySelectorAll('p').forEach((p) => {
            const text = p.textContent || '';
            if (text.trim()) {
              paragraphs.push(new Paragraph({ children: [new TextRun(text)] }));
            }
          });
          
          // Si aucun paragraphe, créer un paragraphe vide
          if (paragraphs.length === 0) {
            paragraphs.push(new Paragraph({ children: [new TextRun('')] }));
          }
          
          // Créer le document DOCX
          const doc = new Document({
            sections: [{
              properties: {},
              children: paragraphs,
            }],
          });
          
          // Convertir en blob et mettre à jour fileDetails
          const blob = await Packer.toBlob(doc);
          const arrayBuffer = await blob.arrayBuffer();
          
          // Mettre à jour fileDetails avec le nouveau contenu
          if (selectedFile && selectedFile.name === file.name && fileDetails) {
            setFileDetails({
              ...fileDetails,
              content: arrayBuffer
            });
          } else {
            setSelectedFile(file);
            setFileDetails({
              content: arrayBuffer,
              description: file.name
            });
            setIsFileContentVisible(true);
          }
          
          console.log('Texte inséré dans DOCX avec succès');
        })
        .catch((err) => {
          console.error('Erreur lors de l\'insertion dans DOCX:', err);
          alert('Erreur lors de l\'insertion dans le fichier DOCX: ' + err.message);
        });
    } else {
      alert('Type de fichier non supporté pour l\'insertion');
    }
  }, [selectedFile, fileDetails, getEditableFiles, setIsFileContentVisible]);

  return (
    <div className={`flex min-h-screen w-full relative overflow-x-hidden theme-${theme}`}>
      {/* Infobulle de limitation pour les utilisateurs non connectés */}
      {showLimitInfo && (
        <div className="fixed top-4 right-4 z-50 bg-yellow-500 text-white px-6 py-4 rounded-lg shadow-xl max-w-md animate-slide-in-right">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <h3 className="font-semibold text-lg">Limit Reached</h3>
              </div>
              <p className="text-sm">{limitMessage}</p>
            </div>
            <button
              onClick={() => setShowLimitInfo(false)}
              className="text-white hover:text-gray-200 transition-colors"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      )}
      
      {/* Sidebar Container - reste identique */}
      <div className="flex">
        <div className={`hidden lg:block bg-gray-200 transition-all duration-300 fixed top-0 left-0 h-full ${
          isSidebarOpen ? 'w-64 overflow-y-auto' : 'w-20 overflow-visible'
        } z-40`}>
          <Sidebar
            onFileSelect={handleFileSelect}
            getRepoStructure={getRepoStructure}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
            isSidebarOpen={isSidebarOpen}
            toggleSidebar={toggleSidebar}
            addFileToSidebar={addFileToSidebar}
            onDirectorySelect={handleDirectorySelect}
          />
        </div>

        <div className="lg:hidden">
          <button
            onClick={toggleSidebar}
            className="fixed top-4 left-4 z-50 bg-white shadow-lg rounded-md p-2 text-gray-700 hover:text-blue-500 transition-colors"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>

          {isSidebarOpen && (
            <>
              <div
                className="fixed inset-0 bg-black bg-opacity-50 z-30"
                onClick={toggleSidebar}
              />
              <div className="fixed inset-y-0 left-0 z-40 w-64 bg-gray-200 shadow-lg">
                <Sidebar
                  onFileSelect={handleFileSelect}
                  getRepoStructure={getRepoStructure}
                  selectedModel={selectedModel}
                  setSelectedModel={setSelectedModel}
                  isSidebarOpen={isSidebarOpen}
                  toggleSidebar={toggleSidebar}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Indicateur de statut d'indexation 
        {indexingStatus && (
          <div className="fixed top-4 right-4 z-50 bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg">
            {indexingStatus}
          </div>
        )}
      */}
      
      {/* Main Content - Layout 3 colonnes */}
      <div
        className={`flex-1 flex transition-all duration-300 ${
          isSidebarOpen ? 'lg:ml-64' : 'lg:ml-20'
        } relative z-30 h-screen overflow-hidden`}
      >
        {/* Colonne centrale - FileViewer */}
        <div className="w-2/5 flex-shrink-0 border-r border-gray-200 overflow-hidden mr-2 h-full flex flex-col">
          <FileViewer
            file={selectedFile}
            fileDetails={fileDetails}
            onFileSelect={handleFileSelect}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
            isProcessingDrop={isProcessingDrop}
          />
        </div>

        {/* Colonne droite - ChatPanel */}
        <div className="flex-1 w-3/5 flex-shrink-0 overflow-hidden ml-2">
          <ChatPanel
            chatHistory={chatHistory}
            loading={loading || isProcessingDrop}
            onQuerySubmit={handleQuerySubmitWithStream}
            selectedModel={selectedModel}
            researchMode={researchMode}
            setResearchMode={setResearchMode}
            suggestedActions={suggestedActions}
            onSuggestedActionClick={handleSuggestedActionClick}
            getEditableFiles={getEditableFiles}
            isProcessingDrop={isProcessingDrop}
            onTextSelect={handleTextSelect}
            isSearchingOnline={isSearchingOnline}
            currentStatus={currentStatus}
            isFileContentVisible={isFileContentVisible}
            setIsFileContentVisible={setIsFileContentVisible}
          />
        </div>
      </div>

      {/* Modal d'affichage des données structurées */}
      {showStructuredData && structuredData && (
        <StructuredDataDisplay
          data={structuredData}
          onClose={() => {
            setShowStructuredData(false);
            setStructuredData(null);
          }}
        />
      )}

      {/* Modal d'insertion de texte */}
      {showInsertModal && selectedTextToInsert && (
        <InsertTextModal
          selectedText={selectedTextToInsert}
          editableFiles={[]} // Sera chargé de manière asynchrone dans le modal
          getEditableFiles={getEditableFiles}
          onInsert={handleInsertText}
          onClose={() => {
            setShowInsertModal(false);
            setSelectedTextToInsert('');
          }}
        />
      )}

      {/* Indicateur de chargement pour l'extraction */}
      {extracting && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-6 shadow-xl">
            <div className="flex items-center space-x-3">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <span className="text-gray-700 font-medium">{t('status.extracting.structured')}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FlexiAnalyseApp;