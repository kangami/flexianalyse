import React from 'react';
import SearchProgress from './SearchProgress';

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
}

const renderCell = (value: unknown): { text: string; isNull: boolean } => {
  if (value === null || value === undefined) return { text: 'NULL', isNull: true };
  if (typeof value === 'object') return { text: JSON.stringify(value), isNull: false };
  return { text: String(value), isNull: false };
};

const DbResultGrid: React.FC<DbResultGridProps> = ({ columns, rows, sql, loading }) => {
  const hasData = columns.length > 0;

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <svg className="w-4 h-4 text-purple-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <ellipse cx="12" cy="5" rx="8" ry="3" strokeWidth="1.6" />
            <path strokeWidth="1.6" d="M4 5v14c0 1.66 3.6 3 8 3s8-1.34 8-3V5M4 12c0 1.66 3.6 3 8 3s8-1.34 8-3" />
          </svg>
          <span className="text-xs font-semibold text-gray-700 truncate">Result</span>
          {hasData && (
            <span className="text-[10px] text-gray-400 tabular-nums flex-shrink-0">
              {rows.length} row{rows.length === 1 ? '' : 's'} · {columns.length} col{columns.length === 1 ? '' : 's'}
            </span>
          )}
        </div>
      </div>

      {/* SQL (when a query ran) */}
      {sql && (
        <div className="px-4 py-2 border-b border-gray-100 bg-gray-50 flex-shrink-0">
          <p className="text-[9px] font-semibold text-gray-400 uppercase tracking-wide mb-1">Live SQL</p>
          <pre className="text-[11px] text-gray-700 overflow-x-auto"><code>{sql}</code></pre>
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
            <p className="text-xs">Ask a data question and the table result appears here.</p>
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
              {rows.map((row, i) => (
                <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                  <td className="text-gray-400 px-2 py-1.5 border-b border-r border-gray-100 tabular-nums align-top">{i + 1}</td>
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
    </div>
  );
};

export default DbResultGrid;
