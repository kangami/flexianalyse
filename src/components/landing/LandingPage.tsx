// src/components/landing/LandingPage.tsx
import React, { useState, useEffect } from 'react';
import { ArrowRight, FileText, Search, Zap, Shield, Globe, Brain, Sparkles, Target } from 'lucide-react';
import LoginModal from '../auth/LoginModal';
import { Link, useNavigate } from 'react-router-dom';

const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [displayText, setDisplayText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  
  const texts = ['FlexiAnalyse', 'AI Analytics', 'Smart Docs', 'FlexiAnalyse'];
  
  useEffect(() => {
    const currentText = texts[currentIndex];
    const timeout = setTimeout(() => {
      if (!isDeleting) {
        if (displayText.length < currentText.length) {
          setDisplayText(currentText.slice(0, displayText.length + 1));
        } else {
          setTimeout(() => setIsDeleting(true), 2000);
        }
      } else {
        if (displayText.length > 0) {
          setDisplayText(displayText.slice(0, -1));
        } else {
          setIsDeleting(false);
          setCurrentIndex((prev) => (prev + 1) % texts.length);
        }
      }
    }, isDeleting ? 100 : 150);

    return () => clearTimeout(timeout);
  }, [displayText, isDeleting, currentIndex, texts]);

  return (
    <div 
      className="w-full h-full bg-gradient-to-br from-slate-50 to-blue-50 flex flex-col"
      style={{ minHeight: '100vh', height: '100vh' }}
    >
     
      {/* Navigation */}
      <nav className="fixed top-0 w-full bg-white/80 backdrop-blur-md border-b border-gray-200 z-40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900 typing-cursor-home">
                {displayText}
              </span>
            </div>
            <button
              onClick={() => navigate('/app')}
              className="relative bg-gradient-to-r from-blue-600 to-purple-600 text-white px-6 py-2 rounded-full font-semibold hover:from-blue-700 hover:to-purple-700 transition-all pulse-border overflow-hidden group"
            >
              <span className="relative z-10">Try it</span>
              <div className="absolute inset-0 bg-gradient-to-r from-blue-700 to-purple-700 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-24 pb-16 px-4 sm:px-6 lg:px-8 flex-1 flex items-center">
        <div className="max-w-6xl mx-auto text-center w-full">
          <div className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-100 to-purple-100 text-blue-800 px-4 py-2 rounded-full text-sm font-medium mb-8">
            <Brain className="w-4 h-4" />
            Powered by the World's Most Advanced AI Models
          </div>
          
          <h1 className="text-4xl sm:text-6xl font-bold text-gray-900 mb-6 leading-tight">
            Unleash the Power of
            <br />
            <span className="gradient-text-flow font-extrabold">
              Next-Generation AI
            </span>
            <br />
            for Document Analysis
          </h1>
          
          <p className="text-xl text-gray-600 mb-8 max-w-4xl mx-auto leading-relaxed">
            FlexiAnalyse brings together the most sophisticated AI minds on the planet - 
            <strong className="text-gray-800"> GPT-5, GPT-4, Claude, Mistral, and GPT-3.5 Nano</strong> - 
            to transform your documents into actionable intelligence. Experience the future of document analysis today.
          </p>

          {/* AI Models Showcase - Hero Version */}
          <div className="flex flex-wrap justify-center gap-3 mb-8">
            <div className="group relative">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-green-600 to-emerald-600 rounded-full blur opacity-75 group-hover:opacity-100 transition duration-300"></div>
              <span className="relative px-6 py-3 bg-white rounded-full text-green-700 font-bold text-lg shadow-lg">
                GPT-5
              </span>
            </div>
            <div className="group relative">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-full blur opacity-75 group-hover:opacity-100 transition duration-300"></div>
              <span className="relative px-6 py-3 bg-white rounded-full text-blue-700 font-bold text-lg shadow-lg">
                GPT-4
              </span>
            </div>
            <div className="group relative">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-600 to-indigo-600 rounded-full blur opacity-75 group-hover:opacity-100 transition duration-300"></div>
              <span className="relative px-6 py-3 bg-white rounded-full text-purple-700 font-bold text-lg shadow-lg">
                Claude
              </span>
            </div>
            <div className="group relative">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-orange-600 to-red-600 rounded-full blur opacity-75 group-hover:opacity-100 transition duration-300"></div>
              <span className="relative px-6 py-3 bg-white rounded-full text-orange-700 font-bold text-lg shadow-lg">
                Mistral
              </span>
            </div>
            <div className="group relative">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-gray-600 to-slate-600 rounded-full blur opacity-75 group-hover:opacity-100 transition duration-300"></div>
              <span className="relative px-6 py-3 bg-white rounded-full text-gray-700 font-bold text-lg shadow-lg">
                GPT-3.5 Nano
              </span>
            </div>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-16">
            <button
              onClick={() => navigate('/app')}
              className="relative bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 text-white px-8 py-4 rounded-full font-semibold hover:from-blue-700 hover:via-purple-700 hover:to-pink-700 transition-all flex items-center justify-center gap-2 shadow-xl pulse-border overflow-hidden group"
            >
              <span className="relative z-10">Experience the Future Now</span>
              <ArrowRight className="w-5 h-5 relative z-10 group-hover:translate-x-1 transition-transform" />
              <div className="absolute inset-0 bg-gradient-to-r from-blue-700 via-purple-700 to-pink-700 opacity-0 group-hover:opacity-100 transition-opacity"></div>
            </button>
            <button className="glow-border text-gray-700 px-8 py-4 rounded-full font-semibold hover:bg-gray-50 transition-all">
              Watch Live Demo
            </button>
          </div>

          {/* Demo Preview avec animation */}
          <div className="relative max-w-4xl mx-auto">
            <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 p-8 transform hover:scale-105 transition-transform duration-300">
              <div className="flex items-center gap-2 mb-6">
                <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                <div className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                <div className="flex-1 bg-gray-100 rounded-full h-8 flex items-center justify-center text-sm text-gray-600 relative overflow-hidden">
                  <span>FlexiAnalyse • AI Analysis in Progress...</span>
                  <div className="absolute top-0 left-0 h-full w-0 bg-gradient-to-r from-blue-200 to-purple-200 animate-pulse"></div>
                </div>
              </div>
              <div className="text-left space-y-4">
                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-lg transform hover:translate-x-2 transition-transform">
                  <p className="text-blue-800 font-medium flex items-center gap-2">
                    <FileText className="w-4 h-4 animate-bounce" />
                    Document Analyzed: Strategic_Business_Plan_2024.pdf
                  </p>
                </div>
                <div className="bg-green-50 border-l-4 border-green-400 p-4 rounded-lg transform hover:translate-x-2 transition-transform" style={{transitionDelay: '0.1s'}}>
                  <p className="text-green-800 font-medium flex items-center gap-2">
                    <Sparkles className="w-4 h-4 animate-spin" />
                    AI Insights Extracted: 23 critical insights identified across 5 AI models
                  </p>
                </div>
                <div className="bg-purple-50 border-l-4 border-purple-400 p-4 rounded-lg transform hover:translate-x-2 transition-transform" style={{transitionDelay: '0.2s'}}>
                  <p className="text-purple-800 font-medium flex items-center gap-2">
                    <Target className="w-4 h-4 animate-pulse" />
                    Strategic Recommendations: 7 high-impact actions prioritized
                  </p>
                </div>
                <div className="bg-orange-50 border-l-4 border-orange-400 p-4 rounded-lg transform hover:translate-x-2 transition-transform" style={{transitionDelay: '0.3s'}}>
                  <p className="text-orange-800 font-medium flex items-center gap-2">
                    <Brain className="w-4 h-4 animate-bounce" />
                    Multi-Model Consensus: 94% agreement across all AI models
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-6">
              Why FlexiAnalyse Dominates the AI Landscape
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              We don't just use one AI model - we orchestrate an entire symphony of artificial intelligence
            </p>
            
            {/* Detailed AI Models Section */}
            <div className="bg-gradient-to-r from-gray-50 to-blue-50 rounded-2xl p-8 mb-12">
              <h3 className="text-2xl font-bold text-gray-900 mb-6">The Ultimate AI Arsenal</h3>
              <div className="grid md:grid-cols-5 gap-4">
                <div className="bg-white p-4 rounded-xl shadow-sm border-2 border-green-200 hover:border-green-400 transition-all transform hover:scale-105 hover:rotate-1">
                  <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg flex items-center justify-center mx-auto mb-3">
                    <Zap className="w-6 h-6 text-white" />
                  </div>
                  <h4 className="font-bold text-green-700 mb-2">GPT-5</h4>
                  <p className="text-sm text-gray-600">The latest breakthrough in reasoning and analysis</p>
                </div>
                <div className="bg-white p-4 rounded-xl shadow-sm border-2 border-blue-200 hover:border-blue-400 transition-all transform hover:scale-105 hover:rotate-1">
                  <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center mx-auto mb-3">
                    <Brain className="w-6 h-6 text-white" />
                  </div>
                  <h4 className="font-bold text-blue-700 mb-2">GPT-4</h4>
                  <p className="text-sm text-gray-600">Proven excellence in complex document understanding</p>
                </div>
                <div className="bg-white p-4 rounded-xl shadow-sm border-2 border-purple-200 hover:border-purple-400 transition-all transform hover:scale-105 hover:rotate-1">
                  <div className="w-12 h-12 bg-gradient-to-r from-purple-500 to-indigo-500 rounded-lg flex items-center justify-center mx-auto mb-3">
                    <Sparkles className="w-6 h-6 text-white" />
                  </div>
                  <h4 className="font-bold text-purple-700 mb-2">Claude</h4>
                  <p className="text-sm text-gray-600">Exceptional at nuanced analysis and ethical reasoning</p>
                </div>
                <div className="bg-white p-4 rounded-xl shadow-sm border-2 border-orange-200 hover:border-orange-400 transition-all transform hover:scale-105 hover:rotate-1">
                  <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-red-500 rounded-lg flex items-center justify-center mx-auto mb-3">
                    <Target className="w-6 h-6 text-white" />
                  </div>
                  <h4 className="font-bold text-orange-700 mb-2">Mistral</h4>
                  <p className="text-sm text-gray-600">Lightning-fast processing with European precision</p>
                </div>
                <div className="bg-white p-4 rounded-xl shadow-sm border-2 border-gray-200 hover:border-gray-400 transition-all transform hover:scale-105 hover:rotate-1">
                  <div className="w-12 h-12 bg-gradient-to-r from-gray-500 to-slate-500 rounded-lg flex items-center justify-center mx-auto mb-3">
                    <Globe className="w-6 h-6 text-white" />
                  </div>
                  <h4 className="font-bold text-gray-700 mb-2">GPT-3.5 Nano</h4>
                  <p className="text-sm text-gray-600">Efficient processing for rapid insights</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center p-8 bg-gradient-to-br from-blue-50 to-cyan-50 rounded-2xl transform hover:scale-105 transition-transform">
              <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center mx-auto mb-6">
                <Search className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-semibold text-gray-900 mb-4">Quantum-Level Search</h3>
              <p className="text-gray-600 leading-relaxed">
                Our multi-model approach doesn't just find information - it understands context, intent, and hidden connections across your entire document ecosystem
              </p>
            </div>

            <div className="text-center p-8 bg-gradient-to-br from-green-50 to-emerald-50 rounded-2xl transform hover:scale-105 transition-transform">
              <div className="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-500 rounded-xl flex items-center justify-center mx-auto mb-6">
                <FileText className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-semibold text-gray-900 mb-4">Universal Format Mastery</h3>
              <p className="text-gray-600 leading-relaxed">
                From PDFs to PowerPoints, Excel to Word - our AI ensemble extracts meaning from any format with surgical precision and human-like understanding
              </p>
            </div>

            <div className="text-center p-8 bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl transform hover:scale-105 transition-transform">
              <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center mx-auto mb-6">
                <Shield className="w-8 h-8 text-white" />
              </div>
              <h3 className="text-2xl font-semibold text-gray-900 mb-4">Fort Knox Security</h3>
              <p className="text-gray-600 leading-relaxed">
                Your documents are protected by military-grade encryption and privacy protocols that even our AI models respect and maintain
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600">
        <div className="max-w-4xl mx-auto text-center px-4 sm:px-6 lg:px-8">
          <h2 className="text-4xl font-bold text-white mb-6">
            Ready to Experience the AI Revolution?
          </h2>
          <p className="text-xl text-blue-100 mb-8 leading-relaxed">
            Join the elite community of innovators who have already discovered what happens when 
            the world's most powerful AI models work together in perfect harmony
          </p>
          <button
            onClick={() => setIsLoginModalOpen(true)}
            className="bg-white text-purple-600 px-10 py-5 rounded-full font-bold text-lg hover:bg-gray-100 transition-all inline-flex items-center gap-3 shadow-2xl pulse-border"
          >
            Unlock the Power Now
            <ArrowRight className="w-6 h-6" />
          </button>
          <p className="text-blue-200 mt-4 text-sm">No credit card required • Instant access • Revolutionary results</p>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center space-x-3 mb-4 md:mb-0">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold">FlexiAnalyse</span>
            </div>
            <div className="flex items-center space-x-6 text-gray-400">
              <Link to="/privacy-policy" className="hover:text-white transition-colors cursor-pointer">Privacy Policy</Link>
              <Link to="/terms-of-use" className="hover:text-white transition-colors cursor-pointer">Terms of Use</Link>
              <span className="hover:text-white transition-colors cursor-pointer">About Us</span>
              <span className="hover:text-white transition-colors cursor-pointer">Contact</span>
              <span className="hover:text-white transition-colors cursor-pointer">API</span>
              <span className="hover:text-white transition-colors cursor-pointer">Blog</span>
              <span className="hover:text-white transition-colors cursor-pointer">Careers</span>
              <span className="hover:text-white transition-colors cursor-pointer">Support</span>
            </div>
          </div>
        </div>
      </footer>

      {/* Login Modal */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
      />
    </div>
  );
};

export default LandingPage;