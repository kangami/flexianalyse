import React from 'react';

/**
 * Database Report — the measured (non-fabricated) health & overview of a connected
 * SQL database. Renders the JSON produced by the backend report_builder. Every
 * figure here is measured; dimensions we can't measure yet are shown as "coming
 * soon", never faked.
 */

interface Check { label: string; value: string | number }
interface Dimension { key: string; label: string; score: number | null; checks: Check[] }
export interface ReportData {
  engine?: string | null;
  version?: string | null;
  overview: Record<string, number | null | boolean>;
  health: { score: number | null; weights: Record<string, number>; dimensions: Dimension[] };
  critical_tables: { table: string; referenced_by: number; rows: number | null }[];
  architecture: {
    hub_tables: { table: string; referenced_by: number }[];
    junction_tables: { count: number; sample: string[] };
    orphan_tables: { count: number; sample: string[] };
    domains: { name: string; tables: number }[];
  };
  summary?: string;
  recommendations?: string[];
  generated_at?: string;
}

interface Props {
  data: ReportData | null;
  status: string;                 // none | pending | running | done | failed
  generatedAt?: string | null;
  generating?: boolean;
  onGenerate: () => void;
  onAsk?: () => void;
  onDiagram?: () => void;
}

const nf = (n: number) => n.toLocaleString();
const fmtInt = (v: unknown) => (typeof v === 'number' ? nf(v) : '—');
const fmtRows = (v: unknown) => {
  if (typeof v !== 'number') return '—';
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return nf(v);
};
const fmtBytes = (v: unknown) => {
  if (typeof v !== 'number') return '—';
  const u = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];
  let i = 0, n = v;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(n < 10 && i > 0 ? 1 : 0)} ${u[i]}`;
};

const scoreColor = (s: number) =>
  s >= 80 ? '#16a34a' : s >= 60 ? '#d97706' : '#dc2626';

const OVERVIEW_FIELDS: { key: string; label: string; fmt: (v: unknown) => string }[] = [
  { key: 'tables', label: 'Tables', fmt: fmtInt },
  { key: 'columns', label: 'Columns', fmt: fmtInt },
  { key: 'estimated_rows', label: 'Est. rows', fmt: fmtRows },
  { key: 'db_size_bytes', label: 'Size', fmt: fmtBytes },
  { key: 'schemas', label: 'Schemas', fmt: fmtInt },
  { key: 'views', label: 'Views', fmt: fmtInt },
  { key: 'materialized_views', label: 'Mat. views', fmt: fmtInt },
  { key: 'sequences', label: 'Sequences', fmt: fmtInt },
  { key: 'functions', label: 'Functions', fmt: fmtInt },
  { key: 'procedures', label: 'Procedures', fmt: fmtInt },
  { key: 'triggers', label: 'Triggers', fmt: fmtInt },
  { key: 'foreign_keys', label: 'Foreign keys', fmt: fmtInt },
  { key: 'indexes', label: 'Indexes', fmt: fmtInt },
];

const COMING_SOON = ['Security', 'Data Quality', 'Performance (runtime)', 'Migration Readiness'];

const DatabaseReport: React.FC<Props> = ({ data, status, generatedAt, generating, onGenerate }) => {
  // ── Non-ready states ──────────────────────────────────────────────────────
  if (status !== 'done' || !data) {
    const running = status === 'pending' || status === 'running' || generating;
    return (
      <div className="h-full flex flex-col items-center justify-center text-center px-6 gap-4 bg-white">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center text-white" style={{ background: 'linear-gradient(135deg,#8b5cf6,#6d28d9)' }}>
          <i className={`bi ${running ? 'bi-arrow-repeat animate-spin' : status === 'failed' ? 'bi-exclamation-triangle' : 'bi-clipboard-data'} text-2xl`} />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-800">
            {running ? 'Analysing your database…' : status === 'failed' ? 'Report generation failed' : 'No database report yet'}
          </p>
          <p className="text-xs text-gray-500 mt-1 max-w-xs">
            {running
              ? 'We are measuring your schema, relationships and health. This runs in the background.'
              : status === 'failed'
              ? 'Something went wrong while building the report. You can try again.'
              : 'Generate a measured health & overview report of your connected database.'}
          </p>
        </div>
        {!running && (
          <button onClick={onGenerate} className="px-5 py-2.5 rounded-lg text-white text-sm font-semibold" style={{ background: 'linear-gradient(135deg,#8b5cf6,#6d28d9)' }}>
            {status === 'failed' ? 'Retry' : 'Generate report'}
          </button>
        )}
      </div>
    );
  }

  const { overview, health, critical_tables, architecture } = data;
  const global = health.score;

  return (
    <div className="h-full overflow-auto bg-gray-50">
      {/* Header */}
      <div className="sticky top-0 z-10 flex items-center justify-between px-5 py-3 bg-white border-b border-gray-200">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <i className="bi bi-clipboard-data text-purple-600" />
            <span className="text-sm font-bold text-gray-800">Database Report</span>
            {data.engine && (
              <span className="text-[10px] font-semibold text-purple-700 bg-purple-50 rounded px-1.5 py-0.5 uppercase">
                {data.engine}{data.version ? ` ${data.version}` : ''}
              </span>
            )}
          </div>
          {generatedAt && <p className="text-[10px] text-gray-400 mt-0.5">Generated {new Date(generatedAt).toLocaleString()}</p>}
        </div>
        <div className="flex items-center gap-1.5">
          <button onClick={onGenerate} disabled={generating} title="Regenerate" className="w-8 h-8 rounded-lg flex items-center justify-center text-gray-500 border border-gray-200 hover:bg-gray-50 disabled:opacity-40">
            <i className={`bi bi-arrow-repeat ${generating ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="p-5 space-y-6 max-w-4xl mx-auto">
        {/* Health score + dimensions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="rounded-2xl bg-white border border-gray-200 p-5 flex flex-col items-center justify-center">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-2">Health score</p>
            {global != null ? (
              <div className="text-5xl font-black tabular-nums" style={{ color: scoreColor(global) }}>{global}</div>
            ) : <div className="text-2xl text-gray-300">n/a</div>}
            <p className="text-[9px] text-gray-400 mt-2 text-center">Weighted from the measured dimensions →</p>
          </div>
          <div className="md:col-span-2 rounded-2xl bg-white border border-gray-200 p-5 space-y-3">
            {health.dimensions.filter(d => d.score != null).map(d => (
              <div key={d.key}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-gray-700">{d.label}
                    <span className="ml-1.5 text-[9px] text-gray-400">· {Math.round((health.weights[d.key] || 0) * 100)}%</span>
                  </span>
                  <span className="text-xs font-bold tabular-nums" style={{ color: scoreColor(d.score!) }}>{d.score}</span>
                </div>
                <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${d.score}%`, background: scoreColor(d.score!) }} />
                </div>
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
                  {d.checks.map((c, i) => (
                    <span key={i} className="text-[10px] text-gray-500">{c.label}: <span className="font-medium text-gray-700">{c.value}</span></span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI summary + recommendations */}
        {(data.summary || (data.recommendations && data.recommendations.length > 0)) && (
          <div className="rounded-2xl bg-white border border-gray-200 p-5">
            <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-2">AI Summary</p>
            {data.summary && <p className="text-sm text-gray-700 leading-relaxed mb-3">{data.summary}</p>}
            {data.recommendations && data.recommendations.length > 0 && (
              <ul className="space-y-1.5">
                {data.recommendations.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <i className="bi bi-lightbulb text-amber-500 mt-0.5 flex-shrink-0" />{r}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {/* Overview grid */}
        <div>
          <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-2">Overview</p>
          <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2.5">
            {OVERVIEW_FIELDS.map(f => (
              <div key={f.key} className="rounded-xl bg-white border border-gray-100 px-3 py-2.5 text-center">
                <div className="text-lg font-black text-gray-800 tabular-nums">{f.fmt(overview[f.key])}</div>
                <div className="text-[9px] text-gray-400 uppercase tracking-wide">{f.label}</div>
              </div>
            ))}
          </div>
          {overview.capped && (
            <p className="text-[10px] text-gray-400 mt-2 italic">Analysis covers the {fmtInt(overview.catalogued_tables)} catalogued tables (your plan's limit); overview counts are the full database.</p>
          )}
        </div>

        {/* Critical tables + architecture */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-2xl bg-white border border-gray-200 p-5">
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">Top Critical Tables</p>
            {critical_tables.length === 0 ? <p className="text-xs text-gray-400">No foreign-key relationships detected.</p> : (
              <div className="space-y-1.5">
                {critical_tables.map((t, i) => (
                  <div key={t.table} className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-gray-300 w-4 tabular-nums">{i + 1}</span>
                    <span className="text-sm font-medium text-gray-800 truncate flex-1">{t.table}</span>
                    {t.rows != null && <span className="text-[10px] text-gray-400 tabular-nums">{fmtRows(t.rows)} rows</span>}
                    <span className="text-[10px] font-semibold text-purple-700 bg-purple-50 rounded px-1.5 py-0.5 whitespace-nowrap">ref. by {t.referenced_by}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-2xl bg-white border border-gray-200 p-5">
            <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">Architecture</p>
            <div className="grid grid-cols-2 gap-2 mb-3">
              <div className="rounded-lg bg-gray-50 px-3 py-2 text-center">
                <div className="text-lg font-black text-gray-800 tabular-nums">{architecture.junction_tables.count}</div>
                <div className="text-[9px] text-gray-400 uppercase">Junction (N:N)</div>
              </div>
              <div className="rounded-lg bg-gray-50 px-3 py-2 text-center">
                <div className="text-lg font-black text-gray-800 tabular-nums">{architecture.orphan_tables.count}</div>
                <div className="text-[9px] text-gray-400 uppercase">Orphan tables</div>
              </div>
            </div>
            {architecture.domains.length > 0 && (
              <>
                <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1.5">Business domains (inferred)</p>
                <div className="flex flex-wrap gap-1.5">
                  {architecture.domains.map(d => (
                    <span key={d.name} className="text-[10px] text-gray-600 bg-gray-100 rounded-full px-2 py-0.5">{d.name} · {d.tables}</span>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Honest scope note */}
        <div className="rounded-2xl border border-dashed border-gray-200 p-4">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide mb-1">Coming soon</p>
          <p className="text-xs text-gray-500">
            {COMING_SOON.join(' · ')} — these need deeper analysis (sampling, runtime stats) and will be added with a transparent methodology rather than an arbitrary score.
          </p>
        </div>
      </div>
    </div>
  );
};

export default DatabaseReport;
