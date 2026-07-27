import React, { useEffect, useState } from 'react';
import { authFetch, API_BASE } from '../../lib/apiClient';
import { useLanguage } from '../../contexts/LanguageContext';
import { TIERS, Tier, BILLABLE, pricingCopy, tierPrice } from '../../lib/pricing';

/**
 * In-app Plans overlay. Uses the SAME shared pricing source (src/lib/pricing) as
 * the public /pricing page — same tiers, USD prices, and translated copy — so the
 * two never diverge. Highlights the org's current plan (/api/v2/plan) and, for
 * paid tiers, launches Stripe checkout (/api/v2/billing/checkout).
 */

interface PlansViewProps {
  open: boolean;
  onClose: () => void;
  orgId: string | null;
}

const PlansView: React.FC<PlansViewProps> = ({ open, onClose, orgId }) => {
  const { language, t } = useLanguage();
  const c = pricingCopy(language);
  const tiers = TIERS;
  const [currentPlan, setCurrentPlan] = useState<string>('free');
  const [annual, setAnnual] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const headers: Record<string, string> = {};
    if (orgId) headers['X-Organization-Id'] = orgId;
    authFetch(`${API_BASE}/api/v2/plan`, { headers })
      .then(r => r.json())
      .then(d => setCurrentPlan(d.plan || 'free'))
      .catch(() => setCurrentPlan('free'));
  }, [open, orgId]);

  if (!open) return null;

  const onCta = async (tier: Tier) => {
    // Enterprise → contact sales; Free is never an upgrade target here.
    if (tier.id === 'enterprise') {
      window.location.href = `mailto:contact@flexianalyse.com?subject=${encodeURIComponent(t('plans.emailSubject', { plan: tier.name }))}`;
      return;
    }
    if (!BILLABLE.has(tier.id)) return;
    setBusy(tier.id);
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (orgId) headers['X-Organization-Id'] = orgId;
      const r = await authFetch(`${API_BASE}/api/v2/billing/checkout`, {
        method: 'POST', headers,
        body: JSON.stringify({ plan: tier.id, interval: annual ? 'year' : 'month' }),
      });
      const d = await r.json();
      if (d.url) window.location.href = d.url;
      else { setBusy(null); alert(d.error || 'Checkout failed'); }
    } catch { setBusy(null); }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white shadow-2xl p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{t('plans.title')}</h2>
            <p className="text-sm text-gray-500 mt-0.5">{c.subtitle}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100">
            <i className="bi bi-x text-2xl"></i>
          </button>
        </div>

        {/* Monthly / Annual toggle */}
        <div className="flex justify-center mb-5">
          <div className="inline-flex items-center gap-1 p-1 rounded-full bg-gray-100 border border-gray-200">
            <button onClick={() => setAnnual(false)} className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors ${!annual ? 'bg-white text-violet-700 shadow-sm' : 'text-gray-500'}`}>{c.monthly}</button>
            <button onClick={() => setAnnual(true)} className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-colors inline-flex items-center gap-1.5 ${annual ? 'bg-white text-violet-700 shadow-sm' : 'text-gray-500'}`}>
              {c.annual} <span className="text-[9px] font-bold text-emerald-600 bg-emerald-100 rounded-full px-1.5">{c.twoMonthsFree}</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {tiers.map(tier => {
            const tc = c.tiers[tier.id];
            const isCurrent = tier.id === currentPlan;
            return (
              <div
                key={tier.id}
                className={`flex flex-col rounded-xl border p-4 transition-shadow ${
                  isCurrent ? 'border-violet-400 ring-2 ring-violet-200 shadow-md' : tier.highlight ? 'border-violet-300 shadow-sm' : 'border-gray-200 hover:shadow-sm'
                }`}
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-gray-900">{tier.name}</h3>
                  {isCurrent
                    ? <span className="text-[9px] font-bold uppercase tracking-wide text-violet-600 bg-violet-50 px-2 py-0.5 rounded-full">{c.current}</span>
                    : tier.highlight && <span className="text-[9px] font-bold uppercase tracking-wide text-white px-2 py-0.5 rounded-full" style={{ background: 'linear-gradient(135deg,#8b5cf6,#6d28d9)' }}>{c.mostPopular}</span>}
                </div>
                <p className="text-[11px] text-gray-500 mt-0.5 min-h-[28px]">{tc.tagline}</p>
                <div className="mt-2 mb-1">
                  <span className="text-2xl font-extrabold text-gray-900">{tierPrice(tier, annual, c)}</span>
                  {tier.monthly !== null && tier.monthly > 0 && <span className="text-[11px] text-gray-400"> {c.perMonth}</span>}
                </div>
                <p className="text-[10px] text-gray-400 mb-3 h-3">
                  {tier.monthly !== null && tier.monthly > 0 && annual ? c.billed(tier.yearly as number) : ' '}
                </p>
                <ul className="flex flex-col gap-1.5 flex-1">
                  {tc.features.map((f, i) => {
                    const heading = i === 0 && tier.id === 'enterprise';
                    return (
                      <li key={i} className={`flex items-start gap-1.5 text-[11px] ${heading ? 'text-gray-400 italic' : 'text-gray-600'}`}>
                        {!heading && <i className="bi bi-check-lg text-violet-500 mt-0.5 flex-shrink-0"></i>}
                        <span>{f}</span>
                      </li>
                    );
                  })}
                </ul>
                <button
                  disabled={isCurrent || busy === tier.id}
                  onClick={() => onCta(tier)}
                  className={`mt-4 w-full text-xs font-medium px-3 py-2 rounded-lg transition-colors disabled:cursor-default ${
                    isCurrent ? 'bg-gray-100 text-gray-400' : 'text-white hover:opacity-90'
                  }`}
                  style={isCurrent ? undefined : { background: 'linear-gradient(135deg,#8b5cf6,#6d28d9)' }}
                >
                  {isCurrent ? c.currentPlan : busy === tier.id ? '…' : tc.cta}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default PlansView;
