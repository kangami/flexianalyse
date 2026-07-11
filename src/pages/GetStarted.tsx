import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, ArrowLeft, CheckCircle2, Shield, Network, Zap, Users } from 'lucide-react';
import Navbar from '../components/landing/Navbar';

const companySizes = ['1–100', '101–500', '501–1,000', '1,001–2,000', '2,000+'];

const countries = [
  'United States', 'United Kingdom', 'Canada', 'France', 'Germany', 'Australia',
  'Netherlands', 'Switzerland', 'Belgium', 'Spain', 'Italy', 'Brazil', 'India',
  'Japan', 'Singapore', 'South Korea', 'UAE', 'South Africa', 'Mexico', 'Other',
];

const GetStarted: React.FC = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2>(1);
  const [animating, setAnimating] = useState(false);
  const [direction, setDirection] = useState<'forward' | 'backward'>('forward');

  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [workEmail, setWorkEmail] = useState('');
  const [companySize, setCompanySize] = useState('');
  const [country, setCountry] = useState('');
  const [message, setMessage] = useState('');

  const [submitted, setSubmitted] = useState(false);
  const [alreadyExists, setAlreadyExists] = useState(false);
  const [apiError, setApiError] = useState('');
  const [loading, setLoading] = useState(false);

  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:5000';

  const goNext = () => {
    if (!country || !firstName.trim() || !lastName.trim()) return;
    setDirection('forward');
    setAnimating(true);
    setTimeout(() => {
      setStep(2);
      setAnimating(false);
    }, 400);
  };

  const goBack = () => {
    setApiError('');
    setDirection('backward');
    setAnimating(true);
    setTimeout(() => {
      setStep(1);
      setAnimating(false);
    }, 400);
  };

  const handleSubmit = async () => {
    if (!workEmail.trim() || !companySize) return;
    setApiError('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/api/v2/leads`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          firstName: firstName.trim(),
          lastName: lastName.trim(),
          workEmail: workEmail.trim(),
          companySize,
          country,
          message: message.trim(),
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setApiError(data.error || 'Something went wrong');
        setLoading(false);
        return;
      }

      if (data.exists) {
        setAlreadyExists(true);
      }

      setAnimating(true);
      setTimeout(() => {
        setSubmitted(true);
        setAnimating(false);
        setLoading(false);
      }, 400);
    } catch {
      setApiError('Unable to connect to server. Please try again.');
      setLoading(false);
    }
  };

  const inputClass =
    'w-full px-4 py-3 rounded-xl border border-gray-200 bg-white/80 backdrop-blur-sm text-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 placeholder:text-gray-400';

  const labelClass = 'block text-sm font-medium text-gray-700 mb-1.5';

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 flex flex-col">
      <Navbar />

      {/* Main content */}
      <div className="flex-1 flex items-center justify-center px-4 pt-24 pb-12">
        <div className="max-w-5xl w-full grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-16 items-center">

          {/* ─── Left Side: Value Proposition ─── */}
          <div className="space-y-8">
            <div>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-gray-900 leading-tight mb-4">
                You bring your systems.{' '}
                <span className="gradient-text-flow">We make them work together — intelligently.</span>
              </h2>
              <p className="text-lg text-gray-600 leading-relaxed">
                FlexiAnalyse connects your data sources, enforces your access control policies,
                and orchestrates AI agents so every operation runs seamlessly.
              </p>
            </div>

            <div className="space-y-4">
              {[
                { icon: <Network className="w-5 h-5" />, title: 'Unified Connectivity', desc: 'Bring together Google Drive, Dropbox, SharePoint, SQL and more in one place.' },
                { icon: <Shield className="w-5 h-5" />, title: 'Your Policies, Enforced', desc: 'Role-based access, encryption, and audit logs — security built in, not bolted on.' },
                { icon: <Zap className="w-5 h-5" />, title: 'AI-Powered Orchestration', desc: 'Intelligent agents that understand, plan, and execute work across your enterprise.' },
                { icon: <Users className="w-5 h-5" />, title: 'Human-in-the-Loop', desc: 'Stay in control with approvals, oversight, and guardrails at every step.' },
              ].map((item) => (
                <div key={item.title} className="flex items-start gap-3">
                  <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                    {item.icon}
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-gray-800">{item.title}</h4>
                    <p className="text-sm text-gray-500">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ─── Right Side: Form Card ─── */}
          <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8 sm:p-10 relative overflow-hidden">
            {/* Step indicator */}
            {!submitted && (
              <div className="flex items-center gap-3 mb-8">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors duration-300 ${step === 1 ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-600'}`}>1</div>
                <div className={`h-0.5 flex-1 rounded transition-colors duration-300 ${step === 2 ? 'bg-blue-600' : 'bg-gray-200'}`} />
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors duration-300 ${step === 2 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-400'}`}>2</div>
              </div>
            )}

            {/* ── Success State ── */}
            {submitted ? (
              <div
                className="flex flex-col items-center justify-center text-center py-8"
                style={{ animation: 'fadeInUp 0.5s ease-out forwards' }}
              >
                {alreadyExists ? (
                  <>
                    <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-5">
                      <CheckCircle2 className="w-9 h-9 text-blue-600" />
                    </div>
                    <h3 className="text-2xl font-bold text-gray-900 mb-2">We know you!</h3>
                    <p className="text-gray-600 mb-6 max-w-xs">
                      We already have your information — we will connect with you <strong>ASAP</strong>!
                    </p>
                  </>
                ) : (
                  <>
                    <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-5">
                      <CheckCircle2 className="w-9 h-9 text-green-600" />
                    </div>
                    <h3 className="text-2xl font-bold text-gray-900 mb-2">You're all set!</h3>
                    <p className="text-gray-600 mb-6 max-w-xs">
                      Thank you, {firstName}. Our team will reach out to <strong>{workEmail}</strong> shortly.
                    </p>
                  </>
                )}
                <button
                  onClick={() => navigate('/')}
                  className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-full font-semibold text-sm hover:shadow-lg transition-all"
                >
                  Back to Home
                </button>
              </div>
            ) : (
              <div>
                {/* ── Step 1 ── */}
                <div
                  style={{
                    display: step === 1 && !animating ? 'block' : step === 1 && animating ? 'block' : 'none',
                    animation: step === 1
                      ? animating
                        ? direction === 'forward'
                          ? 'fadeOutLeft 0.4s ease-in forwards'
                          : 'fadeInRight 0.4s ease-out forwards'
                        : 'fadeInRight 0.4s ease-out forwards'
                      : undefined,
                  }}
                >
                  <h3 className="text-xl font-bold text-gray-900 mb-1">
                    We are delighted to know you
                  </h3>
                  <p className="text-sm text-gray-500 mb-6">Welcome to the family.</p>

                  <div className="space-y-4">
                    <div>
                      <label className={labelClass}>Country</label>
                      <select
                        className={inputClass}
                        value={country}
                        onChange={(e) => setCountry(e.target.value)}
                        required
                        autoFocus
                      >
                        <option value="" disabled>Select your country</option>
                        {countries.map((c) => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={labelClass}>First Name</label>
                      <input
                        type="text"
                        className={inputClass}
                        placeholder="John"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        required
                      />
                    </div>
                    <div>
                      <label className={labelClass}>Last Name</label>
                      <input
                        type="text"
                        className={inputClass}
                        placeholder="Doe"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <div className="mt-8 flex justify-center">
                    <button
                      type="button"
                      onClick={goNext}
                      disabled={!country || !firstName.trim() || !lastName.trim()}
                      className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-full font-semibold text-sm inline-flex items-center gap-2 hover:shadow-lg hover:scale-105 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
                    >
                      Next
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* ── Step 2 ── */}
                <div
                  style={{
                    display: step === 2 && !animating ? 'block' : step === 2 && animating ? 'block' : 'none',
                    animation: step === 2
                      ? animating
                        ? direction === 'backward'
                          ? 'fadeOutRight 0.4s ease-in forwards'
                          : 'fadeInLeft 0.4s ease-out forwards'
                        : 'fadeInLeft 0.4s ease-out forwards'
                      : undefined,
                  }}
                >
                  <h3 className="text-xl font-bold text-gray-900 mb-1">
                    Let's build something extraordinary
                  </h3>
                  <p className="text-sm text-gray-500 mb-6">Together, we'll transform the way you operate.</p>

                  <div className="space-y-4">
                    <div>
                      <label className={labelClass}>Work Email</label>
                      <input
                        type="email"
                        className={inputClass}
                        placeholder="john@company.com"
                        value={workEmail}
                        onChange={(e) => setWorkEmail(e.target.value)}
                        required
                        autoFocus
                      />
                    </div>
                    <div>
                      <label className={labelClass}>Company Size</label>
                      <select
                        className={inputClass}
                        value={companySize}
                        onChange={(e) => setCompanySize(e.target.value)}
                        required
                      >
                        <option value="" disabled>Select company size</option>
                        {companySizes.map((size) => (
                          <option key={size} value={size}>{size} employees</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className={labelClass}>Message <span className="text-gray-400 font-normal">(optional)</span></label>
                      <textarea
                        className={`${inputClass} resize-none`}
                        rows={4}
                        placeholder="Tell us a bit about what you're looking to achieve…"
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Error message */}
                  {apiError && (
                    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
                      {apiError}
                    </div>
                  )}

                  <div className="mt-8 flex items-center justify-between">
                    <button
                      type="button"
                      onClick={goBack}
                      disabled={loading}
                      className="px-5 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-900 inline-flex items-center gap-1.5 transition-colors disabled:opacity-40"
                    >
                      <ArrowLeft className="w-4 h-4" />
                      Back
                    </button>
                    <button
                      type="button"
                      onClick={handleSubmit}
                      disabled={!workEmail.trim() || !companySize || loading}
                      className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-full font-semibold text-sm inline-flex items-center gap-2 hover:shadow-lg hover:scale-105 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
                    >
                      {loading ? 'Submitting...' : 'Submit'}
                      {!loading && <CheckCircle2 className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Contact line */}
            <p className="mt-6 pt-6 border-t border-gray-100 text-center text-xs text-gray-500">
              Prefer email? Reach us at{' '}
              <a
                href="mailto:contact@flexianalyse.com"
                className="text-blue-600 hover:underline font-medium"
              >
                contact@flexianalyse.com
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GetStarted;
