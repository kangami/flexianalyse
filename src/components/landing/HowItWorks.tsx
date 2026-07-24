import React from 'react';
import {
  Database, MessageSquareText, Terminal, History,
  Cloud, ServerCog, ShieldCheck, Lock, FileCheck2, Users, Eye, GitBranch,
  ArrowRight, Code2, Briefcase,
} from 'lucide-react';

/**
 * "How it works" — the current + future narrative of FlexiAnalyse as a database
 * intelligence agent: how you connect (cloud or on-prem), and the security &
 * traceability guarantees. Anchored at #how-it-works for the navbar link.
 */

const steps = [
  {
    icon: <Database className="w-6 h-6" />,
    title: 'Connect',
    body: 'Point FlexiAnalyse at your database, managed in the cloud or running on-premise. Setup takes minutes.',
    grad: 'linear-gradient(135deg,#a78bfa,#8b5cf6)',
  },
  {
    icon: <MessageSquareText className="w-6 h-6" />,
    title: 'Ask',
    body: 'Ask in plain language, or write SQL directly. The agent maps your words to your schema: “customers” finds your renters, “last quarter” finds the right dates.',
    grad: 'linear-gradient(135deg,#8b5cf6,#7c3aed)',
  },
  {
    icon: <Terminal className="w-6 h-6" />,
    title: 'Trust',
    body: 'Get the answer and the exact SQL that produced it. Verifiable, grounded in your real data, never a black box.',
    grad: 'linear-gradient(135deg,#7c3aed,#6d28d9)',
  },
  {
    icon: <History className="w-6 h-6" />,
    title: 'Audit',
    body: 'Every question, generated query and result is recorded: a full trail of who asked what, and when.',
    grad: 'linear-gradient(135deg,#6d28d9,#4c1d95)',
  },
];

const audiences = [
  {
    icon: <Code2 className="w-6 h-6" />,
    tag: 'For technical teams',
    title: 'Developers, DBAs & data teams',
    body: 'Skip the boilerplate. Explore an unfamiliar schema, generate and verify SQL, profile tables, and reach on-prem databases without opening a port.',
    items: ['Write SQL directly or let the agent draft it', 'Interactive schema explorer & table stats', 'On-prem access, read-only guardrails, audit trail'],
  },
  {
    icon: <Briefcase className="w-6 h-6" />,
    tag: 'For business teams',
    title: 'CFOs, CS managers & operators',
    body: 'Get the numbers without waiting on anyone. Ask in plain language and receive a clear answer you can trust, with the query behind it if you ever want to check.',
    items: ['Ask in plain English or French, no SQL', 'Trusted figures, grounded in real data', 'Self-serve, no dashboards to build first'],
  },
];

const guarantees = [
  { icon: <Eye className="w-5 h-5" />, title: 'Read-only by default', body: 'The agent only reads your data. Nothing is modified unless you explicitly enable it.' },
  { icon: <FileCheck2 className="w-5 h-5" />, title: 'Writes require confirmation', body: 'Every UPDATE / INSERT / DELETE is previewed and needs your explicit approval before it commits.' },
  { icon: <Terminal className="w-5 h-5" />, title: 'Grounded, verifiable answers', body: 'Each answer ships with the exact SQL that produced it, so you can always check the work.' },
  { icon: <History className="w-5 h-5" />, title: 'Full audit trail', body: 'Who asked what, which query ran, and when, logged for every action across your organisation.' },
  { icon: <Lock className="w-5 h-5" />, title: 'Encrypted everywhere', body: 'SSL/TLS connections, credentials encrypted at rest, or kept entirely inside your network on-prem.' },
  { icon: <Users className="w-5 h-5" />, title: 'Scoped, isolated access', body: 'Plan- and role-scoped, with strict multi-tenant isolation between organisations.' },
];

