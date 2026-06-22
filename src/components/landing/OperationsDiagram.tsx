import React, { useState, useEffect, useRef } from 'react';
import {
  FileText, MoreHorizontal,
  Search, Network, ShieldAlert, TrendingUp, Clock, AlertTriangle, BarChart3,
  Users, DollarSign, Scale, Settings, Sparkles, CheckCircle2, ArrowRight,
  Briefcase, Receipt, FileCheck, Building2, Wrench, ChevronRight, X
} from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────
interface ConnectorItem {
  icon: React.ReactNode;
  label: string;
  color: string;
  description: string;
}

interface AgentItem {
  icon: React.ReactNode;
  label: string;
  color: string;
  description: string;
}

interface WorkflowItem {
  icon: React.ReactNode;
  label: string;
  description: string;
}

// ─── Brand SVG Icons ─────────────────────────────────────────────────────────
const GoogleDriveIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 87.3 78" xmlns="http://www.w3.org/2000/svg">
    <path d="M6.6 66.85l3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8H0c0 1.55.4 3.1 1.2 4.5l5.4 9.35z" fill="#0066DA"/>
    <path d="M43.65 25L29.9 1.2c-1.35.8-2.5 1.9-3.3 3.3L1.2 52.5c-.8 1.4-1.2 2.95-1.2 4.5h27.5L43.65 25z" fill="#00AC47"/>
    <path d="M73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5H59.85l6.1 10.6 7.6 13.2z" fill="#EA4335"/>
    <path d="M43.65 25L57.4 1.2C56.05.4 54.5 0 52.9 0H34.4c-1.6 0-3.15.45-4.5 1.2L43.65 25z" fill="#00832D"/>
    <path d="M59.85 57H27.5l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2L59.85 57z" fill="#2684FC"/>
    <path d="M73.4 26.5l-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3L43.65 25l16.2 32h27.5c0-1.55-.4-3.1-1.2-4.5L73.4 26.5z" fill="#FFBA00"/>
  </svg>
);

const DropboxIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 43 40" xmlns="http://www.w3.org/2000/svg">
    <path d="M12.6 0L0 8.1l8.9 7.1 12.6-7.8L12.6 0zM0 22.3l12.6 8.1 8.9-7.4-12.6-7.8L0 22.3zm21.5.7l8.9 7.4 12.6-8.1-8.9-7.1-12.6 7.8zm21.5-14.9L30.4 0l-8.9 7.4 12.6 7.8 8.9-7.1zM12.7 32.4l8.8 7.4 8.9-7.4-8.9-7.1-8.8 7.1z" fill="#0061FF"/>
  </svg>
);

const SharePointIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <circle cx="18" cy="11" r="9" fill="#036C70"/>
    <circle cx="13" cy="20" r="7" fill="#1A9BA1"/>
    <circle cx="20" cy="23" r="5.5" fill="#37C6D0"/>
    <path d="M10 7v18c0 1.1-.9 2-2 2H6V5h2c1.1 0 2 .9 2 2z" fill="#03787C" opacity="0.8"/>
  </svg>
);

const OutlookIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <path d="M28 5H14v22h14c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2z" fill="#1976D2"/>
    <path d="M14 5L2 8v16l12 3V5z" fill="#1565C0"/>
    <ellipse cx="8" cy="16" rx="4" ry="5" fill="#fff" opacity="0.9"/>
  </svg>
);

const SlackIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 54 54" xmlns="http://www.w3.org/2000/svg">
    <path d="M19.7 43.3c0 3-2.4 5.4-5.4 5.4s-5.4-2.4-5.4-5.4 2.4-5.4 5.4-5.4h5.4v5.4zm2.7 0c0-3 2.4-5.4 5.4-5.4s5.4 2.4 5.4 5.4v13.5c0 3-2.4 5.4-5.4 5.4s-5.4-2.4-5.4-5.4V43.3z" fill="#E01E5A" transform="translate(0 -10) scale(0.85)"/>
    <path d="M27.8 19.7c-3 0-5.4-2.4-5.4-5.4s2.4-5.4 5.4-5.4 5.4 2.4 5.4 5.4v5.4h-5.4zm0 2.7c3 0 5.4 2.4 5.4 5.4s-2.4 5.4-5.4 5.4H14.3c-3 0-5.4-2.4-5.4-5.4s2.4-5.4 5.4-5.4h13.5z" fill="#36C5F0" transform="translate(0 -10) scale(0.85)"/>
    <path d="M51.3 27.8c0-3 2.4-5.4 5.4-5.4s5.4 2.4 5.4 5.4-2.4 5.4-5.4 5.4h-5.4v-5.4zm-2.7 0c0 3-2.4 5.4-5.4 5.4s-5.4-2.4-5.4-5.4V14.3c0-3 2.4-5.4 5.4-5.4s5.4 2.4 5.4 5.4v13.5z" fill="#2EB67D" transform="translate(0 -10) scale(0.85)"/>
    <path d="M43.3 51.3c3 0 5.4 2.4 5.4 5.4s-2.4 5.4-5.4 5.4-5.4-2.4-5.4-5.4v-5.4h5.4zm0-2.7c-3 0-5.4-2.4-5.4-5.4s2.4-5.4 5.4-5.4h13.5c3 0 5.4 2.4 5.4 5.4s-2.4 5.4-5.4 5.4H43.3z" fill="#ECB22E" transform="translate(0 -10) scale(0.85)"/>
  </svg>
);

const SqlIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
    <ellipse cx="16" cy="8" rx="12" ry="5" fill="#E48E00"/>
    <path d="M4 8v16c0 2.76 5.37 5 12 5s12-2.24 12-5V8c0 2.76-5.37 5-12 5S4 10.76 4 8z" fill="#FFC107"/>
    <ellipse cx="16" cy="8" rx="12" ry="5" fill="#E48E00" opacity="0.3"/>
    <path d="M4 14c0 2.76 5.37 5 12 5s12-2.24 12-5" fill="none" stroke="#E48E00" strokeWidth="0.5"/>
    <path d="M4 20c0 2.76 5.37 5 12 5s12-2.24 12-5" fill="none" stroke="#E48E00" strokeWidth="0.5"/>
  </svg>
);

// ─── Data ────────────────────────────────────────────────────────────────────
const connectors: ConnectorItem[] = [
  { icon: <GoogleDriveIcon />, label: 'Google Drive', color: 'text-green-600', description: 'Connect your Google Workspace documents and spreadsheets' },
  { icon: <DropboxIcon />, label: 'Dropbox', color: 'text-blue-500', description: 'Sync files from Dropbox Business or Personal' },
  { icon: <SqlIcon />, label: 'SQL Databases', color: 'text-purple-600', description: 'Connect PostgreSQL, MySQL, SQL Server and more' },
  { icon: <SharePointIcon />, label: 'SharePoint', color: 'text-teal-600', description: 'Access SharePoint sites, libraries and lists' },
  { icon: <OutlookIcon />, label: 'Outlook / Email', color: 'text-blue-700', description: 'Ingest emails and attachments automatically' },
  { icon: <SlackIcon />, label: 'Slack', color: 'text-purple-500', description: 'Monitor channels and extract key decisions' },
  { icon: <MoreHorizontal className="w-5 h-5" />, label: 'Other Systems', color: 'text-gray-500', description: 'Custom integrations via REST API or webhooks' },
];

const analysisCards = [
  { icon: <FileText className="w-6 h-6" />, label: 'Document\nUnderstanding', description: 'AI reads and comprehends documents like a human expert' },
  { icon: <Search className="w-6 h-6" />, label: 'Data\nExtraction', description: 'Automatically pull structured data from unstructured sources' },
  { icon: <Network className="w-6 h-6" />, label: 'Entity & Relational\nMapping', description: 'Discover relationships between people, orgs and contracts' },
  { icon: <ShieldAlert className="w-6 h-6" />, label: 'Policy & Risk\nDetection', description: 'Flag compliance issues and policy violations instantly' },
];

const knowledgeNodes = [
  { label: 'Contracts', description: 'Track all contractual agreements and obligations' },
  { label: 'Vendors', description: 'Manage supplier relationships and performance' },
  { label: 'Invoices', description: 'Process and reconcile financial documents' },
  { label: 'Employees', description: 'HR records, onboarding and compliance' },
  { label: 'Projects', description: 'Monitor project timelines and deliverables' },
  { label: 'Entities', description: 'Organizations, people and their connections' },
  { label: 'Tasks', description: 'Assigned work items and their status' },
  { label: 'Assets', description: 'Physical and digital asset inventory' },
];

