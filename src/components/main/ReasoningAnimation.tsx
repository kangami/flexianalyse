import React, { useState, useEffect } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';

interface ReasoningAnimationProps {
  isVisible: boolean;
  selectedModel?: string;
  onComplete?: () => void;
  customSteps?: ReasoningStep[];
}

interface ReasoningStep {
  id: number;
  text: string;
  description: string;
  duration: number;
  icon?: string;
}

const ReasoningAnimation: React.FC<ReasoningAnimationProps> = ({ 
  isVisible, 
  selectedModel, 
  onComplete,
  customSteps 
}) => {
  const { t } = useLanguage();
  
  const defaultSteps: ReasoningStep[] = [
    { 
      id: 1, 
      text: t('reasoning.analyzing.question'), 
      description: t('reasoning.analyzing.description'),
      duration: 2000 
    },
    { 
      id: 2, 
      text: t('reasoning.gathering.info'), 
      description: t('reasoning.gathering.description'),
      duration: 3000 
    },
    { 
      id: 3, 
      text: t('reasoning.processing'), 
      description: t('reasoning.processing.description'),
      duration: 4000 
    },
    { 
      id: 4, 
      text: t('reasoning.formulating'), 
      description: t('reasoning.formulating.description'),
      duration: 2500 
    },
    { 
      id: 5, 
      text: t('reasoning.finalizing'), 
      description: t('reasoning.finalizing.description'),
      duration: 1500 
    }
  ];

  const steps = customSteps || defaultSteps;
  const [currentStep, setCurrentStep] = useState(0);
  const [displayedText, setDisplayedText] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!isVisible) {
      setCurrentStep(0);
      setDisplayedText("");
      setProgress(0);
      return;
    }

    // Démarrer l'animation
    setCurrentStep(1);
    
    const runAnimation = async () => {
      for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        setCurrentStep(i + 1);
        
        // Animation de frappe
        setIsTyping(true);
        setDisplayedText("");
        
        for (let j = 0; j <= step.text.length; j++) {
          setDisplayedText(step.text.slice(0, j));
          await new Promise(resolve => setTimeout(resolve, 50));
        }
        
        setIsTyping(false);
        
        // Mettre à jour la progression
        setProgress(((i + 1) / steps.length) * 100);
        
        // Attendre la durée de l'étape (sauf pour la dernière)
        if (i < steps.length - 1) {
          await new Promise(resolve => setTimeout(resolve, step.duration));
        }
      }
      
      // Animation terminée
      if (onComplete) {
        onComplete();
      }
    };

    runAnimation();
  }, [isVisible]);

  if (!isVisible) return null;

  const currentStepData = steps[currentStep - 1];
  const modelVariant = selectedModel?.includes('nano') ? 'nano' : 
                      selectedModel?.includes('mini') ? 'mini' : 'full';

  const getModelColors = () => {
    switch (modelVariant) {
      case 'nano':
        return {
          gradient: 'from-green-600 to-teal-600',
          bg: 'from-green-50 to-teal-50',
          border: 'border-green-200',
          progress: 'from-green-600 to-teal-600'
        };
      case 'mini':
        return {
          gradient: 'from-blue-600 to-indigo-600',
          bg: 'from-blue-50 to-indigo-50',
          border: 'border-blue-200',
          progress: 'from-blue-600 to-indigo-600'
        };
      default:
        return {
          gradient: 'from-purple-600 to-pink-600',
          bg: 'from-purple-50 to-pink-50',
          border: 'border-purple-200',
          progress: 'from-purple-600 to-pink-600'
        };
    }
  };

  const colors = getModelColors();

  return (
    <div className={`relative mb-6 p-6 bg-gradient-to-r ${colors.bg} border ${colors.border} rounded-lg shadow-sm overflow-hidden`}>
      {/* Particules d'arrière-plan */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(8)].map((_, i) => (
          <div
            key={i}
            className={`absolute w-1 h-1 bg-gradient-to-r ${colors.gradient} rounded-full opacity-30`}
            style={{
              left: `${5 + i * 12}%`,
              top: `${20 + (i % 3) * 30}%`,
              animation: `float ${2 + (i % 3)}s ease-in-out infinite`,
              animationDelay: `${i * 0.3}s`
            }}
          ></div>
        ))}
      </div>

      <div className="relative flex items-center space-x-4">
        {/* Icône animée */}
        <div className="flex-shrink-0">
          <div className={`w-12 h-12 bg-gradient-to-r ${colors.gradient} rounded-full flex items-center justify-center shadow-lg`}>
            <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          </div>
        </div>

        {/* Contenu principal */}
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <h3 className="text-lg font-semibold text-gray-800">
              {displayedText}
              {isTyping && <span className="animate-pulse text-gray-500">|</span>}
            </h3>
          </div>
          
          {currentStepData && (
            <p className="text-sm text-gray-600 mb-3 animate-fade-in">
              {currentStepData.description}
            </p>
          )}

          {/* Barre de progression améliorée */}
          <div className="relative w-full bg-gray-200 rounded-full h-3 mb-2 overflow-hidden">
            <div 
              className={`absolute top-0 left-0 h-full bg-gradient-to-r ${colors.progress} rounded-full transition-all duration-700 ease-out`}
              style={{ width: `${progress}%` }}
            >
              {/* Animation de brillance */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 transform -skew-x-12 animate-shimmer"></div>
            </div>
          </div>
          
          <div className="flex justify-between text-xs text-gray-500">
            <span className="font-medium">{t('reasoning.step', { current: String(currentStep), total: String(steps.length) })}</span>
            <span className="flex items-center space-x-1">
              <span>{t('reasoning.powered.by')}</span>
              <span className={`font-bold bg-gradient-to-r ${colors.gradient} bg-clip-text text-transparent`}>
                {selectedModel?.toUpperCase() || 'GPT-5'}
              </span>
              <span>🚀</span>
            </span>
          </div>
        </div>
      </div>

      {/* Styles CSS inline pour les animations */}
      <style jsx>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px) rotate(0deg); }
          50% { transform: translateY(-10px) rotate(180deg); }
        }
        
        @keyframes shimmer {
          0% { transform: translateX(-100%) skewX(-12deg); }
          100% { transform: translateX(200%) skewX(-12deg); }
        }
        
        @keyframes fade-in {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
        
        .animate-fade-in {
          animation: fade-in 0.5s ease-out;
        }
      `}</style>
    </div>
  );
};

export default ReasoningAnimation;