import React, { useState, useEffect, useRef } from 'react';
import AceEditor from 'react-ace';
import mammoth from 'mammoth';
import { CKEditor } from '@ckeditor/ckeditor5-react';
import ClassicEditor from '@ckeditor/ckeditor5-build-classic';

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

interface EditableFile {
  file: File;
  content: string | ArrayBuffer;
  type: 'code' | 'docx';
}

interface InsertTextModalProps {
  selectedText: string;
  editableFiles: EditableFile[];
  onInsert: (file: File, text: string, lineNumber?: number) => void;
  onClose: () => void;
  getEditableFiles?: () => Promise<EditableFile[]>;
}

const InsertTextModal: React.FC<InsertTextModalProps> = ({
  selectedText,
  editableFiles: initialEditableFiles,
  onInsert,
  onClose,
  getEditableFiles
}) => {
  const [editableFiles, setEditableFiles] = useState<EditableFile[]>(initialEditableFiles);
  const [selectedFileIndex, setSelectedFileIndex] = useState<number>(0);
  const [insertMode, setInsertMode] = useState<'auto' | 'manual'>('auto');
  const [insertLineNumber, setInsertLineNumber] = useState<string>('');
  const [fileContent, setFileContent] = useState<string>('');
  const [docxContent, setDocxContent] = useState<string>('');
  const [highlightLine, setHighlightLine] = useState<number | null>(null);
  const [loadingFiles, setLoadingFiles] = useState<boolean>(false);
  const editorRef = useRef<any>(null);

  const codeExtensions = [
    '.java', '.py', '.cs', '.js', '.ts', '.cpp', '.c', '.h',
    '.rb', '.go', '.php', '.html', '.css', '.scss', '.jsx',
    '.tsx', '.sql', '.json', '.xml', '.md', '.txt'
  ];

  // Charger les fichiers éditables si getEditableFiles est fourni
  useEffect(() => {
    if (getEditableFiles && editableFiles.length === 0) {
      setLoadingFiles(true);
      getEditableFiles()
        .then(files => {
          setEditableFiles(files);
          if (files.length > 0) {
            setSelectedFileIndex(0);
          }
        })
        .catch(err => {
          console.error('Erreur lors du chargement des fichiers:', err);
        })
        .finally(() => {
          setLoadingFiles(false);
        });
    } else if (editableFiles.length > 0) {
      setSelectedFileIndex(0);
    }
  }, [editableFiles.length, getEditableFiles]);

  // Charger le contenu du fichier sélectionné
  useEffect(() => {
    if (editableFiles.length === 0) return;

    const selectedFileData = editableFiles[selectedFileIndex];
    if (!selectedFileData) return;

    const extension = selectedFileData.file.name.substring(
      selectedFileData.file.name.lastIndexOf('.')
    ).toLowerCase();

    if (selectedFileData.type === 'code' && typeof selectedFileData.content === 'string') {
      setFileContent(selectedFileData.content);
      setDocxContent('');
      
      // Calculer la ligne d'insertion pour le mode auto
      if (insertMode === 'auto') {
        const lines = selectedFileData.content.split('\n');
        setHighlightLine(lines.length);
        // Scroll vers la fin après un court délai
        setTimeout(() => {
          if (editorRef.current) {
            const editor = editorRef.current.editor;
            if (editor) {
              const session = editor.getSession();
              session.setScrollTop(Infinity);
            }
          }
        }, 100);
      } else if (insertLineNumber) {
        const lineNum = parseInt(insertLineNumber, 10);
        if (lineNum > 0 && lineNum <= lines.length) {
          setHighlightLine(lineNum);
          setTimeout(() => {
            if (editorRef.current) {
              const editor = editorRef.current.editor;
              if (editor) {
                const session = editor.getSession();
                editor.gotoLine(lineNum);
              }
            }
          }, 100);
        }
      }
    } else if (selectedFileData.type === 'docx' && selectedFileData.content instanceof ArrayBuffer) {
      setFileContent('');
      // Charger le contenu DOCX
      mammoth.extractRawText({ arrayBuffer: selectedFileData.content })
        .then(result => {
          setDocxContent(result.value);
        })
        .catch(err => {
          console.error('Error loading DOCX:', err);
          setDocxContent('Error loading document');
        });
    }
  }, [selectedFileIndex, editableFiles, insertMode, insertLineNumber]);

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

  const handleInsert = () => {
    if (editableFiles.length === 0) return;

    const selectedFileData = editableFiles[selectedFileIndex];
    let lineNum: number | undefined;
    
    if (insertMode === 'manual' && insertLineNumber) {
      lineNum = parseInt(insertLineNumber, 10);
      if (isNaN(lineNum) || lineNum < 1) {
        alert('Veuillez entrer un numéro de ligne valide (≥ 1)');
        return;
      }
    }
    // Mode auto : passer undefined pour que le texte soit ajouté à la fin
    // (le code dans handleInsertText gère undefined en faisant lines.push(text))

    onInsert(selectedFileData.file, selectedText, lineNum);
    onClose();
  };

  const selectedFileData = editableFiles[selectedFileIndex];
  const isCodeFile = selectedFileData?.type === 'code';
  const extension = selectedFileData 
    ? selectedFileData.file.name.substring(selectedFileData.file.name.lastIndexOf('.')).toLowerCase()
    : '';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b">
          <h3 className="text-lg font-semibold text-gray-800">
            📝 Insérer le texte dans le document
          </h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl font-bold"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Left panel - File selection and options */}
          <div className="w-80 border-r p-4 overflow-y-auto flex flex-col">
            {/* Selected text preview */}
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-700 mb-2">Texte sélectionné :</p>
              <div className="bg-gray-50 p-3 rounded border border-gray-200 max-h-32 overflow-y-auto">
                <p className="text-sm text-gray-800">{selectedText}</p>
              </div>
            </div>

            {/* File selection */}
            {editableFiles.length > 0 && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Fichier à modifier :
                </label>
                <select
                  value={selectedFileIndex}
                  onChange={(e) => {
                    const newIndex = parseInt(e.target.value, 10);
                    setSelectedFileIndex(newIndex);
                    setInsertLineNumber(''); // Reset line number when changing file
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {editableFiles.map((fileData, index) => (
                    <option key={index} value={index}>
                      {fileData.file.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Insert mode */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Mode d'insertion :
              </label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="auto"
                    checked={insertMode === 'auto'}
                    onChange={(e) => {
                      setInsertMode(e.target.value as 'auto' | 'manual');
                      setInsertLineNumber('');
                    }}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Auto : Ajouter à la fin</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="manual"
                    checked={insertMode === 'manual'}
                    onChange={(e) => setInsertMode(e.target.value as 'auto' | 'manual')}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">Manuel : Spécifier la ligne</span>
                </label>
              </div>
            </div>

            {/* Line number input */}
            {insertMode === 'manual' && isCodeFile && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Numéro de ligne :
                </label>
                <input
                  type="number"
                  min="1"
                  value={insertLineNumber}
                  onChange={(e) => {
                    const value = e.target.value;
                    setInsertLineNumber(value);
                    const lineNum = parseInt(value, 10);
                    if (lineNum > 0 && fileContent) {
                      const lines = fileContent.split('\n');
                      if (lineNum <= lines.length) {
                        setHighlightLine(lineNum);
                        setTimeout(() => {
                          if (editorRef.current) {
                            const editor = editorRef.current.editor;
                            if (editor) {
                              editor.gotoLine(lineNum, 0, true);
                            }
                          }
                        }, 100);
                      }
                    }
                  }}
                  onFocus={(e) => e.target.select()}
                  placeholder="Ex: 10"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  autoFocus={insertMode === 'manual'}
                />
                <p className="text-xs text-gray-500 mt-1">
                  {fileContent ? (
                    <>
                      Le document a <strong>{fileContent.split('\n').length}</strong> ligne{fileContent.split('\n').length > 1 ? 's' : ''}.
                      {insertMode === 'manual' && (
                        <span className="block mt-1 text-blue-600">
                          💡 Cliquez sur un numéro de ligne dans l'aperçu pour le sélectionner automatiquement
                        </span>
                      )}
                    </>
                  ) : ''}
                </p>
              </div>
            )}

            {/* Action buttons */}
            <div className="mt-auto pt-4 border-t flex gap-3">
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium"
              >
                Annuler
              </button>
              <button
                onClick={handleInsert}
                className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium"
              >
                {insertMode === 'auto' ? 'Ajouter' : 'Insérer'}
              </button>
            </div>
          </div>

          {/* Right panel - File preview */}
          <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
            {selectedFileData && (
              <>
                <h4 className="text-sm font-semibold text-gray-700 mb-2">
                  {selectedFileData.file.name}
                </h4>
                {isCodeFile && fileContent ? (
                  <div className="relative">
                    <AceEditor
                      ref={editorRef}
                      mode={getLanguage(extension)}
                      theme="monokai"
                      value={fileContent}
                      readOnly={true}
                      name="file-preview"
                      editorProps={{ $blockScrolling: true }}
                      setOptions={{
                        showLineNumbers: true,
                        showGutter: true,
                        tabSize: 2,
                        readOnly: true,
                        highlightActiveLine: false,
                        highlightGutterLine: false,
                        fontSize: 13,
                        fontFamily: 'Monaco, Menlo, "Ubuntu Mono", Consolas, "source-code-pro", monospace'
                      }}
                      style={{ width: '100%', minHeight: '400px' }}
                      markers={
                        highlightLine !== null
                          ? [
                              {
                                startRow: insertMode === 'auto' ? fileContent.split('\n').length - 1 : highlightLine - 1,
                                startCol: 0,
                                endRow: insertMode === 'auto' ? fileContent.split('\n').length - 1 : highlightLine - 1,
                                endCol: 1000,
                                className: 'insertion-marker',
                                type: 'fullLine'
                              }
                            ]
                          : []
                      }
                      onGutterClick={(e) => {
                        // Permettre de cliquer sur le numéro de ligne pour le sélectionner
                        if (insertMode === 'manual') {
                          const lineNum = e.getDocumentPosition().row + 1;
                          setInsertLineNumber(lineNum.toString());
                          setHighlightLine(lineNum);
                          setTimeout(() => {
                            if (editorRef.current) {
                              const editor = editorRef.current.editor;
                              if (editor) {
                                editor.gotoLine(lineNum, 0, true);
                              }
                            }
                          }, 100);
                        }
                      }}
                    />
                    <style>{`
                      .insertion-marker {
                        background-color: rgba(34, 197, 94, 0.3) !important;
                        position: absolute;
                        z-index: 1;
                      }
                      .ace_gutter {
                        cursor: ${insertMode === 'manual' ? 'pointer' : 'default'} !important;
                      }
                      .ace_gutter-cell {
                        user-select: none;
                      }
                      .ace_gutter-cell:hover {
                        background-color: ${insertMode === 'manual' ? 'rgba(59, 130, 246, 0.1)' : 'transparent'} !important;
                      }
                    `}</style>
                  </div>
                ) : selectedFileData.type === 'docx' ? (
                  <div className="bg-white p-4 rounded border border-gray-200 min-h-[400px]">
                    {docxContent ? (
                      <div className="prose max-w-none">
                        <pre className="whitespace-pre-wrap text-sm">{docxContent}</pre>
                        {insertMode === 'auto' && (
                          <div className="mt-4 p-2 bg-green-100 border-2 border-green-400 rounded">
                            <p className="text-sm text-green-800 font-medium">
                              ➕ Le texte sera ajouté ici
                            </p>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-gray-500 text-sm">Chargement...</div>
                    )}
                  </div>
                ) : null}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default InsertTextModal;

