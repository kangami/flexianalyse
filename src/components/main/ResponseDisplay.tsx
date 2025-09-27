import React, { useEffect, useRef } from "react";
import MarkdownResponse from "./MarkdownResponse";

interface ChatMessage {
  id: string;
  userQuery: string;
  aiResponse: string;
}

interface ResponseDisplayProps {
  loading?: boolean;
  chatHistory: ChatMessage[];
}

const ResponseDisplay: React.FC<ResponseDisplayProps> = ({ loading = false, chatHistory }) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

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

  return (
    <div className="flex-1 overflow-y-auto px-4 py-2 pb-8 smooth-scroll">
      <div className="mx-auto w-full max-w-3xl">
        {chatHistory.length > 0 ? (
          <div className="space-y-6">
            {chatHistory.map((message, index) => {
              const isLastMessage = index === chatHistory.length - 1;
              const isStreaming = isLastMessage && loading && message.aiResponse;
              
              return (
                <div key={message.id} className="space-y-3 message-appear">
                  {/* Question de l'utilisateur */}
                  <div className="flex justify-end">
                    <div className="bg-blue-100 text-gray-800 px-4 py-3 rounded-lg max-w-[80%] shadow-sm message-bubble">
                      <p className="break-words">{message.userQuery}</p>
                    </div>
                  </div>
                  
                  {/* Réponse de l'IA */}
                  {message.aiResponse && (
                    <div className="flex justify-start">
                      <div className={`bg-gray-50 text-gray-800 px-4 py-3 rounded-lg max-w-[80%] shadow-sm message-bubble relative ${
                        isStreaming ? 'streaming-text' : ''
                      }`}>
                        <MarkdownResponse content={message.aiResponse} />
                        
                        {/* Indicateur de streaming */}
                        {isStreaming && (
                          <div className="streaming-indicator">
                            <span className="streaming-dot"></span>
                            <span className="streaming-dot" style={{ marginLeft: '4px' }}></span>
                            <span className="streaming-dot" style={{ marginLeft: '4px' }}></span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Indicateur de chargement initial */}
                  {!message.aiResponse && isLastMessage && loading && (
                    <div className="flex justify-start">
                      <div className="bg-gray-50 px-4 py-3 rounded-lg message-appear">
                        <div className="streaming-indicator">
                          <span className="streaming-dot"></span>
                          <span className="streaming-dot" style={{ marginLeft: '4px' }}></span>
                          <span className="streaming-dot" style={{ marginLeft: '4px' }}></span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full min-h-[60vh] text-center">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-800 mb-2">
              What do you want to know?
            </h1>
            <p className="text-gray-500 max-w-md">
              Start by asking a question or uploading a file to get insights.
            </p>
          </div>
        )}

        {/* Loader global */}
        {loading && chatHistory.length === 0 && (
          <div className="flex justify-center py-6">
            <div className="main-loader"></div>
          </div>
        )}

        <div ref={messagesEndRef} />
        <div ref={bottomRef} className="h-8"/>
      </div>
    </div>
  );
};

export default ResponseDisplay;