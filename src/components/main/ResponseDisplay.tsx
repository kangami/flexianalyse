import React, { useEffect, useRef, useState } from "react";
import MarkdownResponse from "./MarkdownResponse";

interface ChatMessage {
  id: string;
  userQuery: string;
  aiResponse: string;
}

interface AnimatedMessage extends ChatMessage {
  displayedAiResponse: string;
  isAnimating: boolean;
}

interface ResponseDisplayProps {
  loading?: boolean;
  chatHistory: ChatMessage[];
}

const ResponseDisplay: React.FC<ResponseDisplayProps> = ({ loading = false, chatHistory }) => {
  const [animatedMessages, setAnimatedMessages] = useState<AnimatedMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Dans ResponseDisplay.tsx, remplacez le useEffect par cette version :
  useEffect(() => {
    setAnimatedMessages(prevAnimated => {
      const newAnimated = chatHistory.map(chatMsg => {
        // Chercher si ce message existe déjà dans l'animation
        const existing = prevAnimated.find(animMsg => animMsg.id === chatMsg.id);
        
        // CORRECTION: Si le message existe déjà (même sans animation), le garder tel quel
        if (existing) {
          // Seulement animer si c'est vraiment un nouveau contenu de réponse
          if (chatMsg.aiResponse && existing.aiResponse !== chatMsg.aiResponse) {
            // Nouvelle réponse → animer
            const animatedMessage: AnimatedMessage = {
              ...chatMsg,
              displayedAiResponse: '',
              isAnimating: true
            };
            
            setTimeout(() => {
              let currentIndex = 0;
              const fullContent = chatMsg.aiResponse;
              const typingSpeed = 0.6; // Vitesse accélérée

              const typingInterval = setInterval(() => {
                if (currentIndex < fullContent.length) {
                  setAnimatedMessages(prev => {
                    return prev.map(msg => 
                      msg.id === chatMsg.id
                        ? { 
                            ...msg, 
                            displayedAiResponse: fullContent.slice(0, currentIndex + 3), // Avance par 3 caractères pour accélérer
                            isAnimating: currentIndex < fullContent.length - 1
                          }
                        : msg
                    );
                  });
                  currentIndex++;
                } else {
                  clearInterval(typingInterval);
                  setAnimatedMessages(prev => {
                    return prev.map(msg => 
                      msg.id === chatMsg.id
                        ? { ...msg, isAnimating: false }
                        : msg
                    );
                  });
                }
              }, typingSpeed);
            }, 100);
            
            return animatedMessage;
          } else {
            // Message existant inchangé → garder tel quel
            return existing;
          }
        }
        
        // NOUVEAU MESSAGE: l'ajouter sans animation s'il a déjà une réponse
        if (chatMsg.aiResponse) {
          // Si c'est un message qui arrive avec une réponse complète → pas d'animation
          return {
            ...chatMsg,
            displayedAiResponse: chatMsg.aiResponse,
            isAnimating: false
          };
        } else {
          // Message sans réponse → ajouter normalement
          return {
            ...chatMsg,
            displayedAiResponse: '',
            isAnimating: false
          };
        }
      });
      
      return newAnimated;
    });
  }, [chatHistory]);

  // Scroll automatique quand les messages changent
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [animatedMessages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-2 pb-8">
      <div className="mx-auto w-full max-w-3xl">
        {animatedMessages.length > 0 ? (
          <div className="space-y-6">
            {animatedMessages.map((message) => (
              <div key={message.id} className="space-y-3">
                {/* User Query */}
                <div className="flex justify-end">
                  <div className="bg-blue-100 text-gray-800 px-4 py-3 rounded-lg max-w-[80%]">
                    <p className="break-words">{message.userQuery}</p>
                  </div>
                </div>
                
                {/* Model Response */}
                {message.displayedAiResponse && (
                  <div className="flex justify-start">
                    <div className="bg-gray-50 text-gray-800 px-4 py-3 rounded-lg max-w-[80%] relative">
                      <MarkdownResponse content={message.displayedAiResponse} />
                      {/* Curseur d'animation optionnel */}
                      {message.isAnimating && (
                        <span className="inline-block w-2 h-4 bg-gray-600 ml-1 animate-pulse">|</span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
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

        {loading && (
          <div className="flex justify-center py-6">
            <div className="w-8 h-8 border-3 border-gray-300 border-t-blue-500 rounded-full animate-spin"></div>
          </div>
        )}

        <div ref={bottomRef} className="h-8"/>
      </div>
    </div>
  );
};

export default ResponseDisplay;