const insightsCards = [
  { icon: <AlertTriangle className="w-5 h-5" />, label: 'Risk &\nExceptions', color: 'text-red-500', description: 'Identify risks, anomalies and policy exceptions in real time' },
  { icon: <Clock className="w-5 h-5" />, label: 'Obligations &\nRenewals', color: 'text-amber-500', description: 'Never miss a deadline, renewal date or compliance obligation' },
  { icon: <TrendingUp className="w-5 h-5" />, label: 'Bottlenecks &\nDelays', color: 'text-orange-500', description: 'Spot process bottlenecks and predict delays before they happen' },
  { icon: <BarChart3 className="w-5 h-5" />, label: 'Trends &\nOpportunities', color: 'text-green-500', description: 'Uncover trends, patterns and growth opportunities across data' },
];

const agents: AgentItem[] = [
  { icon: <Users className="w-6 h-6" />, label: 'HR Agent', color: 'bg-blue-100 text-blue-700', description: 'Automates employee lifecycle tasks' },
  { icon: <DollarSign className="w-6 h-6" />, label: 'Finance Agent', color: 'bg-green-100 text-green-700', description: 'Handles invoices, expenses and reconciliation' },
  { icon: <Scale className="w-6 h-6" />, label: 'Legal Agent', color: 'bg-purple-100 text-purple-700', description: 'Reviews contracts and flags legal risks' },
  { icon: <Settings className="w-6 h-6" />, label: 'Operations Agent', color: 'bg-orange-100 text-orange-700', description: 'Optimizes workflows and resource allocation' },
  { icon: <Sparkles className="w-6 h-6" />, label: 'Custom Agents', color: 'bg-gray-100 text-gray-700', description: 'Build your own agents for specific needs' },
];

const capabilities = [
  'Understand requests & context',
  'Plan and break down tasks',
  'Take actions across systems',
  'Seek approvals when needed',
  'Learn and improve continuously',
];

const workflows: WorkflowItem[] = [
  { icon: <Briefcase className="w-4 h-4" />, label: 'Employee Onboarding', description: 'Automate new hire paperwork, access provisioning and training' },
  { icon: <Receipt className="w-4 h-4" />, label: 'Invoice Processing', description: 'Extract, validate and route invoices for approval' },
  { icon: <FileCheck className="w-4 h-4" />, label: 'Contract Management', description: 'Draft, review, negotiate and track contract lifecycle' },
  { icon: <Building2 className="w-4 h-4" />, label: 'Vendor Management', description: 'Evaluate vendors, track SLAs and manage renewals' },
  { icon: <Wrench className="w-4 h-4" />, label: 'IT/Facilities Requests', description: 'Handle service tickets, equipment and workspace requests' },
];

const businessOutcomes = [
  'Save time & reduce manual work',
  'Improve accuracy & compliance',
  'Accelerate cycle times & approvals',
  'Increase visibility & control',
  'Empower teams with AI',
];

const governanceItems = [
  'Role-Based Access Control',
  'Audit Logs & Activity Tracking',
  'Data Privacy & Security',
  'Policy Enforcement & Guardrails',
  'Human-in-the-Loop Oversight',
];

// ─── Hook: Intersection Observer ─────────────────────────────────────────────
function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setInView(true); },
      { threshold }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  return { ref, inView };
}

// ─── Sub-components ──────────────────────────────────────────────────────────
const DetailPanel: React.FC<{ title: string; description: string; onClose: () => void }> = ({ title, description, onClose }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm animate-fadeIn" onClick={onClose}>
    <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-sm w-full mx-4 animate-scaleIn" onClick={e => e.stopPropagation()}>
      <div className="flex justify-between items-start mb-3">
        <h4 className="text-lg font-bold text-gray-900">{title}</h4>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600"><X className="w-5 h-5" /></button>
      </div>
      <p className="text-gray-600 text-sm leading-relaxed">{description}</p>
    </div>
  </div>
);

