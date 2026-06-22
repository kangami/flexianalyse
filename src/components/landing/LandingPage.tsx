// src/components/landing/LandingPage.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Play } from 'lucide-react';
import LoginModal from '../auth/LoginModal';
import Navbar from './Navbar';
import OperationsDiagram from './OperationsDiagram';
import FeaturesSection from './FeaturesSection';
import UseCasesSection from './UseCasesSection';
import TestimonialsSection from './TestimonialsSection';
import FAQSection from './FAQSection';

const heroStats = [
  { v: '10x',  l: 'Productivity per role' },
  { v: '50+',  l: 'Data connectors' },
  { v: '90%',  l: 'Less manual work' },
  { v: '24/7', l: 'AI intelligence' },
];

const HERO_VIDEOS = ['/flexi-back1.mp4', '/flexi-back2.mp4', '/flexi-back3.mp4'];

const footerLinks = [
  { label: 'Privacy Policy', to: '/privacy-policy' },
  { label: 'Terms of Use',   to: '/terms-of-use' },
  { label: 'About Us',       to: '/about' },
  { label: 'Contact',        to: '/contact' },
  { label: 'Blog',           to: '/blog' },
  { label: 'Careers',        to: '/careers' },
  { label: 'Support',        to: '/support' },
];

const LandingPage: React.FC = () => {
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // ── Background video crossfade ────────────────────────
  const videoRefs = useRef<(HTMLVideoElement | null)[]>([null, null, null]);
  const activeRef  = useRef(0);
  const [activeVideo, setActiveVideo] = useState(0);

  useEffect(() => {
    videoRefs.current[0]?.play().catch(() => {});
  }, []);

  const handleVideoEnd = (idx: number) => {
    if (idx !== activeRef.current) return;
    const next = (idx + 1) % HERO_VIDEOS.length;
    activeRef.current = next;
    setActiveVideo(next);
    videoRefs.current[next]?.play().catch(() => {});
  };

  return (
    <div className="w-full flex flex-col" style={{ minHeight: '100vh' }}>
      <Navbar />

      {/* ── Hero ──────────────────────────────────────────── */}
      <section
        className="relative min-h-[100svh] flex items-center justify-center overflow-hidden pt-16"
        style={{ background: 'linear-gradient(135deg,#04091e 0%,#0a1640 45%,#0d1a50 70%,#120d35 100%)' }}
      >
        {/* ── Background videos (crossfade) ── */}
        {HERO_VIDEOS.map((src, idx) => (
          <video
            key={src}
            ref={el => { videoRefs.current[idx] = el; }}
            src={src}
            muted
            playsInline
            preload="auto"
            onEnded={() => handleVideoEnd(idx)}
            className="absolute inset-0 w-full h-full object-cover pointer-events-none"
            style={{
              filter: 'blur(3px) brightness(0.55)',
              transform: 'scale(1.07)',
              opacity: activeVideo === idx ? 1 : 0,
              transition: 'opacity 1.4s ease-in-out',
              zIndex: 0,
            }}
          />
        ))}
        {/* Dark overlay — keeps text legible over any video */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'rgba(4,9,30,0.52)', zIndex: 1 }}
        />

        {/* Ambient orbs */}
        <div className="absolute -top-20 -left-32 w-[700px] h-[700px] rounded-full pointer-events-none"
             style={{ background: 'radial-gradient(circle,rgba(59,130,246,0.22),transparent 65%)', filter: 'blur(60px)' }} />
        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] rounded-full pointer-events-none"
             style={{ background: 'radial-gradient(circle,rgba(139,92,246,0.18),transparent 65%)', filter: 'blur(60px)' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/3 w-[900px] h-[400px] rounded-full pointer-events-none"
             style={{ background: 'radial-gradient(circle,rgba(6,182,212,0.08),transparent 65%)', filter: 'blur(80px)' }} />
        {/* Subtle grid */}
        <div className="absolute inset-0 pointer-events-none"
             style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.03) 1px,transparent 1px)', backgroundSize: '64px 64px' }} />

        <div className="relative z-10 max-w-6xl mx-auto px-4 sm:px-6 py-24 text-center">
          {/* Status badge */}
          <div className="inline-flex items-center gap-2.5 mb-8 px-5 py-2 rounded-full border border-blue-400/20 bg-blue-500/10 backdrop-blur-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400" style={{ boxShadow: '0 0 8px #34d399' }} />
            <span className="text-blue-300 text-sm font-semibold tracking-wide">Enterprise Operations Intelligence</span>
          </div>

          {/* Headline */}
          <h1 className="text-5xl sm:text-6xl lg:text-[78px] font-black leading-[1.03] tracking-tight text-white mb-6">
            Your entire organisation.<br />
            <span style={{
              background: 'linear-gradient(90deg,#60a5fa 0%,#a78bfa 50%,#f472b6 100%)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
            }}>
              One single truth.
            </span>
          </h1>

          {/* Sub-headline */}
          <p className="text-lg sm:text-xl text-gray-300 max-w-2xl mx-auto mb-10 leading-relaxed">
            A{' '}
            <span className="text-white font-semibold">dedicated AI agent for every role</span>
            {' '}— connecting all your data, surfacing hidden insights, and making every employee{' '}
            <span className="text-white font-semibold">10X more effective</span>.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link
              to="/get-started"
              className="group inline-flex items-center gap-2 px-8 py-4 rounded-xl text-white font-bold text-lg transition-all duration-200 hover:scale-105"
              style={{ background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)', boxShadow: '0 8px 40px rgba(139,92,246,0.45)' }}
            >
              Start For Free
              <ArrowRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <button
              className="inline-flex items-center gap-3 px-8 py-4 rounded-xl text-white font-semibold text-lg border border-white/15 backdrop-blur-sm hover:bg-white/10 transition-all duration-200"
              style={{ background: 'rgba(255,255,255,0.06)' }}
            >
              <span className="w-9 h-9 flex items-center justify-center rounded-full" style={{ background: 'rgba(255,255,255,0.15)' }}>
                <Play className="w-4 h-4 fill-white text-white" />
              </span>
              Watch Demo
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-2xl mx-auto">
            {heroStats.map(s => (
              <div
                key={s.l}
                className="rounded-xl p-4 text-center backdrop-blur-sm"
                style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
              >
                <div
                  className="text-3xl sm:text-4xl font-black mb-1"
                  style={{ background: 'linear-gradient(135deg,#60a5fa,#a78bfa)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}
                >
                  {s.v}
                </div>
                <div className="text-xs text-gray-400 leading-tight">{s.l}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Wave transition to white */}
        <div className="absolute bottom-0 inset-x-0 pointer-events-none" style={{ zIndex: 20 }}>
          <svg viewBox="0 0 1440 96" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none" className="w-full block" style={{ height: '80px' }}>
            <path d="M0,48 C360,96 1080,0 1440,48 L1440,96 L0,96 Z" fill="white" />
          </svg>
        </div>
      </section>

      {/* ── Main page sections (white bg) ── */}
      <div className="bg-white">
        <OperationsDiagram />
        <FeaturesSection />
        <UseCasesSection />
        <TestimonialsSection />
        <FAQSection />

        {/* ── Final CTA Banner ─────────────────────────────── */}
        <section
          className="py-24 px-4"
          style={{ background: 'linear-gradient(135deg,#04091e 0%,#0a1640 50%,#120d35 100%)' }}
        >
          {/* Orbs */}
          <div className="pointer-events-none absolute inset-0 overflow-hidden">
            <div style={{ position: 'absolute', top: '-80px', left: '20%', width: '400px', height: '400px', background: 'radial-gradient(circle,rgba(59,130,246,0.15),transparent 65%)', filter: 'blur(60px)' }} />
            <div style={{ position: 'absolute', bottom: '-80px', right: '20%', width: '400px', height: '400px', background: 'radial-gradient(circle,rgba(139,92,246,0.15),transparent 65%)', filter: 'blur(60px)' }} />
          </div>
          <div className="relative max-w-3xl mx-auto text-center">
            <p className="text-blue-400 text-sm font-semibold uppercase tracking-widest mb-4">Get Started Today</p>
            <h2 className="text-4xl sm:text-5xl font-black text-white mb-5 leading-tight">
              Ready to 10X your team?
            </h2>
            <p className="text-xl text-gray-300 mb-8 leading-relaxed">
              Connect your data, deploy AI agents for every role, and get operational intelligence — in minutes, not months.
            </p>
            <Link
              to="/get-started"
              className="inline-flex items-center gap-2 px-10 py-4 rounded-xl text-white font-bold text-lg transition-all hover:scale-105"
              style={{ background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)', boxShadow: '0 8px 40px rgba(139,92,246,0.45)' }}
            >
              Get Started Free <ArrowRight className="w-5 h-5" />
            </Link>
          </div>
        </section>

        {/* ── Footer ─────────────────────────────────────────── */}
        <footer className="bg-gray-950 text-white py-12">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex flex-col md:flex-row justify-between items-center gap-6 mb-8">
              <div className="flex items-center gap-3">
                <img src="/flexiAnalyseLogo_website.png" alt="FlexiAnalyse Logo" className="w-9 h-9 object-contain" />
                <div>
                  <span className="text-xl font-bold text-white tracking-tight">FlexiAnalyse</span>
                  <p className="text-xs text-gray-500">Enterprise Operations Intelligence</p>
                </div>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-sm text-gray-400">
                {footerLinks.map(l => (
                  <Link key={l.to} to={l.to} className="hover:text-white transition-colors">{l.label}</Link>
                ))}
              </div>
            </div>
            <div className="border-t border-gray-800 pt-6 text-center text-gray-600 text-sm">
              © {new Date().getFullYear()} FlexiAnalyse. All rights reserved.
            </div>
          </div>
        </footer>
      </div>

      <LoginModal isOpen={isLoginModalOpen} onClose={() => setIsLoginModalOpen(false)} />
    </div>
  );
};

export default LandingPage;