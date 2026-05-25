import React, { useState, useRef, ChangeEvent, useEffect, useMemo, useCallback } from 'react';
import { Paginator } from '../ui/Paginator';
import { FolderOpen, Folder } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../auth/AuthProvider';
import LoginModal from '../auth/LoginModal';
import SignUpModal from '../auth/SignUpModal';
import { auth } from '../../lib/firebase';

type SidebarPanel = 'connector' | 'agents' | 'organisation' | 'history' | 'settings' | 'user' | null;
type OrganisationTab = 'organisation' | 'user' | 'permission';

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

interface RecentDocument {
  id: string;
  file_name: string;
  mime_type?: string | null;
  size_bytes?: number | null;
  status?: string | null;
  created_at?: string | null;
  processed_at?: string | null;
}

interface RecentDocumentContent {
  id: string;
  file_name: string;
  mime_type?: string | null;
  content_base64: string;
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
  onLogout?: () => void;
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

  constructor(baseURL = import.meta.env.VITE_API_URL || 'https://flexianalyse.com') {
    this.baseURL = baseURL;
  }

  private getOrCreateClientSessionId(): string {
    const key = 'bugmentor_session_id';
    const existing = localStorage.getItem(key);
    if (existing) {
      return existing;
    }

    const generated = `session_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(key, generated);
    return generated;
  }

  private async buildAuthHeaders(): Promise<Record<string, string>> {
    const headers: Record<string, string> = {
      'Session-ID': this.getOrCreateClientSessionId(),
    };

    const firebaseUser = auth.currentUser;
    if (firebaseUser) {
      const token = await firebaseUser.getIdToken();
      headers.Authorization = `Bearer ${token}`;
      headers['Session-ID'] = firebaseUser.uid;
    }

    return headers;
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

      const headers = await this.buildAuthHeaders();

      const response = await fetch(`${this.baseURL}/upload`, {
        method: 'POST',
        headers,
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

  async getRecentDocuments(limit = 5): Promise<RecentDocument[]> {
    try {
      const headers = await this.buildAuthHeaders();
      if (!headers.Authorization) {
        return [];
      }

      const response = await fetch(`${this.baseURL}/users/me/recent-documents?limit=${limit}`, {
        method: 'GET',
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return Array.isArray(data.documents) ? data.documents : [];
    } catch (error) {
      console.warn('Error fetching recent documents:', error);
      return [];
    }
  }

  async getRecentDocumentContent(documentId: string): Promise<RecentDocumentContent | null> {
    try {
      const headers = await this.buildAuthHeaders();
      if (!headers.Authorization) {
        return null;
      }

      const response = await fetch(`${this.baseURL}/users/me/documents/${documentId}/content`, {
        method: 'GET',
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.warn('Error fetching document content:', error);
      return null;
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
  addFileToSidebar,
  onLogout
}) => {
  const { language, setLanguage } = useLanguage();
  const { theme, setTheme } = useTheme();
  const { user, isAuthenticated, logout } = useAuth();
  const [files, setFiles] = useState<FileNode[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [modelStatus, setModelStatus] = useState<{ [key: string]: boolean }>({});
  const [, setIsLoadingModels] = useState<boolean>(true);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [recentDocuments, setRecentDocuments] = useState<RecentDocument[]>([]);
  
  const [searchHistory, setSearchHistory] = useState<string[]>([]);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState<boolean>(false);
  const [isSignUpModalOpen, setIsSignUpModalOpen] = useState<boolean>(false);
  
  // Icon rail active panel state
  const [activePanel, setActivePanel] = useState<SidebarPanel>(null);
  const [organisationTab, setOrganisationTab] = useState<OrganisationTab>('organisation');
  
  // Organisation management state
  const [orgs, setOrgs] = useState<{ id: string; name: string }[]>([]);
  const [departments, setDepartments] = useState<{ id: string; organization_id: string; name: string }[]>([]);
  const [roles, setRoles] = useState<{ id: string; organization_id: string; name: string }[]>([]);
  const [users, setUsers] = useState<{ id: string; email: string; full_name: string }[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>('');
  const [orgName, setOrgName] = useState('');
  const [deptName, setDeptName] = useState('');
  const [roleName, setRoleName] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [userPassword, setUserPassword] = useState('');
  const [userFullName, setUserFullName] = useState('');
  const [permRoleId, setPermRoleId] = useState('');
  const [permAction, setPermAction] = useState('read');
  const [permResource, setPermResource] = useState('chat');
  const [orgMsg, setOrgMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [deptEditId, setDeptEditId] = useState<string | null>(null);
  const [deptEditName, setDeptEditName] = useState('');

  const API = import.meta.env.VITE_API_URL || 'http://localhost:5000';
  const flyoutRef = useRef<HTMLDivElement>(null);
  const iconRailRef = useRef<HTMLDivElement>(null);
  
  // Load org data when panel opens
  useEffect(() => {
    if (activePanel === 'organisation') {
      fetch(`${API}/api/v2/organizations`).then(r => r.json()).then(d => { setOrgs(d.data || []); if (d.data?.[0]) setSelectedOrgId(d.data[0].id); }).catch(() => {});
      fetch(`${API}/api/v2/users`).then(r => r.json()).then(d => setUsers(d.data || [])).catch(() => {});
      fetch(`${API}/api/v2/roles`).then(r => r.json()).then(d => setRoles(d.data || [])).catch(() => {});
    }
  }, [activePanel]);

  // Auto-dismiss orgMsg after 5s
  useEffect(() => {
    if (!orgMsg) return;
    const t = setTimeout(() => setOrgMsg(null), 5000);
    return () => clearTimeout(t);
  }, [orgMsg]);

  // Load departments when org changes
  useEffect(() => {
    if (selectedOrgId) {
      fetch(`${API}/api/v2/departments?organization_id=${selectedOrgId}`).then(r => r.json()).then(d => setDepartments(d.data || [])).catch(() => {});
    }
  }, [selectedOrgId]);
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


  useEffect(() => {
    const loadRecentDocuments = async () => {
      if (!isAuthenticated || !user) {
        setRecentDocuments([]);
        return;
      }

      const docs = await apiService.getRecentDocuments(5);
      setRecentDocuments(docs);
    };

    loadRecentDocuments();
  }, [apiService, isAuthenticated, user]);


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

  const decodeBase64ToArrayBuffer = useCallback((base64: string): ArrayBuffer => {
    const binary = window.atob(base64);
    const buffer = new ArrayBuffer(binary.length);
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < binary.length; i += 1) {
      bytes[i] = binary.charCodeAt(i);
    }
    return buffer;
  }, []);

  const handleRecentDocumentClick = useCallback(async (doc: RecentDocument) => {

    setIsLoading(true);
    setError(null);

    try {
      const contentPayload = await apiService.getRecentDocumentContent(doc.id);
      if (!contentPayload?.content_base64) {
        throw new Error('Missing content payload');
      }

      const fileBuffer = decodeBase64ToArrayBuffer(contentPayload.content_base64);
      const fileName = contentPayload.file_name || doc.file_name;
      const mimeType = contentPayload.mime_type || doc.mime_type || 'application/octet-stream';
      const reconstructedFile = new File([fileBuffer], fileName, { type: mimeType });

      setFiles(prevFiles => {
        const allCurrentFiles = extractAllFiles(prevFiles);
        const alreadyExists = allCurrentFiles.some(
          existing => existing.name === reconstructedFile.name && existing.size === reconstructedFile.size,
        );
        if (alreadyExists) {
          return prevFiles;
        }
        return buildFileTree([...allCurrentFiles, reconstructedFile]);
      });

      await handleFileClick(reconstructedFile);
    } catch (error) {
      console.error('Error opening recent document:', error);
      setError('Failed to open recent document');
    } finally {
      setIsLoading(false);
    }
  }, [apiService, buildFileTree, decodeBase64ToArrayBuffer, extractAllFiles, handleFileClick]);

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


  // Handle icon click - toggle panel
  const handleIconClick = useCallback((panel: SidebarPanel) => {
    setActivePanel(prev => prev === panel ? null : panel);
  }, []);

  // Close flyout when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        activePanel &&
        flyoutRef.current && !flyoutRef.current.contains(event.target as Node) &&
        iconRailRef.current && !iconRailRef.current.contains(event.target as Node)
      ) {
        setActivePanel(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [activePanel]);

  // Render the flyout panel content based on active panel
  const renderFlyoutContent = () => {
    switch (activePanel) {
      case 'connector':
        return (
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Connector</h3>
            <div className="space-y-2">
              <button
                onClick={() => { fileInputRef.current?.click(); setActivePanel(null); }}
                className="w-full text-left px-3 py-2 rounded-md text-sm text-gray-700 hover:bg-purple-50 hover:text-purple-700 transition-colors"
              >
                <i className="bi bi-file-earmark-plus mr-2"></i>
                Import a file
              </button>
              <button
                onClick={() => { folderInputRef.current?.click(); setActivePanel(null); }}
                className="w-full text-left px-3 py-2 rounded-md text-sm text-gray-700 hover:bg-purple-50 hover:text-purple-700 transition-colors"
              >
                <i className="bi bi-folder-plus mr-2"></i>
                Import a folder
              </button>
              <hr className="my-2 border-gray-200" />
              <p className="text-xs text-gray-400 px-3">More connectors coming soon...</p>
            </div>
          </div>
        );
      case 'agents':
        return (
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Agents</h3>
            <p className="text-xs text-gray-500">No agents available yet.</p>
            <p className="text-xs text-gray-400 mt-2">AI agents will appear here as they become available.</p>
          </div>
        );
      case 'organisation':
        return (
          <div className="flex flex-col h-full">
            {/* Horizontal Tabs */}
            <div className="flex border-b border-gray-200 bg-gray-50">
              {[
                { id: 'organisation' as OrganisationTab, label: 'Organisation', icon: 'bi-buildings' },
                { id: 'user' as OrganisationTab, label: 'User', icon: 'bi-people' },
                { id: 'permission' as OrganisationTab, label: 'Permission', icon: 'bi-shield-lock' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setOrganisationTab(tab.id)}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2.5 text-xs font-semibold transition-colors ${
                    organisationTab === tab.id
                      ? 'text-purple-600 border-b-2 border-purple-600 bg-white'
                      : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  <i className={`bi ${tab.icon} text-sm`}></i>
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto p-4">
              {orgMsg && (
                <div className={`mb-3 px-3 py-2 rounded-md text-xs flex items-center justify-between gap-2 ${orgMsg.ok ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-600'}`}>
                  <span>{orgMsg.text}</span>
                  <button onClick={() => setOrgMsg(null)} className="flex-shrink-0 hover:opacity-70">
                    <i className="bi bi-x text-sm"></i>
                  </button>
                </div>
              )}
              {organisationTab === 'organisation' && (
                <div className="space-y-4">
                  <div>
                    <label className="text-[10px] font-semibold text-gray-500 uppercase">Active Organisation</label>
                    <select value={selectedOrgId} onChange={e => setSelectedOrgId(e.target.value)}
                      className="mt-1 w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 bg-white">
                      {orgs.length === 0 && <option value="">— No organisations —</option>}
                      {orgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
                    </select>
                  </div>
                  <div className="border border-gray-200 rounded-lg p-3">
                    <p className="text-xs font-semibold text-gray-700 mb-2">Create Organisation</p>
                    <input value={orgName} onChange={e => setOrgName(e.target.value)} placeholder="Organisation name"
                      className="w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2" />
                    <button onClick={async () => {
                      if (!orgName) return;
                      const r = await fetch(`${API}/api/v2/organizations`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:orgName}) });
                      const d = await r.json();
                      if (r.ok) { setOrgs(prev => [...prev, d]); setSelectedOrgId(d.id); setOrgName(''); setOrgMsg({text:'Organisation created!',ok:true}); }
                      else setOrgMsg({text:d.error||'Error',ok:false});
                    }} className="w-full px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700 transition-colors">
                      <i className="bi bi-plus-lg mr-1"></i>Create
                    </button>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Departments</h4>
                    <div className="flex gap-1 mb-2">
                      <input value={deptName} onChange={e => setDeptName(e.target.value)} placeholder="Department name"
                        className="flex-1 text-xs border border-gray-300 rounded-md px-2 py-1.5" />
                      <button onClick={async () => {
                        if (!deptName || !selectedOrgId) return;
                        const r = await fetch(`${API}/api/v2/departments`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:deptName, organization_id:selectedOrgId}) });
                        const d = await r.json();
                        if (r.ok) { setDepartments(prev => [...prev, d]); setDeptName(''); setOrgMsg({text:'Department created!',ok:true}); }
                        else setOrgMsg({text:d.error||'Error',ok:false});
                      }} className="px-3 py-1.5 text-xs font-medium text-purple-600 border border-purple-300 rounded-md hover:bg-purple-50 transition-colors">
                        <i className="bi bi-plus-lg"></i>
                      </button>
                    </div>
                    {departments.length === 0 ? (
                      <p className="text-xs text-gray-400 italic">No departments yet</p>
                    ) : (
                      <Paginator items={departments}>
                        {pageItems => (
                          <div className="space-y-1">
                            {pageItems.map(d => (
                              deptEditId === d.id ? (
                                <div key={d.id} className="flex items-center gap-1">
                                  <input value={deptEditName} onChange={e => setDeptEditName(e.target.value)}
                                    className="flex-1 text-xs border border-purple-300 rounded px-2 py-1" />
                                  <button onClick={async () => {
                                    const r = await fetch(`${API}/api/v2/departments/${d.id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:deptEditName}) });
                                    if (r.ok) { setDepartments(prev => prev.map(x => x.id === d.id ? {...x, name:deptEditName} : x)); setDeptEditId(null); setOrgMsg({text:'Department updated!',ok:true}); }
                                    else setOrgMsg({text:'Update failed',ok:false});
                                  }} className="text-green-600 hover:text-green-700 px-1"><i className="bi bi-check-lg text-xs"></i></button>
                                  <button onClick={() => setDeptEditId(null)} className="text-gray-400 hover:text-gray-600 px-1"><i className="bi bi-x text-xs"></i></button>
                                </div>
                              ) : (
                                <div key={d.id} className="flex items-center justify-between border border-gray-200 rounded px-2 py-1 group">
                                  <span className="text-xs text-gray-700">{d.name}</span>
                                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onClick={() => { setDeptEditId(d.id); setDeptEditName(d.name); }} className="text-gray-400 hover:text-purple-600"><i className="bi bi-pencil text-[10px]"></i></button>
                                    <button onClick={async () => {
                                      const r = await fetch(`${API}/api/v2/departments/${d.id}`, { method:'DELETE' });
                                      if (r.ok) { setDepartments(prev => prev.filter(x => x.id !== d.id)); setOrgMsg({text:'Department deleted',ok:true}); }
                                      else setOrgMsg({text:'Delete failed',ok:false});
                                    }} className="text-gray-400 hover:text-red-600"><i className="bi bi-trash text-[10px]"></i></button>
                                  </div>
                                </div>
                              )
                            ))}
                          </div>
                        )}
                      </Paginator>
                    )}
                  </div>
                </div>
              )}

              {organisationTab === 'user' && (
                <div className="space-y-4">
                  <div className="border border-gray-200 rounded-lg p-3">
                    <p className="text-xs font-semibold text-gray-700 mb-2">Create User</p>
                    <input value={userEmail} onChange={e => setUserEmail(e.target.value)} placeholder="Email"
                      className="w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2" />
                    <input value={userPassword} onChange={e => setUserPassword(e.target.value)} placeholder="Password" type="password"
                      className="w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2" />
                    <input value={userFullName} onChange={e => setUserFullName(e.target.value)} placeholder="Full name"
                      className="w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2" />
                    <button onClick={async () => {
                      if (!userEmail || !userPassword) return;
                      const r = await fetch(`${API}/api/v2/users`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email:userEmail, password:userPassword, full_name:userFullName}) });
                      const d = await r.json();
                      if (r.ok) { setUsers(prev => [...prev, d]); setUserEmail(''); setUserPassword(''); setUserFullName(''); setOrgMsg({text:'User created!',ok:true}); }
                      else setOrgMsg({text:d.error||'Error',ok:false});
                    }} className="w-full px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700">
                      <i className="bi bi-person-plus mr-1"></i>Create User
                    </button>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Users ({users.length})</h4>
                    {users.length === 0 ? (
                      <p className="text-xs text-gray-400 italic">No users yet</p>
                    ) : (
                      <div className="space-y-1">
                        {users.map(u => (
                          <div key={u.id} className="flex items-center gap-2 border border-gray-200 rounded-lg px-3 py-2">
                            <div className="w-6 h-6 rounded-full bg-purple-100 flex items-center justify-center">
                              <i className="bi bi-person text-purple-600 text-[10px]"></i>
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-xs font-medium text-gray-800 truncate">{u.full_name || u.email}</p>
                              <p className="text-[10px] text-gray-500 truncate">{u.email}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {organisationTab === 'permission' && (
                <div className="space-y-4">
                  <div className="border border-gray-200 rounded-lg p-3">
                    <p className="text-xs font-semibold text-gray-700 mb-2">Create Role</p>
                    <input value={roleName} onChange={e => setRoleName(e.target.value)} placeholder="Role name"
                      className="w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2" />
                    <button onClick={async () => {
                      if (!roleName || !selectedOrgId) return;
                      const r = await fetch(`${API}/api/v2/roles`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:roleName, organization_id:selectedOrgId}) });
                      const d = await r.json();
                      if (r.ok) { setRoles(prev => [...prev, d]); setRoleName(''); setOrgMsg({text:'Role created!',ok:true}); }
                      else setOrgMsg({text:d.error||'Error',ok:false});
                    }} className="w-full px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700">
                      <i className="bi bi-plus-lg mr-1"></i>Create Role
                    </button>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">Roles ({roles.length})</h4>
                    {roles.length === 0 ? (
                      <p className="text-xs text-gray-400 italic">No roles yet</p>
                    ) : (
                      <div className="space-y-1">
                        {roles.map(r => (
                          <div key={r.id} className="text-xs text-gray-700 border border-gray-200 rounded px-2 py-1">{r.name}</div>
                        ))}
                      </div>
                    )}
                  </div>
                  <hr className="border-gray-200" />
                  <div className="border border-gray-200 rounded-lg p-3">
                    <p className="text-xs font-semibold text-gray-700 mb-2">Add Permission</p>
                    <select value={permRoleId} onChange={e => setPermRoleId(e.target.value)}
                      className="w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2 bg-white">
                      <option value="">— Select role —</option>
                      {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                    <select value={permAction} onChange={e => setPermAction(e.target.value)}
                      className="w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2 bg-white">
                      {['read','write','execute','delete'].map(a => <option key={a} value={a}>{a}</option>)}
                    </select>
                    <select value={permResource} onChange={e => setPermResource(e.target.value)}
                      className="w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2 bg-white">
                      {['chat','agent','connector','reporting','organisation'].map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                    <button onClick={async () => {
                      if (!permRoleId) return;
                      const r = await fetch(`${API}/api/v2/permissions`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({role_id:permRoleId, action:permAction, resource:permResource}) });
                      const d = await r.json();
                      if (r.ok) setOrgMsg({text:'Permission added!',ok:true});
                      else setOrgMsg({text:d.error||'Error',ok:false});
                    }} className="w-full px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700">
                      <i className="bi bi-plus-lg mr-1"></i>Add Permission
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      case 'history':
        return (
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">History</h3>
            <div className="max-h-64 overflow-y-auto">
              {searchHistory.length > 0 ? (
                <div className="space-y-1">
                  <p className="text-xs text-gray-400 mb-2">Recent searches</p>
                  {searchHistory.map((query, index) => (
                    <button
                      key={index}
                      className="w-full text-left px-2 py-1.5 rounded text-xs text-gray-600 hover:bg-purple-50 hover:text-purple-700 transition-colors truncate"
                      title={query}
                    >
                      <i className="bi bi-clock-history mr-2 text-gray-400"></i>
                      {query}
                    </button>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-500">No history yet.</p>
              )}
              {files.length > 0 && (
                <>
                  <hr className="my-3 border-gray-200" />
                  <p className="text-xs text-gray-400 mb-2">Open files</p>
                  <ul className="space-y-1">
                    {renderFileTree(files)}
                  </ul>
                </>
              )}
              {recentDocuments.length > 0 && (
                <>
                  <hr className="my-3 border-gray-200" />
                  <p className="text-xs text-gray-400 mb-2">Recent documents</p>
                  {recentDocuments.map((doc) => (
                    <button
                      key={doc.id}
                      onClick={() => { handleRecentDocumentClick(doc); setActivePanel(null); }}
                      className="w-full text-left px-2 py-1.5 rounded text-xs text-blue-600 hover:bg-purple-50 hover:text-purple-700 transition-colors truncate"
                      title={doc.file_name}
                    >
                      <i className="bi bi-file-earmark mr-2"></i>
                      {doc.file_name}
                    </button>
                  ))}
                </>
              )}
            </div>
          </div>
        );
      case 'settings':
        return (
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Settings</h3>
            <div className="space-y-4">
              {/* Theme selection */}
              <div>
                <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">Theme</p>
                <div className="space-y-1">
                  {[
                    { value: 'white' as const, label: 'White', color: 'bg-white border border-gray-300' },
                    { value: 'dark' as const, label: 'Dark', color: 'bg-gray-900' },
                    { value: 'dark-blue' as const, label: 'Dark Blue', color: 'bg-blue-950' },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setTheme(opt.value)}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                        theme === opt.value
                          ? 'bg-purple-50 text-purple-700 font-medium'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <div className={`w-4 h-4 rounded-full ${opt.color} flex-shrink-0`}></div>
                      {opt.label}
                      {theme === opt.value && <i className="bi bi-check2 ml-auto text-purple-600"></i>}
                    </button>
                  ))}
                </div>
              </div>

              <hr className="border-gray-200" />

              {/* Language selection */}
              <div>
                <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">Language</p>
                <div className="space-y-1">
                  {[
                    { code: 'en' as const, name: 'English', flag: '\uD83C\uDDEC\uD83C\uDDE7' },
                    { code: 'fr' as const, name: 'Fran\u00e7ais', flag: '\uD83C\uDDEB\uD83C\uDDF7' },
                    { code: 'es' as const, name: 'Espa\u00f1ol', flag: '\uD83C\uDDEA\uD83C\uDDF8' },
                  ].map((lang) => (
                    <button
                      key={lang.code}
                      onClick={() => setLanguage(lang.code)}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                        language === lang.code
                          ? 'bg-purple-50 text-purple-700 font-medium'
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                    >
                      <span>{lang.flag}</span>
                      {lang.name}
                      {language === lang.code && <i className="bi bi-check2 ml-auto text-purple-600"></i>}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        );
      case 'user':
        return (
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Account</h3>
            {isAuthenticated && user ? (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  {user.avatar ? (
                    <img
                      src={user.avatar}
                      alt={user.name || user.email}
                      className="w-8 h-8 rounded-full object-cover border-2 border-purple-400"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center">
                      <i className="bi bi-person-fill text-purple-600"></i>
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-800 truncate">
                      {user.name || user.email}
                    </div>
                    {user.name && (
                      <div className="text-xs text-gray-500 truncate">{user.email}</div>
                    )}
                  </div>
                </div>
                {user.plan && (
                  <p className="text-xs text-gray-500">
                    Plan: <span className="font-medium capitalize">{user.plan}</span>
                  </p>
                )}
                <button
                  onClick={() => {
                    setFiles([]);
                    setPendingFiles([]);
                    setRecentDocuments([]);
                    setError(null);
                    setActivePanel(null);
                    if (onLogout) onLogout();
                    else logout();
                  }}
                  className="w-full text-left px-3 py-2 rounded-md text-xs text-red-600 hover:bg-red-50 transition-colors"
                >
                  <i className="bi bi-box-arrow-left mr-2"></i>
                  Sign out
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-gray-500">Not signed in</p>
                <button
                  onClick={() => { setIsLoginModalOpen(true); setActivePanel(null); }}
                  className="w-full px-3 py-2 rounded-md text-sm font-medium transition-colors bg-purple-600 text-white hover:bg-purple-700"
                >
                  Sign in
                </button>
              </div>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
  <>
    {/* Hidden file inputs */}
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

    {/* Mobile Hamburger Menu */}
    <div className="lg:hidden">
      <button
        onClick={toggleSidebar}
        className="fixed top-4 left-4 z-50 bg-white shadow-lg rounded-md p-2 text-gray-700 hover:text-purple-500 transition-colors"
      >
        <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-30" onClick={toggleSidebar} />
      )}

      {/* Mobile Sidebar - same icon rail design */}
      {isSidebarOpen && (
        <div className="fixed inset-y-0 left-0 z-40 flex">
          {/* Icon rail */}
          <div className="w-16 bg-gray-100 border-r border-gray-200 flex flex-col items-center py-4 h-full">
            {/* Logo */}
            <div className="mb-6">
              <div className="w-9 h-9 bg-gradient-to-br from-purple-600 to-blue-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">F</span>
              </div>
            </div>

            {/* Nav icons */}
            <nav className="flex-1 flex flex-col items-center gap-1">
              {[
                { id: 'connector' as SidebarPanel, icon: 'bi-command', label: 'Connector' },
                { id: 'agents' as SidebarPanel, icon: 'bi-outlet', label: 'Agents' },
                { id: 'organisation' as SidebarPanel, icon: 'bi-buildings', label: 'Organisation' },
                { id: 'history' as SidebarPanel, icon: 'bi-chat-right', label: 'History' },
              ].map((item) => (
                <button
                  key={item.id}
                  onClick={() => handleIconClick(item.id)}
                  className={`relative w-12 flex flex-col items-center justify-center py-2 rounded-md transition-colors group ${
                    activePanel === item.id
                      ? 'text-purple-600 bg-purple-50'
                      : 'text-black hover:text-purple-500 hover:bg-gray-200'
                  }`}
                >
                  {activePanel === item.id && (
                    <div className="absolute -right-2 top-1 bottom-1 w-0.5 bg-purple-600 rounded-l"></div>
                  )}
                  <i className={`bi ${item.icon} text-lg font-bold`}></i>
                  <span className="text-[9px] mt-0.5 leading-tight font-bold">{item.label}</span>
                </button>
              ))}
            </nav>

            {/* Settings icon */}
            <button
              onClick={() => handleIconClick('settings')}
              className={`relative w-12 flex flex-col items-center justify-center py-2 rounded-md transition-colors mb-1 ${
                activePanel === 'settings'
                  ? 'text-purple-600 bg-purple-50'
                  : 'text-black hover:text-purple-500 hover:bg-gray-200'
              }`}
            >
              {activePanel === 'settings' && (
                <div className="absolute -right-2 top-1 bottom-1 w-0.5 bg-purple-600 rounded-l"></div>
              )}
              <i className="bi bi-gear text-lg font-bold"></i>
              <span className="text-[9px] mt-0.5 leading-tight font-bold">Settings</span>
            </button>

            {/* User icon at bottom */}
            <button
              onClick={() => handleIconClick('user')}
              className={`relative w-12 flex flex-col items-center justify-center py-2 rounded-md transition-colors ${
                activePanel === 'user'
                  ? 'text-purple-600 bg-purple-50'
                  : 'text-black hover:text-purple-500 hover:bg-gray-200'
              }`}
            >
              {activePanel === 'user' && (
                <div className="absolute -right-2 top-1 bottom-1 w-0.5 bg-purple-600 rounded-l"></div>
              )}
              <i className="bi bi-person text-lg font-bold"></i>
              <span className="text-[9px] mt-0.5 leading-tight font-bold">Account</span>
            </button>
          </div>

          {/* Mobile flyout panel */}
          {activePanel && (
            <div className={`${activePanel === 'organisation' ? 'w-80' : 'w-56'} bg-white border-r border-gray-200 shadow-lg h-full overflow-y-auto`}>
              {renderFlyoutContent()}
            </div>
          )}
        </div>
      )}
    </div>

    {/* Desktop Sidebar - Icon Rail + Flyout */}
    <div className="hidden lg:flex h-screen" ref={iconRailRef}>
      {/* Icon Rail */}
      <div className="w-16 bg-gray-100 border-r border-gray-200 flex flex-col items-center py-4 h-full relative">
        {/* Logo */}
        <div className="mb-8">
          <div className="w-9 h-9 bg-gradient-to-br from-purple-600 to-blue-500 rounded-lg flex items-center justify-center shadow-sm">
            <span className="text-white font-bold text-sm">F</span>
          </div>
        </div>

        {/* Navigation icons */}
        <nav className="flex-1 flex flex-col items-center gap-1">
          {[
            { id: 'connector' as SidebarPanel, icon: 'bi-command', label: 'Connector' },
            { id: 'agents' as SidebarPanel, icon: 'bi-outlet', label: 'Agents' },
            { id: 'organisation' as SidebarPanel, icon: 'bi-buildings', label: 'Organisation' },
            { id: 'history' as SidebarPanel, icon: 'bi-chat-right', label: 'History' },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => handleIconClick(item.id)}
              className={`relative w-12 flex flex-col items-center justify-center py-2.5 rounded-md transition-all duration-200 group ${
                activePanel === item.id
                  ? 'text-purple-600 bg-purple-50'
                  : 'text-black hover:text-purple-500 hover:bg-gray-200'
              }`}
              title={item.label}
            >
              {/* Purple right border indicator */}
              {activePanel === item.id && (
                <div className="absolute -right-2 top-1 bottom-1 w-0.5 bg-purple-600 rounded-l"></div>
              )}
              <i className={`bi ${item.icon} text-lg font-bold`}></i>
              <span className="text-[9px] mt-0.5 leading-tight font-bold">{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Settings icon */}
        <button
          onClick={() => handleIconClick('settings')}
          className={`relative w-12 flex flex-col items-center justify-center py-2.5 rounded-md transition-all duration-200 mb-1 ${
            activePanel === 'settings'
              ? 'text-purple-600 bg-purple-50'
              : 'text-black hover:text-purple-500 hover:bg-gray-200'
          }`}
          title="Settings"
        >
          {activePanel === 'settings' && (
            <div className="absolute -right-2 top-1 bottom-1 w-0.5 bg-purple-600 rounded-l"></div>
          )}
          <i className="bi bi-gear text-lg font-bold"></i>
          <span className="text-[9px] mt-0.5 leading-tight font-bold">Settings</span>
        </button>

        {/* User icon at bottom */}
        <button
          onClick={() => handleIconClick('user')}
          className={`relative w-12 flex flex-col items-center justify-center py-2.5 rounded-md transition-all duration-200 ${
            activePanel === 'user'
              ? 'text-purple-600 bg-purple-50'
              : 'text-black hover:text-purple-500 hover:bg-gray-200'
          }`}
          title="Account"
        >
          {activePanel === 'user' && (
            <div className="absolute -right-2 top-1 bottom-1 w-0.5 bg-purple-600 rounded-l"></div>
          )}
          <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center overflow-hidden">
            {isAuthenticated && user?.avatar ? (
              <img src={user.avatar} alt="" className="w-full h-full object-cover" />
            ) : (
              <i className="bi bi-person text-black font-bold"></i>
            )}
          </div>
        </button>

        {/* Error indicator */}
        {error && (
          <div className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full animate-pulse" title={error}></div>
        )}

        {/* Loading indicator */}
        {isLoading && (
          <div className="absolute top-2 left-2 w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
        )}
      </div>

      {/* Flyout Panel */}
      {activePanel && (
        <div
          ref={flyoutRef}
          className={`${activePanel === 'organisation' ? 'w-80' : 'w-56'} bg-white border-r border-gray-200 shadow-sm h-full overflow-y-auto animate-in slide-in-from-left-2 duration-200`}
        >
          {renderFlyoutContent()}
        </div>
      )}
    </div>

    {/* Login Modal */}
    {!isSignUpModalOpen && (
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onSwitchToSignUp={() => {
          setIsLoginModalOpen(false);
          setTimeout(() => setIsSignUpModalOpen(true), 300);
        }}
      />
    )}
    
    {/* Sign Up Modal */}
    {!isLoginModalOpen && (
      <SignUpModal
        isOpen={isSignUpModalOpen}
        onClose={() => setIsSignUpModalOpen(false)}
        onSwitchToLogin={() => {
          setIsSignUpModalOpen(false);
          setTimeout(() => setIsLoginModalOpen(true), 300);
        }}
      />
    )}
  </>);
};

export default Sidebar;