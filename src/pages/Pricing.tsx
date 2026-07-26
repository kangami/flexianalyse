import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, ServerCog } from 'lucide-react';
import Navbar from '../components/landing/Navbar';
import { useLanguage } from '../contexts/LanguageContext';

/** Public pricing page. Prices mirror backend config/plans.py (the runtime source
 * of truth for gating). Annual billing = 2 months off. Copy is translated inline
 * (en/fr/es) and picked from the current app language. */

interface Tier { id: string; name: string; monthly: number | null; yearly: number | null; highlight?: boolean }

const tiers: Tier[] = [
  { id: 'free', name: 'Free', monthly: 0, yearly: 0 },
  { id: 'pro', name: 'Pro', monthly: 29, yearly: 290 },
  { id: 'business', name: 'Business', monthly: 99, yearly: 990, highlight: true },
  { id: 'enterprise', name: 'Enterprise', monthly: null, yearly: null },
];

type TierCopy = { tagline: string; cta: string; features: string[] };
interface Copy {
  title1: string; title2: string; subtitle: string;
  monthly: string; annual: string; twoMonthsFree: string;
  perMonth: string; custom: string; mostPopular: string;
  billed: (y: number) => string;
  onprem: string; fairuse: string; home: string; getStarted: string;
  tiers: Record<string, TierCopy>;
}

