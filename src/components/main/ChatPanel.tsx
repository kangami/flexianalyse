import React from 'react';
import ResponseDisplay from './ResponseDisplay';
import { useLanguage } from '../../contexts/LanguageContext';

interface ChatMessage {
  id: string;
  userQuery: string;
  aiResponse: string;
  displayedAiResponse?: string;
}

interface SuggestedAction {
  id: string;
  title: string;
  description: string;
  sample_prompt: string;
}

interface EditableFile {
  file: File;
  content: string | ArrayBuffer;
  type: 'code' | 'docx';
}

interface ChatPanelProps {
  chatHistory: ChatMessage[];
  loading: boolean;
  onQuerySubmit: (query: string, mode: 'online' | 'local') => void;
  selectedModel: string;
  setSelectedModel?: (model: string) => void;
  researchMode: 'online' | 'local';
  setResearchMode: React.Dispatch<React.SetStateAction<'online' | 'local'>>;
  suggestedActions?: SuggestedAction[];
  onSuggestedActionClick?: (action: SuggestedAction) => void;
  editableFiles?: EditableFile[];
  onTextSelect?: (text: string) => void;
  getEditableFiles?: () => Promise<EditableFile[]>;
  isSearchingOnline?: boolean;
  currentStatus?: string;
  isFileContentVisible?: boolean;
  setIsFileContentVisible?: (visible: boolean) => void;
  isProcessingDrop?: boolean;
  isMobile?: boolean;
  onFileSelect?: (file: File, details: { content: string | ArrayBuffer; description: string }) => void;
  detectedDocType?: { type: string; label: string; confidence: number } | null;
}

const ChatPanel: React.FC<ChatPanelProps> = ({
  chatHistory,
  loading,
  onQuerySubmit,
  selectedModel,
  setSelectedModel,
  researchMode,
  setResearchMode,
  suggestedActions = [],
  onSuggestedActionClick,
  editableFiles = [],
  onTextSelect,
  getEditableFiles,
  isSearchingOnline = false,
  currentStatus = '',
  isFileContentVisible = false,
  setIsFileContentVisible,
  isProcessingDrop = false,
  isMobile = false,
  onFileSelect,
  detectedDocType = null
}) => {
  const { t } = useLanguage();

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center shadow-md">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <span className="text-lg font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            FlexiAnalyse
          </span>
        </div>
      </div>

      {/* Zone de chat avec QueryForm intégré */}
      <div className="flex-1 overflow-hidden flex flex-col">
        <ResponseDisplay
          chatHistory={chatHistory}
          loading={loading}
          editableFiles={editableFiles}
          onTextSelect={onTextSelect}
          getEditableFiles={getEditableFiles}
          isSearchingOnline={isSearchingOnline}
          currentStatus={currentStatus}
          onQuerySubmit={onQuerySubmit}
          selectedModel={selectedModel}
          setSelectedModel={setSelectedModel}
          researchMode={researchMode}
          setResearchMode={setResearchMode}
          suggestedActions={suggestedActions}
          onSuggestedActionClick={onSuggestedActionClick}
          isFileContentVisible={isFileContentVisible}
          setIsFileContentVisible={setIsFileContentVisible}
          isMobile={isMobile}
          onFileSelect={onFileSelect}
          detectedDocType={detectedDocType}
        />
      </div>
    </div>
  );
};

export default ChatPanel;

