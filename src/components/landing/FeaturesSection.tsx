import React, { useState } from 'react';
import { Users, DollarSign, Scale, Settings, BarChart3, Shield, CheckCircle2, ArrowRight } from 'lucide-react';

const roles = [
  {
    role: 'CEO & Executives',
    agent: 'Executive Agent',
    icon: <BarChart3 className="w-6 h-6" />,
    metric: '10x', metricLabel: 'faster decisions',
    grad: 'linear-gradient(135deg,#f59e0b,#f97316)',
    bg: '#fffbeb', border: '#fef3c7',
    description: 'Real-time visibility into every operation. Ask in plain English — get board-ready summaries, exception reports and strategic insights instantly.',
    capabilities: ['Cross-department dashboards', 'Exception & risk alerts', 'Natural language Q&A across all data'],
  },
  {
    role: 'Finance & CFO',
    agent: 'Finance Agent',
    icon: <DollarSign className="w-6 h-6" />,
    metric: '80%', metricLabel: 'AP automation',
    grad: 'linear-gradient(135deg,#10b981,#059669)',
    bg: '#f0fdf4', border: '#bbf7d0',
    description: 'Automate invoice processing, detect anomalies, forecast cash flow and instantly reconcile accounts across all your financial systems.',
    capabilities: ['Invoice extraction & matching', 'Anomaly & fraud detection', 'Real-time cash flow forecasting'],
  },
  {
    role: 'Legal & Compliance',
    agent: 'Legal Agent',
    icon: <Scale className="w-6 h-6" />,
    metric: '3x', metricLabel: 'faster contract review',
    grad: 'linear-gradient(135deg,#8b5cf6,#7c3aed)',
    bg: '#faf5ff', border: '#e9d5ff',
    description: 'AI-powered contract analysis, obligation tracking and risk flagging across your entire legal portfolio — in seconds, not days.',
    capabilities: ['Contract risk scoring', 'Obligation & renewal alerts', 'Clause extraction & redlining'],
  },
  {
    role: 'HR & People Ops',
    agent: 'HR Agent',
    icon: <Users className="w-6 h-6" />,
    metric: '70%', metricLabel: 'onboarding time saved',
    grad: 'linear-gradient(135deg,#3b82f6,#0ea5e9)',
    bg: '#eff6ff', border: '#bfdbfe',
    description: 'Automate the full employee lifecycle — from onboarding paperwork to compliance tracking, leave management and offboarding workflows.',
    capabilities: ['Automated onboarding flows', 'Policy compliance tracking', 'Employee document management'],
  },
  {
    role: 'Operations',
    agent: 'Ops Agent',
    icon: <Settings className="w-6 h-6" />,
    metric: '5x', metricLabel: 'workflow velocity',
    grad: 'linear-gradient(135deg,#f97316,#ef4444)',
    bg: '#fff7ed', border: '#fed7aa',
    description: 'Identify bottlenecks, orchestrate cross-functional workflows, track KPIs in real time and surface operational insights before they become problems.',
    capabilities: ['Bottleneck detection', 'Cross-system automation', 'SLA & KPI monitoring'],
  },
  {
    role: 'IT & Security',
    agent: 'IT Agent',
    icon: <Shield className="w-6 h-6" />,
    metric: '60%', metricLabel: 'ticket resolution time',
    grad: 'linear-gradient(135deg,#475569,#1e40af)',
    bg: '#f8fafc', border: '#e2e8f0',
    description: 'Automate IT service requests, monitor system health, enforce security policies and get instant answers on access, compliance and audit trails.',
    capabilities: ['Auto-triage service tickets', 'Access & compliance auditing', 'Security policy enforcement'],
  },
];

const FeaturesSection: React.FC = () => {
  const [activeIdx, setActiveIdx] = useState<number | null>(null);

  return (
    <section className="py-24 relative overflow-hidden" style={{ background: '#f8fafc' }}>
      <div className="absolute top-0 inset-x-0 h-px" style={{ background: 'linear-gradient(90deg,transparent,#bfdbfe,transparent)' }} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold mb-5 text-purple-700" style={{ background: '#f3e8ff' }}>
            Role-Based Intelligence
          </span>
          <h2 className="text-4xl sm:text-5xl font-black text-gray-900 mb-5 leading-tight">
            A Dedicated AI Agent<br />
            <span style={{ background: 'linear-gradient(90deg,#3b82f6,#8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
              for Every Role
            </span>
          </h2>
          <p className="text-xl text-gray-500 max-w-2xl mx-auto">
            Not a generic chatbot. FlexiAnalyse deploys specialised AI agents trained for each function — so every employee works like an expert.
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
          Need a custom agent?{' '}
          <span className="text-purple-600 font-semibold cursor-pointer hover:underline">
            Build your own with our Agent Builder →
          </span>
        </p>
      </div>
    </section>
  );
};

export default FeaturesSection;