// src/components/landing/LandingPage.tsx
import React, { useState } from 'react';
import { ArrowRight, FileText } from 'lucide-react';
import LoginModal from '../auth/LoginModal';
import { Link } from 'react-router-dom';
import Navbar from './Navbar';
import OperationsDiagram from './OperationsDiagram';

const LandingPage: React.FC = () => {
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  return (
    <div 
      className="w-full bg-gradient-to-br from-slate-50 to-blue-50 flex flex-col"
      style={{ minHeight: '100vh' }}
    >
      {/* Navigation */}
      <Navbar />

      {/* Interactive Operations Diagram */}
      <OperationsDiagram />

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
              <div className="flex items-center space-x-2">
                <img src="/flexiAnalyseLogo_website.png" alt="FlexiAnalyse Logo" className="w-9 h-9 object-contain" />
                <span className="text-xl font-bold text-white-900 tracking-tight">FlexiAnalyse</span>
              </div>
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