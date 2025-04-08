import React from 'react';
import QueryForm from './QueryForm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';


interface FileDetails {
  content: string;
  description: string;
}

interface FileSelectedComponentProps {
  file: File;
  details: FileDetails;
  isFileContentVisible: boolean;
  setIsFileContentVisible: (visible: boolean) => void;
}

const FileSelectedComponent: React.FC<FileSelectedComponentProps> = ({ file, details, isFileContentVisible, setIsFileContentVisible }) => {
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
            <pre className="text-sm text-gray-800">
              <code>
                <SyntaxHighlighter language="java" style={vscDarkPlus} className="rounded-md">
                  {details.content}
                </SyntaxHighlighter>
              </code>
            </pre>
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