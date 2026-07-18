import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signInWithPopup,
  updateProfile,
} from 'firebase/auth';
import {
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Shield,
  Network,
  Zap,
  Users,
  User as UserIcon,
  Building2,
} from 'lucide-react';
import Navbar from '../components/landing/Navbar';
import { useAuth } from '../components/auth/AuthProvider';
import { auth, googleProvider } from '../lib/firebase';
import { apiFetch, setPendingFullName } from '../lib/apiClient';

const companySizes = ['1–100', '101–500', '501–1,000', '1,001–2,000', '2,000+'];

const countries = [
  'United States', 'United Kingdom', 'Canada', 'France', 'Germany', 'Australia',
  'Netherlands', 'Switzerland', 'Belgium', 'Spain', 'Italy', 'Brazil', 'India',
  'Japan', 'Singapore', 'South Korea', 'UAE', 'South Africa', 'Mexico', 'Other',
];

/** Connexion (défaut) ou création de compte. */
type Mode = 'signin' | 'signup';
/** Compte perso → accès direct à /app. Entreprise → formulaire lead, contact commercial. */
type AccountType = 'personal' | 'company';

const GoogleIcon: React.FC = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" aria-hidden="true">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
);

/** Les codes Firebase bruts ne sont pas lisibles par un utilisateur. */
const friendlyAuthError = (error: unknown): string => {
  const code = (error as { code?: string })?.code || '';
  switch (code) {
    case 'auth/invalid-credential':
    case 'auth/wrong-password':
    case 'auth/user-not-found':
      return 'Incorrect email or password.';
    case 'auth/email-already-in-use':
      return 'An account already exists with this email. Try signing in instead.';
    case 'auth/weak-password':
      return 'Password is too weak — use at least 6 characters.';
    case 'auth/invalid-email':
      return 'That email address looks invalid.';
    case 'auth/too-many-requests':
      return 'Too many attempts. Please wait a moment and try again.';
    case 'auth/popup-closed-by-user':
    case 'auth/cancelled-popup-request':
      return '';
    case 'auth/unauthorized-domain':
      return 'This domain is not authorised for sign-in. Contact support.';
    default:
      return 'Something went wrong. Please try again.';
  }
};

