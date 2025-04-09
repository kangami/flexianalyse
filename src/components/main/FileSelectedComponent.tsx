import React, { useState, useEffect } from 'react';
import QueryForm from './QueryForm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import mammoth from 'mammoth';
import { Document, Page, pdfjs } from 'react-pdf';
import * as pdfjsLib from 'pdfjs-dist';

// Set up the pdf.js worker using the local worker script
pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.js';

interface FileDetails {
  content: string | ArrayBuffer; // Use ArrayBuffer for binary files
  description: string;
}

interface FileSelectedComponentProps {
  file: File;
  details: FileDetails;
  isFileContentVisible: boolean;
  setIsFileContentVisible: (visible: boolean) => void;
}

const FileSelectedComponent: React.FC<FileSelectedComponentProps> = ({ file, details, isFileContentVisible, setIsFileContentVisible }) => {
  // Define code file extensions
  const codeExtensions = [
    '.java', '.py', '.cs', '.js', '.ts', '.cpp', '.c', '.h',
    '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx',
    '.tsx', '.sql',
  ];

  // Determine file type
  const extension = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
  const isCodeFile = codeExtensions.includes(extension);
  const isDocxFile = extension === '.docx';
  const isPdfFile = extension === '.pdf';

  // State for .docx content
  const [docxContent, setDocxContent] = useState<string | null>(null);
  // State for .pdf pages
  const [numPages, setNumPages] = useState<number | null>(null);
  // State for PDF loading error
  const [pdfError, setPdfError] = useState<string | null>(null);

  // Extract .docx content using mammoth
  useEffect(() => {
    if (isDocxFile && details.content instanceof ArrayBuffer) {
      mammoth
        .extractRawText({ arrayBuffer: details.content })
        .then((result) => {
          setDocxContent(result.value);
        })
        .catch((err) => {
          console.error('Error extracting .docx content:', err);
          setDocxContent('Error extracting .docx content.');
        });
    }
  }, [isDocxFile, details.content]);

  // Determine language for syntax highlighting
  const getLanguage = (ext: string): string => {
    switch (ext) {
      case '.java': return 'java';
      case '.py': return 'python';
      case '.cs': return 'csharp';
      case '.js': return 'javascript';
      case '.ts': return 'typescript';
      case '.cpp': case '.c': case '.h': return 'cpp';
      case '.rb': return 'ruby';
      case '.go': return 'go';
      case '.php': return 'php';
      case '.html': return 'html';
      case '.css': return 'css';
      case '.scss': return 'scss';
      case '.jsx': return 'jsx';
      case '.tsx': return 'tsx';
      case '.sql': return 'sql';
      default: return 'text';
    }
  };

  // Handle PDF load success
  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPdfError(null);
  };
  // Handle PDF load error
  const onDocumentLoadError = (error: Error) => {
    console.error('Error loading PDF:', error);
    setPdfError('Failed to load PDF file.');
  };

  return (
    <div className="flex-1 flex flex-col h-screen">
      {/* Scrollable File Description (Main Discussion Chat) */}
      <div className="flex-1 overflow-y-auto p-4">
        {/* File Description */}
        <div className="mb-4">
          <h2 className="text-lg font-semibold">{file.name}</h2>
          <p className="text-gray-600">{details.description}</p>
          {/* Placeholder for chat messages (this can grow) */}
          <div className="mt-4">
            {/* Simulate chat messages */}
            {Array.from({ length: 20 }).map((_, index) => (
              <p key={index} className="text-gray-600">
                Chat message {index + 1}: This is a sample message to demonstrate scrolling.
              </p>
            ))}
          </div>
        </div>
      </div>

      {/* File Content */}
      {isFileContentVisible && (
        <div className="fixed pb-20 mb-8 ml-20 mr-20 h-2/3 bottom-20 left-72 right-4 z-10 bg-gray-50 p-4 rounded-md shadow-md border border-gray-200">
          <div className="flex justify-between items-center ">
            <h3 className="text-sm font-semibold">{file.name}</h3>
            <button
              onClick={() => setIsFileContentVisible(false)}
              className="text-gray-500 hover:text-blue-700"
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
                  d="M20 12H4"
                />
              </svg>
            </button>
          </div>
          <div className="h-full overflow-y-auto">
            {isCodeFile && typeof details.content === 'string' ? (
              <SyntaxHighlighter
                language={getLanguage(extension)}
                style={vscDarkPlus}
                customStyle={{ margin: 0, padding: 4, background: 'black' }}
              >
                {details.content}
              </SyntaxHighlighter>
            ) : isDocxFile ? (
              docxContent ? (
                <pre className="text-sm text-gray-800 whitespace-pre-wrap">
                  {docxContent}
                </pre>
              ) : (
                <div className="text-gray-600 text-sm">
                  Loading .docx content...
                </div>
              )
            ) : isPdfFile && details.content instanceof ArrayBuffer ? (
              pdfError ? (
                <div className="text-red-600 text-sm">
                  {pdfError}
                </div>
              ) : (
                <Document
                  file={details.content}
                  onLoadSuccess={onDocumentLoadSuccess}
                  onLoadError={onDocumentLoadError}
                >
                  {numPages &&
                    Array.from(new Array(numPages), (el, index) => (
                      <Page
                        key={`page_${index + 1}`}
                        pageNumber={index + 1}
                        scale={0.5} // Adjust scale to fit within the container
                      />
                    ))}
                </Document>
              )
            ) : (
              <div className="text-gray-600 text-sm">
                Unsupported file type.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Query Form */}
      <QueryForm
        isFileContentVisible={isFileContentVisible}
        setIsFileContentVisible={setIsFileContentVisible}
      />
    </div>
  );
};

export default FileSelectedComponent;