import React from 'react';
import { LineChart, Settings2, DollarSign, Rocket, LifeBuoy, ShieldCheck } from 'lucide-react';

const stats = [
  { value: '5+', label: 'Database engines', desc: 'PostgreSQL, MySQL, SQL Server, Oracle and more' },
  { value: '2',  label: 'Connection modes', desc: 'Cloud databases, or on-prem via a secure agent' },
  { value: '100%', label: 'Answers backed by SQL', desc: 'Verifiable results, grounded in your real data' },
];

const industries = [
  {
    icon: <LineChart className="w-6 h-6" />,
    industry: 'Analysts & data teams',
    headline: 'Clear the query backlog.',
    items: ['Ad-hoc questions answered instantly', 'Explore unfamiliar schemas fast', 'Share the exact SQL behind an answer'],
    iconColor: '#7c3aed', bg: '#faf5ff', border: '#e9d5ff', dot: '#8b5cf6',
  },
  {
    icon: <Settings2 className="w-6 h-6" />,
    industry: 'Product & operations',
    headline: 'Answers without waiting on data.',
    items: ['Self-serve metrics, no SQL needed', 'Spot anomalies and outliers', 'Check the numbers in seconds'],
    iconColor: '#6366f1', bg: '#eef2ff', border: '#c7d2fe', dot: '#818cf8',
  },
  {
    icon: <DollarSign className="w-6 h-6" />,
    industry: 'Finance & revenue',
    headline: 'Figures you can trust.',
    items: ['Month-over-month and cohorts', 'Reconciliations across tables', 'Every figure shows its query'],
    iconColor: '#7c3aed', bg: '#f5f3ff', border: '#ddd6fe', dot: '#8b5cf6',
  },
  {
    icon: <Rocket className="w-6 h-6" />,
    industry: 'Founders & SMBs',
    headline: 'Your database, on tap.',
    items: ['Connect a database in minutes', 'No data warehouse to build', 'Plain-language answers, day one'],
    iconColor: '#8b5cf6', bg: '#f5f3ff', border: '#ddd6fe', dot: '#a78bfa',
  },
  {
    icon: <LifeBuoy className="w-6 h-6" />,
    industry: 'Support & success',
    headline: 'Look things up, fast.',
    items: ['Check account, order or record status', 'Read-only, safe by default', 'No dashboards to build first'],
    iconColor: '#4338ca', bg: '#eef2ff', border: '#c7d2fe', dot: '#6366f1',
  },
  {
    icon: <ShieldCheck className="w-6 h-6" />,
    industry: 'IT & security',
    headline: 'Access with guardrails.',
    items: ['On-prem without opening ports', 'Full audit trail of every query', 'Writes gated behind confirmation'],
    iconColor: '#6d28d9', bg: '#f5f3ff', border: '#ddd6fe', dot: '#7c3aed',
  },
];

const UseCasesSection: React.FC = () => {
  return (
    <section className="py-16 bg-white relative overflow-hidden">
      {/* Faint grid */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{ backgroundImage: 'linear-gradient(rgba(124,58,237,0.035) 1px,transparent 1px),linear-gradient(90deg,rgba(124,58,237,0.035) 1px,transparent 1px)', backgroundSize: '40px 40px' }}
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold mb-5 text-violet-700" style={{ background: '#ede9fe' }}>
            Who it's for
          </span>
          <h2 className="text-4xl sm:text-5xl font-black text-gray-900 mb-5 leading-tight">
            Everyone gets to<br />
            <span style={{ background: 'linear-gradient(90deg,#8b5cf6,#6d28d9)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
              ask the data.
            </span>
          </h2>
          <p className="text-xl text-gray-500 max-w-2xl mx-auto">
            From analysts clearing a query backlog to teams who never learned SQL, FlexiAnalyse turns your database into something anyone can ask.
          </p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-20">
          {stats.map(s => (
            <div key={s.label} className="text-center rounded-2xl p-8 hover:shadow-lg transition-shadow" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
              <div
                className="text-6xl font-black mb-2"
                style={{ background: 'linear-gradient(135deg,#a78bfa,#6d28d9)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}
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
          <h3 className="text-2xl font-bold text-gray-900 mb-2">Built for how teams actually work</h3>
          <p className="text-gray-500">One database agent, many jobs to be done.</p>
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