import React, { useEffect, useState } from 'react';
import { useLanguage } from '../../contexts/LanguageContext';
import SearchProgress from './SearchProgress';

const PAGE_SIZE = 100;

/**
 * DBeaver-style read-only result grid for the LEFT pane.
 *
 * Renders the columns + rows returned by a Text-to-SQL query. Theme-aware via the
 * global `.theme-*` overrides on bg-white / bg-gray-* / text-gray-* / border-gray-*.
 */

export interface DbResultGridProps {
  columns: string[];
  rows: Record<string, unknown>[];
  sql?: string;
  loading?: boolean;
  /** True total matched by the query, when more rows exist than are displayed. */
  totalRows?: number;
}

const renderCell = (value: unknown): { text: string; isNull: boolean } => {
  if (value === null || value === undefined) return { text: 'NULL', isNull: true };
  if (typeof value === 'object') return { text: JSON.stringify(value), isNull: false };
  return { text: String(value), isNull: false };
};

const DbResultGrid: React.FC<DbResultGridProps> = ({ columns, rows, sql, loading, totalRows }) => {
  const { t } = useLanguage();
  const hasData = columns.length > 0;
  const truncated = typeof totalRows === 'number' && totalRows > rows.length;
  // Collapsed by default so a long analytical query (CTEs/window functions)
  // doesn't push the result grid off-screen.
  const [showSql, setShowSql] = useState(false);

  const [page, setPage] = useState(0);
  useEffect(() => { setPage(0); }, [rows]);
  const pageCount = Math.ceil(rows.length / PAGE_SIZE) || 1;
  const safePage = Math.min(page, pageCount - 1);
  const start = safePage * PAGE_SIZE;
  const pageRows = rows.slice(start, start + PAGE_SIZE);

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <svg className="w-4 h-4 text-purple-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <ellipse cx="12" cy="5" rx="8" ry="3" strokeWidth="1.6" />
            <path strokeWidth="1.6" d="M4 5v14c0 1.66 3.6 3 8 3s8-1.34 8-3V5M4 12c0 1.66 3.6 3 8 3s8-1.34 8-3" />
          </svg>
          <span className="text-xs font-semibold text-gray-700 truncate">{t('grid.result')}</span>
          {hasData && (
            <span className="text-[10px] text-gray-400 tabular-nums flex-shrink-0">
              {truncated
                ? t('grid.rowsOf', { shown: rows.length, total: totalRows!.toLocaleString() })
                : t('grid.rows', { count: rows.length, plural: rows.length === 1 ? '' : 's' })}
              {' · '}{t('grid.cols', { count: columns.length, plural: columns.length === 1 ? '' : 's' })}
            </span>
          )}
        </div>
      </div>

      {/* SQL (when a query ran) — collapsible, capped height so it never eats
          the whole pane on a long analytical query. */}
      {sql && (
        <div className="border-b border-gray-100 bg-gray-50 flex-shrink-0">
          <button
            onClick={() => setShowSql((s) => !s)}
            className="w-full flex items-center gap-1.5 px-4 py-1.5 text-[9px] font-semibold text-gray-400 uppercase tracking-wide hover:text-purple-600 transition-colors"
          >
            <svg className={`w-3 h-3 transition-transform ${showSql ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
            </svg>
            {t('dbchat.liveSql')}
          </button>
          {showSql && (
            <pre className="text-[11px] text-gray-700 overflow-auto max-h-40 px-4 pb-2"><code>{sql}</code></pre>
          )}
        </div>
      )}

      {/* Body */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <SearchProgress />
          </div>
        ) : !hasData ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-400 gap-2 px-6 text-center">
            <svg className="w-10 h-10 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <ellipse cx="12" cy="5" rx="8" ry="3" strokeWidth="1.5" />
              <path strokeWidth="1.5" d="M4 5v14c0 1.66 3.6 3 8 3s8-1.34 8-3V5M4 12c0 1.66 3.6 3 8 3s8-1.34 8-3" />
            </svg>
            <p className="text-xs">{t('grid.empty')}</p>
          </div>
        ) : (
          <table className="w-full text-xs border-collapse">
            <thead className="sticky top-0 z-10">
              <tr className="bg-gray-100">
                <th className="text-left font-semibold text-gray-400 px-2 py-1.5 border-b border-r border-gray-200 w-10 tabular-nums">#</th>
                {columns.map((col) => (
                  <th key={col} className="text-left font-semibold text-gray-700 px-3 py-1.5 border-b border-r border-gray-200 whitespace-nowrap">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pageRows.map((row, i) => (
                <tr key={start + i} className={(start + i) % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="text-gray-400 px-2 py-1.5 border-b border-r border-gray-100 tabular-nums align-top">{start + i + 1}</td>
                  {columns.map((col) => {
                    const { text, isNull } = renderCell(row[col]);
                    return (
                      <td
                        key={col}
                        className={`px-3 py-1.5 border-b border-r border-gray-100 align-top max-w-xs truncate ${isNull ? 'text-gray-300 italic' : 'text-gray-800'}`}
                        title={text}
                      >
                        {text}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination — 100 rows/page */}
      {hasData && rows.length > PAGE_SIZE && (
        <div className="flex items-center justify-between px-4 py-1.5 border-t border-gray-200 bg-gray-50 flex-shrink-0 text-[10px] text-gray-500">
          <span className="tabular-nums">{start + 1}–{Math.min(start + PAGE_SIZE, rows.length)} / {rows.length.toLocaleString()}</span>
          <div className="flex items-center gap-2">
            <button
              disabled={safePage === 0}
              onClick={() => setPage(safePage - 1)}
              aria-label={t('fileviewer.page.previous')}
              className="p-1 rounded hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" /></svg>
            </button>
            <span className="tabular-nums font-medium">{t('grid.page', { current: safePage + 1, total: pageCount })}</span>
            <button
              disabled={safePage >= pageCount - 1}
              onClick={() => setPage(safePage + 1)}
              aria-label={t('fileviewer.page.next')}
              className="p-1 rounded hover:bg-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" /></svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default DbResultGrid;
