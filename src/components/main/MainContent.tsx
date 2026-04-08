import React, { useState, useEffect, useRef, useMemo } from 'react';
import QueryForm from "./QueryForm";
import ResponseDisplay from "./ResponseDisplay";

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

interface MainContentProps {
  responses: { query: string; answer: string }[];
  selectedModel: string;
  setSelectedModel: (model: string) => void;
  isFileContentVisible: boolean;
  setIsFileContentVisible: (visible: boolean) => void;
  onQuerySubmit: (query: string, mode: 'online' | 'local') => void;
  loading: boolean;
  researchMode: 'online' | 'local';
  setResearchMode: React.Dispatch<React.SetStateAction<'online' | 'local'>>;
  chatHistory: ChatMessage[];
  suggestedActions?: SuggestedAction[];
  onSuggestedActionClick?: (action: SuggestedAction) => void;
  editableFiles?: EditableFile[];
  onTextSelect?: (text: string) => void;
  getEditableFiles?: () => Promise<EditableFile[]>;
}

interface ChatMessage {
  userQuery: string;
  aiResponse: string;
  displayedAiResponse?: string;
}

interface Response {
  query: string;
  answer: string;
}

const MainContent: React.FC<MainContentProps> = ({ responses, selectedModel, setSelectedModel, isFileContentVisible, setIsFileContentVisible, onQuerySubmit, loading, researchMode, chatHistory, setResearchMode, suggestedActions = [], onSuggestedActionClick, editableFiles = [], onTextSelect, getEditableFiles, isSearchingOnline = false}) => {
  // State for animated chat messages
  const [animatedChatHistory, setAnimatedChatHistory] = useState<ChatMessage[]>([]);
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
    const typingSpeed = 2;

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

  const handleQuerySubmit = (query: string, mode: string) => {
    // Immediately append the user query to animatedChatHistory
    const newMessage: ChatMessage = { userQuery: query, aiResponse: '' };
    setAnimatedChatHistory((prev) => [...prev, newMessage]);

    // Call the original onQuerySubmit to trigger the API call
    onQuerySubmit(query, mode);
  };

  // Fonction pour convertir les responses en ChatMessage
  const convertResponsesToChatMessages = (responses: Response[]): ChatMessage[] => {
    return responses.map(response => ({
      userQuery: response.query,
      aiResponse: response.answer,
      displayedAiResponse: response.answer // Pas d'animation dans MainContent
    }));
  };

  const chatMessages = convertResponsesToChatMessages(responses);
  
  return (
    <div className="h-screen flex flex-col flex-1 overflow-y-auto" style={{ overflowY: 'auto', scrollbarWidth: 'thin' }}>
      {/* Zone des messages - Modifiée pour le responsive */}
      <div className="flex-1 overflow-y-auto p-2 md:p-4 flex justify-center">
        <div className="w-full max-w-4xl px-2 md:px-0">
          <ResponseDisplay 
            chatHistory={chatHistory}
            loading={loading}
            editableFiles={editableFiles}
            onTextSelect={onTextSelect}
            getEditableFiles={getEditableFiles}
            isSearchingOnline={isSearchingOnline}
          />
        </div>
      </div>

      {/* Zone du formulaire - Modifiée pour le responsive */}
      <div className="border-t p-4 bg-white sticky bottom-0">
        <div className="w-full max-w-2xl mx-auto px-2 md:px-0">
          <QueryForm
            isFileContentVisible={isFileContentVisible}
            setIsFileContentVisible={setIsFileContentVisible}
            onQuerySubmit={handleQuerySubmit}
            loading={loading}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
            researchMode={researchMode}
            setResearchMode={setResearchMode}
            suggestedActions={suggestedActions}
            onSuggestedActionClick={onSuggestedActionClick}
          />
        </div>
      </div>
    </div>
  );

};

export default MainContent;
