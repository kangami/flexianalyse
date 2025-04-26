import React, { useState, useEffect, useRef } from 'react';
import QueryForm from './QueryForm';
import AceEditor from 'react-ace';
import mammoth from 'mammoth';
import { Document, Page, pdfjs } from 'react-pdf';
import { Packer, Document as DocxDocument, Paragraph, TextRun } from 'docx';
import { saveAs } from 'file-saver';
import { CKEditor } from '@ckeditor/ckeditor5-react';
import ClassicEditor from '@ckeditor/ckeditor5-build-classic';
import { htmlToText } from 'html-to-text';

import ace from 'ace-builds/src-noconflict/ace'; 

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

// Configure Ace to load worker scripts from the correct path
ace.config.set('basePath', '/node_modules/ace-builds/src-noconflict');
pdfjs.GlobalWorkerOptions.workerSrc = '/pdf.worker.js';

interface FileDetails {
  content: string | ArrayBuffer;
  description: string;
}

interface ChatMessage {
  userQuery: string;
  aiResponse: string;
  displayedAiResponse?: string;
}

interface FileSelectedComponentProps {
  file: File;
  details: FileDetails;
  isFileContentVisible: boolean;
  setIsFileContentVisible: (visible: boolean) => void;
  chatHistory: ChatMessage[];
  setFileDetails: (details: FileDetails | null) => void;
  onQuerySubmit: (query: string) => void;
  loading: boolean;
  selectedModel: string;
}

