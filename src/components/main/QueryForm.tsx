import React, { useState, useRef, useEffect } from 'react';

interface QueryFormProps {
    isFileContentVisible: boolean;
    setIsFileContentVisible: (visible: boolean) => void;
    onQuerySubmit: (query: string, mode: 'online' | 'local') => void;
    loading: boolean;
    selectedModel: string;
    researchMode: 'online' | 'local';
    setResearchMode: React.Dispatch<React.SetStateAction<'online' | 'local'>>;
}

const QueryForm: React.FC<QueryFormProps> = ({ 
    isFileContentVisible, 
    setIsFileContentVisible, 
    onQuerySubmit, 
    loading, 
    selectedModel,
    researchMode, 
    setResearchMode 
}) => {
    const [query, setQuery] = useState<string>('');
    const [isMobile, setIsMobile] = useState(false);
    
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    
    // Détection mobile
    useEffect(() => {
        const checkIfMobile = () => {
            setIsMobile(window.innerWidth < 768);
        };

        checkIfMobile();
        window.addEventListener('resize', checkIfMobile);
        return () => window.removeEventListener('resize', checkIfMobile);
    }, []);
    
    // Auto-resize textarea based on content
    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = `${Math.min(textarea.scrollHeight, isMobile ? 120 : 128)}px`;
        }
    }, [query, isMobile]);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (query.trim() && !loading) {
            onQuerySubmit(query, researchMode);
            setQuery('');
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    return (
    <div className={`
      fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200
      ${isMobile 
        ? 'px-3 pt-2 pb-3 bg-white border-t border-gray-200' 
        : 'px-4 pb-4'
      }
    `}>
      <div className={`
        w-full bg-white shadow-lg rounded-xl border
        ${isMobile ? 'max-w-none' : 'max-w-3xl mx-auto'}
      `}>
        {/* Mobile handle */}
        {isMobile && (
          <div className="flex justify-center pt-2">
            <div className="w-12 h-1 bg-gray-300 rounded-full"></div>
          </div>
        )}

        <div className="p-3 sm:p-4">
          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="What do you want to know?"
            className={`
              w-full bg-transparent outline-none text-gray-700 placeholder-gray-400
              resize-none overflow-y-auto whitespace-pre-wrap
              scrollbar-thin scrollbar-track-transparent scrollbar-thumb-gray-300
              ${isMobile ? 'min-h-[44px] text-base' : 'min-h-[40px] text-sm'}
            `}
            disabled={loading}
            rows={1}
          />

          {/* Controls */}
          <div className={`
            flex flex-col sm:flex-row justify-between items-start sm:items-center
            gap-3 mt-3
          `}>
            {/* Left controls */}
            <div className="flex flex-wrap gap-2">
              {/* Model badge */}
              <span className={`
                bg-gray-100 text-gray-700 rounded-full px-3 py-1 text-xs
                ${isMobile ? 'font-medium' : 'font-normal'}
              `}>
                {selectedModel}
              </span>

              {/* File toggle */}
              {!isFileContentVisible && (
                <button
                  onClick={() => setIsFileContentVisible(true)}
                  className={`
                    bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full px-3 py-1
                    flex items-center gap-1 text-xs transition-colors
                  `}
                >
                  <span>📄</span>
                  <span>File</span>
                </button>
              )}

              {/* Research mode toggle */}
              <button
                onClick={() => setResearchMode(researchMode === 'online' ? 'local' : 'online')}
                className={`
                  ${researchMode === 'online' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-700'}
                  rounded-full px-3 py-1 text-xs flex items-center gap-1 transition-colors
                `}
              >
                {researchMode === 'online' ? (
                  <>
                    <svg 
                      xmlns="http://www.w3.org/2000/svg" 
                      viewBox="0 0 20 20" 
                      fill="currentColor" 
                      className="w-3 h-3"
                    >
                      <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clipRule="evenodd" />
                    </svg>
                    Research
                  </>
                ) : (
                  <>
                    <svg 
                      xmlns="http://www.w3.org/2000/svg" 
                      viewBox="0 0 20 20" 
                      fill="currentColor" 
                      className="w-3 h-3"
                    >
                      <path fillRule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5z" clipRule="evenodd" />
                    </svg>
                    Local
                  </>
                )}
              </button>
            </div>

            {/* Submit button */}
            <button
              onClick={handleSubmit}
              disabled={loading || !query.trim()}
              className={`
                self-end sm:self-center rounded-full p-2 sm:p-2
                ${loading 
                  ? 'bg-gray-300 cursor-not-allowed' 
                  : 'bg-blue-500 hover:bg-blue-600 active:scale-95'
                }
                text-white transition-all
              `}
            >
              {loading ? (
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
                  <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" className="opacity-75"/>
                </svg>
              ) : (
                <svg
                  className="h-5 w-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                </svg>
              )}
            </button>
          </div>

          {/* Mobile helper text */}
          {isMobile && (
            <div className="mt-2 text-xs text-gray-500 text-center">
              Press Enter to send, Shift+Enter for new line
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default QueryForm;