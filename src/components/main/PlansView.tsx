import React, { useEffect, useState } from 'react';
import { authFetch, API_BASE } from '../../lib/apiClient';

/**
 * Plans / pricing overlay — driven entirely by the backend catalogue
 * (/api/v2/plans) so tiers and prices stay in one place (config/plans.py).
 * Highlights the org's current plan (/api/v2/plan). No payment yet: upgrade
 * CTAs open a contact email rather than a checkout.
 */

interface PlanCard {
  id: string;
  name: string;
  price: number | null;
  currency: string;
  period: string;
  tagline: string;
  features: string[];
  cta: string;
}

interface PlansViewProps {
  open: boolean;
  onClose: () => void;
  orgId: string | null;
}

const priceLabel = (p: PlanCard): string => {
  if (p.price === null) return 'Sur devis';
  if (p.price === 0) return 'Gratuit';
  return `${p.price} €`;
};

const PlansView: React.FC<PlansViewProps> = ({ open, onClose, orgId }) => {
  const [plans, setPlans] = useState<PlanCard[]>([]);
  const [currentPlan, setCurrentPlan] = useState<string>('free');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    const headers: Record<string, string> = {};
    if (orgId) headers['X-Organization-Id'] = orgId;
    Promise.all([
      authFetch(`${API_BASE}/api/v2/plans`, { headers }).then(r => r.json()).catch(() => ({ data: [] })),
      authFetch(`${API_BASE}/api/v2/plan`, { headers }).then(r => r.json()).catch(() => ({ plan: 'free' })),
    ])
      .then(([cat, cur]) => {
        setPlans(Array.isArray(cat.data) ? cat.data : []);
        setCurrentPlan(cur.plan || 'free');
      })
      .finally(() => setLoading(false));
  }, [open, orgId]);

  if (!open) return null;

  const upgrade = (p: PlanCard) => {
    const subject = encodeURIComponent(`FlexiAnalyse — Passer au plan ${p.name}`);
    window.location.href = `mailto:contact@flexianalyse.com?subject=${subject}`;
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-5xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white shadow-2xl p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Plans & tarifs</h2>
            <p className="text-sm text-gray-500 mt-0.5">Choisissez le palier adapté à votre usage.</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded hover:bg-gray-100">
            <i className="bi bi-x text-2xl"></i>
          </button>
        </div>

        {loading ? (
          <p className="text-sm text-gray-400 py-12 text-center">Chargement…</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {plans.map(p => {
              const isCurrent = p.id === currentPlan;
              return (
                <div
                  key={p.id}
                  className={`flex flex-col rounded-xl border p-4 transition-shadow ${
                    isCurrent ? 'border-purple-400 ring-2 ring-purple-200 shadow-md' : 'border-gray-200 hover:shadow-sm'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-bold text-gray-900">{p.name}</h3>
                    {isCurrent && (
                      <span className="text-[9px] font-bold uppercase tracking-wide text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full">
                        Actuel
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-gray-500 mt-0.5 min-h-[28px]">{p.tagline}</p>
                  <div className="mt-2 mb-3">
                    <span className="text-2xl font-extrabold text-gray-900">{priceLabel(p)}</span>
                    {p.price !== null && p.price !== 0 && (
                      <span className="text-[11px] text-gray-400"> / {p.period}</span>
                    )}
                  </div>
                  <ul className="flex flex-col gap-1.5 flex-1">
                    {p.features.map((f, i) => (
                      <li key={i} className="flex items-start gap-1.5 text-[11px] text-gray-600">
                        <i className="bi bi-check-lg text-green-500 mt-0.5 flex-shrink-0"></i>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  <button
                    disabled={isCurrent}
                    onClick={() => upgrade(p)}
                    className={`mt-4 w-full text-xs font-medium px-3 py-2 rounded-lg transition-colors ${
                      isCurrent
                        ? 'bg-gray-100 text-gray-400 cursor-default'
                        : 'bg-purple-600 text-white hover:bg-purple-700'
                    }`}
                  >
                    {isCurrent ? 'Plan actuel' : p.cta}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        <p className="text-[10px] text-gray-400 text-center mt-5">
          Le paiement en ligne arrive bientôt — pour changer de plan, contactez-nous.
        </p>
      </div>
    </div>
  );
};

export default PlansView;
