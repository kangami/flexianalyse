import React, { useState, useRef, ChangeEvent, useEffect, useMemo, useCallback } from 'react';
import { FolderOpen, Folder, ChevronRight, Search, User, FileText } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../auth/AuthProvider';
import LoginModal from '../auth/LoginModal';
import SignUpModal from '../auth/SignUpModal';

interface FileDescription {
  file_name: string;
  description: string;
  model_used?: string;
}

interface FileNode {
  name: string;
  children?: FileNode[];
  file?: File;
  isOpen?: boolean;
}

interface FileDetails {
  content: string | ArrayBuffer;
  description: string;
}

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  description?: string;
  cost_tier?: string;
  is_default?: boolean;
}

interface SidebarProps {
  onFileSelect: (file: File, details: FileDetails) => void;
  getRepoStructure: (structureFn: () => string, files: File[]) => void;
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  addFileToSidebar?: (file: File) => void;
  onDirectorySelect?: (files: File[]) => void;
}

// Cache configuration
const CACHE_CONFIG = {
  MODELS_KEY: 'ai_models_cache',
  MODEL_STATUS_KEY: 'model_status_cache',
  DURATION: 30 * 60 * 1000, // 30 minutes
};

// Utility functions for caching
const cacheUtils = {
  set: (key: string, data: any) => {
    try {
      const cacheData = {
        data,
        timestamp: Date.now(),
        expiry: Date.now() + CACHE_CONFIG.DURATION
      };
      localStorage.setItem(key, JSON.stringify(cacheData));
    } catch (error) {
      console.warn('Cache set failed:', error);
    }
  },
  
  get: (key: string) => {
    try {
      const cached = localStorage.getItem(key);
      if (!cached) return null;
      
      const cacheData = JSON.parse(cached);
      if (Date.now() > cacheData.expiry) {
        localStorage.removeItem(key);
        return null;
      }
      
      return cacheData.data;
    } catch (error) {
      console.warn('Cache get failed:', error);
      return null;
    }
  },
  
  clear: (key: string) => {
    try {
      localStorage.removeItem(key);
    } catch (error) {
      console.warn('Cache clear failed:', error);
    }
  }
};

// Debounce utility
const debounce = (func: Function, delay: number) => {
  let timeoutId: NodeJS.Timeout;
  return (...args: any[]) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(null, args), delay);
  };
};

// API service for backend communication
class AIBackendService {
  private baseURL: string;
  private uploadQueue: Set<string> = new Set();

  constructor(baseURL = 'http://127.0.0.1:5000') {
    this.baseURL = baseURL;
  }

