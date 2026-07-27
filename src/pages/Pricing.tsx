import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Check, ServerCog } from 'lucide-react';
import Navbar from '../components/landing/Navbar';
import { useLanguage } from '../contexts/LanguageContext';
import { useAuth } from '../components/auth/AuthProvider';
import { authFetch, API_BASE } from '../lib/apiClient';
import { TIERS, Tier, pricingCopy, tierPrice } from '../lib/pricing';

/** Public pricing page. Tiers, prices and copy come from the shared src/lib/pricing
 * module (same source as the in-app Plans overlay). Annual billing = 2 months off. */

const Pricing: React.FC = () => {
  const { language } = useLanguage();
  const c = pricingCopy(language);
  const tiers = TIERS;
  const { isAuthenticated, account } = useAuth();
  const navigate = useNavigate();
  const [annual, setAnnual] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const priceLabel = (t: Tier) => tierPrice(t, annual, c);

  // Free → sign up. Enterprise → contact (get-started lead form). Paid tiers →
  // Stripe checkout when signed in, else route to sign-up first.
  const onCta = async (t: Tier) => {
    if (t.id === 'free' || t.id === 'enterprise') { navigate('/get-started'); return; }
    if (!isAuthenticated) { navigate('/get-started', { state: { next: '/pricing' } }); return; }
    setBusy(t.id);
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (account?.organization_id) headers['X-Organization-Id'] = account.organization_id;
      const r = await authFetch(`${API_BASE}/api/v2/billing/checkout`, {
        method: 'POST', headers,
        body: JSON.stringify({ plan: t.id, interval: annual ? 'year' : 'month' }),
      });
      const d = await r.json();
      if (d.url) window.location.href = d.url;
      else { setBusy(null); alert(d.error || 'Checkout failed'); }
    } catch { setBusy(null); }
  };

  return (
    <div className="w-full flex flex-col min-h-screen bg-gray-50">
      <Navbar />

      {/* Header */}
      <section className="pt-28 pb-10 px-4 relative overflow-hidden" style={{ background: 'linear-gradient(135deg,#000000 0%,#150a2e 60%,#0a0a0f 100%)' }}>
        <div className="absolute -top-24 left-1/3 w-[500px] h-[500px] rounded-full pointer-events-none" style={{ background: 'radial-gradient(circle,rgba(139,92,246,0.22),transparent 65%)', filter: 'blur(70px)' }} />
        <div className="relative max-w-3xl mx-auto text-center">
          <h1 className="text-4xl sm:text-5xl font-black text-white mb-4 leading-tight">
            {c.title1}{' '}
            <span style={{ background: 'linear-gradient(90deg,#c4b5fd,#a78bfa 50%,#7c3aed)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
              {c.title2}
            </span>
          </h1>
          <p className="text-lg text-gray-300 mb-7">{c.subtitle}</p>

          {/* Monthly / Annual toggle */}
          <div className="inline-flex items-center gap-1 p-1 rounded-full bg-white/10 border border-white/15">
            <button onClick={() => setAnnual(false)} className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-colors ${!annual ? 'bg-white text-violet-800' : 'text-gray-300'}`}>{c.monthly}</button>
            <button onClick={() => setAnnual(true)} className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-colors inline-flex items-center gap-1.5 ${annual ? 'bg-white text-violet-800' : 'text-gray-300'}`}>
              {c.annual} <span className="text-[10px] font-bold text-emerald-500 bg-emerald-100 rounded-full px-1.5">{c.twoMonthsFree}</span>
            </button>
          </div>
        </div>
      </section>

      {/* Cards */}
      <section className="px-4 -mt-4 pb-16">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {tiers.map((t) => {
            const tc = c.tiers[t.id];
            return (
              <div key={t.id} className={`relative rounded-2xl bg-white p-6 flex flex-col border ${t.highlight ? 'border-violet-400 shadow-xl' : 'border-gray-200 shadow-sm'}`}>
                {t.highlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-bold text-white px-3 py-1 rounded-full whitespace-nowrap" style={{ background: 'linear-gradient(135deg,#8b5cf6,#6d28d9)' }}>
                    {c.mostPopular}
                  </span>
                )}
                <p className="text-sm font-bold text-gray-900">{t.name}</p>
                <p className="text-xs text-gray-500 mb-4 min-h-[2rem]">{tc.tagline}</p>
                <div className="mb-1 flex items-end gap-1">
                  <span className="text-4xl font-black text-gray-900">{priceLabel(t)}</span>
                  {t.monthly !== null && t.monthly > 0 && <span className="text-xs text-gray-400 mb-1.5">{c.perMonth}</span>}
                </div>
                <p className="text-[11px] text-gray-400 mb-5 h-4">
                  {t.monthly !== null && t.monthly > 0 && annual ? c.billed(t.yearly as number) : ' '}
                </p>

                <button
                  onClick={() => onCta(t)}
                  disabled={busy === t.id}
                  className={`px-4 py-2.5 rounded-lg text-sm font-semibold mb-5 transition-all disabled:opacity-50 ${t.highlight ? 'text-white hover:scale-[1.02]' : 'text-violet-700 border border-violet-200 hover:bg-violet-50'}`}
                  style={t.highlight ? { background: 'linear-gradient(135deg,#8b5cf6,#6d28d9)' } : undefined}
                >
                  {busy === t.id ? '…' : tc.cta}
                </button>

                <ul className="space-y-2">
                  {tc.features.map((f, i) => {
                    const heading = i === 0 && t.id === 'enterprise';
                    return (
                      <li key={i} className={`flex items-start gap-2 text-sm ${heading ? 'text-gray-400 italic' : 'text-gray-700'}`}>
                        {!heading && <Check className="w-4 h-4 text-violet-500 flex-shrink-0 mt-0.5" />}
                        {f}
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>

        {/* On-prem note + fair-use note */}
        <div className="max-w-4xl mx-auto mt-10 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="rounded-xl bg-white border border-gray-200 p-4 flex items-start gap-3">
            <ServerCog className="w-5 h-5 text-violet-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-gray-600">{c.onprem}</p>
          </div>
          <div className="rounded-xl bg-white border border-gray-200 p-4">
            <p className="text-xs text-gray-600">{c.fairuse}</p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-950 text-white py-10 mt-auto">
        <div className="max-w-6xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-3">
            <img src="/flexiAnalyseLogo_website.png" alt="FlexiAnalyse Logo" className="w-8 h-8 object-contain" />
            <span className="text-lg font-bold tracking-tight">FlexiAnalyse</span>
          </Link>
          <div className="flex items-center gap-5 text-sm text-gray-400">
            <Link to="/" className="hover:text-white transition-colors">{c.home}</Link>
            <Link to="/get-started" className="hover:text-white transition-colors">{c.getStarted}</Link>
          </div>
          <p className="text-xs text-gray-600">© {new Date().getFullYear()} FlexiAnalyse.</p>
        </div>
      </footer>
    </div>
  );
};

export default Pricing;