// ─── Main Component ──────────────────────────────────────────────────────────
const OperationsDiagram: React.FC = () => {
  const [expandedConnector, setExpandedConnector] = useState<ConnectorItem | null>(null);
  const [expandedAgent, setExpandedAgent] = useState<AgentItem | null>(null);

  const hero = useInView(0.1);
  const connectCol = useInView(0.15);
  const understandCol = useInView(0.15);
  const orchestrateCol = useInView(0.15);
  const outcomesRow = useInView(0.2);
  const governanceRow = useInView(0.2);

  return (
    <section className="pt-16 pb-8">
      {/* Section headline */}
      <div
        ref={hero.ref}
        className={`text-center mb-12 px-4 transition-all duration-700 ${hero.inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}
      >
        <span className="inline-block px-4 py-1.5 rounded-full text-sm font-semibold mb-5 text-blue-700" style={{ background: '#dbeafe' }}>
          How It Works
        </span>
        <h2 className="text-3xl sm:text-5xl font-black text-gray-900 mb-3">
          Connect <span className="text-blue-600">→</span> Understand <span className="text-purple-600">→</span> Orchestrate
        </h2>
        <p className="text-lg text-gray-500 max-w-2xl mx-auto">
          Three steps to full enterprise intelligence, from raw data to autonomous AI agents acting on your behalf.
        </p>
      </div>

      {/* 3-Column Diagram */}
      <div className="max-w-7xl mx-auto px-4 grid grid-cols-1 lg:grid-cols-3 gap-6 mb-10">

        {/* ── Column 1: CONNECT ── */}
        <div
          ref={connectCol.ref}
          className={`relative bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl border border-blue-100 p-6 transition-all duration-700 delay-100 ${
            connectCol.inView ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-12'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="w-7 h-7 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">1</span>
            <h2 className="text-lg font-bold text-blue-700 uppercase tracking-wide">Connect</h2>
          </div>
          <p className="text-sm text-blue-600 mb-5">Bring your data together</p>

          <div className="space-y-2">
            {connectors.map((c) => (
              <button
                key={c.label}
                onClick={() => setExpandedConnector(c)}
                className="w-full flex items-center gap-3 p-2.5 bg-white rounded-xl border border-gray-100 hover:border-blue-300 hover:shadow-md hover:scale-[1.02] transition-all duration-200 group text-left relative"
              >
                <span className={`${c.color} group-hover:scale-110 transition-transform`}>{c.icon}</span>
                <span className="text-sm font-medium text-gray-700 group-hover:text-blue-700 transition-colors">{c.label}</span>
                <ChevronRight className="w-3.5 h-3.5 ml-auto text-gray-300 group-hover:text-blue-500 transition-colors" />
                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-52 bg-gray-900 text-white text-xs rounded-lg p-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 text-center">
                  {c.description}
                </div>
              </button>
            ))}
          </div>

          {/* Arrow indicator */}
          <div className="hidden lg:flex absolute -right-4 top-1/2 -translate-y-1/2 z-10">
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center shadow-lg animate-pulse-slow">
              <ArrowRight className="w-4 h-4 text-white" />
            </div>
          </div>

          {/* Secure badge */}
          <div className="mt-5 flex items-center gap-2 bg-white/80 rounded-lg p-2.5 border border-blue-100">
            <ShieldAlert className="w-4 h-4 text-blue-600" />
            <div>
              <span className="text-xs font-semibold text-gray-800">Secure by design</span>
              <span className="text-xs text-gray-500 block">Role-based access, encryption & audit logs</span>
            </div>
          </div>
        </div>

        {/* ── Column 2: UNDERSTAND ── */}
        <div
          ref={understandCol.ref}
          className={`relative bg-gradient-to-br from-white to-blue-50 rounded-2xl border border-blue-100 p-6 transition-all duration-700 delay-200 ${
            understandCol.inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="w-7 h-7 bg-blue-600 text-white rounded-full flex items-center justify-center text-sm font-bold">2</span>
            <h2 className="text-lg font-bold text-blue-700 uppercase tracking-wide">Understand</h2>
          </div>
          <p className="text-sm text-blue-600 mb-5">Turn data into operational intelligence</p>

          {/* AI-Powered Analysis */}
          <div className="bg-blue-50/70 rounded-xl p-4 mb-4 border border-blue-100">
            <h3 className="text-xs font-bold text-blue-800 uppercase tracking-wider mb-3">AI-Powered Analysis</h3>
            <div className="grid grid-cols-2 gap-2">
              {analysisCards.map((card) => (
                <div
                  key={card.label}
                  className="group bg-white rounded-lg p-2.5 border border-gray-100 hover:border-blue-300 hover:shadow-md transition-all duration-200 cursor-pointer relative"
                  title={card.description}
                >
                  <div className="text-blue-600 mb-1 group-hover:scale-110 transition-transform">{card.icon}</div>
                  <span className="text-[11px] font-medium text-gray-700 leading-tight whitespace-pre-line">{card.label}</span>
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 bg-gray-900 text-white text-xs rounded-lg p-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 text-center">
                    {card.description}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Unified Knowledge Layer */}
          <div className="bg-green-50/70 rounded-xl p-4 mb-4 border border-green-100">
            <h3 className="text-xs font-bold text-green-800 uppercase tracking-wider mb-3">Unified Knowledge Layer</h3>
            <div className="relative flex flex-wrap gap-2 justify-center py-3">
              {/* SVG connection lines */}
              <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
                <line x1="30%" y1="25%" x2="70%" y2="25%" stroke="#86efac" strokeWidth="1" className="animate-pulse-slow" />
                <line x1="20%" y1="50%" x2="50%" y2="30%" stroke="#86efac" strokeWidth="1" className="animate-pulse-slow" />
                <line x1="50%" y1="30%" x2="80%" y2="50%" stroke="#86efac" strokeWidth="1" className="animate-pulse-slow" />
                <line x1="30%" y1="75%" x2="70%" y2="75%" stroke="#86efac" strokeWidth="1" className="animate-pulse-slow" />
                <line x1="20%" y1="50%" x2="30%" y2="75%" stroke="#86efac" strokeWidth="1" className="animate-pulse-slow" />
                <line x1="80%" y1="50%" x2="70%" y2="75%" stroke="#86efac" strokeWidth="1" className="animate-pulse-slow" />
              </svg>
              {knowledgeNodes.map((node) => (
                <span
                  key={node.label}
                  className="relative z-10 px-3 py-1.5 bg-white rounded-full text-xs font-medium text-green-800 border border-green-200 hover:bg-green-100 hover:scale-110 transition-all duration-200 cursor-default shadow-sm group/node"
                >
                  {node.label}
                  {/* Tooltip */}
                  <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-44 bg-gray-900 text-white text-xs rounded-lg p-2 opacity-0 group-hover/node:opacity-100 transition-opacity pointer-events-none z-20 text-center font-normal">
                    {node.description}
                  </span>
                </span>
              ))}
              {/* Center FlexiAnalyse node */}
              <span className="relative z-10 px-3 py-1.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-full text-xs font-bold shadow-md">
                FlexiAnalyse
              </span>
            </div>
          </div>

          {/* Insights & Intelligence */}
          <div className="bg-purple-50/50 rounded-xl p-4 border border-purple-100">
            <h3 className="text-xs font-bold text-purple-800 uppercase tracking-wider mb-3">Insights & Intelligence</h3>
            <div className="grid grid-cols-2 gap-2">
              {insightsCards.map((card) => (
                <div key={card.label} className="flex items-center gap-2 bg-white rounded-lg p-2 border border-gray-100 hover:shadow-md transition-all group cursor-default relative">
                  <span className={`${card.color} group-hover:scale-110 transition-transform`}>{card.icon}</span>
                  <span className="text-[11px] font-medium text-gray-700 whitespace-pre-line leading-tight">{card.label}</span>
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 bg-gray-900 text-white text-xs rounded-lg p-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-20 text-center">
                    {card.description}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Arrow to Orchestrate */}
          <div className="hidden lg:flex absolute -right-4 top-1/2 -translate-y-1/2 z-10">
            <div className="w-8 h-8 bg-purple-600 rounded-full flex items-center justify-center shadow-lg animate-pulse-slow">
              <ArrowRight className="w-4 h-4 text-white" />
            </div>
          </div>
        </div>

        {/* ── Column 3: ORCHESTRATE ── */}
        <div
          ref={orchestrateCol.ref}
          className={`bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl border border-purple-100 p-6 transition-all duration-700 delay-300 ${
            orchestrateCol.inView ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-12'
          }`}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="w-7 h-7 bg-purple-600 text-white rounded-full flex items-center justify-center text-sm font-bold">3</span>
            <h2 className="text-lg font-bold text-purple-700 uppercase tracking-wide">Orchestrate</h2>
          </div>
          <p className="text-sm text-purple-600 mb-5">AI agents coordinate and complete work</p>

          {/* AI Agent Workforce */}
          <div className="bg-white/70 rounded-xl p-4 mb-4 border border-purple-100">
            <h3 className="text-xs font-bold text-purple-800 uppercase tracking-wider mb-3">AI Agent Workforce</h3>
            <div className="grid grid-cols-3 gap-2">
              {agents.map((agent) => (
                <button
                  key={agent.label}
                  onClick={() => setExpandedAgent(agent)}
                  className={`relative flex flex-col items-center gap-1 p-2 rounded-lg ${agent.color} hover:shadow-md hover:scale-105 transition-all duration-200 group/agent`}
                >
                  {agent.icon}
                  <span className="text-[10px] font-medium text-center leading-tight">{agent.label}</span>
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-44 bg-gray-900 text-white text-xs rounded-lg p-2 opacity-0 group-hover/agent:opacity-100 transition-opacity pointer-events-none z-20 text-center font-normal">
                    {agent.description}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Agent Capabilities */}
          <div className="bg-white/70 rounded-xl p-4 mb-4 border border-purple-100">
            <h3 className="text-xs font-bold text-purple-800 uppercase tracking-wider mb-3">Agent Capabilities</h3>
            <ul className="space-y-1.5">
              {capabilities.map((cap) => (
                <li key={cap} className="flex items-center gap-2 text-xs text-gray-700">
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                  {cap}
                </li>
              ))}
            </ul>
          </div>

          {/* Example Workflows */}
          <div className="bg-white/70 rounded-xl p-4 border border-purple-100">
            <h3 className="text-xs font-bold text-purple-800 uppercase tracking-wider mb-3">Example Workflows</h3>
            <ul className="space-y-1.5">
              {workflows.map((wf) => (
                <li key={wf.label} className="relative flex items-center gap-2 text-xs text-gray-700 p-1.5 rounded-lg hover:bg-purple-50 transition-colors group/wf">
                  <span className="text-purple-500">{wf.icon}</span>
                  {wf.label}
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-500 ml-auto" />
                  {/* Tooltip */}
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 bg-gray-900 text-white text-xs rounded-lg p-2 opacity-0 group-hover/wf:opacity-100 transition-opacity pointer-events-none z-20 text-center font-normal">
                    {wf.description}
                  </div>
                </li>
              ))}
            </ul>
            <p className="text-[10px] text-purple-500 mt-2 font-medium">+ more workflows</p>
          </div>
        </div>
      </div>

      {/* ── Business Outcomes ── */}
      <div
        ref={outcomesRow.ref}
        className={`max-w-7xl mx-auto px-4 mb-8 transition-all duration-700 delay-100 ${
          outcomesRow.inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
        }`}
      >
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
           <div className="flex items-center justify-center gap-3 mb-4">
             <div className="w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
               <TrendingUp className="w-4 h-4 text-white" />
             </div>
             <h3 className="text-base font-bold text-gray-900 text-center">Business Outcomes</h3>
           </div>
          <div className="flex flex-wrap gap-4 justify-center">
            {businessOutcomes.map((outcome) => (
              <div key={outcome} className="flex items-center gap-2 text-sm text-gray-700">
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                {outcome}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Governance & Control Layer ── */}
      <div
        ref={governanceRow.ref}
        className={`max-w-7xl mx-auto px-4 mb-12 transition-all duration-700 delay-200 ${
          governanceRow.inView ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'
        }`}
      >
        <div className="bg-gradient-to-r from-blue-900 to-purple-900 rounded-2xl p-5 text-white">
          <div className="flex flex-col items-center gap-4 text-center">
            {/* Title - now fully centered on its own row */}
            <div className="flex items-center justify-center gap-2">
              <ShieldAlert className="w-6 h-6 text-blue-300" />
              <h3 className="text-sm font-bold uppercase tracking-wider">Governance & Control Layer</h3>
            </div>

            {/* Items - centered below the title */}
            <div className="flex flex-wrap gap-4 justify-center">
              {governanceItems.map((item) => (
                <span key={item} className="flex items-center gap-1.5 text-xs text-blue-200">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                  {item}
                </span>
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-white/20 text-center">
            <p className="text-sm font-medium text-blue-100">
              <strong className="text-white">One platform. Every operation.</strong> FlexiAnalyse is your enterprise operations intelligence layer.
            </p>
          </div>
        </div>
      </div>

      {/* ── Detail Panels (click to expand) ── */}
      {expandedConnector && (
        <DetailPanel
          title={expandedConnector.label}
          description={expandedConnector.description}
          onClose={() => setExpandedConnector(null)}
        />
      )}
      {expandedAgent && (
        <DetailPanel
          title={expandedAgent.label}
          description={expandedAgent.description}
          onClose={() => setExpandedAgent(null)}
        />
      )}
    </section>
  );
};

export default OperationsDiagram;
