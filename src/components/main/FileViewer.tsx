import React, { useState, useEffect, useRef, useCallback } from 'react';
import AceEditor from 'react-ace';
import mammoth from 'mammoth';
import { Document, Page, pdfjs } from 'react-pdf';
import workerSrc from 'pdfjs-dist/legacy/build/pdf.worker?url';
import { useLanguage } from '../../contexts/LanguageContext';

// Import Ace editor modes and themes
import 'ace-builds/src-noconflict/mode-java';
import 'ace-builds/src-noconflict/mode-python';
import 'ace-builds/src-noconflict/mode-csharp';
import 'ace-builds/src-noconflict/mode-javascript';
import 'ace-builds/src-noconflict/mode-typescript';
import 'ace-builds/src-noconflict/mode-c_cpp';
import 'ace-builds/src-noconflict/mode-ruby';
import 'ace-builds/src-noconflict/mode-php';
import 'ace-builds/src-noconflict/mode-html';
import 'ace-builds/src-noconflict/mode-css';
import 'ace-builds/src-noconflict/mode-sass';
import 'ace-builds/src-noconflict/mode-sql';
import 'ace-builds/src-noconflict/theme-monokai';

pdfjs.GlobalWorkerOptions.workerSrc = workerSrc;

interface FileDetails {
  content: string | ArrayBuffer;
  description: string;
}

interface FileViewerProps {
  file: File | null;
  fileDetails: FileDetails | null;
  onFileSelect?: (file: File, details: FileDetails) => void;
  onDragOver?: (e: React.DragEvent) => void;
  onDrop?: (e: React.DragEvent) => void;
  isProcessingDrop?: boolean;
  selectedDirectory?: File[] | null;
}

