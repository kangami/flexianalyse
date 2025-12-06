// src/App.tsx - Version avec Error Boundary
import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './components/auth/AuthProvider';
import { ThemeProvider } from './contexts/ThemeContext';
import { LanguageProvider } from './contexts/LanguageContext';
import LandingPage from './components/landing/LandingPage';
import FlexiAnalyseApp from './FlexiAnalyseApp';
import ErrorBoundary from './components/ErrorBoundary';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfUse from './pages/TermsOfUse';

// Composant qui gère l'affichage conditionnel
const AppContent: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  // Affichage pendant le chargement
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-white animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
          <p className="text-gray-600">Chargement de FlexiAnalyse...</p>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      
      {/* Page publique */}
      <Route path="/" element={isAuthenticated ? <Navigate to="/app" replace /> : <LandingPage />} />
      
      {/* App principale (accessible sans authentification mais avec limitations) */}
      <Route path="/app" element={<FlexiAnalyseApp />} />
      
      {/* Pages légales */}
      <Route path="/privacy-policy" element={<PrivacyPolicy />} />
      <Route path="/terms-of-use" element={<TermsOfUse />} />
    </Routes>
  );
};

// Composant principal App
const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <LanguageProvider>
          <div className="min-h-screen w-full">
            <AuthProvider>
              <AppContent />
            </AuthProvider>
          </div>
        </LanguageProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;