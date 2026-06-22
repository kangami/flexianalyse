import React from 'react';
import { Building2, Heart, ShoppingCart, Factory, Scale, Zap } from 'lucide-react';

const stats = [
  { value: '50+', label: 'Native Connectors', desc: 'Google Drive, SharePoint, Slack, SQL and more' },
  { value: '10x',  label: 'Productivity Boost', desc: 'Per role, across every department' },
  { value: '90%', label: 'Manual Work Eliminated', desc: 'Through AI automation and orchestration' },
];

const industries = [
  {
    icon: <Building2 className="w-6 h-6" />,
    industry: 'Financial Services',
    headline: 'Reconcile faster. Detect fraud earlier.',
    items: ['AP/AR automation', 'Real-time anomaly detection', 'Audit-ready reporting'],
    iconColor: '#059669', bg: '#f0fdf4', border: '#bbf7d0', dot: '#10b981',
  },
  {
    icon: <Heart className="w-6 h-6" />,
    industry: 'Healthcare',
    headline: 'Compliance without complexity.',
    items: ['Patient data intelligence', 'HIPAA-compliant workflows', 'Automated compliance tracking'],
    iconColor: '#dc2626', bg: '#fff1f2', border: '#fecdd3', dot: '#f43f5e',
  },
  {
    icon: <ShoppingCart className="w-6 h-6" />,
    industry: 'Retail & E-Commerce',
    headline: 'Unify supply chain intelligence.',
    items: ['Demand forecasting', 'Supplier performance tracking', 'Inventory optimisation'],
    iconColor: '#7c3aed', bg: '#faf5ff', border: '#e9d5ff', dot: '#8b5cf6',
  },
  {
    icon: <Factory className="w-6 h-6" />,
    industry: 'Manufacturing',
    headline: 'Predict downtime before it happens.',
    items: ['Asset health monitoring', 'Production line optimisation', 'Vendor SLA tracking'],
    iconColor: '#c2410c', bg: '#fff7ed', border: '#fed7aa', dot: '#f97316',
  },
  {
    icon: <Scale className="w-6 h-6" />,
    industry: 'Legal & Professional Services',
    headline: 'Every contract. Every obligation. Zero misses.',
    items: ['Contract lifecycle management', 'Risk & obligation tracking', 'Matter intelligence'],
    iconColor: '#4338ca', bg: '#eef2ff', border: '#c7d2fe', dot: '#6366f1',
  },
  {
    icon: <Zap className="w-6 h-6" />,
    industry: 'Energy & Utilities',
    headline: 'Monitor assets in real time.',
    items: ['Asset & maintenance intelligence', 'Regulatory compliance', 'Field operations automation'],
    iconColor: '#b45309', bg: '#fffbeb', border: '#fef3c7', dot: '#f59e0b',
  },
];

const UseCasesSection: React.FC = () => {
  return (
    <section className="py-24 bg-white relative overflow-hidden">
      {/* Faint grid */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ backgroundImage: 'linear-gradient(rgba(30,64,175,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(30,64,175,0.03) 1px,transparent 1px)', backgroundSize: '40px 40px' }}
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold mb-5 text-blue-700" style={{ background: '#dbeafe' }}>
            The Single Point of Truth
          </span>
          <h2 className="text-4xl sm:text-5xl font-black text-gray-900 mb-5 leading-tight">
            One Platform.<br />
            <span style={{ background: 'linear-gradient(90deg,#3b82f6,#8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
              Every Operation.
            </span>
          </h2>
          <p className="text-xl text-gray-500 max-w-2xl mx-auto">
            FlexiAnalyse connects all your enterprise data sources into a single intelligent layer — so every question gets an instant, accurate answer.
          </p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-20">
          {stats.map(s => (
            <div key={s.label} className="text-center rounded-2xl p-8 hover:shadow-lg transition-shadow" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
              <div
                className="text-6xl font-black mb-2"
                style={{ background: 'linear-gradient(135deg,#3b82f6,#8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}
              >
                {s.value}
              </div>
              <div className="text-lg font-bold text-gray-900 mb-1">{s.label}</div>
              <div className="text-sm text-gray-500">{s.desc}</div>
            </div>
          ))}
        </div>

        {/* Industry grid */}
        <div className="text-center mb-10">
          <h3 className="text-2xl font-bold text-gray-900 mb-2">Built for Every Industry</h3>
          <p className="text-gray-500">FlexiAnalyse adapts to your sector's needs — out of the box.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {industries.map(ind => (
            <div
              key={ind.industry}
              className="group rounded-2xl p-6 cursor-default transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5"
              style={{ background: ind.bg, border: `1px solid ${ind.border}` }}
            >
              <div
                className="w-11 h-11 rounded-xl flex items-center justify-center mb-4 transition-transform group-hover:scale-110"
                style={{ background: ind.bg, border: `1px solid ${ind.border}`, color: ind.iconColor }}
              >
                {ind.icon}
              </div>
              <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-1">{ind.industry}</p>
              <h4 className="text-base font-bold text-gray-900 mb-3">{ind.headline}</h4>
              <ul className="space-y-1.5">
                {ind.items.map(item => (
                  <li key={item} className="flex items-center gap-2 text-sm text-gray-600">
                    <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: ind.dot }} />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default UseCasesSection;