import React from 'react';

/**
 * Anticipated-question chips shown above a query input. The dbAnalyse agent
 * proposes 4 business questions; a 5th fixed chip opens the database ER diagram.
 * Sits above both the AppHome main input and the DbChatPanel follow-up input.
 */

interface SuggestionChipsProps {
  questions: string[];
  loading?: boolean;
  onPick: (q: string) => void;
  onShowDiagram: () => void;
  compact?: boolean;
}

const SuggestionChips: React.FC<SuggestionChipsProps> = ({ questions, loading, onPick, onShowDiagram, compact }) => {
  if (loading && questions.length === 0) {
    return (
      <div className={`flex items-center gap-1.5 text-gray-400 ${compact ? 'text-[10px]' : 'text-[11px]'} px-1 mb-2`}>
        <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
          <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" className="opacity-75" />
        </svg>
        Analysing your database…
      </div>
    );
  }

  if (questions.length === 0) return null;

  const pill = `rounded-full border border-gray-200 bg-white hover:border-purple-400 hover:bg-purple-50/40 text-gray-700 transition-colors ${compact ? 'px-2.5 py-1 text-[10px]' : 'px-3 py-1.5 text-xs'}`;

  return (
    <div className="flex flex-wrap gap-1.5 mb-2">
      {questions.slice(0, 4).map((q, i) => (
        <button key={i} type="button" onClick={() => onPick(q)} className={`${pill} truncate max-w-[280px]`} title={q}>
          {q}
        </button>
      ))}
      <button
        type="button"
        onClick={onShowDiagram}
        className={`${pill} inline-flex items-center gap-1.5 text-purple-600 border-purple-200`}
        title="Show the database schema diagram"
      >
        <svg className={compact ? 'w-3 h-3' : 'w-3.5 h-3.5'} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <rect x="3" y="3" width="7" height="5" rx="1" strokeWidth="1.6" />
          <rect x="14" y="7" width="7" height="5" rx="1" strokeWidth="1.6" />
          <rect x="7" y="16" width="7" height="5" rx="1" strokeWidth="1.6" />
          <path strokeWidth="1.6" d="M10 8v5h7M10.5 13v3" />
        </svg>
        Database diagram
      </button>
    </div>
  );
};

export default SuggestionChips;