const FileSelectedComponent: React.FC<FileSelectedComponentProps> = ({ file, details, isFileContentVisible, 
  setIsFileContentVisible, chatHistory, setFileDetails, onQuerySubmit, loading, selectedModel}) => {
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

  // State for editable content
  const [codeContent, setCodeContent] = useState<string>(
    isCodeFile && typeof details.content === 'string' ? details.content : ''
  );

  // State for .docx content
  const [docxContent, setDocxContent] = useState<string | null>(null);
  const [editedDocxContent, setEditedDocxContent] = useState<string>('');

  // State for .pdf pages
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pdfError, setPdfError] = useState<string | null>(null);

  // State for animated chat messages
  const [animatedChatHistory, setAnimatedChatHistory] = useState<ChatMessage[]>([]);

  // Update codeContent when the file or details change
  useEffect(() => {
    if (isCodeFile && typeof details.content === 'string') {
      setCodeContent(details.content);
    }
  }, [isCodeFile, details.content]);

  // Store the original .docx ArrayBuffer to avoid overwriting it
  const [originalDocxBuffer, setOriginalDocxBuffer] = useState<ArrayBuffer | null>(null);

  // Extract .docx content using mammoth
  useEffect(() => {
    if (isDocxFile && details.content instanceof ArrayBuffer) {
      setOriginalDocxBuffer(details.content);
      mammoth
        .convertToHtml({ arrayBuffer: details.content })
        .then((result) => {
          setDocxContent(result.value);
          setEditedDocxContent(result.value);
        })
        .catch((err) => {
          console.error('Error extracting .docx content:', err.message, err.stack);
          setDocxContent(`<p>Erreur lors de l'extraction du contenu .docx : ${err.message}</p>`);
          setEditedDocxContent(`<p>Erreur lors de l'extraction du contenu .docx : ${err.message}</p>`);
        });
    } else {
      setDocxContent(null);
      setEditedDocxContent('');
      setOriginalDocxBuffer(null);
    }
  }, [isDocxFile, details.content]);

  // Update editedDocxContent when chatHistory changes (for AI modifications)
  useEffect(() => {
    if (isDocxFile && chatHistory.length > 0) {
      const latestMessage = chatHistory[chatHistory.length - 1];
      const aiResponse = latestMessage.aiResponse;

      // Use regex to detect the modified content block
      const modifiedContentMatch = aiResponse.match(/```modified-file-content\n([\s\S]*?)\n```/);
      let modifiedContent: string | null = null;

      if (modifiedContentMatch && modifiedContentMatch[1]) {
        modifiedContent = modifiedContentMatch[1].trim();
      } else {
        const updateDocxContent = async () => {
          let originalText = '';
          if (docxContent && originalDocxBuffer) {
            try {
              const result = await mammoth.convertToHtml({ arrayBuffer: originalDocxBuffer });
              originalText = result.value;
            } catch (err) {
              console.error('Error converting original .docx for comparison:', err);
              originalText = '';
            }
          }

          const lines = aiResponse.split('\n');
          let potentialContent: string[] = [];
          let isCollecting = false;

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!isCollecting && trimmedLine.length > 0 && originalText.includes(trimmedLine)) {
              isCollecting = true;
              potentialContent.push(line);
            } else if (isCollecting) {
              if (trimmedLine === '' && potentialContent.length > 0) {
                break;
              }
              potentialContent.push(line);
            }
          }

          if (potentialContent.length > 0) {
            modifiedContent = potentialContent.join('\n').trim();
          }

          if (modifiedContent) {
            // Convert the modified text content to HTML for CKEditor
            const htmlContent = `<p>${modifiedContent.replace(/\n/g, '</p><p>')}</p>`;
            setEditedDocxContent(htmlContent);
          }
        };

        updateDocxContent();
      }

      if (modifiedContent) {
        // Convert the modified text content to HTML for CKEditor
        const htmlContent = `<p>${modifiedContent.replace(/\n/g, '</p><p>')}</p>`;
        setEditedDocxContent(htmlContent);
      }
    }
  }, [isDocxFile, chatHistory, docxContent, originalDocxBuffer]);

  // Typing animation effect for aiResponse
  useEffect(() => {
    // If no new message or chatHistory is empty, reset or do nothing
    if (chatHistory.length === 0) {
      setAnimatedChatHistory([]);
      return;
    }

    // Check if the latest message in chatHistory already exists in animatedChatHistory
    const latestChatMessage = chatHistory[chatHistory.length - 1];
    const latestAnimatedMessage = animatedChatHistory[animatedChatHistory.length - 1];

    // If the latest message is already in animatedChatHistory, or if there's no aiResponse, do nothing
    if (latestAnimatedMessage && latestAnimatedMessage.userQuery === latestChatMessage.userQuery && latestAnimatedMessage.aiResponse === latestChatMessage.aiResponse) {
      return;
    }

    // If the latest message in chatHistory doesn't have an aiResponse yet, do nothing
    if (!latestChatMessage.aiResponse) return;

    // Update animatedChatHistory with the latest message (which now has an aiResponse)
    const newMessageIndex = chatHistory.length - 1;
    const newMessage = chatHistory[newMessageIndex];

    const updatedChatHistory = [...animatedChatHistory];
    updatedChatHistory[newMessageIndex] = { ...newMessage, displayedAiResponse: '' };
    setAnimatedChatHistory(updatedChatHistory);

    let currentIndex = 0;
    const fullContent = newMessage.aiResponse;
    const typingSpeed = 10;

    const typingInterval = setInterval(() => {
      if (currentIndex < fullContent.length) {
        setAnimatedChatHistory((prev) => {
          const newHistory = [...prev];
          newHistory[newMessageIndex].displayedAiResponse = fullContent.slice(0, currentIndex + 1);
          return newHistory;
        });
        currentIndex++;
      } else {
        clearInterval(typingInterval);
      }
    }, typingSpeed);

    // Clean up
    return () => clearInterval(typingInterval);
  }, [chatHistory]);

  // Handle query submission to show user query immediately
  const handleQuerySubmit = (query: string) => {
    // Immediately append the user query to animatedChatHistory
    const newMessage: ChatMessage = { userQuery: query, aiResponse: '' };
    setAnimatedChatHistory((prev) => [...prev, newMessage]);

    // Call the original onQuerySubmit to trigger the API call
    onQuerySubmit(query);
  };

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

  // Save edited code content
  const handleSaveCode = () => {
    console.log('Saving code content:', codeContent);
    const blob = new Blob([codeContent], { type: 'text/plain;charset=utf-8' });
    saveAs(blob, file.name);
  };

  // Parse HTML and map to docx elements
  const parseHtmlToDocx = (html: string) => {
    const paragraphs: Paragraph[] = [];
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const elements = doc.body.childNodes;

    elements.forEach((element) => {
      if (element.nodeName === 'P') {
        const paragraphTextRuns: TextRun[] = [];
        const processNode = (node: Node, currentTextRuns: TextRun[]) => {
          if (node.nodeType === Node.TEXT_NODE) {
            const text = node.textContent?.trim();
            if (text) {
              currentTextRuns.push(new TextRun({ text }));
            }
          } else if (node.nodeType === Node.ELEMENT_NODE) {
            const el = node as HTMLElement;
            let text = el.textContent?.trim() || '';
            if (!text && el.tagName !== 'BR') return;

            if (el.tagName === 'STRONG') {
              currentTextRuns.push(new TextRun({ text, bold: true }));
            } else if (el.tagName === 'I') {
              currentTextRuns.push(new TextRun({ text, italics: true }));
            } else if (el.tagName === 'U') {
              currentTextRuns.push(new TextRun({ text, underline: { type: 'SINGLE' } }));
            } else if (el.tagName === 'A') {
              const href = el.getAttribute('href') || '';
              currentTextRuns.push(new TextRun({ text: `${text} (${href})`, color: '0000FF', underline: { type: 'SINGLE' } }));
            } else if (el.tagName === 'BR') {
              if (currentTextRuns.length > 0) {
                paragraphs.push(new Paragraph({ children: [...currentTextRuns] }));
                currentTextRuns.length = 0;
              }
              currentTextRuns.push(TextRun.break());
            } else {
              Array.from(el.childNodes).forEach(child => processNode(child, currentTextRuns));
            }
          }
        };

        Array.from(element.childNodes).forEach(child => processNode(child, paragraphTextRuns));
        if (paragraphTextRuns.length > 0) {
          paragraphs.push(new Paragraph({ children: paragraphTextRuns }));
        }
      }
    });

    return paragraphs;
  };

  // Save edited .docx content
  const handleSaveDocx = () => {
    const paragraphs = parseHtmlToDocx(editedDocxContent);
    const doc = new DocxDocument({
      sections: [
        {
          properties: {},
          children: paragraphs,
        },
      ],
    });
    Packer.toBlob(doc).then((blob) => {
      saveAs(blob, file.name);
    }).catch((err) => {
      console.error('Error saving .docx file:', err);
    });
  };

  return (
    <div className="flex-1 flex flex-col h-screen">
      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-4">
          <h2 className="text-lg font-semibold">{file.name}</h2>
        </div>
        <div className="mt-4 flex justify-center">
          <div className="w-full max-w-2xl">
            {animatedChatHistory.length > 0 ? (
              animatedChatHistory.map((message, index) => (
                <div key={index} className="mb-4">
                  {/* User Query (Right Side, Light Blue Background) */}
                  <div className="flex justify-end mb-2">
                    <div className="bg-blue-100 text-gray-800 p-3 rounded-lg max-w-md">
                      <p>{message.userQuery}</p>
                    </div>
                  </div>
                  {/* Model Response (Left Side, Light Gray Background) */}
                  <div className="flex justify-start">
                    <div className=" text-gray-800 p-3 max-w-md">
                      <p className="whitespace-pre-wrap">{message.displayedAiResponse || ''}</p>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-gray-600 text-center">No messages yet. Ask a question below!</p>
            )}
            {/* Loading Animation (Left Side) */}
            {loading && (
              <div className="flex justify-start mb-2">
                <div className="bg-gray-100 p-3 rounded-lg max-w-md flex items-center">
                  <div className="w-6 h-6 border-4 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {isFileContentVisible && (
        <div className="fixed pb-20 mb-8 ml-20 mr-20 h-2/3 bottom-20 left-72 right-4 z-10 bg-gray-50 p-4 rounded-md shadow-md border border-gray-200">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-semibold">{file.name}</h3>
            <div className="flex items-center space-x-2">
              {(isCodeFile || isDocxFile) && (
                <button
                  onClick={isCodeFile ? handleSaveCode : handleSaveDocx}
                  className="text-blue-500 hover:text-blue-700 text-sm"
                >
                  Save
                </button>
              )}
              <button
                onClick={() => setIsFileContentVisible(false)}
                className="text-gray-500 hover:text-blue-700"
              >
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0.0.0 24"
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
          </div>
          <div className="h-full overflow-y-auto">
            {isCodeFile && typeof details.content === 'string' ? (
              <AceEditor
                mode={getLanguage(extension)}
                theme="monokai"
                value={codeContent}
                onChange={(newValue) => setCodeContent(newValue)}
                name="code-editor"
                editorProps={{ $blockScrolling: true }}
                setOptions={{
                  enableBasicAutocompletion: true,
                  enableLiveAutocompletion: true,
                  enableSnippets: true,
                  showLineNumbers: true,
                  tabSize: 2,
                }}
                style={{ width: '100%', height: '100%' }}
              />
            ) : isDocxFile ? (
              docxContent ? (
                <CKEditor
                  editor={ClassicEditor}
                  data={editedDocxContent}
                  onChange={(event, editor) => {
                    const data = editor.getData();
                    setEditedDocxContent(data);
                  }}
                  config={{
                    toolbar: [
                      'heading', '|',
                      'bold', 'italic', 'underline', 'strikethrough', '|',
                      'bulletedList', 'numberedList', '|',
                      'undo', 'redo'
                    ],
                  }}
                />
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
                        scale={0.5}
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

      <QueryForm
        isFileContentVisible={isFileContentVisible}
        setIsFileContentVisible={setIsFileContentVisible}
        onQuerySubmit={handleQuerySubmit}
        loading={loading}
        selectedModel={selectedModel}
      />
    </div>
  );
};

export default FileSelectedComponent;