const HowItWorks: React.FC = () => {
  return (
    <section id="how-it-works" className="py-20 relative overflow-hidden bg-white scroll-mt-20">
      <div className="absolute top-0 inset-x-0 h-px" style={{ background: 'linear-gradient(90deg,transparent,#ddd6fe,transparent)' }} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-16">
          <span className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold mb-5 text-violet-700" style={{ background: '#f5f3ff' }}>
            How it works
          </span>
          <h2 className="text-4xl sm:text-5xl font-black text-gray-900 mb-5 leading-tight">
            From a question to an<br />
            <span style={{ background: 'linear-gradient(90deg,#8b5cf6,#6d28d9)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
              answer you can trust
            </span>
          </h2>
          <p className="text-xl text-gray-500 max-w-2xl mx-auto">
            Connect a database, ask in plain language, and get an answer backed by the exact query that ran, with a full audit trail behind every result.
          </p>
        </div>

        {/* Steps */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-24">
          {steps.map((s, i) => (
            <div key={s.title} className="relative rounded-2xl p-6 bg-white border border-gray-100 shadow-sm hover:shadow-lg transition-shadow">
              <span className="absolute top-5 right-5 text-5xl font-black text-gray-100 select-none">{i + 1}</span>
              <div className="w-12 h-12 rounded-xl text-white flex items-center justify-center shadow-md mb-4" style={{ background: s.grad }}>
                {s.icon}
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">{s.title}</h3>
              <p className="text-sm text-gray-600 leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>

        {/* Two audiences, one assistant */}
        <div className="text-center mb-12">
          <span className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold mb-4 text-violet-700" style={{ background: '#f5f3ff' }}>
            One assistant, two audiences
          </span>
          <h3 className="text-3xl sm:text-4xl font-black text-gray-900 leading-tight">
            Technical enough for engineers.<br className="hidden sm:block" /> Simple enough for everyone else.
          </h3>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-24">
          {audiences.map((a) => (
            <div key={a.tag} className="rounded-2xl p-8 border border-violet-100 bg-white hover:shadow-lg transition-shadow">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl text-white flex items-center justify-center shadow-md" style={{ background: 'linear-gradient(135deg,#8b5cf6,#6d28d9)' }}>
                  {a.icon}
                </div>
                <div>
                  <p className="text-[11px] text-violet-500 font-semibold uppercase tracking-wide">{a.tag}</p>
                  <p className="text-lg font-bold text-gray-900">{a.title}</p>
                </div>
              </div>
              <p className="text-sm text-gray-600 leading-relaxed mb-5">{a.body}</p>
              <ul className="space-y-2">
                {a.items.map((x) => (
                  <li key={x} className="flex items-center gap-2 text-sm text-gray-700">
                    <ShieldCheck className="w-4 h-4 text-violet-500 flex-shrink-0" />{x}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Connection modes */}
        <div className="text-center mb-12">
          <span className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold mb-4 text-violet-700" style={{ background: '#ede9fe' }}>
            Two ways to connect
          </span>
          <h3 className="text-3xl sm:text-4xl font-black text-gray-900 leading-tight">
            Your data, wherever it lives
          </h3>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-24">
          {/* Cloud mode */}
          <div className="rounded-2xl p-8 border border-violet-100" style={{ background: 'linear-gradient(180deg,#faf9ff,#ffffff)' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl text-white flex items-center justify-center shadow-md" style={{ background: 'linear-gradient(135deg,#a78bfa,#8b5cf6)' }}>
                <Cloud className="w-6 h-6" />
              </div>
              <div>
                <p className="text-[11px] text-gray-400 font-semibold uppercase tracking-wide">Connection mode</p>
                <p className="text-lg font-bold text-gray-900">Cloud database</p>
              </div>
            </div>
            <p className="text-sm text-gray-600 leading-relaxed mb-5">
              For managed databases reachable over the network: PostgreSQL, MySQL, SQL Server, Oracle and more. FlexiAnalyse connects directly over an encrypted channel; credentials are encrypted at rest.
            </p>
            <ul className="space-y-2">
              {['Direct SSL / TLS connection', 'Credentials encrypted at rest', 'Test the connection before you save'].map(x => (
                <li key={x} className="flex items-center gap-2 text-sm text-gray-700">
                  <ShieldCheck className="w-4 h-4 text-violet-500 flex-shrink-0" />{x}
                </li>
              ))}
            </ul>
          </div>

          {/* On-prem mode */}
          <div className="rounded-2xl p-8 border border-violet-100" style={{ background: 'linear-gradient(180deg,#f7f5ff,#ffffff)' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl text-white flex items-center justify-center shadow-md" style={{ background: 'linear-gradient(135deg,#7c3aed,#4c1d95)' }}>
                <ServerCog className="w-6 h-6" />
              </div>
              <div>
                <p className="text-[11px] text-gray-400 font-semibold uppercase tracking-wide">Connection mode</p>
                <p className="text-lg font-bold text-gray-900">On-prem / private network</p>
              </div>
            </div>
            <p className="text-sm text-gray-600 leading-relaxed mb-5">
              Your database never leaves your network. A lightweight agent runs inside your infrastructure and dials out to FlexiAnalyse over an encrypted channel, so you never open an inbound port or expose your database to the internet.
            </p>
            <ul className="space-y-2">
              {['No inbound ports, no VPN to configure', 'Credentials stay on your side; only results transit', 'One command to run the agent (Docker)'].map(x => (
                <li key={x} className="flex items-center gap-2 text-sm text-gray-700">
                  <ShieldCheck className="w-4 h-4 text-violet-600 flex-shrink-0" />{x}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Security & traceability */}
        <div className="text-center mb-12">
          <span className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold mb-4 text-violet-700" style={{ background: '#f5f3ff' }}>
            Security &amp; traceability
          </span>
          <h3 className="text-3xl sm:text-4xl font-black text-gray-900 leading-tight mb-4">
            Trust built into every answer
          </h3>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto">
            Powerful access to your data demands guardrails. Every result is verifiable, every action is logged, and nothing changes without your say-so.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-24">
          {guarantees.map(g => (
            <div key={g.title} className="rounded-2xl p-6 bg-gray-50 border border-gray-100 hover:border-violet-200 hover:bg-white transition-colors">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center mb-3 text-violet-600" style={{ background: '#f5f3ff' }}>
                {g.icon}
              </div>
              <h4 className="text-base font-bold text-gray-900 mb-1.5">{g.title}</h4>
              <p className="text-sm text-gray-600 leading-relaxed">{g.body}</p>
            </div>
          ))}
        </div>

        {/* Vision — today / tomorrow */}
        <div className="rounded-3xl overflow-hidden relative" style={{ background: 'linear-gradient(135deg,#000000 0%,#140a2e 50%,#0a0a0f 100%)' }}>
          <div className="absolute -top-20 -left-20 w-96 h-96 rounded-full pointer-events-none" style={{ background: 'radial-gradient(circle,rgba(139,92,246,0.25),transparent 65%)', filter: 'blur(60px)' }} />
          <div className="absolute bottom-0 right-0 w-96 h-96 rounded-full pointer-events-none" style={{ background: 'radial-gradient(circle,rgba(124,58,237,0.2),transparent 65%)', filter: 'blur(60px)' }} />
          <div className="relative p-10 sm:p-14">
            <span className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold mb-6 text-violet-200 border border-violet-400/25" style={{ background: 'rgba(139,92,246,0.12)' }}>
              Where we're going
            </span>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div>
                <div className="flex items-center gap-2 mb-3 text-violet-300">
                  <GitBranch className="w-5 h-5" />
                  <span className="text-sm font-bold uppercase tracking-wide">Today</span>
                </div>
                <p className="text-2xl font-black text-white mb-3 leading-snug">A trusted conversation with your databases</p>
                <p className="text-gray-300 leading-relaxed">
                  Ask questions in plain language and get answers you can verify: grounded in real SQL, safe by default, and fully auditable, whether your data sits in the cloud or behind your firewall.
                </p>
              </div>
              <div>
                <div className="flex items-center gap-2 mb-3 text-violet-400">
                  <ArrowRight className="w-5 h-5" />
                  <span className="text-sm font-bold uppercase tracking-wide">Tomorrow</span>
                </div>
                <p className="text-2xl font-black text-white mb-3 leading-snug">An autonomous database analyst</p>
                <p className="text-gray-300 leading-relaxed">
                  FlexiAnalyse is growing into a proactive analyst: profiling your data, learning your business vocabulary, mapping relationships, spotting anomalies and surfacing the insights you didn't think to ask for.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default HowItWorks;
