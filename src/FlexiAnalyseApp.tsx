// App.tsx - Modifications nécessaires

import React, { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "./components/main/Sidebar";
import MainContent from "./components/main/MainContent";
import FileSelectedComponent from "./components/main/FileSelectedComponent";
import StructuredDataDisplay from "./components/main/StructuredDataDisplay";
import InsertTextModal from "./components/main/InsertTextModal";
import mammoth from 'mammoth';
import * as pdfjslib from 'pdfjs-dist/legacy/build/pdf';
import pdfWorker from 'pdfjs-dist/legacy/build/pdf.worker?url';
import { franc } from 'franc-min';
import { useAuth } from './components/auth/AuthProvider';

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
  const { user, logout } = useAuth();

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

  // Ref pour tracker les derniers fichiers indexés
  const lastIndexedFilesRef = useRef<File[]>([]);

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

  const handleFileSelect = (file: File, details: FileDetails) => {
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
  };

  const apiUrl = 'http://127.0.0.1:5000'; // 'http://127.0.0.1:5000' 'https://flexianalyse.com';

  // Fonctions d'extraction de texte (restent identiques)
  const extractTextFromDocx = async (content: ArrayBuffer): Promise<string> => {
    try {
      const result = await mammoth.extractRawText({ arrayBuffer: content });
      return result.value;
    } catch (error) {
      console.error('Error extracting text from .docx:', error);
      return 'Error extracting text from .docx';
    }
  };

  const detectLanguage = (text: string): string => {
    const langCode = franc(text);
    if(langCode === 'fra') return 'fr';
    if(langCode === 'eng') return 'en';
    if(langCode === 'spa') return 'es';
    return 'en';
  };

  const extractTextFromPdf = async (arrayBuffer: ArrayBuffer): Promise<string> => {
    try {
      const bufferCopy = arrayBuffer.slice(0);
      const pdf = await pdfjslib.getDocument({ data: bufferCopy }).promise;

      let text = '';
      for (let i = 1; i <= pdf.numPages; i++) {
        const page = await pdf.getPage(i);
        const content = await page.getTextContent();
        const strings = content.items.map(item => (item as any).str).join(' ');
        text += strings + '\n';
      }

      return text;
    } catch (error) {
      console.error('Error extracting text from PDF:', error);
      return 'Error extracting text from PDF';
    }
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
      
      setIndexingStatus(`Extraction du contenu de ${files.length} fichiers...`);
      
      // Extraire le contenu de tous les fichiers
      const fileContents: { fileName: string; content: string }[] = [];
      
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        console.log(`Traitement du fichier ${i + 1}/${files.length}: ${file.name}`);
        setIndexingStatus(`Traitement de ${file.name} (${i + 1}/${files.length})...`);
        
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
      setIndexingStatus(`Indexation sur le serveur (${fileContents.length} fichiers)...`);

      // Envoyer au backend pour indexation
      const response = await fetch(`${apiUrl}/index-directory`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Session-ID': sessionId
        },
        body: JSON.stringify({
          files: fileContents
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
      const currentFileNames = directoryFiles.map(file => file.name).sort();
      const lastFileNames = lastIndexedFilesRef.current.map(file => file.name).sort();
      const hasFilesChanged =
        directoryFiles.length !== lastIndexedFilesRef.current.length ||
        currentFileNames.some((name, index) => name !== lastFileNames[index]);

      console.log('=== VÉRIFICATION DES FICHIERS DU RÉPERTOIRE ===');
      console.log('Fichiers actuels:', directoryFiles.length);
      console.log('Derniers fichiers indexés:', lastIndexedFilesRef.current.length);
      console.log('Changements détectés:', hasFilesChanged);

      if (directoryFiles.length > 0 && hasFilesChanged) {
        console.log('🔄 Démarrage de l\'indexation backend...');
        await indexDirectoryContentOnBackend(directoryFiles);
        lastIndexedFilesRef.current = directoryFiles;
      } else if (directoryFiles.length > 0) {
        console.log('ℹ️ Fichiers déjà indexés, pas de changement');
        setIsDirectoryIndexed(true);
      } else {
        console.log('📂 Aucun fichier de répertoire à indexer');
        setIsDirectoryIndexed(false);
      }
    };

    loadDirectoryFiles();
  }, [directoryFiles, sessionId]);

  // Fonction principale de gestion des requêtes utilisateur
  const handleQuerySubmit = async (query: string, mode: 'online' | 'local') => {
    //setResearchMode(mode);
    
    const language = detectLanguage(query);
    console.log(`Mode de recherche: ${mode}, Langue détectée: ${language}`);
    
    const messageId = Math.random().toString(36).substr(2, 9);
    const newMessage: ChatMessage = { 
      id: messageId,
      userQuery: query, 
      aiResponse: '' 
    };
    setChatHistory((prev) => [...prev, newMessage]);
    setLoading(true);

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

      let requestPayload: any = {
        user_query: query,
        selected_model: effectiveModel,
        language: language,
        research_mode: effectiveMode,
        conversation_history: conversationHistory,
      };

      if (effectiveMode === 'local') {
        // S'assurer que le vector store backend est prêt avant la première requête locale
        if (directoryFiles.length > 0 && !isDirectoryIndexed) {
          console.log('📚 Vector store non prêt, démarrage indexation avant la requête locale...');
          setIndexingStatus('Indexation des documents en cours...');
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
    }
  };

  // Nouvelle fonction pour gérer les requêtes avec streaming
  const handleQuerySubmitWithStream = async (query: string, mode: 'online' | 'local') => {
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

    try {
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
                
                if (jsonData.content) {
                  // Ajouter le contenu à la réponse accumulée
                  accumulatedResponse += jsonData.content;
                  
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
    }
  };


  const getRepoStructure = useCallback((structureFn: () => string, files: File[]) => {
    const structure = structureFn();
    setRepoStructure(structure);
    setDirectoryFiles(files);
  }, []);

  // Fonction pour extraire les données structurées
  const handleExtractStructured = useCallback(async () => {
    if (!selectedFile || !fileDetails) {
      console.error('Aucun fichier sélectionné pour l\'extraction');
      return;
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
          language: 'fr'
        })
      });

      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
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
    <div className="flex min-h-screen w-full relative overflow-x-hidden">
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
      
      {/* Main Content */}
      <div
        className={`flex-1 flex flex-col transition-all duration-300 ${
          isSidebarOpen ? 'lg:ml-64' : 'lg:ml-20'
        } relative z-30 overflow-y-auto`}
        style={{ height: '100vh', overflowY: 'auto' }}
      >
        {selectedFile && fileDetails ? (
          <FileSelectedComponent
            file={selectedFile}
            details={fileDetails}
            isFileContentVisible={isFileContentVisible}
            setIsFileContentVisible={setIsFileContentVisible}
            chatHistory={chatHistory}
            setFileDetails={setFileDetails}
            onQuerySubmit={handleQuerySubmitWithStream}
            loading={loading}
            selectedModel={selectedModel}
            researchMode={researchMode}
            setResearchMode={setResearchMode}
            suggestedActions={suggestedActions}
            onSuggestedActionClick={handleSuggestedActionClick}
            getEditableFiles={getEditableFiles}
            onTextSelect={handleTextSelect}
            isSearchingOnline={isSearchingOnline}
          />
        ) : (
          <MainContent 
            responses={responses}
            selectedModel={selectedModel}
            isFileContentVisible={isFileContentVisible}
            setIsFileContentVisible={setIsFileContentVisible}
            onQuerySubmit={handleQuerySubmitWithStream}
            loading={loading}
            researchMode={researchMode}
            setResearchMode={setResearchMode}
            chatHistory={chatHistory}
            suggestedActions={suggestedActions}
            onSuggestedActionClick={handleSuggestedActionClick}
            getEditableFiles={getEditableFiles}
            onTextSelect={handleTextSelect}
          />
        )}
        <footer className="w-full p-4 text-center text-gray-500 text-sm">
          Pro • Enterprise • API • Blog • Careers • Store • Finance • English
        </footer>
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
              <span className="text-gray-700 font-medium">Extraction des données structurées en cours...</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FlexiAnalyseApp;