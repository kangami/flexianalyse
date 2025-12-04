import React, { useState, useRef, ChangeEvent, useEffect, useMemo, useCallback } from 'react';
import { FolderOpen, Folder } from 'lucide-react';

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

  constructor(baseURL = 'http://localhost:5000') {
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
    } catch (error) {
      const result = { model_id: modelId, status: 'unavailable', error: error.message };
      
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
  getRepoStructure, 
  selectedModel, 
  setSelectedModel, 
  isSidebarOpen, 
  toggleSidebar 
}) => {
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

  const buildFileTree = useCallback((fileList: File[]): FileNode[] => {
    const tree: FileNode[] = [];
    const pathMap: { [key: string]: FileNode } = {};

    fileList.forEach((file) => {
      const path = (file as any).webkitRelativePath || file.name;
      const parts = path.split('/');

      let currentPath = '';
      let parentNode: FileNode | null = null;

      parts.forEach((part, index) => {
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
        }
        parentNode = pathMap[currentPath];
      });
    });

    return tree;
  }, []);

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
        
        // Immediately display files in interface
        const fileTree = buildFileTree(acceptedFiles);
        setFiles(fileTree);

        // Add to pending uploads
        setPendingFiles(prev => [...prev, ...acceptedFiles]);
        
        // Schedule debounced upload
        debouncedUpload(acceptedFiles, selectedModel);
        
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
  }, [filterFiles, buildFileTree, debouncedUpload, selectedModel, clearPreviousState]);

  const handleFolderChange = useCallback(async (event: ChangeEvent<HTMLInputElement>): Promise<void> => {
    if (event.target.files) {
      setIsLoading(true);
      clearPreviousState();
      setError(null);
      
      try {
        const acceptedFiles = filterFiles(event.target.files);
        
        // Immediately display files in interface
        const fileTree = buildFileTree(acceptedFiles);
        setFiles(fileTree);

        // Add to pending uploads
        setPendingFiles(prev => [...prev, ...acceptedFiles]);
        
        // Schedule debounced upload
        debouncedUpload(acceptedFiles, selectedModel);
        
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
  }, [filterFiles, buildFileTree, debouncedUpload, selectedModel, clearPreviousState]);

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

  const renderFileTree = useCallback((nodes: FileNode[]): JSX.Element[] => {
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
              className="font-semibold truncate max-w-[180px]"
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
            <span className="truncate max-w-[180px] inline-block align-middle">
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
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-800">{error}</p>
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

              {/* Export button */}
              <button className="w-full flex items-center space-x-3 p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="font-medium text-gray-700">Export</span>
              </button>

              {/* Model dropdown */}
              <div className="relative" ref={modelDropdownRef}>
                <button
                  onClick={() => handleMobileModelDropdownOpen()}
                  className="w-full flex items-center justify-between p-3 text-left bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center space-x-3">
                    <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    <span className="font-medium text-gray-700">Model</span>
                  </div>
                  <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                
                {isMobileModelDropdownOpen  && (
                  <div className="mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-80 overflow-y-auto">
                    {isLoadingModels ? (
                      <div className="px-4 py-6 text-center">
                        <div className="flex items-center justify-center space-x-2">
                          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                          <span className="text-sm text-gray-600">Loading models...</span>
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
                          className={`w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 ${
                            selectedModel === model.id ? 'bg-blue-50 border-blue-200' : ''
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center space-x-2">
                                <p className={`text-sm font-medium truncate ${
                                  selectedModel === model.id ? 'text-blue-900' : 'text-gray-900'
                                }`}>
                                  {model.name}
                                </p>
                                {getModelStatusIcon(model.id)}
                              </div>
                              <p className={`text-xs truncate ${
                                selectedModel === model.id ? 'text-blue-600' : 'text-gray-500'
                              }`}>
                                {model.provider}
                              </p>
                            </div>
                            {selectedModel === model.id && (
                              <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
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

            {/* Explorer Section */}
            <div className="flex-1 min-h-0">
              <h3 className="text-sm font-semibold mb-3 text-gray-700">EXPLORER</h3>
              
              <div className="h-full overflow-y-auto">
                {isLoading ? (
                  <div className="flex items-center text-blue-600 text-sm">
                    <svg
                      className="animate-spin h-5 w-5 mr-2 text-blue-600"
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
                  <p className="text-gray-500 text-sm">
                    No files imported yet.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
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

    {/* Desktop Sidebar - Comportement original */}
    <div className="hidden lg:block h-screen bg-gray-100 p-4 flex flex-col">
      {/* Error display */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-800">{error}</p>
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
          {isSidebarOpen ? 'Export' : (
            <div className="flex items-center space-x-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-xs">Export</span>
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
            className={`text-gray-700 hover:text-blue-500 ${!isSidebarOpen ? 'flex items-center justify-center w-full py-1 px-2 rounded hover:bg-gray-200' : 'flex items-center space-x-2'}`}
          >
            {isSidebarOpen ? (
              <div className="flex items-center space-x-2">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span className="text-sm font-medium truncate max-w-40">Model</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            ) : (
              <div className="flex items-center space-x-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span className="text-xs">Model</span>
              </div>
            )}
          </a>
          
          {isDesktopModelDropdownOpen  && (
            <div className={`absolute bg-white shadow-lg border border-gray-200 rounded-md z-50 max-h-80 overflow-y-auto ${isSidebarOpen ? 'right-0 top-full w-56 mt-2' : 'left-full top-0 w-64 ml-2'}`}>
              {isLoadingModels ? (
                <div className="px-4 py-3 text-center">
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                    <span className="text-sm text-gray-600">Loading models...</span>
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
                    className={`block w-full text-left px-4 py-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 ${
                      selectedModel === model.id ? 'bg-blue-50 border-blue-200' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <p className={`text-sm font-medium truncate ${
                            selectedModel === model.id ? 'text-blue-900' : 'text-gray-900'
                          }`}>
                            {model.name}
                          </p>
                          {getModelStatusIcon(model.id)}
                        </div>
                        <p className={`text-xs truncate ${
                          selectedModel === model.id ? 'text-blue-600' : 'text-gray-500'
                        }`}>
                          {model.provider}
                        </p>
                      </div>
                      {selectedModel === model.id && (
                        <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
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

      <div className="flex-1 overflow-y-auto">
        {isSidebarOpen && (
          <h3 className="text-sm font-semibold mb-3">EXPLORER</h3>
        )}
        
        {isLoading ? (
          <div className="flex items-center text-blue-600 text-sm">
            <svg
              className="animate-spin h-5 w-5 mr-2 text-blue-600"
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
            {isSidebarOpen && renderFileTree(files)}
          </ul>
        ) : (
          <p className={`text-gray-600 ${isSidebarOpen ? 'text-sm' : 'text-xs text-center'}`}>
            {isSidebarOpen ? 'No files imported yet.' : 'No files'}
          </p>
        )}
      </div>
      
      {/* Toggle button */}
      <div
        onClick={toggleSidebar}
        className="bg-gray-100 text-gray-700 p-2 h-10 flex items-center justify-center transition-all duration-300 absolute bottom-0 right-0 cursor-pointer"
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