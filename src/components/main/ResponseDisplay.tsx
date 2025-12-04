import React, { useEffect, useRef, useState } from "react";
import MarkdownResponse from "./MarkdownResponse";

interface ChatMessage {
  id: string;
  userQuery: string;
  aiResponse: string;
}

interface EditableFile {
  file: File;
  content: string | ArrayBuffer;
  type: 'code' | 'docx';
}

interface ResponseDisplayProps {
  loading?: boolean;
  chatHistory: ChatMessage[];
  onTextSelect?: (selectedText: string) => void;
  enableTextSelection?: boolean;
  editableFiles?: EditableFile[];
  getEditableFiles?: () => Promise<EditableFile[]>;
  isSearchingOnline?: boolean;
}

const ResponseDisplay: React.FC<ResponseDisplayProps> = ({ loading = false, chatHistory, onTextSelect, enableTextSelection = false, editableFiles = [], getEditableFiles, isSearchingOnline = false }) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const [selectedText, setSelectedText] = useState<string>('');
  const [showInsertButton, setShowInsertButton] = useState<boolean>(false);
  const [insertButtonPosition, setInsertButtonPosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [availableEditableFiles, setAvailableEditableFiles] = useState<EditableFile[]>(editableFiles);
  const selectionRef = useRef<Selection | null>(null);
  const savedRangeRef = useRef<Range | null>(null);
  const hideButtonTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  // Scroll pendant le streaming
  useEffect(() => {
    if (chatHistory.length > 0) {
      const lastMessage = chatHistory[chatHistory.length - 1];
      if (lastMessage.aiResponse) {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      }
    }
  }, [chatHistory]);

  // Charger les fichiers éditables de manière asynchrone
  useEffect(() => {
    if (getEditableFiles) {
      getEditableFiles()
        .then(files => {
          setAvailableEditableFiles(files);
        })
        .catch(err => {
          console.error('Erreur lors du chargement des fichiers éditables:', err);
        });
    } else {
      setAvailableEditableFiles(editableFiles);
    }
  }, [editableFiles, getEditableFiles]);

  // Gestion de la sélection de texte pour l'édition en ligne
  useEffect(() => {
    // Permettre la sélection si enableTextSelection est true OU si onTextSelect est disponible
    // (on vérifiera les fichiers éditables au moment du clic sur le bouton)
    const canSelect = enableTextSelection || (onTextSelect !== undefined);
    if (!canSelect || !onTextSelect) return;

    const handleMouseUp = () => {
      // Annuler tout timeout précédent
      if (hideButtonTimeoutRef.current) {
        clearTimeout(hideButtonTimeoutRef.current);
        hideButtonTimeoutRef.current = null;
      }

      // Petit délai pour s'assurer que la sélection est complète
      setTimeout(() => {
        const selection = window.getSelection();
        if (!selection || selection.rangeCount === 0) {
          // Ne pas désélectionner immédiatement, attendre un peu
          hideButtonTimeoutRef.current = setTimeout(() => {
            setShowInsertButton(false);
            setSelectedText('');
            savedRangeRef.current = null;
          }, 100);
          return;
        }

        const range = selection.getRangeAt(0);
        
        // Sauvegarder la sélection pour la préserver
        savedRangeRef.current = range.cloneRange();
        selectionRef.current = selection;
        
        // Vérifier que la sélection est dans une bulle de message (pas dans les boutons, icônes, etc.)
        const container = range.commonAncestorContainer;
        const messageBubble = (container.nodeType === Node.TEXT_NODE 
          ? container.parentElement 
          : container as HTMLElement)?.closest('.message-bubble');
        
        if (!messageBubble) {
          hideButtonTimeoutRef.current = setTimeout(() => {
            setShowInsertButton(false);
            setSelectedText('');
            savedRangeRef.current = null;
          }, 100);
          return;
        }

        // Exclure les sélections dans les éléments non pertinents (liens, code, icônes, etc.)
        const excludedElements = messageBubble.querySelectorAll('a, code, pre, .streaming-indicator, .web-search-indicator, button, svg, img');
        let isExcluded = false;
        
        excludedElements.forEach(el => {
          if (range.intersectsNode(el)) {
            isExcluded = true;
          }
        });

        if (isExcluded) {
          hideButtonTimeoutRef.current = setTimeout(() => {
            setShowInsertButton(false);
            setSelectedText('');
            savedRangeRef.current = null;
          }, 100);
          return;
        }

        // Extraire uniquement le texte visible (sans les balises HTML)
        let selectedText = selection.toString().trim();
        
        // Nettoyer le texte sélectionné : supprimer les espaces multiples et les retours à la ligne excessifs
        selectedText = selectedText
          .replace(/\s+/g, ' ') // Remplacer les espaces multiples par un seul
          .replace(/\n{3,}/g, '\n\n') // Limiter les retours à la ligne multiples
          .trim();

        // Vérifier que la sélection a une longueur minimale (au moins 3 caractères)
        if (selectedText.length < 3) {
          hideButtonTimeoutRef.current = setTimeout(() => {
            setShowInsertButton(false);
            setSelectedText('');
            savedRangeRef.current = null;
          }, 100);
          return;
        }

        setSelectedText(selectedText);
        
        // Obtenir la position de la sélection pour afficher le bouton
        const rect = range.getBoundingClientRect();
        setInsertButtonPosition({
          x: rect.left + rect.width / 2,
          y: rect.top - 8
        });
        setShowInsertButton(true);
      }, 10); // Petit délai pour s'assurer que la sélection est complète
    };

    const handleMouseDown = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      
      // Si on clique sur le bouton d'insertion, ne rien faire
      if (target.closest('.insert-button-container')) {
        return;
      }
      
      // Si on clique ailleurs que dans une bulle de message, cacher le bouton après un délai
      if (!target.closest('.message-bubble')) {
        hideButtonTimeoutRef.current = setTimeout(() => {
          setShowInsertButton(false);
          setSelectedText('');
          savedRangeRef.current = null;
          if (selectionRef.current) {
            selectionRef.current.removeAllRanges();
          }
        }, 200);
      }
    };

    // Préserver la sélection même si l'utilisateur bouge la souris
    const handleSelectionChange = () => {
      const selection = window.getSelection();
      if (selection && selection.rangeCount > 0 && savedRangeRef.current) {
        // Si la sélection a changé mais qu'on a une sélection sauvegardée valide,
        // on peut la restaurer si nécessaire
        try {
          const currentRange = selection.getRangeAt(0);
          if (currentRange.toString().trim().length === 0 && savedRangeRef.current.toString().trim().length > 0) {
            // La sélection a été perdue, mais on a une sauvegarde - on peut la restaurer si on veut
            // Pour l'instant, on ne fait rien pour éviter les conflits
          }
        } catch (e) {
          // Ignorer les erreurs
        }
      }
    };

    document.addEventListener('mouseup', handleMouseUp);
    document.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('selectionchange', handleSelectionChange);

    return () => {
      document.removeEventListener('mouseup', handleMouseUp);
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('selectionchange', handleSelectionChange);
      if (hideButtonTimeoutRef.current) {
        clearTimeout(hideButtonTimeoutRef.current);
      }
    };
  }, [enableTextSelection, onTextSelect, availableEditableFiles]);

  return (
    <div className="flex-1 overflow-y-auto px-3 py-1 pb-28 smooth-scroll">
      <div className="mx-auto w-full max-w-4xl">
        {chatHistory.length > 0 ? (
          <div className="space-y-3">
            {chatHistory.map((message, index) => {
              const isLastMessage = index === chatHistory.length - 1;
              const isStreaming = isLastMessage && loading && message.aiResponse;
              
              return (
                <div key={message.id} className="space-y-2 message-appear">
                  {/* Question de l'utilisateur */}
                  <div className="flex justify-end">
                    <div className="bg-blue-100 text-gray-800 px-3 py-2 rounded-lg max-w-[85%] shadow-sm message-bubble text-sm">
                      <p className="break-words leading-relaxed">{message.userQuery}</p>
                    </div>
                  </div>
                  
                  {/* Réponse de l'IA */}
                  {message.aiResponse && (
                    <div className="flex justify-start">
                      <div className={`bg-gray-50 text-gray-800 px-3 py-2 rounded-lg max-w-[85%] shadow-sm message-bubble relative text-sm ${
                        isStreaming ? 'streaming-text' : ''
                      } ${(enableTextSelection || onTextSelect !== undefined) ? 'selectable-text' : ''}`}
                      style={(enableTextSelection || onTextSelect !== undefined) ? { userSelect: 'text', cursor: 'text' } : {}}
                      >
                        <MarkdownResponse content={message.aiResponse} />
                        
                        {/* Indicateur de streaming */}
                        {isStreaming && (
                          <div className="streaming-indicator mt-1">
                            <span className="streaming-dot"></span>
                            <span className="streaming-dot" style={{ marginLeft: '4px' }}></span>
                            <span className="streaming-dot" style={{ marginLeft: '4px' }}></span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Indicateur de chargement initial */}
                  {!message.aiResponse && isLastMessage && loading && !isSearchingOnline && (
                    <div className="flex justify-start">
                      <div className="bg-gray-50 px-3 py-2 rounded-lg message-appear">
                        <div className="streaming-indicator">
                          <span className="streaming-dot"></span>
                          <span className="streaming-dot" style={{ marginLeft: '4px' }}></span>
                          <span className="streaming-dot" style={{ marginLeft: '4px' }}></span>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* Indicateur de recherche en ligne animé */}
                  {isSearchingOnline && isLastMessage && (
                    <div className="flex justify-start mt-2">
                      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 shadow-sm pulse-border">
                        <div className="flex items-center gap-2">
                          <div className="web-search-indicator">
                            <span className="web-search-dot"></span>
                            <span className="web-search-dot"></span>
                            <span className="web-search-dot"></span>
                          </div>
                          <span className="text-blue-700 font-medium text-sm animate-pulse">
                            🔍 Recherche sur le web...
                          </span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full min-h-[30vh] text-center py-8">
            <h1 className="text-xl sm:text-2xl font-bold text-gray-800 mb-2">
              What do you want to know?
            </h1>
            <p className="text-gray-500 max-w-md text-sm">
              Start by asking a question or uploading a file to get insights.
            </p>
          </div>
        )}

        {/* Loader global */}
        {loading && chatHistory.length === 0 && (
          <div className="flex justify-center py-4">
            <div className="main-loader"></div>
          </div>
        )}

        <div ref={messagesEndRef} />
        <div ref={bottomRef} className="h-24"/>
      </div>

      {/* Bouton flottant pour insérer le texte sélectionné */}
      {(enableTextSelection || onTextSelect !== undefined) && showInsertButton && selectedText && (
        <div 
          className="insert-button-container fixed z-50"
          style={{
            left: `${insertButtonPosition.x}px`,
            top: `${insertButtonPosition.y}px`,
            transform: 'translate(-50%, -100%)',
            pointerEvents: 'auto'
          }}
        >
          <button
            onMouseDown={(e) => {
              // Empêcher la propagation pour éviter que handleMouseDown ne cache le bouton
              e.stopPropagation();
            }}
            onClick={(e) => {
              e.stopPropagation();
              if (onTextSelect && selectedText) {
                onTextSelect(selectedText);
                setShowInsertButton(false);
                setSelectedText('');
                savedRangeRef.current = null;
                if (selectionRef.current) {
                  selectionRef.current.removeAllRanges();
                }
              }
            }}
            className="group bg-white/95 hover:bg-blue-50 text-blue-600 hover:text-blue-700 border border-blue-200/80 hover:border-blue-300 rounded-lg shadow-sm hover:shadow-md px-2.5 py-1.5 text-xs font-medium whitespace-nowrap transition-all duration-200 ease-in-out flex items-center gap-1.5 backdrop-blur-sm"
            title="Insérer ce texte dans le document"
          >
            <svg 
              className="w-3.5 h-3.5 transition-transform duration-200 group-hover:scale-110 group-hover:rotate-90" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2.5} 
                d="M12 6v6m0 0v6m0-6h6m-6 0H6" 
              />
            </svg>
            <span className="font-semibold">Insérer</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default ResponseDisplay;