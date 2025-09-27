// App.tsx - Modifications nécessaires

import React, { useState, useEffect, useCallback, useRef } from "react";
import Sidebar from "./components/main/Sidebar";
import MainContent from "./components/main/MainContent";
import FileSelectedComponent from "./components/main/FileSelectedComponent";
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

pdfjslib.GlobalWorkerOptions.workerSrc = pdfWorker;

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
  const [selectedModel, setSelectedModel] = useState<string>('mistral');
  const [researchMode, setResearchMode] = useState<'online' | 'local'>('online');
  const [isMobile, setIsMobile] = useState(false);
  
  // NOUVEAU: États pour gérer l'indexation backend
  const [isDirectoryIndexed, setIsDirectoryIndexed] = useState<boolean>(false);
  const [indexingStatus, setIndexingStatus] = useState<string>('');
  const [sessionId] = useState(() => Math.random().toString(36).substr(2, 9));

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
  };

  const apiUrl = 'https://flexianalyse.com'; // 'http://127.0.0.1:5000' 'https://flexianalyse.com';

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
      let requestPayload: any = {
        user_query: query,
        selected_model: selectedModel,
        language: language,
        research_mode: effectiveMode,
      };

      if (effectiveMode === 'local') {
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

      console.log(`📡 Envoi de la requête au backend...`);

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
        throw new Error(errorData.error || 'Échec du traitement de la requête');
      }

      const data = await response.json();
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

  const getRepoStructure = useCallback((structureFn: () => string, files: File[]) => {
    const structure = structureFn();
    setRepoStructure(structure);
    setDirectoryFiles(files);
  }, []);

  return (
    <div className="flex min-h-screen w-screen relative">
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
        } relative z-30`}
      >
        {selectedFile && fileDetails ? (
          <FileSelectedComponent
            file={selectedFile}
            details={fileDetails}
            isFileContentVisible={isFileContentVisible}
            setIsFileContentVisible={setIsFileContentVisible}
            chatHistory={chatHistory}
            setFileDetails={setFileDetails}
            onQuerySubmit={handleQuerySubmit}
            loading={loading}
            selectedModel={selectedModel}
            researchMode={researchMode}
            setResearchMode={setResearchMode}
          />
        ) : (
          <MainContent 
            responses={responses}
            selectedModel={selectedModel}
            isFileContentVisible={isFileContentVisible}
            setIsFileContentVisible={setIsFileContentVisible}
            onQuerySubmit={handleQuerySubmit}
            loading={loading}
            researchMode={researchMode}
            setResearchMode={setResearchMode}
            chatHistory={chatHistory}
          />
        )}
        <footer className="w-full p-4 text-center text-gray-500 text-sm">
          Pro • Enterprise • API • Blog • Careers • Store • Finance • English
        </footer>
      </div>
    </div>
  );
};

export default FlexiAnalyseApp;