const COPY: Record<string, Copy> = {
  en: {
    title1: 'Simple pricing.', title2: 'On-prem on every plan.',
    subtitle: 'Pay for scale, not for access. Every tier can reach a private database through a secure agent.',
    monthly: 'Monthly', annual: 'Annual', twoMonthsFree: '2 months free',
    perMonth: '/ month', custom: 'Custom', mostPopular: 'MOST POPULAR',
    billed: (y) => `billed $${y} / year`,
    onprem: 'Your database can stay on-prem on any plan: a lightweight agent dials out, no inbound ports, credentials never leave your network.',
    fairuse: "Question limits are fair-use monthly caps; most teams stay well under. Beyond the cap you can add questions or move up a tier. Report generation and schema syncs don't count.",
    home: 'Home', getStarted: 'Get Started',
    tiers: {
      free: { tagline: 'Try the database assistant', cta: 'Get started', features: ['1 database (cloud or on-prem)', 'Up to 15 tables', '50 AI questions / month', 'Database Report + Schema explorer', '1 seat'] },
      pro: { tagline: 'For regular individual use', cta: 'Start Pro', features: ['1 database (cloud or on-prem)', 'Up to 150 tables', '500 AI questions / month', 'Advanced model (GPT-4o)', '3 seats included (+$12/seat)', 'History + follow-up questions'] },
      business: { tagline: 'For teams', cta: 'Start Business', features: ['5 databases', 'Up to 500 tables each', '2,500 AI questions / month', 'Writes with confirmation', 'Full audit trail', '10 seats included (+$15/seat)'] },
      enterprise: { tagline: 'For large organisations', cta: 'Contact us', features: ['Everything in Business, plus:', 'Unlimited databases & tables', 'Multiple on-prem agents', 'SSO / SAML · SLA', 'Dedicated support'] },
    },
  },
  fr: {
    title1: 'Tarifs simples.', title2: 'On-prem sur tous les plans.',
    subtitle: "Payez pour l'échelle, pas pour l'accès. Chaque palier peut atteindre une base privée via un agent sécurisé.",
    monthly: 'Mensuel', annual: 'Annuel', twoMonthsFree: '2 mois offerts',
    perMonth: '/ mois', custom: 'Sur devis', mostPopular: 'LE PLUS POPULAIRE',
    billed: (y) => `facturé ${y} $ / an`,
    onprem: "Votre base peut rester on-prem sur n'importe quel plan : un agent léger se connecte en sortie, aucun port entrant, les identifiants ne quittent jamais votre réseau.",
    fairuse: "Les limites de questions sont des plafonds mensuels « fair-use » ; la plupart des équipes restent bien en dessous. Au-delà, vous pouvez ajouter des questions ou monter de palier. La génération du rapport et les synchronisations de schéma ne comptent pas.",
    home: 'Accueil', getStarted: 'Commencer',
    tiers: {
      free: { tagline: "Essayer l'agent base de données", cta: 'Commencer', features: ['1 base de données (cloud ou on-prem)', "Jusqu'à 15 tables", '50 questions IA / mois', 'Database Report + Schema explorer', '1 siège'] },
      pro: { tagline: 'Pour un usage individuel régulier', cta: 'Choisir Pro', features: ['1 base de données (cloud ou on-prem)', "Jusqu'à 150 tables", '500 questions IA / mois', 'Modèle avancé (GPT-4o)', '3 sièges inclus (+12 $/siège)', 'Historique + questions de suivi'] },
      business: { tagline: 'Pour les équipes', cta: 'Choisir Business', features: ['5 bases de données', "Jusqu'à 500 tables par base", '2 500 questions IA / mois', 'Écritures avec confirmation', "Journaux d'audit complets", '10 sièges inclus (+15 $/siège)'] },
      enterprise: { tagline: 'Pour les grands comptes', cta: 'Nous contacter', features: ['Tout Business, plus :', 'Bases & tables illimitées', 'Agents on-prem multiples', 'SSO / SAML · SLA', 'Support dédié'] },
    },
  },
  es: {
    title1: 'Precios simples.', title2: 'On-prem en todos los planes.',
    subtitle: 'Paga por la escala, no por el acceso. Cada plan puede acceder a una base privada mediante un agente seguro.',
    monthly: 'Mensual', annual: 'Anual', twoMonthsFree: '2 meses gratis',
    perMonth: '/ mes', custom: 'A medida', mostPopular: 'MÁS POPULAR',
    billed: (y) => `facturado $${y} / año`,
    onprem: 'Tu base de datos puede permanecer on-prem en cualquier plan: un agente ligero se conecta hacia afuera, sin puertos entrantes, y las credenciales nunca salen de tu red.',
    fairuse: 'Los límites de preguntas son topes mensuales «fair-use»; la mayoría de los equipos se mantienen muy por debajo. Más allá del tope puedes añadir preguntas o subir de plan. La generación del informe y las sincronizaciones de esquema no cuentan.',
    home: 'Inicio', getStarted: 'Empezar',
    tiers: {
      free: { tagline: 'Prueba el asistente de base de datos', cta: 'Empezar', features: ['1 base de datos (nube u on-prem)', 'Hasta 15 tablas', '50 preguntas IA / mes', 'Database Report + Explorador de esquema', '1 asiento'] },
      pro: { tagline: 'Para uso individual regular', cta: 'Elegir Pro', features: ['1 base de datos (nube u on-prem)', 'Hasta 150 tablas', '500 preguntas IA / mes', 'Modelo avanzado (GPT-4o)', '3 asientos incluidos (+$12/asiento)', 'Historial + preguntas de seguimiento'] },
      business: { tagline: 'Para equipos', cta: 'Elegir Business', features: ['5 bases de datos', 'Hasta 500 tablas cada una', '2 500 preguntas IA / mes', 'Escrituras con confirmación', 'Registro de auditoría completo', '10 asientos incluidos (+$15/asiento)'] },
      enterprise: { tagline: 'Para grandes empresas', cta: 'Contáctanos', features: ['Todo lo de Business, más:', 'Bases y tablas ilimitadas', 'Múltiples agentes on-prem', 'SSO / SAML · SLA', 'Soporte dedicado'] },
    },
  },
};

const Pricing: React.FC = () => {
  const { language } = useLanguage();
  const c = COPY[language] || COPY.en;
  const [annual, setAnnual] = useState(false);

  const priceLabel = (t: Tier) => {
    if (t.monthly === null) return c.custom;
    if (t.monthly === 0) return '$0';
    return annual ? `$${Math.round((t.yearly as number) / 12)}` : `$${t.monthly}`;
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

                <Link
                  to="/get-started"
                  className={`text-center px-4 py-2.5 rounded-lg text-sm font-semibold mb-5 transition-all ${t.highlight ? 'text-white hover:scale-[1.02]' : 'text-violet-700 border border-violet-200 hover:bg-violet-50'}`}
                  style={t.highlight ? { background: 'linear-gradient(135deg,#8b5cf6,#6d28d9)' } : undefined}
                >
                  {tc.cta}
                </Link>

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
