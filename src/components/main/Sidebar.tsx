import React, { useState, useRef, ChangeEvent, useEffect } from 'react';

// Define types for file descriptions
interface FileDescription {
  file_name: string;
  description: string;
}

interface FileNode {
  name: string;
  children?: FileNode[];
  file?: File;
  isOpen?: boolean; // Track if folder is expanded
}

interface FileDetails {
    content: string | ArrayBuffer;
    description: string;
}

interface SidebarProps {
    onFileSelect: (file: File, details: FileDetails) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ onFileSelect }) => {
    const [files, setFiles] = useState<FileNode[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [isFileDropdownOpen, setIsFileDropdownOpen] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const folderInputRef = useRef<HTMLInputElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);

  // Define allowed code file extensions
  const allowedExtensions: string[] = [
    '.java', '.py', '.cs', '.js', '.ts', '.cpp', '.c', '.h',
    '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx',
    '.tsx', '.sql', '.docx',
  ];

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsFileDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Filter files based on extensions
  const filterFiles = (fileList: FileList): File[] => {
    return Array.from(fileList).filter((file) => {
      const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      return allowedExtensions.includes(extension);
    });
  };

  // Build a file tree structure from a list of files
  const buildFileTree = (fileList: File[]): FileNode[] => {
    const tree: FileNode[] = [];
    const pathMap: { [key: string]: FileNode } = {};

    fileList.forEach((file) => {
      // Get the relative path (for folder uploads)
      const path = (file as any).webkitRelativePath || file.name;
      const parts = path.split('/');

      let currentPath = '';
      let parentNode: FileNode | null = null;

      parts.forEach((part, index) => {
        currentPath = currentPath ? `${currentPath}/${part}` : part;
        if (!pathMap[currentPath]) {
          const node: FileNode = { name: part };
          if (index === parts.length - 1) {
            // This is a file
            node.file = file;
          } else {
            // This is a folder
            node.children = [];
            node.isOpen = false; // Initially collapsed
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
  };

  // Handle file selection
  const handleFileChange = (event: ChangeEvent<HTMLInputElement>): void => {
    if (event.target.files) {
      const acceptedFiles = filterFiles(event.target.files);
      const fileTree = buildFileTree(acceptedFiles);
      setFiles(fileTree);
      setError(null);
    }
  };

  // Handle folder selection
  const handleFolderChange = (event: ChangeEvent<HTMLInputElement>): void => {
    if (event.target.files) {
      const acceptedFiles = filterFiles(event.target.files);
      const fileTree = buildFileTree(acceptedFiles);
      setFiles(fileTree);
      setError(null);
    }
  };

  // Trigger file input click
  const handleImportFileClick = () => {
    fileInputRef.current?.click();
    setIsFileDropdownOpen(false);
  };

  // Trigger folder input click
  const handleImportFolderClick = () => {
    folderInputRef.current?.click();
    setIsFileDropdownOpen(false);
  };

  // Toggle folder open/close
  const toggleFolder = (node: FileNode, nodes: FileNode[]): FileNode[] => {
    return nodes.map((n) => {
      if (n === node) {
        return { ...n, isOpen: !n.isOpen };
      }
      if (n.children) {
        return { ...n, children: toggleFolder(node, n.children) };
      }
      return n;
    });
  };

  // Handle folder toggle
  const handleToggleFolder = (node: FileNode) => {
    setFiles((prevFiles) => toggleFolder(node, prevFiles));
  };

  // Handle file click
  const handleFileClick = async (file: File) => {
    setIsLoading(true);
    try {
        // Determine file type
        const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
        const isBinaryFile = ['.docx', '.pdf'].includes(extension);

        // Read file content
        let content: string | ArrayBuffer;
        if (isBinaryFile) {
            // Read binary files as ArrayBuffer
            content = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result as ArrayBuffer);
            reader.onerror = () => reject(new Error('Failed to read file'));
            reader.readAsArrayBuffer(file);
            });
        } else {
            // Read text files as string
            content = await file.text();
        }
  
        // Upload file to backend
        const formData = new FormData();
        formData.append('files', file);
  
        const response = await fetch('http://localhost:5000/upload', {
          method: 'POST',
          body: formData,
        });
  
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(`Upload failed: ${errorData.error || response.statusText}`);
        }
  
        const data = await response.json();
        const description = data.results[0]?.description || 'No description available';
  
        // Pass file details to parent
        onFileSelect(file, { content, description });
        setError(null);
      } catch (error) {
        console.error('Error uploading file:', error);
        if (error.message.includes('Failed to fetch')) {
          setError('Could not connect to the backend. Please ensure the server is running on http://localhost:5000.');
        } else {
          setError(error.message || 'An error occurred while uploading the file.');
        }
      }finally {
        setIsLoading(false);
      }
  };


  // Render the file tree
  const renderFileTree = (nodes: FileNode[]): JSX.Element[] => {
    return nodes.map((node, index) => (
      <li key={index}>
        {node.children ? (
          <div className="flex items-center">
            <button
                onClick={() => handleToggleFolder(node)}
                className={`mr-1 mb-2 text-white px-2 py-1 rounded ${
                    node.isOpen ? 'bg-red-500' : 'bg-green-500'
                }`}>
                {node.isOpen ? '–' : '+'}
            </button>
            <span className="font-semibold">{node.name}</span>
          </div>
        ) : (
          <button
            onClick={() => handleFileClick(node.file!)}
            className="text-blue-500 hover:underline"
          >
            {node.name}
          </button>
        )}
        {node.children && node.isOpen && (
          <ul className="ml-4">
            {renderFileTree(node.children)}
          </ul>
        )}
      </li>
    ));
  };

  return (
    <div className="w-64 h-screen bg-gray-100 p-4 flex flex-col">
      {/* Inline Menu */}
      <div className="flex justify-between mb-4">
        {/* File Menu with Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <a href='#'
            onClick={() => setIsFileDropdownOpen((prev) => !prev)}
            className="text-gray-700 hover:text-blue-500"
          >
            File
          </a>
          {isFileDropdownOpen && (
            <div className="absolute w-screen bg-white shadow-md  mt-1 z-10">
              <a href='#'
                onClick={() => {
                    fileInputRef.current?.click();
                    setIsFileDropdownOpen(false);
                }}
                className="block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100"
              >
                Import a file
              </a>
              <a href='#'
                onClick={() => {
                    folderInputRef.current?.click();
                    setIsFileDropdownOpen(false);
                }}
                className="block w-full text-left px-4 py-2 text-gray-700 hover:bg-gray-100"
              >
                Import a folder
              </a>
            </div>
          )}
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
        </div>

        {/* Context Menu (Placeholder) */}
        <a href='#' className="text-gray-700 hover:text-blue-500">Export</a>

        {/* Model Menu (Placeholder) */}
        <a href='#' className="text-gray-700 hover:text-blue-500">Model</a>
      </div>
              
      {/* Loading Spinner */}
      {isLoading && (
        <div className="flex items-center text-blue-600 text-sm mb-4">
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
          Loading file details...
        </div>
      )}
      {/* Error Message */}
      {error && (
        <div className="text-red-600 text-sm mb-4">
          {error}
        </div>
      )}

      {/* File Structure */}
      {files.length > 0 && (
        <div className="flex-1 overflow-y-auto">
          <h3 className="text-sm font-semibold mb-3">EXPLORER</h3>
          <ul className="text-sm text-gray-600">
            {renderFileTree(files)}
          </ul>
        </div>
      )}
    </div>
  );
};

export default Sidebar;