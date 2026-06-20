import React, { useState, useEffect } from 'react';
import { Briefcase, Hospital, ShoppingCart, Users, Banknote } from 'lucide-react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const useCases = [
  {
    icon: <Hospital className="w-10 h-10 text-white" />,
    title: "Healthcare",
    description: "Predict patient outcomes, optimize treatment plans, and streamline hospital operations with AI-driven analytics.",
    background: "bg-gradient-to-br from-blue-400 to-cyan-300",
    textColor: "text-white"
  },
  {
    icon: <Briefcase className="w-10 h-10 text-white" />,
    title: "Finance",
    description: "Detect fraud, analyze market trends, and automate risk assessment with real-time data processing.",
    background: "bg-gradient-to-br from-green-500 to-emerald-400",
    textColor: "text-white"
  },
  {
    icon: <ShoppingCart className="w-10 h-10 text-white" />,
    title: "Retail",
    description: "Personalize customer experiences, forecast demand, and optimize supply chains using AI insights.",
    background: "bg-gradient-to-br from-purple-500 to-pink-400",
    textColor: "text-white"
  },
  {
    icon: <Users className="w-10 h-10 text-white" />,
    title: "Education",
    description: "Enhance learning outcomes with adaptive AI tools for personalized student engagement and assessment.",
    background: "bg-gradient-to-br from-orange-400 to-yellow-300",
    textColor: "text-gray-800"
  },
  {
    icon: <Banknote className="w-10 h-10 text-white" />,
    title: "Manufacturing",
    description: "Improve operational efficiency, predict equipment failures, and optimize production lines with AI analytics.",
    background: "bg-gradient-to-br from-gray-600 to-blue-500",
    textColor: "text-white"
  }
];

const UseCasesSection: React.FC = () => {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(true);

  // Auto-play functionality
  useEffect(() => {
    if (!isAutoPlaying) return;

    const interval = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % useCases.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [isAutoPlaying]);

  const nextSlide = () => {
    setCurrentSlide((currentSlide + 1) % useCases.length);
  };

  const prevSlide = () => {
    setCurrentSlide((currentSlide - 1 + useCases.length) % useCases.length);
  };

  const goToSlide = (index: number) => {
    setCurrentSlide(index);
  };

  return (
    <section className="py-20 bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <h2 className="text-3xl font-bold text-center text-gray-900 mb-16">
          Trusted by Industries Worldwide
        </h2>

        {/* Carousel Container */}
        <div className="relative overflow-hidden">
          {/* Carousel Slides */}
          <div
            className="flex transition-transform duration-500 ease-in-out"
            style={{ transform: `translateX(-${currentSlide * 100}%)` }}
          >
            {useCases.map((useCase, index) => (
              <div key={index} className="w-full flex-shrink-0 px-4">
                <div className={`${useCase.background} p-8 rounded-xl text-center shadow-sm hover:shadow-lg transition-shadow mx-auto max-w-md`}>
                  <div className="mb-6 flex justify-center">{useCase.icon}</div>
                  <h3 className={`text-xl font-semibold ${useCase.textColor} mb-3`}>{useCase.title}</h3>
                  <p className={`text-lg ${useCase.textColor} opacity-90`}>{useCase.description}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Navigation Arrows */}
          <button
            onClick={prevSlide}
            className="absolute left-4 top-1/2 transform -translate-y-1/2 bg-white p-2 rounded-full shadow-lg hover:bg-gray-50 transition-colors z-10"
            aria-label="Previous slide"
          >
            <ChevronLeft className="w-6 h-6 text-blue-500" />
          </button>
          <button
            onClick={nextSlide}
            className="absolute right-4 top-1/2 transform -translate-y-1/2 bg-white p-2 rounded-full shadow-lg hover:bg-gray-50 transition-colors z-10"
            aria-label="Next slide"
          >
            <ChevronRight className="w-6 h-6 text-blue-500" />
          </button>

          {/* Pagination Dots */}
          <div className="flex justify-center mt-8 space-x-2">
            {useCases.map((_, index) => (
              <button
                key={index}
                onClick={() => goToSlide(index)}
                className={`w-3 h-3 rounded-full transition-colors ${
                  currentSlide === index ? 'bg-blue-500' : 'bg-gray-300'
                }`}
                aria-label={`Go to slide ${index + 1}`}
              />
            ))}
          </div>

          {/* Auto-play is always enabled, pause button removed */}
        </div>
      </div>
    </section>
  );
};

export default UseCasesSection;