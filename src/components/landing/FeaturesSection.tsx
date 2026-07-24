import React, { useState } from 'react';
import { MessagesSquare, Terminal, Network, ShieldCheck, ServerCog, Gauge, CheckCircle2, ArrowRight } from 'lucide-react';

const roles = [
  {
    role: 'Natural-language to SQL',
    agent: 'Ask, don\'t query',
    icon: <MessagesSquare className="w-6 h-6" />,
    metric: 'EN / FR', metricLabel: 'plain language',
    grad: 'linear-gradient(135deg,#a78bfa,#8b5cf6)',
    bg: '#f5f3ff', border: '#ddd6fe',
    description: 'Ask a question in plain English or French. FlexiAnalyse reads your schema, maps your words to your tables, and writes the SQL for you, joins and all.',
    capabilities: ['Schema-aware query generation', 'Maps your vocabulary to the data', 'Handles multi-table joins & analytics'],
  },
  {
    role: 'Grounded, verifiable answers',
    agent: 'No black box',
    icon: <Terminal className="w-6 h-6" />,
    metric: '100%', metricLabel: 'answers show their SQL',
    grad: 'linear-gradient(135deg,#818cf8,#6366f1)',
    bg: '#eef2ff', border: '#c7d2fe',
    description: 'Every answer ships with the exact query that produced it, run against your real data. Figures you can check, never invented.',
    capabilities: ['Exact SQL shown with every result', 'Answers grounded in live data', 'Interprets your question back to you'],
  },
  {
    role: 'Interactive schema explorer',
    agent: 'See your whole database',
    icon: <Network className="w-6 h-6" />,
    metric: '500+', metricLabel: 'tables, fluid',
    grad: 'linear-gradient(135deg,#8b5cf6,#7c3aed)',
    bg: '#faf5ff', border: '#e9d5ff',
    description: 'A live ER diagram of your database. Search and focus a table, click to see its columns, row counts and relationships, even on hundreds of tables.',
    capabilities: ['Searchable, focusable ER diagram', 'Click a table for columns & row stats', 'Reads one-to-many and many-to-many relations at a glance'],
  },
  {
    role: 'Safe writes with confirmation',
    agent: 'Read-only by default',
    icon: <ShieldCheck className="w-6 h-6" />,
    metric: '2-step', metricLabel: 'confirm before commit',
    grad: 'linear-gradient(135deg,#7c3aed,#5b21b6)',
    bg: '#f5f3ff', border: '#ddd6fe',
    description: 'The agent only reads unless you allow more. Any UPDATE / INSERT / DELETE is previewed first and commits only after your explicit approval.',
    capabilities: ['Read-only unless explicitly enabled', 'Preview the impact before it runs', 'Explicit approval on every write'],
  },
  {
    role: 'On-prem & private databases',
    agent: 'Your data stays home',
    icon: <ServerCog className="w-6 h-6" />,
    metric: '0', metricLabel: 'inbound ports',
    grad: 'linear-gradient(135deg,#8b5cf6,#6366f1)',
    bg: '#f5f3ff', border: '#ddd6fe',
    description: 'A lightweight agent runs inside your network and dials out to FlexiAnalyse: no open ports, no VPN. Credentials never leave your side; only results transit.',
    capabilities: ['Outbound-only dial-home agent', 'Credentials stay in your network', 'One Docker command to run it'],
  },
  {
    role: 'Built to scale',
    agent: 'Large databases',
    icon: <Gauge className="w-6 h-6" />,
    metric: 'sec', metricLabel: 'on big schemas',
    grad: 'linear-gradient(135deg,#4b5563,#1f2937)',
    bg: '#f8fafc', border: '#e2e8f0',
    description: 'A persistent schema catalog and per-query table retrieval keep answers fast and accurate on databases with hundreds of tables and millions of rows.',
    capabilities: ['Schema catalog + smart table retrieval', 'Relevant tables picked per question', 'Tiered by plan, from small DBs to enterprise'],
  },
];

const FeaturesSection: React.FC = () => {
  const [activeIdx, setActiveIdx] = useState<number | null>(null);

  return (
    <section className="py-16 relative overflow-hidden" style={{ background: '#f8fafc' }}>
      <div className="absolute top-0 inset-x-0 h-px" style={{ background: 'linear-gradient(90deg,transparent,#ddd6fe,transparent)' }} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold mb-5 text-purple-700" style={{ background: '#f3e8ff' }}>
            What it does
          </span>
          <h2 className="text-4xl sm:text-5xl font-black text-gray-900 mb-5 leading-tight">
            Everything you need to<br />
            <span style={{ background: 'linear-gradient(90deg,#8b5cf6,#6d28d9)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
              trust your data
            </span>
          </h2>
          <p className="text-xl text-gray-500 max-w-2xl mx-auto">
            Not a generic chatbot. A database agent that writes real SQL, shows its work, and keeps your data safe, wherever it lives.
          </p>
        </div>

        {/* Cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {roles.map((r, idx) => (
            <div
              key={r.role}
              className="relative rounded-2xl p-6 cursor-pointer transition-all duration-300 hover:shadow-xl hover:-translate-y-1"
              style={{
                background: r.bg,
                border: `1px solid ${r.border}`,
                boxShadow: activeIdx === idx ? '0 20px 40px rgba(0,0,0,0.1)' : '0 1px 3px rgba(0,0,0,0.05)',
                transform: activeIdx === idx ? 'translateY(-4px)' : undefined,
              }}
              onClick={() => setActiveIdx(activeIdx === idx ? null : idx)}
            >
              {/* Metric badge */}
              <div
                className="absolute -top-3 right-5 text-white text-xs font-black px-3 py-1 rounded-full shadow-md"
                style={{ background: r.grad }}
              >
                {r.metric} {r.metricLabel}
              </div>

              {/* Role header */}
              <div className="flex items-center gap-3 mb-4">
                <div className="w-11 h-11 rounded-xl text-white flex items-center justify-center shadow-md flex-shrink-0" style={{ background: r.grad }}>
                  {r.icon}
                </div>
                <div>
                  <p className="text-[11px] text-gray-400 font-semibold uppercase tracking-wide">{r.agent}</p>
                  <p className="text-sm font-bold text-gray-900">{r.role}</p>
                </div>
              </div>

              {/* Description */}
              <p className="text-sm text-gray-600 leading-relaxed mb-3">{r.description}</p>

              {/* Expandable capabilities */}
              <div
                className="overflow-hidden transition-all duration-300 space-y-1.5"
                style={{ maxHeight: activeIdx === idx ? '120px' : '0', opacity: activeIdx === idx ? 1 : 0 }}
              >
                {r.capabilities.map(cap => (
                  <div key={cap} className="flex items-center gap-2 text-xs text-gray-700">
                    <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                    {cap}
                  </div>
                ))}
              </div>

              {/* Toggle */}
              <div className="flex items-center gap-1 mt-3">
                <span className="text-xs font-semibold" style={{ background: r.grad, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
                  {activeIdx === idx ? 'Hide details' : 'See capabilities'}
                </span>
                <ArrowRight className="w-3.5 h-3.5 text-purple-500 transition-transform" style={{ transform: activeIdx === idx ? 'rotate(90deg)' : 'none' }} />
              </div>
            </div>
          ))}
        </div>

        {/* Bottom note */}
        <p className="text-center text-sm text-gray-400 mt-12">
          Works with PostgreSQL, MySQL, SQL Server, Oracle and more.{' '}
          <span className="text-purple-600 font-semibold cursor-pointer hover:underline">
            See how it connects →
          </span>
        </p>
      </div>
    </section>
  );
};

export default FeaturesSection;