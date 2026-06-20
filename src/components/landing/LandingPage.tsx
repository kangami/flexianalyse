// src/components/landing/LandingPage.tsx
import React, { useState } from 'react';
import { FileText, Users, Hospital, Briefcase, ShoppingCart, Banknote } from 'lucide-react';
import LoginModal from '../auth/LoginModal';
import { Link } from 'react-router-dom';
import Navbar from './Navbar';
import OperationsDiagram from './OperationsDiagram';
import FeaturesSection from './FeaturesSection';
import UseCasesSection from './UseCasesSection';
import TestimonialsSection from './TestimonialsSection';
import FAQSection from './FAQSection';

const LandingPage: React.FC = () => {
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  return (
    <div 
      className="w-full bg-gradient-to-br from-slate-50 to-blue-50 flex flex-col"
      style={{ minHeight: '100vh' }}
    >
       {/* Navigation */}
       <Navbar />

        {/* Hero Section */}
        {/* <section className="py-20 bg-gradient-to-br from-slate-50 to-blue-50">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            FlexiAnalyse - Transforming Data into Insights
          </div>
        </section> */}

       {/* Interactive Operations Diagram */}
       <OperationsDiagram />

       {/* Features Section */}
       <FeaturesSection />

       {/* Use Cases Section */}
       <UseCasesSection />

       {/* Testimonials Section */}
       <TestimonialsSection />

       {/* FAQ Section */}
       <FAQSection />

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-12">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center mb-12">
            <div className="flex items-center space-x-3 mb-4 md:mb-0">
              <div className="flex items-center space-x-2">
                <img src="/flexiAnalyseLogo_website.png" alt="FlexiAnalyse Logo" className="w-9 h-9 object-contain" />
                <span className="text-xl font-bold text-white tracking-tight">FlexiAnalyse</span>
              </div>
            </div>
            <div className="flex items-center space-x-6 text-gray-400">
              <Link to="/privacy-policy" className="hover:text-white transition-colors cursor-pointer">Privacy Policy</Link>
              <Link to="/terms-of-use" className="hover:text-white transition-colors cursor-pointer">Terms of Use</Link>
              <Link to="/about" className="hover:text-white transition-colors cursor-pointer">About Us</Link>
              <Link to="/contact" className="hover:text-white transition-colors cursor-pointer">Contact</Link>
              <Link to="/api" className="hover:text-white transition-colors cursor-pointer">API</Link>
              <Link to="/blog" className="hover:text-white transition-colors cursor-pointer">Blog</Link>
              <Link to="/careers" className="hover:text-white transition-colors cursor-pointer">Careers</Link>
              <Link to="/support" className="hover:text-white transition-colors cursor-pointer">Support</Link>
            </div>
          </div>
          <div className="border-t border-gray-800 pt-8 text-center text-gray-400">
            <p>© {new Date().getFullYear()} FlexiAnalyse. All rights reserved.</p>
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