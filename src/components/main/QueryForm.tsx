import React, { useState, useRef, useEffect } from 'react';

interface QueryFormProps {
    isFileContentVisible: boolean;
    setIsFileContentVisible: (visible: boolean) => void;
}

const QueryForm: React.FC<QueryFormProps> = ({ isFileContentVisible, setIsFileContentVisible }) => {
    const [query, setQuery] = useState<string>('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea based on content
    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
        textarea.style.height = 'auto'; // Reset height
        textarea.style.height = `${textarea.scrollHeight}px`; // Set to scroll height
        }
    }, [query]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Query submitted:', query);
    // Add your query submission logic here
    setQuery('');
  };

  return (
    <div className="fixed bottom-4 left-72 right-4 z-10 flex justify-center">
      <div className="w-full max-w-3xl bg-white rounded-10 shadow-lg p-3 flex items-start border border-gray-200">
        {/* Pro Badge */}
        <span className="bg-gray-200 text-gray-700 text-xs font-semibold px-2 py-1 rounded-full mr-2 mt-1">
          Mentor
        </span>

        {/* Input Field */}
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask anything..."
          className="flex-1 bg-transparent outline-none text-gray-700 placeholder-gray-400 resize-y min-h-[40px] max-h-32 overflow-y-auto whitespace-pre-wrap"
          aria-label="Ask a follow-up question"
        />

        {/* Icons */}
        <div className="flex items-center space-x-2">
          {/* Code Button (appears when File Content is hidden) */}
          {!isFileContentVisible && (
            <button
              onClick={() => setIsFileContentVisible(true)}
              className="text-gray-500 hover:text-gray-700"
            >
              Code
            </button>
          )}
          <button
            onClick={handleSubmit}
            className="bg-blue-500 text-white rounded-full p-2 hover:bg-blue-600"
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
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default QueryForm;