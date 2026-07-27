/** Shared pricing source of truth for the public /pricing page AND the in-app
 * Plans overlay, so tiers, prices, currency and copy never diverge. Prices mirror
 * backend config/plans.py (which stays the runtime source of truth for gating). */

export interface Tier {
  id: string;
  name: string;
  monthly: number | null;   // null = custom / contact
  yearly: number | null;
  highlight?: boolean;
}

export const TIERS: Tier[] = [
  { id: 'free', name: 'Free', monthly: 0, yearly: 0 },
  { id: 'pro', name: 'Pro', monthly: 29, yearly: 290 },
  { id: 'business', name: 'Business', monthly: 99, yearly: 990, highlight: true },
  { id: 'enterprise', name: 'Enterprise', monthly: null, yearly: null },
];

/** Purchasable online (Stripe checkout). Free = sign up, Enterprise = contact. */
export const BILLABLE = new Set(['pro', 'business']);

export type TierCopy = { tagline: string; cta: string; features: string[] };

export interface PricingCopy {
  title1: string; title2: string; subtitle: string;
  monthly: string; annual: string; twoMonthsFree: string;
  perMonth: string; custom: string; mostPopular: string; current: string; currentPlan: string;
  billed: (y: number) => string;
  onprem: string; fairuse: string; home: string; getStarted: string;
  tiers: Record<string, TierCopy>;
}

export const PRICING_COPY: Record<string, PricingCopy> = {
  en: {
    title1: 'Simple pricing.', title2: 'On-prem on every plan.',
    subtitle: 'Pay for scale, not for access. Every tier can reach a private database through a secure agent.',
    monthly: 'Monthly', annual: 'Annual', twoMonthsFree: '2 months free',
    perMonth: '/ month', custom: 'Custom', mostPopular: 'MOST POPULAR', current: 'Current', currentPlan: 'Current plan',
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
    perMonth: '/ mois', custom: 'Sur devis', mostPopular: 'LE PLUS POPULAIRE', current: 'Actuel', currentPlan: 'Plan actuel',
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
    perMonth: '/ mes', custom: 'A medida', mostPopular: 'MÁS POPULAR', current: 'Actual', currentPlan: 'Plan actual',
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

export const pricingCopy = (language: string): PricingCopy => PRICING_COPY[language] || PRICING_COPY.en;

/** Displayed price for a tier given the billing interval. */
export const tierPrice = (t: Tier, annual: boolean, c: PricingCopy): string => {
  if (t.monthly === null) return c.custom;
  if (t.monthly === 0) return '$0';
  return annual ? `$${Math.round((t.yearly as number) / 12)}` : `$${t.monthly}`;
};