  async getAvailableModels(): Promise<{ models: ModelInfo[]; default_model: string }> {
    // Check cache first
    const cached = cacheUtils.get(CACHE_CONFIG.MODELS_KEY);
    if (cached) {
      return cached;
    }

    try {
      const response = await fetch(`${this.baseURL}/models`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();

      // Inject client-side "Auto" smart selector model at the top
      const autoModel: ModelInfo = {
        id: 'auto',
        name: 'Auto (recommended)',
        provider: 'Smart selector',
        description: 'Automatically picks the best model for each query based on its content.',
        cost_tier: 'smart',
        is_default: true,
      };

      const modelsWithAuto = [
        autoModel,
        ...(Array.isArray(data.models) ? data.models : []),
      ];

      const enrichedData = {
        ...data,
        models: modelsWithAuto,
        default_model: 'auto',
      };

      // Cache the result
      cacheUtils.set(CACHE_CONFIG.MODELS_KEY, enrichedData);
      return enrichedData;
    } catch (error) {
      console.error('Error fetching models:', error);
      // Fallback models if backend is unavailable
      const fallbackData = {
        models: [
          {
            id: 'auto',
            name: 'Auto (recommended)',
            provider: 'Smart selector',
            is_default: true,
            cost_tier: 'smart',
          },
          { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'OpenAI', is_default: false, cost_tier: 'low' },
          { id: 'gpt-4o', name: 'GPT-4o', provider: 'OpenAI', is_default: false, cost_tier: 'high' },
          { id: 'gpt-5', name: 'GPT-5', provider: 'OpenAI', is_default: false, cost_tier: 'premium' },
          { id: 'gpt-5-nano', name: 'GPT-5 Nano', provider: 'OpenAI', is_default: false, cost_tier: 'premium' },
          { id: 'mistral', name: 'Mistral Medium', provider: 'Mistral AI', is_default: false, cost_tier: 'medium' },
          { id: 'llama3', name: 'Llama 3.2', provider: 'Local', is_default: false, cost_tier: 'free' },
          { id: 'openai', name: 'OpenAI Legacy', provider: 'OpenAI', is_default: false, cost_tier: 'medium' }
        ],
        default_model: 'auto'
      };
      // Cache fallback data for shorter time
      cacheUtils.set(CACHE_CONFIG.MODELS_KEY, fallbackData);
      return fallbackData;
    }
  }

  async uploadFiles(files: File[], selectedModel: string, language = 'en') {
    // Prevent duplicate uploads
    const fileKey = files.map(f => f.name).join(',') + selectedModel;
    if (this.uploadQueue.has(fileKey)) {
      console.log('Upload already in progress for these files');
      return;
    }

    this.uploadQueue.add(fileKey);
    
    try {
      const formData = new FormData();
      
      files.forEach(file => {
        formData.append('files', file);
      });
      
      formData.append('model', selectedModel);
      formData.append('language', language);

      const response = await fetch(`${this.baseURL}/upload`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error uploading files:', error);
      throw error;
    } finally {
      this.uploadQueue.delete(fileKey);
    }
  }

  async testModel(modelId: string) {
    // Check cache first
    const cached = cacheUtils.get(CACHE_CONFIG.MODEL_STATUS_KEY);
    if (cached && cached[modelId] !== undefined) {
      return { model_id: modelId, status: cached[modelId] ? 'available' : 'unavailable' };
    }

    try {
      const response = await fetch(`${this.baseURL}/models/${modelId}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      const result = response.ok ? 
        await response.json() : 
        { model_id: modelId, status: 'unavailable' };

      // Cache the result
      const statusCache = cached || {};
      statusCache[modelId] = result.status === 'available';
      cacheUtils.set(CACHE_CONFIG.MODEL_STATUS_KEY, statusCache);
      
      return result;
    } catch (error: unknown) {
      const result = { model_id: modelId, status: 'unavailable', error: error instanceof Error ? error.message : 'Unknown error' };
      
      // Cache negative result
      const statusCache = cached || {};
      statusCache[modelId] = false;
      cacheUtils.set(CACHE_CONFIG.MODEL_STATUS_KEY, statusCache);
      
      return result;
    }
  }
}

const Sidebar: React.FC<SidebarProps> = ({ 
  onFileSelect,
  onDirectorySelect,
  getRepoStructure, 
  selectedModel, 
  setSelectedModel,
  isSidebarOpen, 
  toggleSidebar,
  addFileToSidebar
}) => {
  const { t } = useLanguage();
  const { theme } = useTheme();
  const { user, isAuthenticated } = useAuth();
  const [files, setFiles] = useState<FileNode[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isMobileFileDropdownOpen, setIsMobileFileDropdownOpen] = useState<boolean>(false);
  const [isDesktopFileDropdownOpen, setIsDesktopFileDropdownOpen] = useState<boolean>(false);
  const [isMobileModelDropdownOpen, setIsMobileModelDropdownOpen] = useState<boolean>(false);
  const [isDesktopModelDropdownOpen, setIsDesktopModelDropdownOpen] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [modelStatus, setModelStatus] = useState<{ [key: string]: boolean }>({});
  const [isLoadingModels, setIsLoadingModels] = useState<boolean>(true);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  
  // États pour les sections expandables
  const [isExplorerExpanded, setIsExplorerExpanded] = useState<boolean>(true);
  const [isSearchExpanded, setIsSearchExpanded] = useState<boolean>(true);
  const [isUserInfoExpanded, setIsUserInfoExpanded] = useState<boolean>(true);
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState<boolean>(false);
  const [isSignUpModalOpen, setIsSignUpModalOpen] = useState<boolean>(false);
  
  // Faire disparaître automatiquement les erreurs après 5 secondes
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        setError(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const desktopDropdownRef = useRef<HTMLDivElement>(null);
  const modelDropdownRef = useRef<HTMLDivElement>(null);
  const desktopModelDropdownRef = useRef<HTMLDivElement>(null);

  const allowedExtensions: string[] = [
    '.java', '.py', '.cs', '.js', '.ts', '.cpp', '.c', '.h',
    '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx',
    '.tsx', '.sql', '.docx', '.pdf', '.json', '.xml', '.md', '.txt'
  ];

  // Initialize API service
  const apiService = useMemo(() => new AIBackendService(), []);

  // Debounced upload function
  const debouncedUpload = useCallback(
    debounce(async (filesToUpload: File[], model: string) => {
      const effectiveModelForUploads = model === 'auto' ? 'gpt-3.5-turbo' : model;
      try {
        await apiService.uploadFiles(filesToUpload, effectiveModelForUploads);
        console.log('Files uploaded successfully to backend');
        setPendingFiles(prev => prev.filter(f => !filesToUpload.includes(f)));
      } catch (uploadError) {
        console.warn('Backend upload failed:', uploadError);
      }
    }, 2000),
    [apiService]
  );

  // Load search history from localStorage
  useEffect(() => {
    const savedHistory = localStorage.getItem('search_history');
    if (savedHistory) {
      try {
        const history = JSON.parse(savedHistory);
        setSearchHistory(Array.isArray(history) ? history.slice(0, 20) : []); // Limiter à 20 recherches
      } catch (e) {
        console.error('Error loading search history:', e);
      }
    }
  }, []);

  // Load available models on component mount
  useEffect(() => {
    const loadModels = async () => {
      setIsLoadingModels(true);
      try {
        const modelsData = await apiService.getAvailableModels();
        setAvailableModels(modelsData.models);
        
        // Set default model only if no model is selected
        if (!selectedModel && modelsData.default_model) {
          setSelectedModel(modelsData.default_model);
        }

        // Load cached model status
        const cachedStatus = cacheUtils.get(CACHE_CONFIG.MODEL_STATUS_KEY) || {};
        setModelStatus(cachedStatus);

        // Test only the selected model if it exists
        if (selectedModel) {
          const status = await apiService.testModel(selectedModel);
          setModelStatus(prev => ({
            ...prev,
            [selectedModel]: status.status === 'available'
          }));
        }

      } catch (error) {
        console.error('Failed to load models:', error);
        setError('Failed to load available models');
      } finally {
        setIsLoadingModels(false);
      }
    };

    loadModels();
  }, [apiService, setSelectedModel]); // Add apiService and setSelectedModel as dependencies

  // Fonction pour ajouter une recherche à l'historique
  const addToSearchHistory = useCallback((query: string) => {
    if (!query.trim()) return;
    setSearchHistory(prev => {
      const newHistory = [query, ...prev.filter(q => q !== query)].slice(0, 20);
      localStorage.setItem('search_history', JSON.stringify(newHistory));
      return newHistory;
    });
  }, []);

  // Exposer la fonction pour que FlexiAnalyseApp puisse l'utiliser
  useEffect(() => {
    (window as any).__addToSearchHistory = addToSearchHistory;
    return () => {
      delete (window as any).__addToSearchHistory;
    };
  }, [addToSearchHistory]);

  // Test model when dropdown opens (lazy loading)
  const testModelOnDemand = useCallback(async (modelId: string) => {
    if (modelStatus[modelId] === undefined) {
      const status = await apiService.testModel(modelId);
      setModelStatus(prev => ({
        ...prev,
        [modelId]: status.status === 'available'
      }));
    }
  }, [apiService, modelStatus]);

  // Mobile model dropdown
  const handleMobileModelDropdownOpen = useCallback(() => {
    setIsMobileModelDropdownOpen(true);
    setIsMobileFileDropdownOpen(false);
    // Test all models in background when dropdown opens
    availableModels.forEach(model => {
      if (modelStatus[model.id] === undefined) {
        testModelOnDemand(model.id);
      }
    });
  }, [availableModels, modelStatus, testModelOnDemand]);

  // Desktop model dropdown
  const handleDesktopModelDropdownOpen = useCallback(() => {
    setIsDesktopModelDropdownOpen(true);
    setIsDesktopFileDropdownOpen(false);
    // Test all models in background when dropdown opens
    availableModels.forEach(model => {
      if (modelStatus[model.id] === undefined) {
        testModelOnDemand(model.id);
      }
    });
  }, [availableModels, modelStatus, testModelOnDemand]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsMobileFileDropdownOpen(false);
      }

      if (desktopDropdownRef.current && !desktopDropdownRef.current.contains(event.target as Node)) {
        setIsDesktopFileDropdownOpen(false);
      }

      if (modelDropdownRef.current && !modelDropdownRef.current.contains(event.target as Node)) {
        setIsMobileModelDropdownOpen(false);
      }

      // Desktop model dropdown
      if (desktopModelDropdownRef.current && !desktopModelDropdownRef.current.contains(event.target as Node)) {
        setIsDesktopModelDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const filterFiles = useCallback((fileList: FileList): File[] => {
    return Array.from(fileList).filter((file) => {
      const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      return allowedExtensions.includes(extension);
    });
  }, [allowedExtensions]);

  const extractAllFiles = useCallback((nodes: FileNode[]): File[] => {
    const allFiles: File[] = [];
    nodes.forEach((node) => {
      if (node.file) {
        allFiles.push(node.file);
      }
      if (node.children) {
        allFiles.push(...extractAllFiles(node.children));
      }
    });
    return allFiles;
  }, []);

  const buildFileTree = useCallback((fileList: File[]): FileNode[] => {
    const tree: FileNode[] = [];
    const pathMap: { [key: string]: FileNode } = {};

    // Séparer les fichiers avec et sans webkitRelativePath
    const filesWithPath: File[] = [];
    const filesWithoutPath: File[] = [];
    
    fileList.forEach(file => {
      if ((file as any).webkitRelativePath) {
        filesWithPath.push(file);
      } else {
        filesWithoutPath.push(file);
      }
    });

    // Traitement des fichiers avec chemins relatifs (structure de dossiers)
    filesWithPath.forEach((file) => {
      const path = (file as any).webkitRelativePath;
      const parts = path.split('/');

      let currentPath = '';
      let parentNode: FileNode | null = null;

      parts.forEach((part: string, index: number) => {
        currentPath = currentPath ? `${currentPath}/${part}` : part;
        if (!pathMap[currentPath]) {
          const node: FileNode = { name: part };
          if (index === parts.length - 1) {
            node.file = file;
          } else {
            node.children = [];
            node.isOpen = false;
          }
          pathMap[currentPath] = node;

          if (parentNode) {
            parentNode.children!.push(node);
          } else {
            tree.push(node);
          }
        } else {
          // Si le nœud existe déjà et c'est le dernier élément (fichier),
          // mettre à jour le fichier si nécessaire
          if (index === parts.length - 1 && !pathMap[currentPath].file) {
            pathMap[currentPath].file = file;
          }
        }
        parentNode = pathMap[currentPath];
      });
    });

    // Traitement des fichiers sans chemins relatifs
    // Si on a des fichiers avec chemins ET sans chemins, créer un nœud "Other Files"
    // Sinon, si on a seulement des fichiers sans chemins et qu'il y en a plusieurs, créer un nœud "Imported Files"
    if (filesWithoutPath.length > 0) {
      let containerNode: FileNode | null = null;
      
      if (filesWithPath.length > 0) {
        // Mélange : créer un nœud "Other Files"
        containerNode = {
          name: 'Other Files',
          children: [],
          isOpen: true
        };
        tree.push(containerNode);
      } else if (filesWithoutPath.length > 1) {
        // Seulement des fichiers sans chemins et plusieurs fichiers : créer un nœud "Imported Files"
        containerNode = {
          name: 'Imported Files',
          children: [],
          isOpen: true
        };
        tree.push(containerNode);
      }
      
      // Ajouter les fichiers sans chemins
      filesWithoutPath.forEach((file) => {
        const fileNode: FileNode = {
          name: file.name,
          file: file
        };
        
        if (containerNode) {
          containerNode.children!.push(fileNode);
        } else {
          // Un seul fichier sans chemin : l'ajouter directement à la racine
          tree.push(fileNode);
        }
      });
    }

    return tree;
  }, []);

  // Fonction pour ajouter un fichier à la sidebar depuis l'extérieur
  const addFileToSidebarInternal = useCallback((file: File) => {
    setFiles(prevFiles => {
      // Vérifier si le fichier existe déjà
      const fileExists = (nodes: FileNode[]): boolean => {
        for (const node of nodes) {
          if (node.file && node.file.name === file.name && node.file.size === file.size) {
            return true;
          }
          if (node.children && fileExists(node.children)) {
            return true;
          }
        }
        return false;
      };

      if (fileExists(prevFiles)) {
        return prevFiles; // Le fichier existe déjà
      }

      // Ajouter le fichier à l'arbre
      const allCurrentFiles = extractAllFiles(prevFiles);
      const newTree = buildFileTree([...allCurrentFiles, file]);
      
      // Ajouter le fichier aux fichiers en attente pour l'upload
      setPendingFiles(prev => {
        if (!prev.includes(file)) {
          return [...prev, file];
        }
        return prev;
      });

      // Uploader le fichier
      const effectiveModelForUploads = selectedModel === 'auto' ? 'gpt-3.5-turbo' : selectedModel;
      debouncedUpload([file], effectiveModelForUploads);

      return newTree;
    });
  }, [buildFileTree, extractAllFiles, selectedModel, debouncedUpload]);

  // Exposer la fonction via useEffect si addFileToSidebar est fourni
  useEffect(() => {
    if (addFileToSidebar) {
      // Créer une fonction qui peut être appelée depuis l'extérieur
      (window as any).__addFileToSidebar = addFileToSidebarInternal;
    }
    return () => {
      delete (window as any).__addFileToSidebar;
    };
  }, [addFileToSidebar, addFileToSidebarInternal]);

  const generateRepoStructure = useCallback((nodes: FileNode[], indent: number = 0): string => {
    let structure = '';
    nodes.forEach((node) => {
      const prefix = '  '.repeat(indent);
      if (node.children) {
        structure += `${prefix}- ${node.name}/\n`;
        structure += generateRepoStructure(node.children, indent + 1);
      } else {
        structure += `${prefix}- ${node.name}\n`;
      }
    });
    return structure;
  }, []);

  // Clear previous state before processing new files
  const clearPreviousState = useCallback(() => {
    setFiles([]);
    setPendingFiles([]);
    setError(null);
    // Update repo structure with empty state immediately
    getRepoStructure(() => '', []);
  }, [getRepoStructure]);
  
  const handleFileChange = useCallback(async (event: ChangeEvent<HTMLInputElement>): Promise<void> => {
    if (event.target.files) {
      setIsLoading(true);
      setError(null);

      clearPreviousState();

      try {
        const acceptedFiles = filterFiles(event.target.files);
        
        // Vérifier les limitations pour les utilisateurs non connectés
        if (!isAuthenticated) {
          // Bloquer l'upload de plusieurs fichiers (répertoire)
          if (acceptedFiles.length > 1) {
            setError('Repository upload is only available for signed-in users. Please sign in to upload multiple files.');
            setIsLoading(false);
            if (event.target) {
              event.target.value = '';
            }
            return;
          }
          
          // Vérifier la limite d'un seul fichier
          const uploadedFilesKey = 'uploaded_files';
          const stored = localStorage.getItem(uploadedFilesKey);
          let uploadedCount = 0;
          if (stored) {
            try {
              const data = JSON.parse(stored);
              uploadedCount = data.count || 0;
            } catch (e) {
              console.error('Error reading uploaded files:', e);
            }
          }
          
          if (uploadedCount >= 1) {
            setError('You have reached the limit of 1 file upload. Please sign in to upload more files.');
            setIsLoading(false);
            if (event.target) {
              event.target.value = '';
            }
            return;
          }
        }
        
        // Immediately display files in interface
        const fileTree = buildFileTree(acceptedFiles);
        setFiles(fileTree);

        // Add to pending uploads
        setPendingFiles(prev => [...prev, ...acceptedFiles]);
        
        // Schedule debounced upload
        debouncedUpload(acceptedFiles, selectedModel);
        
        // Incrémenter le compteur pour les non connectés
        if (!isAuthenticated && acceptedFiles.length === 1) {
          const uploadedFilesKey = 'uploaded_files';
          const stored = localStorage.getItem(uploadedFilesKey);
          let uploadedCount = 0;
          if (stored) {
            try {
              const data = JSON.parse(stored);
              uploadedCount = data.count || 0;
            } catch (e) {
              console.error('Error reading uploaded files:', e);
            }
          }
          localStorage.setItem(uploadedFilesKey, JSON.stringify({
            count: uploadedCount + 1
          }));
        }
        
        // Si c'est un seul fichier, l'afficher automatiquement dans le FileViewer
        if (acceptedFiles.length === 1 && onFileSelect) {
          const file = acceptedFiles[0];
          const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
          const isBinaryFile = ['.docx', '.pdf'].includes(extension);
          
          try {
            let content: string | ArrayBuffer;
            if (isBinaryFile) {
              content = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result as ArrayBuffer);
                reader.onerror = () => reject(new Error('Failed to read file'));
                reader.readAsArrayBuffer(file);
              });
            } else {
              content = await file.text();
            }
            
            const description = 'No description available';
            onFileSelect(file, { content, description });
          } catch (error) {
            console.error('Error reading file for display:', error);
          }
        }
        
      } catch (error) {
        console.error('Error processing files:', error);
        setError('Failed to process files. Please try again.');
        setFiles([]);
      } finally {
        setIsLoading(false);
        if (event.target) {
          event.target.value = ''; // Clear input value to allow re-uploading same file
        }
      }
    }
  }, [filterFiles, buildFileTree, debouncedUpload, selectedModel, clearPreviousState, onFileSelect, isAuthenticated]);

  const handleFolderChange = useCallback(async (event: ChangeEvent<HTMLInputElement>): Promise<void> => {
    if (event.target.files) {
      setIsLoading(true);
      clearPreviousState();
      setError(null);
      
      try {
        const acceptedFiles = filterFiles(event.target.files);
        
        // Bloquer l'upload de répertoires pour les utilisateurs non connectés
        if (!isAuthenticated && acceptedFiles.length > 1) {
          setError('Repository upload is only available for signed-in users. Please sign in to upload multiple files.');
          setIsLoading(false);
          if (event.target) {
            event.target.value = '';
          }
          return;
        }
        
        // Toujours afficher les fichiers dans la sidebar
        const fileTree = buildFileTree(acceptedFiles);
        setFiles(fileTree);
        
        // Add to pending uploads
        setPendingFiles(prev => [...prev, ...acceptedFiles]);
        
        // Si c'est un répertoire (plusieurs fichiers), utiliser handleDirectorySelect
        if (acceptedFiles.length > 1 && onDirectorySelect) {
          await onDirectorySelect(acceptedFiles);
        } else if (acceptedFiles.length === 1 && onFileSelect) {
          // Si c'est un seul fichier, l'afficher automatiquement dans le FileViewer
          const file = acceptedFiles[0];
          const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
          const isBinaryFile = ['.docx', '.pdf'].includes(extension);
          
          try {
            let content: string | ArrayBuffer;
            if (isBinaryFile) {
              content = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result as ArrayBuffer);
                reader.onerror = () => reject(new Error('Failed to read file'));
                reader.readAsArrayBuffer(file);
              });
            } else {
              content = await file.text();
            }
            
            const description = 'No description available';
            onFileSelect(file, { content, description });
          } catch (error) {
            console.error('Error reading file for display:', error);
          }
        } else {
          // Sinon, traitement normal (upload seulement)
          debouncedUpload(acceptedFiles, selectedModel);
        }
        
      } catch (error) {
        console.error('Error processing folder:', error);
        setError('Failed to process folder. Please try again.');
        setFiles([]);
      } finally {
        setIsLoading(false);

        if (event.target) {
          event.target.value = ''; // Clear input value to allow re-uploading same folder
        }
      }
    }
  }, [filterFiles, buildFileTree, debouncedUpload, selectedModel, clearPreviousState, onDirectorySelect, onFileSelect, isAuthenticated]);

  const toggleFolder = useCallback((node: FileNode, nodes: FileNode[]): FileNode[] => {
    return nodes.map((n) => {
      if (n === node) {
        return { ...n, isOpen: !n.isOpen };
      }
      if (n.children) {
        return { ...n, children: toggleFolder(node, n.children) };
      }
      return n;
    });
  }, []);

  const handleToggleFolder = useCallback((node: FileNode) => {
    setFiles((prevFiles) => toggleFolder(node, prevFiles));
  }, [toggleFolder]);

  const handleFileClick = useCallback(async (file: File) => {
    try {
      const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      const isBinaryFile = ['.docx', '.pdf'].includes(extension);

      let content: string | ArrayBuffer;
      if (isBinaryFile) {
        content = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result as ArrayBuffer);
          reader.onerror = () => reject(new Error('Failed to read file'));
          reader.readAsArrayBuffer(file);
        });
      } else {
        content = await file.text();
      }

      const description = 'No description available';
      onFileSelect(file, { content, description });
      setError(null);

      // Upload this specific file if not already uploaded
      if (pendingFiles.includes(file)) {
        try {
          const effectiveModelForUploads = selectedModel === 'auto' ? 'gpt-3.5-turbo' : selectedModel;
          await apiService.uploadFiles([file], effectiveModelForUploads);
          setPendingFiles(prev => prev.filter(f => f !== file));
          console.log('File uploaded on demand:', file.name);
        } catch (uploadError) {
          console.warn('On-demand upload failed:', uploadError);
        }
      }
    } catch (error) {
      console.error('Error reading file:', error);
      setError('Failed to read file');
    }
  }, [onFileSelect, pendingFiles, apiService, selectedModel]);

  const renderFileTree = useCallback((nodes: FileNode[]): React.ReactElement[] => {
    return nodes.map((node, index) => (
      <li key={index}>
        {node.children ? (
          <div className="flex items-center">
            <div
              onClick={() => handleToggleFolder(node)}
              className="mr-1 mb-2 px-2 py-1 cursor-pointer"
            >
              {node.isOpen ? <FolderOpen size={18} color="#FFD700"/> : <Folder size={18} color="#FFD700" />}
            </div>
            <span 
              className="font-semibold block truncate max-w-full"
              style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
              title={node.name}
            >
              {node.name}
            </span>
          </div>
        ) : (
          <div
            onClick={() => handleFileClick(node.file!)}
            className={`text-blue-500 hover:underline cursor-pointer hover:bg-gray-100 p-1 ${
              pendingFiles.includes(node.file!) ? 'opacity-70' : ''
            }`}
            title={`${node.name}${pendingFiles.includes(node.file!) ? ' (pending upload)' : ''}`}
          >
            <span className="block truncate max-w-full" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {node.name}
              {pendingFiles.includes(node.file!) && (
                <span className="ml-1 text-xs text-orange-500">⏳</span>
              )}
            </span>
          </div>
        )}
        {node.children && node.isOpen && (
          <ul className="ml-4">
            {renderFileTree(node.children)}
          </ul>
        )}
      </li>
    ));
  }, [handleToggleFolder, handleFileClick, pendingFiles]);

  const getSelectedModelInfo = useCallback((): ModelInfo => {
    return availableModels.find(model => model.id === selectedModel) || 
           { id: selectedModel, name: selectedModel, provider: 'Unknown' };
  }, [availableModels, selectedModel]);

  const getModelStatusIcon = useCallback((modelId: string) => {
    const status = modelStatus[modelId];
    if (status === undefined) {
      return <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>;
    }
    return (
      <div className={`w-2 h-2 rounded-full ${
        status ? 'bg-green-500' : 'bg-red-500'
      }`}></div>
    );
  }, [modelStatus]);

  const getCostTierColor = useCallback((costTier?: string) => {
    switch (costTier) {
      case 'free': return 'bg-green-100 text-green-800';
      case 'low': return 'bg-blue-100 text-blue-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-orange-100 text-orange-800';
      case 'premium': return 'bg-purple-100 text-purple-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  }, []);

  // Function to get model logo from CDN
  const getModelLogo = useCallback((model: ModelInfo): string => {
    const modelId = model.id.toLowerCase();
    const provider = model.provider.toLowerCase();

    // Map based on model ID first, then provider
    // Using Simple Icons CDN with SVG format for reliable logo sources
    if (modelId === 'auto') {
      // Auto/Smart selector - using a robot/automation icon
      return 'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/robotframework.svg';
    }
    
    // Check for Claude models BEFORE OpenAI or other generic AI checks
    if (modelId.includes('claude') || provider.includes('anthropic')) {
      return 'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/anthropic.svg';
    }

    // Check for Gemini/Google models BEFORE OpenAI check to avoid conflicts
    if (modelId.includes('gemini') || provider.includes('google')) {
      return 'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/google.svg';
    }
    
    if (modelId.includes('gpt') || provider.includes('openai')) {
      return 'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/openai.svg';
    }
    
    if (modelId.includes('mistral') || provider.includes('mistral')) {
      // Mistral AI - using a generic AI/ML icon as fallback since Mistral isn't in simple-icons
      return 'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/matrix.svg';
    }
    
    if (modelId.includes('llama') || provider.includes('local')) {
      // Llama models are from Meta
      return 'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/meta.svg';
    }
    
    // Default logo for unknown providers
    return 'https://cdn.jsdelivr.net/npm/simple-icons@v11/icons/openai.svg';
  }, []);

  // Memoized file structure calculations
  const fileStructure = useMemo(() => {
    const structure = generateRepoStructure(files);
    const allFiles = extractAllFiles(files);
    return { structure, allFiles };
  }, [files, generateRepoStructure, extractAllFiles]);

  // Update repo structure when file structure changes
  useEffect(() => {
    getRepoStructure(() => fileStructure.structure, fileStructure.allFiles);
  }, [fileStructure, getRepoStructure]);

  // Helper function pour obtenir les classes CSS selon le thème
  const getThemeClasses = useCallback(() => {
    switch (theme) {
      case 'dark':
        return {
          sidebar: 'bg-gray-800',
          text: 'text-gray-200',
          textSecondary: 'text-gray-400',
          bg: 'bg-gray-700',
          border: 'border-gray-600',
          hover: 'hover:bg-gray-700'
        };
      case 'dark-blue':
        return {
          sidebar: 'bg-blue-950',
          text: 'text-blue-100',
          textSecondary: 'text-blue-300',
          bg: 'bg-blue-900',
          border: 'border-blue-800',
          hover: 'hover:bg-blue-900'
        };
      default: // white
        return {
          sidebar: 'bg-gray-100',
          text: 'text-gray-800',
          textSecondary: 'text-gray-600',
          bg: 'bg-white',
          border: 'border-gray-300',
          hover: 'hover:bg-gray-50'
        };
    }
  }, [theme]);

  // Composant de section expandable réutilisable
  const ExpandableSection: React.FC<{
    title: string;
    icon: React.ReactNode;
    isExpanded: boolean;
    onToggle: () => void;
    children: React.ReactNode;
  }> = ({ title, icon, isExpanded, onToggle, children }) => {
    const themeClasses = getThemeClasses();
    
    return (
      <div className="mb-1 overflow-hidden">
        {/* Header */}
        <button
          onClick={onToggle}
          className={`w-full flex items-center justify-between px-2 py-1.5 ${themeClasses.hover} transition-colors duration-200 rounded-sm`}
        >
          <div className="flex items-center gap-2">
            <div 
              className={`transition-transform duration-500 ease-in-out transform origin-center ${
                isExpanded ? 'rotate-90' : 'rotate-0'
              }`}
              style={{ transitionTimingFunction: 'cubic-bezier(0.4, 0, 0.2, 1)' }}
            >
              <ChevronRight size={16} className={themeClasses.textSecondary} />
            </div>
            {icon}
            <span className={`text-sm font-semibold ${themeClasses.text} transition-opacity duration-300`}>
              {title}
            </span>
          </div>
        </button>
        
        {/* Content avec animation fluide */}
        <div
          className="grid transition-all duration-500 ease-in-out"
          style={{
            gridTemplateRows: isExpanded ? '1fr' : '0fr',
            transitionTimingFunction: 'cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        >
          <div className="overflow-hidden">
            <div 
              className={`px-2 pb-1 transition-opacity duration-500 ${
                isExpanded ? 'opacity-100 delay-100' : 'opacity-0 delay-0'
              }`}
              style={{ transitionTimingFunction: 'cubic-bezier(0.4, 0, 0.2, 1)' }}
            >
              {children}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
  <>
    {/* Mobile Hamburger Menu */}
    <div className="lg:hidden">
      {/* Hamburger Button */}
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

      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-30"
          onClick={toggleSidebar}
        />
      )}

      {/* Mobile Sidebar */}
      {isSidebarOpen && (
        <div className="fixed inset-y-0 left-0 z-40 w-80 bg-white shadow-lg transform transition-transform duration-300 ease-in-out">
          <div className="p-4 h-full flex flex-col">
            {/* Header with close button */}
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-semibold text-gray-800">Menu</h2>
              <button
                onClick={toggleSidebar}
                className="p-1 rounded-md text-gray-500 hover:text-gray-700 hover:bg-gray-100"
              >
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Error display */}
            {error && (
              <div className="mb-4 p-3 bg-yellow-500 text-white rounded-lg shadow-lg animate-slide-in-right">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2 flex-1">
                    <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <p className="text-sm font-medium">{error}</p>
                  </div>
                  <button
                    onClick={() => setError(null)}
                    className="text-white hover:text-gray-200 transition-colors flex-shrink-0"
                  >
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </button>
                </div>
              </div>
            )}

            {/* Loading state */}
            {isLoading && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                  <span className="text-sm text-blue-800">Processing files...</span>
                </div>
              </div>
            )}

            {/* Menu Items */}
            <div className="space-y-4 mb-6">
              {/* File dropdown */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    setIsMobileFileDropdownOpen((prev) => !prev);
                    setIsMobileModelDropdownOpen(false);
                  }}
                  className="w-full flex items-center justify-between p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span className="font-medium text-gray-700">File</span>
                  </div>
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                
                {isMobileFileDropdownOpen  && (
                  <div className="mt-2 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden">
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        fileInputRef.current?.click();
                        setIsMobileFileDropdownOpen(false);
                      }}
                      className="w-full text-left px-4 py-3 text-gray-700 hover:bg-gray-50 border-b border-gray-100"
                    >
                      Import a file
                    </button>
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        folderInputRef.current?.click();
                        setIsMobileFileDropdownOpen(false);
                      }}
                      className="w-full text-left px-4 py-3 text-gray-700 hover:bg-gray-50"
                    >
                      Import a folder
                    </button>
                  </div>
                )}
                
              </div>

              {/* Model dropdown */}
              <div className="relative" ref={modelDropdownRef}>
                <button
                  onClick={() => handleMobileModelDropdownOpen()}
                  className={`w-full flex items-center justify-between p-3 text-left ${theme === 'white' ? 'bg-gray-50 hover:bg-gray-100' : theme === 'dark' ? 'bg-gray-700 hover:bg-gray-600' : 'bg-blue-900 hover:bg-blue-800'} rounded-lg transition-colors`}
                >
                  <div className="flex items-center space-x-3">
                    <svg className={`w-5 h-5 ${getThemeClasses().textSecondary}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    <span className={`font-medium ${getThemeClasses().text}`}>{t('sidebar.model')}</span>
                  </div>
                  <svg className={`w-4 h-4 ${getThemeClasses().textSecondary}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                
                {isMobileModelDropdownOpen  && (
                  <div className={`mt-2 ${theme === 'white' ? 'bg-white' : theme === 'dark' ? 'bg-gray-700' : 'bg-blue-900'} ${getThemeClasses().border} rounded-lg shadow-lg max-h-80 overflow-y-auto`}>
                    {isLoadingModels ? (
                      <div className="px-4 py-6 text-center">
                        <div className="flex items-center justify-center space-x-2">
                          <div className={`w-4 h-4 border-2 ${theme === 'white' ? 'border-blue-500' : 'border-blue-300'} border-t-transparent rounded-full animate-spin`}></div>
                          <span className={`text-sm ${getThemeClasses().textSecondary}`}>Loading models...</span>
                        </div>
                      </div>
                    ) : (
                      availableModels.map((model) => (
                        <button
                          key={model.id}
                          onClick={() => {
                            setSelectedModel(model.id);
                            setIsMobileModelDropdownOpen(false);
                          }}
                          className={`w-full text-left px-4 py-3 ${theme === 'white' ? 'hover:bg-gray-50' : theme === 'dark' ? 'hover:bg-gray-600' : 'hover:bg-blue-800'} ${getThemeClasses().border} border-b last:border-b-0 ${
                            selectedModel === model.id ? (theme === 'white' ? 'bg-blue-50 border-blue-200' : theme === 'dark' ? 'bg-gray-600 border-gray-500' : 'bg-blue-800 border-blue-700') : ''
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center space-x-2">
                                <img 
                                  src={getModelLogo(model)} 
                                  alt={`${model.provider} logo`}
                                  className="w-5 h-5 flex-shrink-0"
                                  onError={(e) => {
                                    // Fallback to a default icon if image fails to load
                                    (e.target as HTMLImageElement).style.display = 'none';
                                  }}
                                />
                                <p className={`text-sm font-medium truncate ${
                                  selectedModel === model.id 
                                    ? (theme === 'white' ? 'text-blue-900' : theme === 'dark' ? 'text-blue-300' : 'text-blue-200')
                                    : getThemeClasses().text
                                }`}>
                                  {model.name}
                                </p>
                                {getModelStatusIcon(model.id)}
                              </div>
                              <p className={`text-xs truncate ${
                                selectedModel === model.id 
                                  ? (theme === 'white' ? 'text-blue-600' : theme === 'dark' ? 'text-blue-400' : 'text-blue-300')
                                  : getThemeClasses().textSecondary
                              }`}>
                                {model.provider}
                              </p>
                            </div>
                            {selectedModel === model.id && (
                              <svg className={`w-5 h-5 ${theme === 'white' ? 'text-blue-600' : theme === 'dark' ? 'text-blue-400' : 'text-blue-300'}`} fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                              </svg>
                            )}
                          </div>
                          {model.id === 'gpt-5' && (
                            <div className="flex space-x-1 mt-2">
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                Latest
                              </span>
                            </div>
                          )}
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Sections expandables comme dans le desktop */}
            <div className="flex-1 min-h-0 overflow-y-auto mt-4">
              {/* Section 1: EXPLORER - Fichiers/Répertoires */}
              <ExpandableSection
                title="EXPLORER"
                icon={<FileText size={16} className="text-gray-600" />}
                isExpanded={isExplorerExpanded}
                onToggle={() => setIsExplorerExpanded(!isExplorerExpanded)}
              >
                <div className="max-h-48 overflow-y-auto overflow-x-hidden">
                  {isLoading ? (
                    <div className="flex items-center text-blue-600 text-sm py-2">
                      <svg
                        className="animate-spin h-4 w-4 mr-2"
                        xmlns="http://www.w3.org/2000/svg"
                        fill="none"
                        viewBox="0 0 24 24"
                      >
                        <circle
                          className="opacity-25"
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="4"
                        ></circle>
                        <path
                          className="opacity-75"
                          fill="currentColor"
                          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        ></path>
                      </svg>
                      Loading files...
                    </div>
                  ) : files.length > 0 ? (
                    <ul className="text-sm text-gray-600">
                      {renderFileTree(files)}
                    </ul>
                  ) : (
                    <p className="text-gray-500 text-sm py-2">
                      {t('sidebar.noFiles')}
                    </p>
                  )}
                </div>
              </ExpandableSection>

              {/* Section 2: SEARCH - Historique de recherche */}
              <ExpandableSection
                title="SEARCH"
                icon={<Search size={16} className="text-gray-600" />}
                isExpanded={isSearchExpanded}
                onToggle={() => setIsSearchExpanded(!isSearchExpanded)}
              >
                <div className="max-h-48 overflow-y-auto">
                  {searchHistory.length > 0 ? (
                    <div className="space-y-1">
                      {searchHistory.map((query, index) => (
                        <button
                          key={index}
                          onClick={() => {
                            // Permettre de cliquer sur une recherche pour la réutiliser
                            // Cette fonctionnalité peut être ajoutée plus tard
                          }}
                          className="w-full text-left px-2 py-1.5 rounded text-xs text-gray-600 hover:bg-gray-50 transition-colors truncate"
                          title={query}
                        >
                          {query}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-sm py-2">
                      No search history
                    </p>
                  )}
                </div>
              </ExpandableSection>

              {/* Section 3: USER INFO - Informations utilisateur */}
              <ExpandableSection
                title="USER INFO"
                icon={<User size={16} className="text-gray-600" />}
                isExpanded={isUserInfoExpanded}
                onToggle={() => setIsUserInfoExpanded(!isUserInfoExpanded)}
              >
                <div className="max-h-40 overflow-y-auto">
                  {isAuthenticated && user ? (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        {user.avatar && (
                          <img
                            src={user.avatar}
                            alt={user.name || user.email}
                            className="w-8 h-8 rounded-full object-cover border-2 border-blue-500"
                          />
                        )}
                        <div className="flex-1 min-w-0">
                          <div className="text-gray-800 text-sm font-medium truncate">
                            {user.name || user.email}
                          </div>
                          {user.name && (
                            <div className="text-gray-600 text-xs truncate">
                              {user.email}
                            </div>
                          )}
                        </div>
                      </div>
                      {user.plan && (
                        <div className="text-gray-600 text-xs">
                          Plan: <span className="font-medium capitalize">{user.plan}</span>
                        </div>
                      )}
                      {user.provider && (
                        <div className="text-gray-600 text-xs">
                          Provider: {user.provider}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <p className="text-gray-500 text-sm py-2">
                        Not authenticated
                      </p>
                      <button
                        onClick={() => setIsLoginModalOpen(true)}
                        className="w-full px-3 py-2 rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700"
                      >
                        Sign in
                      </button>
                    </div>
                  )}
                </div>
              </ExpandableSection>
            </div>
          </div>
        </div>
      )}
      
      {/* Login Modal et Sign Up Modal - également pour mobile */}
      {!isSignUpModalOpen && (
        <LoginModal
          isOpen={isLoginModalOpen}
          onClose={() => setIsLoginModalOpen(false)}
          onSwitchToSignUp={() => {
            setIsLoginModalOpen(false);
            setTimeout(() => {
              setIsSignUpModalOpen(true);
            }, 300);
          }}
        />
      )}
      
      {!isLoginModalOpen && (
        <SignUpModal
          isOpen={isSignUpModalOpen}
          onClose={() => setIsSignUpModalOpen(false)}
          onSwitchToLogin={() => {
            setIsSignUpModalOpen(false);
            setTimeout(() => {
              setIsLoginModalOpen(true);
            }, 300);
          }}
        />
      )}
    </div>
    <input
      type="file"
      ref={fileInputRef}
      onChange={handleFileChange}
      className="hidden"
      multiple
    />
    <input
      type="file"
      ref={folderInputRef}
      onChange={handleFolderChange}
      className="hidden"
      // @ts-ignore: webkitdirectory is not in the standard types
      webkitdirectory="true"
      directory="true"
    />

    {/* Desktop Sidebar - Nouvelle structure avec 3 sections */}
    <div className={`hidden lg:block h-screen p-4 flex flex-col ${getThemeClasses().sidebar}`}>
      {/* Error display */}
      {error && (
        <div className="mb-4 p-3 bg-yellow-500 text-white rounded-lg shadow-lg animate-slide-in-right">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-2 flex-1">
              <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <p className="text-sm font-medium">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-white hover:text-gray-200 transition-colors flex-shrink-0"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
          <div className="flex items-center space-x-2">
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-sm text-blue-800">Processing files...</span>
          </div>
        </div>
      )}

      {/* Desktop Menu layout */}
      <div className={`mb-4 ${isSidebarOpen ? 'flex justify-between items-center flex-wrap gap-2' : 'flex flex-col space-y-3'}`}>
        {/* File dropdown */}
        <div className="relative" ref={desktopDropdownRef}>
          <a
            href="#"
            onClick={(e) => { 
              e.preventDefault();
              setIsDesktopFileDropdownOpen((prev) => !prev);
            }}
            className={`text-gray-700 hover:text-blue-500 ${!isSidebarOpen ? 'flex items-center justify-center w-full py-1 px-2 rounded hover:bg-gray-200' : ''}`}
          >
            {isSidebarOpen ? 'File' : (
              <div className="flex items-center space-x-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="text-xs">File</span>
              </div>
            )}
          </a>
          
          {isDesktopFileDropdownOpen && (
            <div className={`absolute bg-white shadow-lg border border-gray-200 rounded-md z-50 max-h-40 overflow-y-auto ${isSidebarOpen ? 'w-60 mt-1' : 'w-48 left-full top-0 ml-2'}`}>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  fileInputRef.current?.click();
                  setIsDesktopFileDropdownOpen(false);
                }}
                className="block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100"
              >
                Import a file
              </button>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  folderInputRef.current?.click();
                  setIsDesktopFileDropdownOpen(false);
                }}
                className="block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100"
              >
                Import a folder
              </button>
            </div>
          )}
        </div>

        {/* Export button */}
        <a 
          href="#" 
          className={`text-gray-700 hover:text-blue-500 ${!isSidebarOpen ? 'flex items-center justify-center w-full py-1 px-2 rounded hover:bg-gray-200' : ''}`}
        >
          {isSidebarOpen ? t('sidebar.export') : (
            <div className="flex items-center space-x-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-xs">{t('sidebar.export')}</span>
            </div>
          )}
        </a>

        {/* Enhanced Model dropdown */}
        <div className="relative" ref={desktopModelDropdownRef}>
          <a
            href="#"
            onClick={(e) =>{
              e.preventDefault();
              handleDesktopModelDropdownOpen();
            }}
            className={`${getThemeClasses().text} ${theme !== 'white' ? 'hover:text-blue-300' : 'hover:text-blue-500'} ${!isSidebarOpen ? 'flex items-center justify-center w-full py-1 px-2 rounded hover:bg-gray-200' : 'flex items-center space-x-2'}`}
          >
            {isSidebarOpen ? (
              <div className="flex items-center space-x-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span className="text-sm font-medium truncate max-w-40">{t('sidebar.model')}</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            ) : (
              <div className="flex items-center space-x-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span className="text-xs">{t('sidebar.model')}</span>
              </div>
            )}
          </a>
          
          {isDesktopModelDropdownOpen  && (
            <div className={`absolute ${theme === 'white' ? 'bg-white' : theme === 'dark' ? 'bg-gray-700' : 'bg-blue-900'} shadow-lg ${getThemeClasses().border} rounded-md z-50 max-h-80 overflow-y-auto ${isSidebarOpen ? 'right-0 top-full w-56 mt-2' : 'left-full top-0 w-64 ml-2'}`}>
              {isLoadingModels ? (
                <div className="px-4 py-3 text-center">
                  <div className="flex items-center justify-center space-x-2">
                    <div className={`w-4 h-4 border-2 ${theme === 'white' ? 'border-blue-500' : 'border-blue-300'} border-t-transparent rounded-full animate-spin`}></div>
                    <span className={`text-sm ${getThemeClasses().textSecondary}`}>Loading models...</span>
                  </div>
                </div>
              ) : (
                availableModels.map((model) => (
                  <a
                    key={model.id}
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      setSelectedModel(model.id);
                      setIsDesktopModelDropdownOpen(false);
                    }}
                    className={`block w-full text-left px-4 py-3 ${theme === 'white' ? 'hover:bg-gray-50' : theme === 'dark' ? 'hover:bg-gray-600' : 'hover:bg-blue-800'} ${getThemeClasses().border} border-b last:border-b-0 ${
                      selectedModel === model.id ? (theme === 'white' ? 'bg-blue-50 border-blue-200' : theme === 'dark' ? 'bg-gray-600 border-gray-500' : 'bg-blue-800 border-blue-700') : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <img 
                            src={getModelLogo(model)} 
                            alt={`${model.provider} logo`}
                            className="w-5 h-5 flex-shrink-0"
                            onError={(e) => {
                              // Fallback to a default icon if image fails to load
                              (e.target as HTMLImageElement).style.display = 'none';
                            }}
                          />
                          <p className={`text-sm font-medium truncate ${
                            selectedModel === model.id 
                              ? (theme === 'white' ? 'text-blue-900' : theme === 'dark' ? 'text-blue-300' : 'text-blue-200')
                              : getThemeClasses().text
                          }`}>
                            {model.name}
                          </p>
                          {getModelStatusIcon(model.id)}
                        </div>
                        <p className={`text-xs truncate ${
                          selectedModel === model.id 
                            ? (theme === 'white' ? 'text-blue-600' : theme === 'dark' ? 'text-blue-400' : 'text-blue-300')
                            : getThemeClasses().textSecondary
                        }`}>
                          {model.provider}
                        </p>
                      </div>
                      {selectedModel === model.id && (
                        <svg className={`w-5 h-5 ${theme === 'white' ? 'text-blue-600' : theme === 'dark' ? 'text-blue-400' : 'text-blue-300'}`} fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    {model.id === 'gpt-5' && (
                      <div className="flex space-x-1 mt-2">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Latest
                        </span>
                      </div>
                    )}
                  </a>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Sections expandables avec hauteurs ajustables */}
      <div className="flex-1 overflow-y-auto">
        {/* Section 1: EXPLORER - Fichiers/Répertoires */}
        {isSidebarOpen && (
          <ExpandableSection
            title="EXPLORER"
            icon={<FileText size={16} className={getThemeClasses().textSecondary} />}
            isExpanded={isExplorerExpanded}
            onToggle={() => setIsExplorerExpanded(!isExplorerExpanded)}
          >
            <div className="max-h-48 overflow-y-auto overflow-x-hidden">
              {isLoading ? (
                <div className={`flex items-center ${getThemeClasses().textSecondary} text-sm py-2`}>
                  <svg
                    className="animate-spin h-4 w-4 mr-2"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Loading files...
                </div>
              ) : files.length > 0 ? (
                <ul className={`text-sm ${getThemeClasses().textSecondary}`}>
                  {renderFileTree(files)}
                </ul>
              ) : (
                <p className={`${getThemeClasses().textSecondary} text-sm py-2`}>
                  {t('sidebar.noFiles')}
                </p>
              )}
            </div>
          </ExpandableSection>
        )}

        {/* Section 2: SEARCH - Historique de recherche */}
        {isSidebarOpen && (
          <ExpandableSection
            title="SEARCH"
            icon={<Search size={16} className={getThemeClasses().textSecondary} />}
            isExpanded={isSearchExpanded}
            onToggle={() => setIsSearchExpanded(!isSearchExpanded)}
          >
            <div className="max-h-48 overflow-y-auto">
              {searchHistory.length > 0 ? (
                <div className="space-y-1">
                  {searchHistory.map((query, index) => (
                    <button
                      key={index}
                      onClick={() => {
                        // Permettre de cliquer sur une recherche pour la réutiliser
                        // Cette fonctionnalité peut être ajoutée plus tard
                      }}
                      className={`w-full text-left px-2 py-1.5 rounded text-xs ${getThemeClasses().textSecondary} ${getThemeClasses().hover} transition-colors truncate`}
                      title={query}
                    >
                      {query}
                    </button>
                  ))}
                </div>
              ) : (
                <p className={`${getThemeClasses().textSecondary} text-sm py-2`}>
                  No search history
                </p>
              )}
            </div>
          </ExpandableSection>
        )}

        {/* Section 3: USER INFO - Informations utilisateur */}
        {isSidebarOpen && (
          <ExpandableSection
            title="USER INFO"
            icon={<User size={16} className={getThemeClasses().textSecondary} />}
            isExpanded={isUserInfoExpanded}
            onToggle={() => setIsUserInfoExpanded(!isUserInfoExpanded)}
          >
            <div className="max-h-40 overflow-y-auto">
              {isAuthenticated && user ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    {user.avatar && (
                      <img
                        src={user.avatar}
                        alt={user.name || user.email}
                        className="w-8 h-8 rounded-full object-cover border-2 border-blue-500"
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <div className={`${getThemeClasses().text} text-sm font-medium truncate`}>
                        {user.name || user.email}
                      </div>
                      {user.name && (
                        <div className={`${getThemeClasses().textSecondary} text-xs truncate`}>
                          {user.email}
                        </div>
                      )}
                    </div>
                  </div>
                  {user.plan && (
                    <div className={`${getThemeClasses().textSecondary} text-xs`}>
                      Plan: <span className="font-medium capitalize">{user.plan}</span>
                    </div>
                  )}
                  {user.provider && (
                    <div className={`${getThemeClasses().textSecondary} text-xs`}>
                      Provider: {user.provider}
                    </div>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  <p className={`${getThemeClasses().textSecondary} text-sm py-2`}>
                    Not authenticated
                  </p>
                  <button
                    onClick={() => setIsLoginModalOpen(true)}
                    className={`w-full px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      theme === 'white' 
                        ? 'bg-blue-600 text-white hover:bg-blue-700' 
                        : theme === 'dark'
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-blue-500 text-white hover:bg-blue-600'
                    }`}
                  >
                    Sign in
                  </button>
                </div>
              )}
            </div>
          </ExpandableSection>
        )}
      </div>
      
      {/* Login Modal - Rendu seulement si le modal d'inscription n'est pas ouvert */}
      {!isSignUpModalOpen && (
        <LoginModal
          isOpen={isLoginModalOpen}
          onClose={() => setIsLoginModalOpen(false)}
          onSwitchToSignUp={() => {
            setIsLoginModalOpen(false);
            // Délai pour permettre l'animation de sortie avant d'ouvrir l'autre modal
            setTimeout(() => {
              setIsSignUpModalOpen(true);
            }, 300);
          }}
        />
      )}
      
      {/* Sign Up Modal - Rendu seulement si le modal de connexion n'est pas ouvert */}
      {!isLoginModalOpen && (
        <SignUpModal
          isOpen={isSignUpModalOpen}
          onClose={() => setIsSignUpModalOpen(false)}
          onSwitchToLogin={() => {
            setIsSignUpModalOpen(false);
            // Délai pour permettre l'animation de sortie avant d'ouvrir l'autre modal
            setTimeout(() => {
              setIsLoginModalOpen(true);
            }, 300);
          }}
        />
      )}
      
      {/* Toggle button */}
      <div
        onClick={toggleSidebar}
        className={`${getThemeClasses().sidebar} ${getThemeClasses().text} p-2 h-10 flex items-center justify-center transition-all duration-300 absolute bottom-0 right-0 cursor-pointer ${getThemeClasses().hover}`}
      >
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d={isSidebarOpen ? 'M15 19l-7-7 7-7' : 'M9 5l7 7-7 7'}
          />
        </svg>
      </div>
    </div>
  </>
);
};

export default Sidebar;