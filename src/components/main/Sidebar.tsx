import React, { useState, useRef, ChangeEvent, useEffect, useMemo, useCallback } from 'react';
import { Paginator } from '../ui/Paginator';
import { FlexiGrid, type FlexiGridColumn } from '../ui/FlexiGrid';
import { FlexiMultiReferentiel } from '../ui/FlexiMultiReferentiel';
import { LanguageSwitcher } from '../ui/LanguageSwitcher';
import { FolderOpen, Folder } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../auth/AuthProvider';
import LoginModal from '../auth/LoginModal';
import SignUpModal from '../auth/SignUpModal';
import { auth } from '../../lib/firebase';

type SidebarPanel = 'connector' | 'agents' | 'organisation' | 'history' | 'settings' | 'user' | null;
type OrganisationTab = 'organisation' | 'user' | 'permission';
type ConnectorType = 'database' | 'google_drive' | 'sharepoint' | 'dropbox' | null;

const CONNECTOR_FIELDS: Record<string, { key: string; label: string; type?: string; placeholder?: string }[]> = {
  database: [
    { key: 'name',           label: 'Connection Name', placeholder: 'My Database' },
    { key: 'connection_url', label: 'Connection URL',   placeholder: 'postgresql://user:pass@host:5432/db' },
  ],
  google_drive: [
    { key: 'name',      label: 'Connection Name',          placeholder: 'My Google Drive' },
    { key: 'folder_id', label: 'Root Folder ID (optional)', placeholder: '1BxiMVs0XRA5…' },
  ],
  sharepoint: [
    { key: 'name',       label: 'Connection Name', placeholder: 'My SharePoint' },
    { key: 'tenant_id',  label: 'Tenant ID',        placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' },
    { key: 'site_url',   label: 'Site URL',         placeholder: 'https://company.sharepoint.com/sites/…' },
  ],
  dropbox: [
    { key: 'name', label: 'Connection Name', placeholder: 'My Dropbox' },
  ],
};

const OAUTH_CONNECTORS: ReadonlySet<string> = new Set(['google_drive', 'sharepoint', 'dropbox']);

const CONNECTOR_META: Record<string, { title: string; apiType: string }> = {
  database:     { title: 'Database (SQL)', apiType: 'sql' },
  google_drive: { title: 'Google Drive',   apiType: 'google_drive' },
  sharepoint:   { title: 'SharePoint',     apiType: 'sharepoint' },
  dropbox:      { title: 'Dropbox',        apiType: 'dropbox' },
};

const PERM_RESOURCES = ['organizations', 'users', 'memberships', 'departments', 'teams', 'roles', 'permissions', 'connectors', 'documents', 'cases', 'analyses', 'prompts', 'ai_agents', 'audit_logs', 'settings', 'billing'] as const;

const RESOURCE_ACTIONS: Record<string, readonly string[]> = {
  organizations: ['read', 'create', 'update', 'manage'],
  users:         ['read', 'create', 'update', 'delete', 'manage', 'export'],
  memberships:   ['read', 'create', 'update', 'delete', 'assign', 'manage'],
  departments:   ['read', 'create', 'update', 'delete', 'assign', 'manage'],
  teams:         ['read', 'create', 'update', 'delete', 'assign', 'manage'],
  roles:         ['read', 'create', 'update', 'delete', 'assign', 'manage'],
  permissions:   ['read', 'assign'],
  connectors:    ['read', 'create', 'update', 'delete', 'manage', 'sync', 'authorize'],
  documents:     ['read', 'create', 'update', 'delete', 'assign', 'manage', 'export'],
  cases:         ['read', 'create', 'update', 'delete', 'assign', 'manage', 'export'],
  analyses:      ['read', 'create', 'delete', 'execute', 'export'],
  prompts:       ['read', 'create', 'update', 'delete', 'execute', 'manage'],
  ai_agents:     ['read', 'create', 'update', 'delete', 'execute', 'manage'],
  audit_logs:    ['read', 'export'],
  settings:      ['read', 'update', 'manage'],
  billing:       ['read', 'update', 'manage', 'export'],
};

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
  const { language, setLanguage, t } = useLanguage();
  const { theme, setTheme } = useTheme();
  const { user, isAuthenticated, logout } = useAuth();

  // Helper function for theme-aware tab colors
  const getTabColors = () => {
    switch (theme) {
      case 'dark':
        return {
          borderColor: '#4b5563',
          bgColor: '#374151',
          hoverBgColor: '#4b5563',
          textColor: '#d1d5db',
          hoverTextColor: '#f3f4f6',
        };
      case 'dark-blue':
        return {
          borderColor: '#3b82f6',
          bgColor: '#1e3a8a',
          hoverBgColor: '#1e40af',
          textColor: '#c7d2fe',
          hoverTextColor: '#e0e7ff',
        };
      default: // white
        return {
          borderColor: '#e5e7eb',
          bgColor: '#f9fafb',
          hoverBgColor: '#f3f4f6',
          textColor: '#6b7280',
          hoverTextColor: '#374151',
        };
    }
  };

  const tabColors = getTabColors();

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

  // Connector panel state
  const [activeConnectorType, setActiveConnectorType] = useState<ConnectorType>(null);
  const [connectorForm, setConnectorForm] = useState<Record<string, string>>({});
  const [connectorMsg, setConnectorMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [connectorSaving, setConnectorSaving] = useState(false);
  
  // Organisation management state
  const [orgs, setOrgs] = useState<{ id: string; name: string }[]>([]);
  const [departments, setDepartments] = useState<{ id: string; organization_id: string; name: string }[]>([]);
  const [roles, setRoles] = useState<{ id: string; organization_id: string; name: string }[]>([]);
  const [users, setUsers] = useState<{ id: string; email: string; full_name: string; role_id: string }[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string>('');
  const [orgName, setOrgName] = useState('');
  const [deptName, setDeptName] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [userRoleId, setUserRoleId] = useState('');
  const [userPassword, setUserPassword] = useState('');
  const [userFullName, setUserFullName] = useState('');
  const [permRoleId, setPermRoleId] = useState('');
  const [permActions, setPermActions] = useState<string[]>([]);
  const [permResource, setPermResource] = useState('chat');
  const [permValidFrom, setPermValidFrom] = useState('');
  const [permValidTo, setPermValidTo] = useState('');
  const [permissions, setPermissions] = useState<{ id: string; action: string; resource: string; role_id?: string; role_name?: string }[]>([]);
  const [orgMsg, setOrgMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [deptEditId, setDeptEditId] = useState<string | null>(null);
  const [deptEditName, setDeptEditName] = useState('');
  const [orgEditId, setOrgEditId] = useState<string | null>(null);
  const [orgEditName, setOrgEditName] = useState('');

  const permissionColumns: FlexiGridColumn<{ id: string; action: string; resource: string; role_id?: string; role_name?: string }>[] = useMemo(() => [
    {
      key: 'role_name',
      header: 'Role',
      render: (item) => <span>{item.role_name || roles.find(r => r.id === item.role_id)?.name || 'N/A'}</span>,
    },
    {
      key: 'resource',
      header: 'Resource',
      render: (item) => <span>{item.resource}</span>,
    },
    {
      key: 'action',
      header: 'Actions',
      render: (item) => <span className="text-purple-600 font-medium">{item.action}</span>,
    },
  ], [roles]);

  const roleColumns: FlexiGridColumn<{ id: string; organization_id: string; name: string }>[] = useMemo(() => [
    {
      key: 'name',
      header: 'Name',
      render: (item, isEditing, editState, setEditState) =>
        isEditing ? (
          <input value={editState.name || ''} onChange={e => setEditState({ ...editState, name: e.target.value })}
            className="w-full border border-purple-300 rounded px-1 py-0.5 text-xs" />
        ) : (
          <span>{item.name}</span>
        ),
    },
    {
      key: 'organization_id',
      header: 'Organisation',
      render: (item, isEditing, editState, setEditState) =>
        isEditing ? (
          <select value={editState.organization_id || ''} onChange={e => setEditState({ ...editState, organization_id: e.target.value })}
            className="w-full border border-purple-300 rounded px-1 py-0.5 text-xs bg-white">
            {orgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
          </select>
        ) : (
          <span>{orgs.find(o => o.id === item.organization_id)?.name || item.organization_id}</span>
        ),
    },
  ], [orgs]);

  const API =import.meta.env.VITE_API_URL || 'https://flexianalyse.com'; // 'http://localhost:5000';
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

  // Load permissions when permission tab opens
  useEffect(() => {
    if (activePanel === 'organisation' && organisationTab === 'permission') {
      fetch(`${API}/api/v2/permissions`).then(r => r.json()).then(d => setPermissions(d.data || [])).catch(() => {});
    }
  }, [activePanel, organisationTab, API]);

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
    if (panel !== 'connector') { setActiveConnectorType(null); setConnectorForm({}); setConnectorMsg(null); }
  }, []);

  const handleSaveConnector = useCallback(async () => {
    if (!activeConnectorType) return;
    setConnectorSaving(true);
    setConnectorMsg(null);

    try {
      if (!selectedOrgId) throw new Error('Select an organisation first (Organisation tab)');

      const apiType = CONNECTOR_META[activeConnectorType].apiType;

      // Construit le body selon le type de connector
      const body: Record<string, string | undefined> = {
        type: apiType,
        organization_id: selectedOrgId,
        name: connectorForm.name || `New ${activeConnectorType}`,
      };

      // Token selon le type
      if (activeConnectorType === 'database') {
        if (!connectorForm.connection_url) throw new Error('Connection URL is required');
        body.token = connectorForm.connection_url;

      } else if (activeConnectorType === 'sharepoint') {
        if (!connectorForm.tenant_id) throw new Error('Tenant ID is required');
        if (!connectorForm.site_url) throw new Error('Site URL is required');
        body.token = JSON.stringify({
          tenant_id: connectorForm.tenant_id,
          site_url: connectorForm.site_url,
        });

      } else if (activeConnectorType === 'google_drive') {
        // Google Drive = OAuth, pas besoin de token manuel
        body.token = connectorForm.folder_id || undefined;
      }

      // Sauvegarde le connector
      const r = await fetch(`${API}/api/v2/connectors`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Organization-Id': selectedOrgId
        },
        body: JSON.stringify(body),
      });

      if (!r.ok) throw new Error((await r.json())?.error || r.statusText);
      const saved = await r.json();

      // OAuth flow pour Google Drive, SharePoint et Dropbox
      if (OAUTH_CONNECTORS.has(activeConnectorType)) {
        const provider = activeConnectorType === 'google_drive' ? 'Google' : activeConnectorType === 'dropbox' ? 'Dropbox' : 'Microsoft';
        setConnectorMsg({ text: `Connector saved — opening ${provider} authorization…`, ok: true });
        setTimeout(() => {
          window.open(`${API}/auth/${activeConnectorType}?connector_id=${saved.id}`, '_blank');
        }, 400);
      } else {
        setConnectorMsg({ text: 'Connection saved successfully!', ok: true });
        setTimeout(() => {
          setActiveConnectorType(null);
          setConnectorForm({});
          setConnectorMsg(null);
        }, 2000);
      }

    } catch (e: any) {
      setConnectorMsg({ text: `Error: ${e.message || e}`, ok: false });
    } finally {
      setConnectorSaving(false);
    }
  }, [activeConnectorType, connectorForm, API, selectedOrgId]);

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

  const renderConnectorForm = () => {
    if (!activeConnectorType) return null;
    return (
      <div className="p-4 flex flex-col gap-3 h-full">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide font-medium">New connection</p>
            <h4 className="text-sm font-semibold text-gray-800">{CONNECTOR_META[activeConnectorType].title}</h4>
          </div>
          <button
            onClick={() => { setActiveConnectorType(null); setConnectorForm({}); setConnectorMsg(null); }}
            className="text-gray-400 hover:text-gray-600 transition-colors p-1 rounded hover:bg-gray-100"
          >
            <i className="bi bi-x text-lg"></i>
          </button>
        </div>

        <div className="flex flex-col gap-2.5 flex-1">
          {/* OAuth info banner */}
          {OAUTH_CONNECTORS.has(activeConnectorType) && (
            <div className="flex items-start gap-2 bg-blue-50 border border-blue-200 rounded-lg px-2.5 py-2">
              <i className="bi bi-shield-lock text-blue-500 text-sm mt-0.5 flex-shrink-0"></i>
              <p className="text-[10px] text-blue-700 leading-snug">
                Authorization happens via{' '}
                {activeConnectorType === 'google_drive' ? 'Google OAuth' : activeConnectorType === 'dropbox' ? 'Dropbox OAuth' : 'Microsoft OAuth'}.
                Fill in the name{activeConnectorType === 'sharepoint' ? ' and tenant details' : ''}, then click <strong>Connect</strong>.
              </p>
            </div>
          )}

          {CONNECTOR_FIELDS[activeConnectorType].map(field => (
            <div key={field.key}>
              <label className="block text-[10px] text-gray-500 mb-1 font-medium uppercase tracking-wide">{field.label}</label>
              <input
                type={field.type || 'text'}
                placeholder={field.placeholder}
                value={connectorForm[field.key] || ''}
                onChange={e => setConnectorForm(f => ({ ...f, [field.key]: e.target.value }))}
                className="w-full text-xs border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-200 placeholder:text-gray-300"
              />
            </div>
          ))}
        </div>

        {connectorMsg && (
          <p className={`text-[10px] font-medium ${connectorMsg.ok ? 'text-green-600' : 'text-red-500'}`}>
            {connectorMsg.ok ? '✓' : '✗'} {connectorMsg.text}
          </p>
        )}

        <button
          disabled={connectorSaving}
          onClick={handleSaveConnector}
          className="w-full text-xs px-3 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 font-medium transition-colors flex items-center justify-center gap-1.5"
        >
          {connectorSaving ? (
            'Saving…'
          ) : activeConnectorType && OAUTH_CONNECTORS.has(activeConnectorType) ? (
            <>
              <i className="bi bi-box-arrow-up-right text-[11px]"></i>
              Connect with {activeConnectorType === 'google_drive' ? 'Google' : activeConnectorType === 'dropbox' ? 'Dropbox' : 'Microsoft'}
            </>
          ) : (
            'Save Connection'
          )}
        </button>
      </div>
    );
  };

  // Render the flyout panel content based on active panel
  const renderFlyoutContent = () => {
    switch (activePanel) {
      case 'connector':
        return (
          <div className="p-4 flex flex-col gap-3">
            <h3 className="text-sm font-semibold text-gray-800">Connectors</h3>
            <div className="flex flex-wrap gap-1">
              {([
                {
                  type: 'database' as ConnectorType,
                  label: 'Database',
                  icon: (
                    <div className="w-7 h-7 rounded-md flex items-center justify-center bg-blue-100">
                      <i className="bi bi-database text-blue-600 text-sm"></i>
                    </div>
                  ),
                },
                {
                  type: 'google_drive' as ConnectorType,
                  label: 'Google Drive',
                  icon: (
                    <svg viewBox="0 0 87.3 78" className="w-7 h-7 p-0.5">
                      <path d="M6.6 66.85l3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8H0a15.6 15.6 0 003.3 8.05l3.3-5.7v11.5z" fill="#0066da"/>
                      <path d="M43.65 25L29.9 1.2c-1.35.8-2.5 1.9-3.3 3.3L.95 52.3A15.6 15.6 0 000 57H27.5L43.65 25z" fill="#00ac47"/>
                      <path d="M73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25A15.6 15.6 0 0087.3 57H59.75l5.85 11.5L73.55 76.8z" fill="#ea4335"/>
                      <path d="M43.65 25L57.4 1.2A15.4 15.4 0 0052.1 0H35.2a15.4 15.4 0 00-5.3.95L43.65 25z" fill="#00832d"/>
                      <path d="M59.75 57H27.5L13.75 80.8c1.35.8 2.9 1.2 4.5 1.2h50.6a15.4 15.4 0 004.5-1.2L59.75 57z" fill="#2684fc"/>
                      <path d="M73.4 28.5l-13.1-22.7c-.8-1.4-1.95-2.5-3.3-3.3L43.65 25 59.75 57h27.45a15.7 15.7 0 00-1.5-6.35L73.4 28.5z" fill="#ffba00"/>
                    </svg>
                  ),
                },
                {
                  type: 'sharepoint' as ConnectorType,
                  label: 'SharePoint',
                  icon: (
                    <div className="w-7 h-7 rounded-md flex items-center justify-center bg-[#038387]">
                      <svg viewBox="0 0 24 24" className="w-4 h-4 fill-white">
                        <path d="M10 2a6 6 0 100 12 6 6 0 000-12zm0 10a4 4 0 110-8 4 4 0 010 8zm7 2a4 4 0 100 8 4 4 0 000-8zm-7 2H4a2 2 0 00-2 2v2h10v-2a2 2 0 00-2-2z"/>
                      </svg>
                    </div>
                  ),
                },
                {
                  type: 'dropbox' as ConnectorType,
                  label: 'Dropbox',
                  icon: (
                    <div className="w-7 h-7 rounded-md flex items-center justify-center bg-[#0061FF]">
                      <svg viewBox="0 0 24 24" className="w-4 h-4 fill-white">
                        <path d="M6 2L0 6l6 4-6 4 6 4 6-4-6-4 6-4-6-4zM18 2l-6 4 6 4-6 4 6 4 6-4-6-4 6-4-6-4zM6 16.5L12 20l6-3.5-6-4-6 4z"/>
                      </svg>
                    </div>
                  ),
                },
              ] as { type: ConnectorType; label: string; icon: React.ReactNode }[]).map(({ type, label, icon }) => (
                <button
                  key={type!}
                  title={label}
                  onClick={() => {
                    setActiveConnectorType(prev => prev === type ? null : type);
                    setConnectorForm({});
                    setConnectorMsg(null);
                  }}
                  className={`w-10 h-10 flex items-center justify-center rounded-lg transition-all ${
                    activeConnectorType === type
                      ? 'bg-purple-100 ring-2 ring-purple-400 ring-offset-1'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  {icon}
                </button>
              ))}
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
            <div className="flex border-b transition-colors" style={{ borderColor: tabColors.borderColor, backgroundColor: tabColors.bgColor }}>
              {[
                { id: 'organisation' as OrganisationTab, label: t('org.tab.organisation'), icon: 'bi-buildings' },
                { id: 'user' as OrganisationTab, label: t('org.tab.user'), icon: 'bi-people' },
                { id: 'permission' as OrganisationTab, label: t('org.tab.permission'), icon: 'bi-shield-lock' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setOrganisationTab(tab.id)}
                  className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-2.5 text-xs font-semibold transition-colors`}
                  style={{
                    color: organisationTab === tab.id ? '#a855f7' : (theme !== 'white' ? '#ffffff' : tabColors.textColor),
                    backgroundColor: organisationTab === tab.id ? (theme === 'white' ? '#ffffff' : (theme === 'dark' ? '#1f2937' : '#1e3a8a')) : 'transparent',
                    borderBottom: organisationTab === tab.id ? '2px solid #a855f7' : 'none',
                    cursor: 'pointer',
                  }}
                  onMouseEnter={(e) => {
                    if (organisationTab !== tab.id) {
                      (e.target as HTMLButtonElement).style.backgroundColor = tabColors.hoverBgColor;
                      (e.target as HTMLButtonElement).style.color = theme !== 'white' ? '#ffffff' : tabColors.hoverTextColor;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (organisationTab !== tab.id) {
                      (e.target as HTMLButtonElement).style.backgroundColor = 'transparent';
                      (e.target as HTMLButtonElement).style.color = theme !== 'white' ? '#ffffff' : tabColors.textColor;
                    }
                  }}
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
                    <label className="text-[10px] font-semibold text-gray-500 uppercase">{t('org.activeOrganisation')}</label>
                    <select value={selectedOrgId} onChange={e => setSelectedOrgId(e.target.value)}
                      className="mt-1 w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 bg-white">
                      {orgs.length === 0 && <option value="">{t('org.noOrganisations')}</option>}
                      {orgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
                    </select>
                  </div>
                  <hr className="border-gray-200" />
                  <div>
                    <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">{t('org.manage')}</h4>
                    <div className="flex gap-1 mb-2">
                      <input value={orgName} onChange={e => setOrgName(e.target.value)} placeholder={t('org.organisationName')}
                        className="flex-1 text-xs border border-gray-300 rounded-md px-2 py-1.5" />
                      <button onClick={async () => {
                        if (!orgName) return;
                        const r = await fetch(`${API}/api/v2/organizations`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:orgName}) });
                        const d = await r.json();
                        if (r.ok) { setOrgs(prev => [...prev, d]); setSelectedOrgId(d.id); setOrgName(''); setOrgMsg({text:t('org.created'),ok:true}); }
                        else setOrgMsg({text:d.error||'Error',ok:false});
                      }} className="px-3 py-1.5 text-xs font-medium text-purple-600 border border-purple-300 rounded-md hover:bg-purple-50 transition-colors">
                        <i className="bi bi-plus-lg"></i>
                      </button>
                    </div>
                    {orgs.length === 0 ? (
                      <p className="text-xs text-gray-400 italic">{t('sidebar.noFiles')}</p>
                    ) : (
                      <Paginator items={orgs}>
                        {pageItems => (
                          <div className="space-y-1">
                            {pageItems.map(o => (
                              orgEditId === o.id ? (
                                <div key={o.id} className="flex items-center gap-1">
                                  <input value={orgEditName} onChange={e => setOrgEditName(e.target.value)}
                                    className="flex-1 text-xs border border-purple-300 rounded px-2 py-1" />
                                  <button onClick={async () => {
                                    const r = await fetch(`${API}/api/v2/organizations/${o.id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:orgEditName}) });
                                    const d = await r.json();
                                    if (r.ok) { setOrgs(prev => prev.map(x => x.id === o.id ? {...x, name:orgEditName} : x)); setOrgEditId(null); setOrgMsg({text:t('org.updated'),ok:true}); }
                                    else setOrgMsg({text:d.error||t('org.deleteError'),ok:false});
                                  }} className="text-green-600 hover:text-green-700 px-1"><i className="bi bi-check-lg text-xs"></i></button>
                                  <button onClick={() => setOrgEditId(null)} className="text-gray-400 hover:text-gray-600 px-1"><i className="bi bi-x text-xs"></i></button>
                                </div>
                              ) : (
                                <div key={o.id} className="flex items-center justify-between border border-gray-200 rounded px-2 py-1 group">
                                  <span className="text-xs text-gray-700">{o.name}</span>
                                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onClick={() => { setOrgEditId(o.id); setOrgEditName(o.name); }} className="text-gray-400 hover:text-purple-600"><i className="bi bi-pencil text-[10px]"></i></button>
                                    <button onClick={async () => {
                                      const r = await fetch(`${API}/api/v2/organizations/${o.id}`, { method:'DELETE' });
                                      if (r.ok) { setOrgs(prev => prev.filter(x => x.id !== o.id)); if (selectedOrgId === o.id) setSelectedOrgId(''); setOrgMsg({text:t('org.deleted'),ok:true}); }
                                      else setOrgMsg({text:t('org.deleteError'),ok:false});
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
                  <hr className="border-gray-200" />
                  <div>
                    <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">{t('org.manageDepartments')}</h4>
                    <div className="flex gap-1 mb-2">
                      <input value={deptName} onChange={e => setDeptName(e.target.value)} placeholder={t('org.departmentName')}
                        className="flex-1 text-xs border border-gray-300 rounded-md px-2 py-1.5" />
                      <button onClick={async () => {
                        if (!deptName || !selectedOrgId) return;
                        const r = await fetch(`${API}/api/v2/departments`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({name:deptName, organization_id:selectedOrgId}) });
                        const d = await r.json();
                        if (r.ok) { setDepartments(prev => [...prev, d]); setDeptName(''); setOrgMsg({text:t('org.created'),ok:true}); }
                        else setOrgMsg({text:d.error||'Error',ok:false});
                      }} className="px-3 py-1.5 text-xs font-medium text-purple-600 border border-purple-300 rounded-md hover:bg-purple-50 transition-colors">
                        <i className="bi bi-plus-lg"></i>
                      </button>
                    </div>
                    {departments.length === 0 ? (
                      <p className="text-xs text-gray-400 italic">{t('org.noDepartments')}</p>
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
                                    if (r.ok) { setDepartments(prev => prev.map(x => x.id === d.id ? {...x, name:deptEditName} : x)); setDeptEditId(null); setOrgMsg({text:t('org.deptUpdated'),ok:true}); }
                                    else setOrgMsg({text:t('org.deleteError'),ok:false});
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
                                      if (r.ok) { setDepartments(prev => prev.filter(x => x.id !== d.id)); setOrgMsg({text:t('org.deptDeleted'),ok:true}); }
                                      else setOrgMsg({text:t('org.deleteError'),ok:false});
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
                    <p className="text-xs font-semibold text-gray-700 mb-2">{t('org.manageUsers')}</p>
                    <select value={userRoleId} onChange={e => setUserRoleId(e.target.value)}
                      className="mt-1 w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2 bg-white">
                      <option value="">{t('org.selectRole')}</option>
                      {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                    <input value={userEmail} onChange={e => setUserEmail(e.target.value)} placeholder={t('org.email')}
                      className="w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2" />
                    <input value={userPassword} onChange={e => setUserPassword(e.target.value)} placeholder={t('org.password')} type="password"
                      className="w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2" />
                    <input value={userFullName} onChange={e => setUserFullName(e.target.value)} placeholder={t('org.fullName')}
                      className="w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2" />
                    <button onClick={async () => {
                      if (!userEmail || !userPassword || !userRoleId) return;
                      const r = await fetch(`${API}/api/v2/users`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email:userEmail, password:userPassword, full_name:userFullName, role_id:userRoleId}) });
                      const d = await r.json();
                      if (r.ok) { setUsers(prev => [...prev, d]); setUserEmail(''); setUserPassword(''); setUserFullName('');setUserRoleId(''); setOrgMsg({text:t('org.userCreated'),ok:true}); }
                      else setOrgMsg({text:d.error||'Error',ok:false});
                    }} className="w-full px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700">
                      <i className="bi bi-person-plus mr-1"></i>{t('org.createUser')}
                    </button>
                  </div>
                  <div>
                    <h4 className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">{t('org.tab.user')} ({users.length})</h4>
                    {users.length === 0 ? (
                      <p className="text-xs text-gray-400 italic">{t('org.noUsers')}</p>
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
                  <div>
                    <h3 className="text-sm font-semibold text-gray-800 mb-3">{t('permission.title')}</h3>
                  </div>
                  <div className="border border-gray-200 rounded-lg p-3">
                    <p className="text-xs font-semibold text-gray-700 mb-2">{t('role.title')}</p>
                    <FlexiGrid
                    columns={roleColumns}
                    data={roles}
                    emptyState={{ organization_id: orgs[0]?.id || '', name: '' }}
                    onCreate={async (item) => {
                      const r = await fetch(`${API}/api/v2/roles`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(item) });
                      const d = await r.json();
                      if (r.ok) { setRoles(prev => [...prev, d]); setOrgMsg({text:'Role created!',ok:true}); return d; }
                      else { setOrgMsg({text:d.error||'Error',ok:false}); return null; }
                    }}
                    onUpdate={async (id, item) => {
                      const r = await fetch(`${API}/api/v2/roles/${id}`, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(item) });
                      const d = await r.json();
                      if (r.ok) { setRoles(prev => prev.map(rl => rl.id === id ? d : rl)); setOrgMsg({text:'Role updated!',ok:true}); return d; }
                      else { setOrgMsg({text:d.error||'Error',ok:false}); return null; }
                    }}
                    onDelete={async (id) => {
                      const res = await fetch(`${API}/api/v2/roles/${id}`, { method:'DELETE' });
                      if (res.ok) { setRoles(prev => prev.filter(rl => rl.id !== id)); setOrgMsg({text:'Role deleted!',ok:true}); return true; }
                      else { const d = await res.json(); setOrgMsg({text:d.error||'Error',ok:false}); return false; }
                    }}
                    onBulkDelete={async (ids) => {
                      let ok = true;
                      for (const id of ids) {
                        const res = await fetch(`${API}/api/v2/roles/${id}`, { method:'DELETE' });
                        if (res.ok) setRoles(prev => prev.filter(rl => rl.id !== id));
                        else ok = false;
                      }
                      if (ok) setOrgMsg({text:'Roles deleted!',ok:true});
                      return ok;
                    }}
                  />
                                                          </div>
                  <hr className="border-gray-200" />
                  <div className="border border-gray-200 rounded-lg p-3">
                    <p className="text-xs font-semibold text-gray-700 mb-2">{t('permission.add')}</p>
                    <label className="text-[10px] font-semibold text-gray-500 uppercase">{t('permission.roleLabel')}</label>
                    <select value={permRoleId} onChange={e => setPermRoleId(e.target.value)}
                      className="mt-1 w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2 bg-white">
                      <option value="">{t('permission.selectRole')}</option>
                      {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                    <label className="text-[10px] font-semibold text-gray-500 uppercase">{t('permission.resourceLabel')}</label>
                    <select value={permResource} onChange={e => { setPermResource(e.target.value); setPermActions([]); }}
                      className="mt-1 w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2 bg-white">
                      <option value="">{t('permission.selectResource')}</option>
                      {PERM_RESOURCES.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                    <FlexiMultiReferentiel
                      label={t('permission.actionLabel')}
                      availableItems={[...(RESOURCE_ACTIONS[permResource] || [])]}
                      selectedItems={permActions}
                      onItemSelect={action => setPermActions([...permActions, action])}
                      onItemRemove={action => setPermActions(permActions.filter(a => a !== action))}
                      disabled={!permResource}
                      placeholder={t('permission.selectActions')}
                      className="mt-1 mb-2"
                    />
                    <label className="text-[10px] font-semibold text-gray-500 uppercase">{t('permission.validFromLabel')}</label>
                    <input type="date" value={permValidFrom} onChange={e => setPermValidFrom(e.target.value)}
                      className="mt-1 w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2 bg-white" />
                    <label className="text-[10px] font-semibold text-gray-500 uppercase">{t('permission.validToLabel')}</label>
                    <input type="date" value={permValidTo} onChange={e => setPermValidTo(e.target.value)}
                      className="mt-1 w-full text-xs border border-gray-300 rounded-md px-2 py-1.5 mb-2 bg-white" />
                    <button onClick={async () => {
                      if (!permRoleId || !permResource || permActions.length === 0) return;
                      const r = await fetch(`${API}/api/v2/permissions`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({role_id:permRoleId, actions:permActions, resource:permResource, valid_from:permValidFrom||null, valid_to:permValidTo||null}) });
                      const d = await r.json();
                      if (r.ok) {
                        let msg = '';
                        if (d.total_created > 0) {
                          msg = t('permission.created.count', {count: d.total_created, plural: d.total_created > 1 ? 's' : ''});
                        }
                        if (d.total_duplicates > 0) {
                          if (msg) msg += ` ${t('permission.duplicate.count', {count: d.total_duplicates, plural: d.total_duplicates > 1 ? '' : ''})}`;
                          else msg = t('permission.duplicate.all');
                        }
                        setOrgMsg({text: msg, ok: true});
                        // Refresh permissions list
                        fetch(`${API}/api/v2/permissions`).then(res => res.json()).then(data => setPermissions(data.data || [])).catch(() => {});
                        // Clear form fields
                        setPermRoleId('');
                        setPermActions([]);
                        setPermResource('');
                        setPermValidFrom('');
                        setPermValidTo('');
                      } else {
                        setOrgMsg({text:d.error||'Error',ok:false});
                      }
                    }} className="w-full px-3 py-1.5 text-xs font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700">
                      <i className="bi bi-plus-lg mr-1"></i>{t('permission.add')}
                    </button>
                  </div>
                  <hr className="border-gray-200 mt-4" />
                  <div className="border border-gray-200 rounded-lg p-3">
                    <p className="text-xs font-semibold text-gray-700 mb-2">{t('permission.saved')}</p>
                    <FlexiGrid
                      columns={permissionColumns}
                      data={permissions}
                      emptyState={{ id: '', action: '', resource: '' }}
                      onCreate={async () => null}
                      onUpdate={async () => null}
                      onDelete={async (id) => {
                        const r = await fetch(`${API}/api/v2/permissions/${id}`, { method: 'DELETE' });
                        if (r.ok) {
                          setPermissions(prev => prev.filter(p => p.id !== id));
                          setOrgMsg({text: t('permission.deleted'), ok: true});
                          return true;
                        } else {
                          setOrgMsg({text: t('permission.errorDeleting'), ok: false});
                          return false;
                        }
                      }}
                      disableCreate={true}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      case 'history':
        return (
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">{t('sidebar.history')}</h3>
            <div className="max-h-64 overflow-y-auto">
              {searchHistory.length > 0 ? (
                <div className="space-y-1">
                  <p className="text-xs text-gray-400 mb-2">{t('sidebar.recent.searches')}</p>
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
                <p className="text-xs text-gray-500">{t('sidebar.noHistory')}</p>
              )}
              {files.length > 0 && (
                <>
                  <hr className="my-3 border-gray-200" />
                  <p className="text-xs text-gray-400 mb-2">{t('sidebar.openFiles')}</p>
                  <ul className="space-y-1">
                    {renderFileTree(files)}
                  </ul>
                </>
              )}
              {recentDocuments.length > 0 && (
                <>
                  <hr className="my-3 border-gray-200" />
                  <p className="text-xs text-gray-400 mb-2">{t('sidebar.recentDocuments')}</p>
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
            <h3 className="text-sm font-semibold text-gray-800 mb-3">{t('sidebar.settings')}</h3>
            <div className="space-y-4">
              {/* Theme selection */}
              <div>
                <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">{t('settings.theme')}</p>
                <div className="flex items-center gap-1.5">
                  {[
                    { value: 'white' as const, bgColor: '#ffffff', borderColor: '#e5e7eb' },
                    { value: 'dark' as const, bgColor: '#1f2937', borderColor: '#374151' },
                    { value: 'dark-blue' as const, bgColor: '#1e3a8a', borderColor: '#1e40af' },
                  ].map((opt) => (
                    <button
                      key={opt.value}
                      onClick={() => setTheme(opt.value)}
                      title={`${opt.value.charAt(0).toUpperCase() + opt.value.slice(1).replace('-', ' ')} theme`}
                      className={`w-6 h-6 rounded transition-all ${
                        theme === opt.value
                          ? 'ring-2 ring-purple-500 ring-offset-1'
                          : 'hover:ring-2 hover:ring-gray-300'
                      }`}
                      style={{
                        backgroundColor: opt.bgColor,
                        borderColor: opt.borderColor,
                        border: '1px solid ' + opt.borderColor,
                      }}
                    >
                      {theme === opt.value && (
                        <i className="bi bi-check text-purple-600 text-xs font-bold"></i>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              <hr className="border-gray-200" />

              {/* Language selection */}
              <div>
                <p className="text-xs font-semibold text-gray-600 mb-2 uppercase tracking-wide">{t('settings.language')}</p>
                <LanguageSwitcher />
              </div>
            </div>
          </div>
        );
      case 'user':
        return (
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">{t('account.title')}</h3>
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
                    {t('account.plan')}: <span className="font-medium capitalize">{user.plan}</span>
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
                  {t('account.signOut')}
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-gray-500">{t('account.notSignedIn')}</p>
                <button
                  onClick={() => { setIsLoginModalOpen(true); setActivePanel(null); }}
                  className="w-full px-3 py-2 rounded-md text-sm font-medium transition-colors bg-purple-600 text-white hover:bg-purple-700"
                >
                  {t('account.signIn')}
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
                { id: 'connector' as SidebarPanel, icon: 'bi-command', label: t('sidebar.connector') },
                { id: 'agents' as SidebarPanel, icon: 'bi-outlet', label: t('sidebar.agents') },
                { id: 'organisation' as SidebarPanel, icon: 'bi-buildings', label: t('sidebar.organisation') },
                { id: 'history' as SidebarPanel, icon: 'bi-chat-right', label: t('sidebar.history') },
              ].map((item) => {
                const isInactive = activePanel !== item.id;
                const inactiveColor = theme !== 'white' ? '#ffffff' : '#000000';
                const hoverBgColor = theme === 'white' ? '#e5e7eb' : (theme === 'dark' ? '#374151' : '#1e40af');
                return (
                <button
                  key={item.id}
                  onClick={() => handleIconClick(item.id)}
                  className={`relative w-12 flex flex-col items-center justify-center py-2 rounded-md transition-colors group ${
                    activePanel === item.id
                      ? 'text-purple-600 bg-purple-50'
                      : ''
                  }`}
                  style={{
                    color: activePanel === item.id ? '#a855f7' : inactiveColor,
                  }}
                  onMouseEnter={(e) => {
                    if (isInactive) {
                      (e.currentTarget as HTMLButtonElement).style.backgroundColor = hoverBgColor;
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (isInactive) {
                      (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  {activePanel === item.id && (
                    <div className="absolute -right-2 top-1 bottom-1 w-0.5 bg-purple-600 rounded-l"></div>
                  )}
                  <i className={`bi ${item.icon} text-lg font-bold`}></i>
                  <span className="text-[9px] mt-0.5 leading-tight font-bold">{item.label}</span>
                </button>
              );
              })}
            </nav>

            {/* Settings icon */}
            {(() => {
              const inactiveColor = theme !== 'white' ? '#ffffff' : '#000000';
              const hoverBgColor = theme === 'white' ? '#e5e7eb' : (theme === 'dark' ? '#374151' : '#1e40af');
              return (
              <button
                onClick={() => handleIconClick('settings')}
                className={`relative w-12 flex flex-col items-center justify-center py-2 rounded-md transition-colors mb-1 ${
                  activePanel === 'settings'
                    ? 'text-purple-600 bg-purple-50'
                    : ''
                }`}
                style={{
                  color: activePanel === 'settings' ? '#a855f7' : inactiveColor,
                }}
                onMouseEnter={(e) => {
                  if (activePanel !== 'settings') {
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = hoverBgColor;
                  }
                }}
                onMouseLeave={(e) => {
                  if (activePanel !== 'settings') {
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
                  }
                }}
              >
                {activePanel === 'settings' && (
                  <div className="absolute -right-2 top-1 bottom-1 w-0.5 bg-purple-600 rounded-l"></div>
                )}
                <i className="bi bi-gear text-lg font-bold"></i>
                <span className="text-[9px] mt-0.5 leading-tight font-bold">{t('sidebar.settings')}</span>
              </button>
            )})()}

            {/* User icon at bottom */}
            {(() => {
              const inactiveColor = theme !== 'white' ? '#ffffff' : '#000000';
              const hoverBgColor = theme === 'white' ? '#e5e7eb' : (theme === 'dark' ? '#374151' : '#1e40af');
              return (
              <button
                onClick={() => handleIconClick('user')}
                className={`relative w-12 flex flex-col items-center justify-center py-2 rounded-md transition-colors ${
                  activePanel === 'user'
                    ? 'text-purple-600 bg-purple-50'
                    : ''
                }`}
                style={{
                  color: activePanel === 'user' ? '#a855f7' : inactiveColor,
                }}
                onMouseEnter={(e) => {
                  if (activePanel !== 'user') {
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = hoverBgColor;
                  }
                }}
                onMouseLeave={(e) => {
                  if (activePanel !== 'user') {
                    (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
                  }
                }}
              >
                {activePanel === 'user' && (
                  <div className="absolute -right-2 top-1 bottom-1 w-0.5 bg-purple-600 rounded-l"></div>
                )}
                <i className="bi bi-person text-lg font-bold"></i>
                <span className="text-[9px] mt-0.5 leading-tight font-bold">{t('sidebar.account')}</span>
              </button>
            )})()}
          </div>

          {/* Mobile flyout panel(s) */}
          {activePanel && (
            <div className="flex h-full">
              <div className={`${activePanel === 'organisation' ? 'w-80' : 'w-56'} bg-white border-r border-gray-200 shadow-lg h-full overflow-y-auto`}>
                {renderFlyoutContent()}
              </div>
              {activePanel === 'connector' && activeConnectorType && (
                <div className="w-60 bg-white border-r border-gray-200 shadow-lg h-full overflow-y-auto">
                  {renderConnectorForm()}
                </div>
              )}
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
          <div className="w-9 h-8  flex items-center justify-center  overflow-hidden">
            <img src="/flexiAnalyseLogo_website.png" alt="FlexiAnalyse" className="w-full h-full object-contain" />
          </div>
        </div>

        {/* Navigation icons */}
        <nav className="flex-1 flex flex-col items-center gap-1">
          {[
            { id: 'connector' as SidebarPanel, icon: 'bi-command', label: t('sidebar.connector') },
            { id: 'agents' as SidebarPanel, icon: 'bi-outlet', label: t('sidebar.agents') },
            { id: 'organisation' as SidebarPanel, icon: 'bi-buildings', label: t('sidebar.organisation') },
            { id: 'history' as SidebarPanel, icon: 'bi-chat-right', label: t('sidebar.history') },
          ].map((item) => {
            const isInactive = activePanel !== item.id;
            const inactiveColor = theme !== 'white' ? '#ffffff' : '#000000';
            const hoverBgColor = theme === 'white' ? '#e5e7eb' : (theme === 'dark' ? '#374151' : '#1e40af');
            return (
            <button
              key={item.id}
              onClick={() => handleIconClick(item.id)}
              className={`relative w-12 flex flex-col items-center justify-center py-2.5 rounded-md transition-all duration-200 group ${
                activePanel === item.id
                  ? 'text-purple-600 bg-purple-50'
                  : ''
              }`}
              title={item.label}
              style={{
                color: activePanel === item.id ? '#a855f7' : inactiveColor,
              }}
              onMouseEnter={(e) => {
                if (isInactive) {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = hoverBgColor;
                }
              }}
              onMouseLeave={(e) => {
                if (isInactive) {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
                }
              }}
            >
              {/* Purple right border indicator */}
              {activePanel === item.id && (
                <div className="absolute -right-2 top-1 bottom-1 w-0.5 bg-purple-600 rounded-l"></div>
              )}
              <i className={`bi ${item.icon} text-lg font-bold`}></i>
              <span className="text-[9px] mt-0.5 leading-tight font-bold">{item.label}</span>
            </button>
          );
          })}
        </nav>

        {/* Settings icon */}
        {(() => {
          const inactiveColor = theme !== 'white' ? '#ffffff' : '#000000';
          const hoverBgColor = theme === 'white' ? '#e5e7eb' : (theme === 'dark' ? '#374151' : '#1e40af');
          return (
          <button
            onClick={() => handleIconClick('settings')}
            className={`relative w-12 flex flex-col items-center justify-center py-2.5 rounded-md transition-all duration-200 mb-1 ${
              activePanel === 'settings'
                ? 'text-purple-600 bg-purple-50'
                : ''
            }`}
            title={t('sidebar.settings')}
            style={{
              color: activePanel === 'settings' ? '#a855f7' : inactiveColor,
            }}
            onMouseEnter={(e) => {
              if (activePanel !== 'settings') {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = hoverBgColor;
              }
            }}
            onMouseLeave={(e) => {
              if (activePanel !== 'settings') {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
              }
            }}
          >
            {activePanel === 'settings' && (
              <div className="absolute -right-2 top-1 bottom-1 w-0.5 bg-purple-600 rounded-l"></div>
            )}
            <i className="bi bi-gear text-lg font-bold"></i>
            <span className="text-[9px] mt-0.5 leading-tight font-bold">{t('sidebar.settings')}</span>
          </button>
        )})()}

        {/* User icon at bottom */}
        {(() => {
          const inactiveColor = theme !== 'white' ? '#ffffff' : '#000000';
          const hoverBgColor = theme === 'white' ? '#e5e7eb' : (theme === 'dark' ? '#374151' : '#1e40af');
          return (
          <button
            onClick={() => handleIconClick('user')}
            className={`relative w-12 flex flex-col items-center justify-center py-2.5 rounded-md transition-all duration-200 ${
              activePanel === 'user'
                ? 'text-purple-600 bg-purple-50'
                : ''
            }`}
            title={t('sidebar.account')}
            style={{
              color: activePanel === 'user' ? '#a855f7' : inactiveColor,
            }}
            onMouseEnter={(e) => {
              if (activePanel !== 'user') {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = hoverBgColor;
              }
            }}
            onMouseLeave={(e) => {
              if (activePanel !== 'user') {
                (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
              }
            }}
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
        )})()}

        {/* Error indicator */}
        {error && (
          <div className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full animate-pulse" title={error}></div>
        )}

        {/* Loading indicator */}
        {isLoading && (
          <div className="absolute top-2 left-2 w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
        )}
      </div>

      {/* Flyout Panel(s) */}
      {activePanel && (
        <div ref={flyoutRef} className="flex h-full">
          <div className={`${activePanel === 'organisation' ? 'w-80' : 'w-56'} bg-white border-r border-gray-200 shadow-sm h-full overflow-y-auto animate-in slide-in-from-left-2 duration-200`}>
            {renderFlyoutContent()}
          </div>
          {activePanel === 'connector' && activeConnectorType && (
            <div className="w-64 bg-white border-r border-gray-200 shadow-sm h-full overflow-y-auto animate-in slide-in-from-left-2 duration-200">
              {renderConnectorForm()}
            </div>
          )}
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