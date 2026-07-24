import React from 'react';
import { Terminal, Lock, History } from 'lucide-react';

/**
 * "Why teams choose FlexiAnalyse" — the trust principles behind the product.
 * (Replaced the earlier placeholder testimonials; add real customer quotes here
 * once they're available, rather than fabricated ones.)
 */

const principles = [
  {
    icon: <Terminal className="w-7 h-7" />,
    title: 'Grounded, not guessed',
    body: 'Every answer is produced by real SQL run against your data, and the query is shown right next to the result. If the question can’t be answered from your data, the agent says so instead of inventing a number.',
    grad: 'linear-gradient(135deg,#a78bfa,#8b5cf6)',
    tint: '#f5f3ff',
  },
  {
    icon: <Lock className="w-7 h-7" />,
    title: 'Your data stays yours',
    body: 'On-prem databases never leave your network: a lightweight agent dials out, so no ports are opened and only results transit. Credentials are encrypted at rest, or kept entirely on your side. Read-only by default.',
    grad: 'linear-gradient(135deg,#818cf8,#6366f1)',
    tint: '#eef2ff',
  },
  {
    icon: <History className="w-7 h-7" />,
    title: 'Every action is traceable',
    body: 'Who asked what, which query ran, and when, recorded as a full audit trail across your organisation. And any write is previewed and gated behind your explicit confirmation before it commits.',
    grad: 'linear-gradient(135deg,#8b5cf6,#7c3aed)',
    tint: '#f5f3ff',
  },
];

const TestimonialsSection: React.FC = () => {
  return (
    <section className="py-14 sm:py-18 bg-gradient-to-br from-gray-50 to-white overflow-hidden">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold mb-5 text-violet-700" style={{ background: '#f5f3ff' }}>
            Why teams choose FlexiAnalyse
          </span>
          <h2 className="text-4xl sm:text-5xl font-black text-gray-900 leading-tight mb-4">
            Powerful access,{' '}
            <span style={{ background: 'linear-gradient(90deg,#8b5cf6,#6d28d9)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
              earned trust
            </span>
          </h2>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Letting an AI touch your production database is a big ask. These are the guarantees that make it safe.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 auto-rows-fr">
          {principles.map((p) => (
            <div
              key={p.title}
              className="bg-white p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 border border-gray-100 flex flex-col"
            >
              <div className="w-14 h-14 rounded-2xl text-white flex items-center justify-center shadow-md mb-5" style={{ background: p.grad }}>
                {p.icon}
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">{p.title}</h3>
              <p className="text-gray-600 leading-relaxed">{p.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default TestimonialsSection;