const FileViewer: React.FC<FileViewerProps> = ({
  file,
  fileDetails,
  onFileSelect,
  onDragOver,
  onDrop,
  isProcessingDrop = false,
  selectedDirectory = null
}) => {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [docxContent, setDocxContent] = useState<string>('');
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState<number>(600);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [scale, setScale] = useState<number>(1.0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageInput, setPageInput] = useState<string>('1');
  const { t } = useLanguage();

  const codeExtensions = [
    '.java', '.py', '.cs', '.js', '.ts', '.cpp', '.c', '.h',
    '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx',
    '.tsx', '.sql', '.json', '.xml', '.md', '.txt'
  ];

  // Déterminer le type de fichier avant les useEffect
  const extension = file && fileDetails ? file.name.substring(file.name.lastIndexOf('.')).toLowerCase() : '';
  const isCodeFile = extension ? codeExtensions.includes(extension) : false;
  const isPdfFile = extension === '.pdf';
  const isDocxFile = extension === '.docx';

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth);
      }
    };
    
    updateWidth();
    window.addEventListener('resize', updateWidth);
    
    return () => {
      window.removeEventListener('resize', updateWidth);
    };
  }, []);

  // Mettre à jour currentPage quand on scroll
  useEffect(() => {
    if (!isPdfFile || !numPages || !containerRef.current) return;

    const handleScroll = () => {
      const container = containerRef.current;
      if (!container) return;

      const scrollTop = container.scrollTop;
      const containerHeight = container.clientHeight;
      const scrollHeight = container.scrollHeight;
      
      // Calculer la page actuelle basée sur la position du scroll
      const pageHeight = scrollHeight / numPages;
      const estimatedPage = Math.floor(scrollTop / pageHeight) + 1;
      const clampedPage = Math.max(1, Math.min(numPages, estimatedPage));
      
      if (clampedPage !== currentPage) {
        setCurrentPage(clampedPage);
        setPageInput(clampedPage.toString());
      }
    };

    const container = containerRef.current;
    container.addEventListener('scroll', handleScroll);
    
    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, [isPdfFile, numPages, currentPage]);

  // Créer un Blob pour le PDF
  useEffect(() => {
    if (file && fileDetails && file.name.toLowerCase().endsWith('.pdf') && fileDetails.content instanceof ArrayBuffer) {
      const blob = new Blob([fileDetails.content], { type: 'application/pdf' });
      setPdfBlob(blob);
    } else {
      setPdfBlob(null);
    }
  }, [file, fileDetails]);

  const getLanguage = (extension: string): string => {
    const langMap: { [key: string]: string } = {
      '.java': 'java',
      '.py': 'python',
      '.cs': 'csharp',
      '.js': 'javascript',
      '.ts': 'typescript',
      '.cpp': 'c_cpp',
      '.c': 'c_cpp',
      '.h': 'c_cpp',
      '.rb': 'ruby',
      '.go': 'golang',
      '.php': 'php',
      '.html': 'html',
      '.css': 'css',
      '.scss': 'sass',
      '.jsx': 'javascript',
      '.tsx': 'typescript',
      '.sql': 'sql',
      '.json': 'json',
      '.xml': 'xml',
      '.md': 'markdown',
      '.txt': 'text'
    };
    return langMap[extension] || 'text';
  };

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPdfError(null);
    setCurrentPage(1);
    setPageInput('1');
  };

  const onDocumentLoadError = (error: Error) => {
    setPdfError(error.message);
  };

  // Charger le contenu DOCX
  useEffect(() => {
    if (file && fileDetails && file.name.toLowerCase().endsWith('.docx') && fileDetails.content instanceof ArrayBuffer) {
      // Vérifier que le fichier n'est pas vide
      if (fileDetails.content.byteLength === 0) {
        setDocxContent('⚠️ Erreur : Le fichier DOCX est vide ou corrompu.');
        return;
      }

      mammoth.extractRawText({ arrayBuffer: fileDetails.content })
        .then(result => {
          if (result.value && result.value.trim().length > 0) {
            setDocxContent(result.value);
          } else {
            setDocxContent('⚠️ Le fichier DOCX semble être vide ou ne contient pas de texte extractible.');
          }
        })
        .catch(err => {
          console.error('Error loading DOCX:', err);
          let errorMessage = 'Erreur lors du chargement du document DOCX.';
          
          if (err.message && err.message.includes('Corrupted zip')) {
            errorMessage = '⚠️ Erreur : Le fichier DOCX est corrompu ou invalide. Veuillez vérifier le fichier.';
          } else if (err.message && err.message.includes('data length = 0')) {
            errorMessage = '⚠️ Erreur : Le fichier DOCX est vide ou n\'a pas pu être lu.';
          } else {
            errorMessage = `⚠️ Erreur : ${err.message || 'Impossible de charger le document DOCX.'}`;
          }
          
          setDocxContent(errorMessage);
        });
    } else if (file && fileDetails && !file.name.toLowerCase().endsWith('.docx')) {
      setDocxContent('');
    }
  }, [file, fileDetails]);

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const processFile = async (file: File): Promise<{ content: string | ArrayBuffer; description: string }> => {
    const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    
    let content: string | ArrayBuffer;
    if (extension === '.pdf' || extension === '.docx') {
      content = await file.arrayBuffer();
    } else {
      content = await file.text();
    }

    return { content, description: file.name };
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0] && onFileSelect) {
      const selectedFile = e.target.files[0];
      const { content, description } = await processFile(selectedFile);
      onFileSelect(selectedFile, { content, description });
    }
  };

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    // Ne désactiver le drag que si on quitte vraiment la zone
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
    if (onDragOver) {
      onDragOver(e);
    }
  }, [onDragOver]);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    if (onDrop) {
      onDrop(e);
      return;
    }

    // Gestion locale du drop si onDrop n'est pas fourni
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0 && onFileSelect) {
      const file = files[0];
      const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      
      const allowedExtensions = [
        '.java', '.py', '.cs', '.js', '.ts', '.cpp', '.c', '.h',
        '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx',
        '.tsx', '.sql', '.docx', '.pdf', '.json', '.xml', '.md', '.txt'
      ];
      
      if (!allowedExtensions.includes(extension)) {
        alert('Type de fichier non supporté');
        return;
      }

      const { content, description } = await processFile(file);
      onFileSelect(file, { content, description });
    }
  }, [onDrop, onFileSelect]);

  if (!file || !fileDetails) {
    // Si un répertoire est sélectionné, afficher un message stylé
    if (selectedDirectory && selectedDirectory.length > 1) {
      return (
        <div 
          className={`flex-1 flex flex-col items-center justify-center border-r border-gray-200 transition-colors relative ${
            isDragging || isProcessingDrop ? 'bg-blue-50 border-blue-300 border-2 border-dashed' : 'bg-gray-50'
          }`}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          {isProcessingDrop && (
            <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90 z-50">
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                <p className="text-blue-600 font-medium">{t('fileviewer.processing')}</p>
              </div>
            </div>
          )}
          <div className="text-center p-8 max-w-lg">
            <div className="mb-6 flex justify-center">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-100 rounded-full blur-xl opacity-50"></div>
                <div className="relative bg-gradient-to-br from-blue-500 to-blue-600 rounded-full p-6 shadow-lg">
                  <svg 
                    className="w-16 h-16 text-white"
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path 
                      strokeLinecap="round" 
                      strokeLinejoin="round" 
                      strokeWidth={2} 
                      d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" 
                    />
                  </svg>
                </div>
              </div>
            </div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">
              {t('fileviewer.directory.selected')}
            </h3>
            <p className="text-gray-600 mb-6">
              {t('fileviewer.directory.selectFile')}
            </p>
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-200 rounded-lg">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm font-medium text-blue-700">
                {selectedDirectory.length} {t('fileviewer.directory.filesAvailable')}
              </span>
            </div>
          </div>
        </div>
      );
    }
    
    // Message par défaut pour drag and drop
    return (
      <div 
        className={`flex-1 flex flex-col items-center justify-center border-r border-gray-200 transition-colors relative ${
          isDragging || isProcessingDrop ? 'bg-blue-50 border-blue-300 border-2 border-dashed' : 'bg-gray-50'
        }`}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {isProcessingDrop && (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90 z-50">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
              <p className="text-blue-600 font-medium">{t('fileviewer.processing')}</p>
            </div>
          </div>
        )}
        <div className={`text-center p-8 max-w-md transition-all ${isDragging ? 'scale-105' : ''}`}>
          <div className="mb-6">
            <svg 
              className={`mx-auto h-16 w-16 transition-colors ${
                isDragging ? 'text-blue-500' : 'text-gray-400'
              }`}
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={1.5} 
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" 
              />
            </svg>
          </div>
          <h3 className={`text-lg font-semibold mb-2 transition-colors ${
            isDragging ? 'text-blue-600' : 'text-gray-700'
          }`}>
            {isDragging ? t('fileviewer.dragDrop') : t('fileviewer.dragDrop')}
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            {t('fileviewer.uploadHint')}
          </p>
          <button
            onClick={handleFileClick}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {t('fileviewer.selectFile')}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleFileChange}
            accept=".pdf,.docx,.txt,.md,.java,.py,.js,.ts,.cpp,.c,.h,.cs,.rb,.go,.php,.html,.css,.scss,.jsx,.tsx,.sql,.json,.xml"
          />
        </div>
      </div>
    );
  }


  return (
    <div className="flex-1 flex flex-col bg-white dark:bg-gray-900 dark-blue:bg-blue-950 overflow-hidden relative h-full">
      {/* Header */}
      <div className="px-4 py-2 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center">
              <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-800">{file.name}</h3>
              <p className="text-xs text-gray-500">{extension.toUpperCase()} file</p>
            </div>
          </div>
          {isPdfFile && numPages && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">
                {numPages} {numPages > 1 ? t('common.pages') : t('common.page')}
              </span>
            </div>
          )}
        </div>
        
        {/* Contrôles de zoom et navigation - Centré en bas du titre */}
        {isPdfFile && numPages && numPages > 0 && (
          <div className="flex items-center justify-center gap-1 bg-gray-50 rounded-md px-1.5 py-0.5">
            <button
              onClick={() => setScale(prev => Math.max(0.5, prev - 0.1))}
              className="p-0.5 hover:bg-gray-200 rounded text-gray-700 transition-colors"
              title={t('fileviewer.zoom.out')}
            >
              <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
              </svg>
            </button>
            <span className="text-[10px] text-gray-700 font-medium min-w-[1.75rem] text-center">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={() => setScale(prev => Math.min(2.0, prev + 0.1))}
              className="p-0.5 hover:bg-gray-200 rounded text-gray-700 transition-colors"
              title={t('fileviewer.zoom.in')}
            >
              <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
              </svg>
            </button>
            
            <div className="h-2.5 w-px bg-gray-300 mx-0.5"></div>
            
            <button
              onClick={() => {
                const newPage = Math.max(1, currentPage - 1);
                setCurrentPage(newPage);
                setPageInput(newPage.toString());
                containerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              disabled={currentPage <= 1}
              className="p-0.5 hover:bg-gray-200 rounded text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={t('fileviewer.page.previous')}
            >
              <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <div className="flex items-center gap-0.5">
              <input
                type="number"
                min="1"
                max={numPages}
                value={pageInput}
                onChange={(e) => {
                  const value = e.target.value;
                  setPageInput(value);
                  const pageNum = parseInt(value);
                  if (!isNaN(pageNum) && pageNum >= 1 && pageNum <= numPages) {
                    setCurrentPage(pageNum);
                    containerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
                  }
                }}
                onBlur={() => {
                  const pageNum = parseInt(pageInput);
                  if (isNaN(pageNum) || pageNum < 1) {
                    setPageInput('1');
                    setCurrentPage(1);
                  } else if (pageNum > numPages) {
                    setPageInput(numPages.toString());
                    setCurrentPage(numPages);
                  } else {
                    setPageInput(pageNum.toString());
                    setCurrentPage(pageNum);
                  }
                }}
                className="w-7 px-0.5 py-0.5 text-[10px] text-center border border-gray-300 rounded bg-white text-gray-800 focus:outline-none focus:ring-1 focus:ring-gray-400"
              />
              <span className="text-[10px] text-gray-700"> {t('fileviewer.page.of')} {numPages}</span>
            </div>
            <button
              onClick={() => {
                const newPage = Math.min(numPages, currentPage + 1);
                setCurrentPage(newPage);
                setPageInput(newPage.toString());
                containerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              disabled={currentPage >= numPages}
              className="p-0.5 hover:bg-gray-200 rounded text-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title={t('fileviewer.page.next')}
            >
              <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
            
            <div className="h-2.5 w-px bg-gray-300 mx-0.5"></div>
            
            <button
              onClick={() => {
                const searchQuery = prompt(t('fileviewer.search.prompt') + ':');
                if (searchQuery) {
                  containerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
                }
              }}
              className="p-0.5 hover:bg-gray-200 rounded text-gray-700 transition-colors"
              title={t('fileviewer.page.search')}
            >
              <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden bg-gray-50 pr-2 fileviewer-content" style={{ scrollbarWidth: 'thin', scrollbarColor: '#cbd5e0 #f7fafc', minHeight: 0 }}>
        {isCodeFile && typeof fileDetails.content === 'string' ? (
          <div className="h-full p-4 overflow-auto" style={{ scrollbarWidth: 'thin', scrollbarColor: '#cbd5e0 #f7fafc' }}>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <AceEditor
                mode={getLanguage(extension)}
                theme="monokai"
                value={fileDetails.content}
                readOnly={true}
                name="file-viewer"
                editorProps={{ $blockScrolling: true }}
                setOptions={{
                  showLineNumbers: true,
                  showGutter: true,
                  tabSize: 2,
                  readOnly: true,
                  fontSize: 13,
                  fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, monospace'
                }}
                style={{ width: '100%', minHeight: '500px' }}
              />
            </div>
          </div>
        ) : (isPdfFile && pdfBlob) ? (
          pdfError ? (
            <div className="h-full flex items-center justify-center p-6">
              <div className="bg-white rounded-lg p-6 text-center">
                <p className="text-red-600 text-sm">{pdfError}</p>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col relative min-h-0">
              <div 
                className="flex-1 overflow-y-auto overflow-x-hidden pr-2 pdf-scroll-container" 
                ref={containerRef} 
                style={{ 
                  scrollbarWidth: 'thin', 
                  scrollbarColor: '#cbd5e0 #f7fafc',
                  minHeight: 0
                }}
              >
                <div className="flex flex-col items-center p-4">
                  <Document
                    file={pdfBlob}
                    onLoadSuccess={onDocumentLoadSuccess}
                    onLoadError={onDocumentLoadError}
                    loading={
                      <div className="text-center py-8">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <p className="mt-2 text-sm text-gray-600">{t('fileviewer.pdf.loading')}</p>
                      </div>
                    }
                    error={
                      <div className="text-center py-8">
                        <p className="text-red-600 text-sm">{t('fileviewer.pdf.error')}</p>
                      </div>
                    }
                  >
                    {numPages && numPages > 0 && (
                      <>
                        {Array.from(new Array(numPages), (el, index) => (
                          <div key={`page_${index + 1}`} className="mb-4 shadow-sm bg-white">
                            <Page
                              pageNumber={index + 1}
                              width={Math.min((containerWidth > 0 ? containerWidth - 64 : 800) * scale, 1200)}
                              scale={scale}
                              renderTextLayer={true}
                              renderAnnotationLayer={true}
                            />
                          </div>
                        ))}
                      </>
                    )}
                  </Document>
                </div>
              </div>
            </div>
          )
        ) : (isDocxFile && fileDetails.content instanceof ArrayBuffer) ? (
          <div className="h-full p-4 overflow-auto" style={{ scrollbarWidth: 'thin', scrollbarColor: '#cbd5e0 #f7fafc' }}>
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div className="prose max-w-none">
                {docxContent && (docxContent.startsWith('⚠️') || docxContent.startsWith('Error')) ? (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-sm text-red-800 font-medium">{docxContent}</p>
                  </div>
                ) : (
                  <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans">
                    {docxContent || t('fileviewer.docx.error')}
                  </pre>
                )}
              </div>
            </div>
          </div>
        ) : typeof fileDetails.content === 'string' ? (
          <div className="h-full p-4 overflow-y-auto">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono">
                {fileDetails.content}
              </pre>
            </div>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center p-6">
            <div className="bg-white rounded-lg p-6 text-center">
              <p className="text-gray-500 text-sm">{t('fileviewer.unsupported')}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FileViewer;

