import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import Navbar from '../components/landing/Navbar';
import SchemaExplorerSection from '../components/landing/SchemaExplorerSection';

/** Dedicated page for the Schema Explorer feature (linked from Platform menu). */
const SchemaExplorer: React.FC = () => {
  return (
    <div className="w-full flex flex-col min-h-screen" style={{ background: '#0a0a0f' }}>
      <Navbar />

      <div className="pt-16 flex-1">
        <SchemaExplorerSection />

        {/* CTA */}
        <section className="py-16 px-4 relative overflow-hidden" style={{ background: 'linear-gradient(135deg,#000000 0%,#100823 50%,#0a0a0f 100%)' }}>
          <div className="pointer-events-none absolute inset-0 overflow-hidden">
            <div style={{ position: 'absolute', top: '-80px', left: '25%', width: '400px', height: '400px', background: 'radial-gradient(circle,rgba(139,92,246,0.2),transparent 65%)', filter: 'blur(60px)' }} />
          </div>
          <div className="relative max-w-3xl mx-auto text-center">
            <h2 className="text-3xl sm:text-4xl font-black text-white mb-5 leading-tight">
              See your own database, mapped in minutes.
            </h2>
            <p className="text-lg text-gray-300 mb-8 leading-relaxed">
              Connect a database and let our agents draw the map. Search it, click into any table, and start asking questions.
            </p>
            <Link
              to="/get-started"
              className="inline-flex items-center gap-2 px-10 py-4 rounded-xl text-white font-bold text-lg transition-all hover:scale-105"
              style={{ background: 'linear-gradient(135deg,#8b5cf6,#6d28d9)', boxShadow: '0 8px 40px rgba(124,58,237,0.5)' }}
            >
              Get Started Free <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </section>
      </div>

      {/* Footer */}
      <footer className="bg-gray-950 text-white py-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-3">
            <img src="/flexiAnalyseLogo_website.png" alt="FlexiAnalyse Logo" className="w-8 h-8 object-contain" />
            <span className="text-lg font-bold tracking-tight">FlexiAnalyse</span>
          </Link>
          <div className="flex items-center gap-5 text-sm text-gray-400">
            <Link to="/" className="hover:text-white transition-colors">Home</Link>
            <Link to="/get-started" className="hover:text-white transition-colors">Get Started</Link>
          </div>
          <p className="text-xs text-gray-600">© {new Date().getFullYear()} FlexiAnalyse.</p>
        </div>
      </footer>
    </div>
  );
};

export default SchemaExplorer;