const GetStarted: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  const [mode, setMode] = useState<Mode>('signin');
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [accountType, setAccountType] = useState<AccountType | null>(null);

  // Étape 1 — identité, commune aux deux types de compte.
  const [country, setCountry] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');

  // Connexion + compte personnel.
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Compte entreprise (lead).
  const [workEmail, setWorkEmail] = useState('');
  const [companySize, setCompanySize] = useState('');
  const [message, setMessage] = useState('');

  const [submitted, setSubmitted] = useState(false);
  const [alreadyExists, setAlreadyExists] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Une fois Firebase authentifié, AuthProvider provisionne le compte puis
  // bascule isAuthenticated — on redirige alors vers la destination demandée.
  useEffect(() => {
    if (!isAuthenticated) return;
    const from = (location.state as { from?: string } | null)?.from;
    navigate(from || '/app', { replace: true });
  }, [isAuthenticated, navigate, location.state]);

  const resetError = () => setError('');

  const handleGoogle = async () => {
    resetError();
    setLoading(true);
    try {
      await signInWithPopup(auth, googleProvider);
      // La redirection est prise en charge par l'effet ci-dessus.
    } catch (err) {
      setError(friendlyAuthError(err));
      setLoading(false);
    }
  };

  const handleSignIn = async () => {
    if (!email.trim() || !password) return;
    resetError();
    setLoading(true);
    try {
      await signInWithEmailAndPassword(auth, email.trim(), password);
    } catch (err) {
      setError(friendlyAuthError(err));
      setLoading(false);
    }
  };

  const handleCreatePersonal = async () => {
    if (!email.trim() || !password) return;
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    resetError();
    setLoading(true);
    const fullName = `${firstName.trim()} ${lastName.trim()}`.trim();
    // Posé AVANT la création : onAuthStateChanged part aussitôt et provisionne
    // le compte, sans attendre updateProfile ci-dessous.
    setPendingFullName(fullName);
    try {
      const credential = await createUserWithEmailAndPassword(auth, email.trim(), password);
      if (fullName) {
        await updateProfile(credential.user, { displayName: fullName });
      }
      // AuthProvider appelle /api/v2/auth/signup (User + organisation par défaut),
      // puis l'effet redirige vers /app.
    } catch (err) {
      setPendingFullName(undefined);
      setError(friendlyAuthError(err));
      setLoading(false);
    }
  };

  const handleSubmitCompany = async () => {
    if (!workEmail.trim() || !companySize) return;
    resetError();
    setLoading(true);
    try {
      const data = await apiFetch<{ exists: boolean; message: string }>('/api/v2/leads', {
        method: 'POST',
        body: JSON.stringify({
          firstName: firstName.trim(),
          lastName: lastName.trim(),
          workEmail: workEmail.trim(),
          companySize,
          country,
          message: message.trim(),
        }),
      });
      setAlreadyExists(Boolean(data.exists));
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to connect to server.');
    } finally {
      setLoading(false);
    }
  };

  const startSignup = () => {
    resetError();
    setMode('signup');
    setStep(1);
  };

  const backToSignin = () => {
    resetError();
    setMode('signin');
    setAccountType(null);
    setStep(1);
  };

  const goToAccountType = () => {
    if (!country || !firstName.trim() || !lastName.trim()) return;
    resetError();
    setStep(2);
  };

  const chooseAccountType = (type: AccountType) => {
    setAccountType(type);
    resetError();
    setStep(3);
  };

  const inputClass =
    'w-full px-4 py-3 rounded-xl border border-gray-200 bg-white/80 backdrop-blur-sm text-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 placeholder:text-gray-400';
  const labelClass = 'block text-sm font-medium text-gray-700 mb-1.5';
  const primaryBtn =
    'px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-full font-semibold text-sm inline-flex items-center gap-2 hover:shadow-lg hover:scale-105 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100';

  const errorBox = error ? (
    <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
      {error}
    </div>
  ) : null;

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-50 via-blue-50 to-purple-50 flex flex-col">
      <Navbar />

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

          {/* ─── Right Side: Auth Card ─── */}
          <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-8 sm:p-10 relative overflow-hidden">

            {/* ── Lead submitted (compte entreprise) ── */}
            {submitted ? (
              <div
                className="flex flex-col items-center justify-center text-center py-8"
                style={{ animation: 'fadeInUp 0.5s ease-out forwards' }}
              >
                <div className={`w-16 h-16 ${alreadyExists ? 'bg-blue-100' : 'bg-green-100'} rounded-full flex items-center justify-center mb-5`}>
                  <CheckCircle2 className={`w-9 h-9 ${alreadyExists ? 'text-blue-600' : 'text-green-600'}`} />
                </div>
                <h3 className="text-2xl font-bold text-gray-900 mb-2">
                  {alreadyExists ? 'We know you!' : "You're all set!"}
                </h3>
                <p className="text-gray-600 mb-6 max-w-xs">
                  {alreadyExists ? (
                    <>We already have your information — we will connect with you <strong>ASAP</strong>!</>
                  ) : (
                    <>Thank you, {firstName}. Our team will reach out to <strong>{workEmail}</strong> shortly.</>
                  )}
                </p>
                <button onClick={() => navigate('/')} className={primaryBtn}>
                  Back to Home
                </button>
              </div>

            /* ── Connexion ── */
            ) : mode === 'signin' ? (
              <div style={{ animation: 'fadeInRight 0.4s ease-out forwards' }}>
                <h3 className="text-xl font-bold text-gray-900 mb-1">Welcome back</h3>
                <p className="text-sm text-gray-500 mb-6">Sign in to reach your workspace.</p>

                <button
                  type="button"
                  onClick={handleGoogle}
                  disabled={loading}
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-gray-700 text-sm font-medium inline-flex items-center justify-center gap-2.5 hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <GoogleIcon />
                  Continue with Google
                </button>

                <div className="flex items-center gap-3 my-6">
                  <div className="h-px flex-1 bg-gray-100" />
                  <span className="text-xs text-gray-400">or</span>
                  <div className="h-px flex-1 bg-gray-100" />
                </div>

                <div className="space-y-4">
                  <div>
                    <label className={labelClass}>Email</label>
                    <input
                      type="email"
                      className={inputClass}
                      placeholder="john@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoFocus
                    />
                  </div>
                  <div>
                    <label className={labelClass}>Password</label>
                    <input
                      type="password"
                      className={inputClass}
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSignIn()}
                    />
                  </div>
                </div>

                {errorBox}

                <div className="mt-8 flex justify-center">
                  <button
                    type="button"
                    onClick={handleSignIn}
                    disabled={!email.trim() || !password || loading}
                    className={primaryBtn}
                  >
                    {loading ? 'Signing in…' : 'Sign in'}
                    {!loading && <ArrowRight className="w-4 h-4" />}
                  </button>
                </div>

                <p className="mt-6 text-center text-sm text-gray-500">
                  New to FlexiAnalyse?{' '}
                  <button
                    type="button"
                    onClick={startSignup}
                    className="text-blue-600 hover:underline font-medium"
                  >
                    Create an account
                  </button>
                </p>
              </div>

            /* ── Création de compte ── */
            ) : (
              <div>
                {/* Indicateur d'étape */}
                <div className="flex items-center gap-3 mb-8">
                  {[1, 2, 3].map((n, i) => (
                    <React.Fragment key={n}>
                      {i > 0 && (
                        <div className={`h-0.5 flex-1 rounded transition-colors duration-300 ${step >= n ? 'bg-blue-600' : 'bg-gray-200'}`} />
                      )}
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors duration-300 ${
                          step === n ? 'bg-blue-600 text-white' : step > n ? 'bg-blue-100 text-blue-600' : 'bg-gray-200 text-gray-400'
                        }`}
                      >
                        {n}
                      </div>
                    </React.Fragment>
                  ))}
                </div>

                {/* ── Étape 1 : identité ── */}
                {step === 1 && (
                  <div style={{ animation: 'fadeInRight 0.4s ease-out forwards' }}>
                    <h3 className="text-xl font-bold text-gray-900 mb-1">We are delighted to know you</h3>
                    <p className="text-sm text-gray-500 mb-6">Welcome to the family.</p>

                    <button
                      type="button"
                      onClick={handleGoogle}
                      disabled={loading}
                      className="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white text-gray-700 text-sm font-medium inline-flex items-center justify-center gap-2.5 hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <GoogleIcon />
                      Sign up with Google
                    </button>

                    <div className="flex items-center gap-3 my-6">
                      <div className="h-px flex-1 bg-gray-100" />
                      <span className="text-xs text-gray-400">or</span>
                      <div className="h-px flex-1 bg-gray-100" />
                    </div>

                    <div className="space-y-4">
                      <div>
                        <label className={labelClass}>Country</label>
                        <select className={inputClass} value={country} onChange={(e) => setCountry(e.target.value)} required>
                          <option value="" disabled>Select your country</option>
                          {countries.map((c) => (
                            <option key={c} value={c}>{c}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className={labelClass}>First Name</label>
                        <input type="text" className={inputClass} placeholder="John" value={firstName} onChange={(e) => setFirstName(e.target.value)} required />
                      </div>
                      <div>
                        <label className={labelClass}>Last Name</label>
                        <input type="text" className={inputClass} placeholder="Doe" value={lastName} onChange={(e) => setLastName(e.target.value)} required />
                      </div>
                    </div>

                    {errorBox}

                    <div className="mt-8 flex items-center justify-between">
                      <button type="button" onClick={backToSignin} className="px-5 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-900 inline-flex items-center gap-1.5 transition-colors">
                        <ArrowLeft className="w-4 h-4" />
                        Sign in
                      </button>
                      <button
                        type="button"
                        onClick={goToAccountType}
                        disabled={!country || !firstName.trim() || !lastName.trim()}
                        className={primaryBtn}
                      >
                        Next
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}

                {/* ── Étape 2 : type de compte ── */}
                {step === 2 && (
                  <div style={{ animation: 'fadeInLeft 0.4s ease-out forwards' }}>
                    <h3 className="text-xl font-bold text-gray-900 mb-1">How will you use FlexiAnalyse?</h3>
                    <p className="text-sm text-gray-500 mb-6">Pick the option that fits you best.</p>

                    <div className="space-y-3">
                      <button
                        type="button"
                        onClick={() => chooseAccountType('personal')}
                        className="w-full text-left p-4 rounded-xl border border-gray-200 hover:border-blue-400 hover:bg-blue-50/50 transition-all duration-200 flex items-start gap-3 group"
                      >
                        <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0">
                          <UserIcon className="w-5 h-5" />
                        </div>
                        <div className="min-w-0">
                          <h4 className="text-sm font-bold text-gray-800">Personal account</h4>
                          <p className="text-xs text-gray-500 mt-0.5">
                            Get your own workspace right away. Choose a password and start using the app.
                          </p>
                        </div>
                        <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-blue-600 flex-shrink-0 mt-1 transition-colors" />
                      </button>

                      <button
                        type="button"
                        onClick={() => chooseAccountType('company')}
                        className="w-full text-left p-4 rounded-xl border border-gray-200 hover:border-purple-400 hover:bg-purple-50/50 transition-all duration-200 flex items-start gap-3 group"
                      >
                        <div className="w-10 h-10 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center flex-shrink-0">
                          <Building2 className="w-5 h-5" />
                        </div>
                        <div className="min-w-0">
                          <h4 className="text-sm font-bold text-gray-800">Company account</h4>
                          <p className="text-xs text-gray-500 mt-0.5">
                            Tell us about your organisation — our team will set things up with you.
                          </p>
                        </div>
                        <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-purple-600 flex-shrink-0 mt-1 transition-colors" />
                      </button>
                    </div>

                    <div className="mt-8">
                      <button type="button" onClick={() => setStep(1)} className="px-5 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-900 inline-flex items-center gap-1.5 transition-colors">
                        <ArrowLeft className="w-4 h-4" />
                        Back
                      </button>
                    </div>
                  </div>
                )}

                {/* ── Étape 3a : compte personnel ── */}
                {step === 3 && accountType === 'personal' && (
                  <div style={{ animation: 'fadeInLeft 0.4s ease-out forwards' }}>
                    <h3 className="text-xl font-bold text-gray-900 mb-1">Choose your password</h3>
                    <p className="text-sm text-gray-500 mb-6">
                      Your workspace is created automatically — you can start right after.
                    </p>

                    <div className="space-y-4">
                      <div>
                        <label className={labelClass}>Email</label>
                        <input type="email" className={inputClass} placeholder="john@company.com" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
                      </div>
                      <div>
                        <label className={labelClass}>Password</label>
                        <input type="password" className={inputClass} placeholder="At least 6 characters" value={password} onChange={(e) => setPassword(e.target.value)} required />
                      </div>
                      <div>
                        <label className={labelClass}>Confirm Password</label>
                        <input
                          type="password"
                          className={inputClass}
                          placeholder="••••••••"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleCreatePersonal()}
                          required
                        />
                      </div>
                    </div>

                    {errorBox}

                    <div className="mt-8 flex items-center justify-between">
                      <button type="button" onClick={() => setStep(2)} disabled={loading} className="px-5 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-900 inline-flex items-center gap-1.5 transition-colors disabled:opacity-40">
                        <ArrowLeft className="w-4 h-4" />
                        Back
                      </button>
                      <button
                        type="button"
                        onClick={handleCreatePersonal}
                        disabled={!email.trim() || !password || !confirmPassword || loading}
                        className={primaryBtn}
                      >
                        {loading ? 'Creating…' : 'Create account'}
                        {!loading && <CheckCircle2 className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                )}

                {/* ── Étape 3b : compte entreprise (lead) ── */}
                {step === 3 && accountType === 'company' && (
                  <div style={{ animation: 'fadeInLeft 0.4s ease-out forwards' }}>
                    <h3 className="text-xl font-bold text-gray-900 mb-1">Let's build something extraordinary</h3>
                    <p className="text-sm text-gray-500 mb-6">Together, we'll transform the way you operate.</p>

                    <div className="space-y-4">
                      <div>
                        <label className={labelClass}>Work Email</label>
                        <input type="email" className={inputClass} placeholder="john@company.com" value={workEmail} onChange={(e) => setWorkEmail(e.target.value)} required autoFocus />
                      </div>
                      <div>
                        <label className={labelClass}>Company Size</label>
                        <select className={inputClass} value={companySize} onChange={(e) => setCompanySize(e.target.value)} required>
                          <option value="" disabled>Select company size</option>
                          {companySizes.map((size) => (
                            <option key={size} value={size}>{size} employees</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className={labelClass}>
                          Message <span className="text-gray-400 font-normal">(optional)</span>
                        </label>
                        <textarea
                          className={`${inputClass} resize-none`}
                          rows={4}
                          placeholder="Tell us a bit about what you're looking to achieve…"
                          value={message}
                          onChange={(e) => setMessage(e.target.value)}
                        />
                      </div>
                    </div>

                    {errorBox}

                    <div className="mt-8 flex items-center justify-between">
                      <button type="button" onClick={() => setStep(2)} disabled={loading} className="px-5 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-900 inline-flex items-center gap-1.5 transition-colors disabled:opacity-40">
                        <ArrowLeft className="w-4 h-4" />
                        Back
                      </button>
                      <button
                        type="button"
                        onClick={handleSubmitCompany}
                        disabled={!workEmail.trim() || !companySize || loading}
                        className={primaryBtn}
                      >
                        {loading ? 'Submitting…' : 'Submit'}
                        {!loading && <CheckCircle2 className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Contact line */}
            <p className="mt-6 pt-6 border-t border-gray-100 text-center text-xs text-gray-500">
              Prefer email? Reach us at{' '}
              <a href="mailto:contact@flexianalyse.com" className="text-blue-600 hover:underline font-medium">
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
