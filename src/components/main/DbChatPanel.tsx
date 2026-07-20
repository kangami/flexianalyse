import React, { useEffect, useRef, useState } from 'react';
import MarkdownResponse from './MarkdownResponse';

/**
 * Clean conversation panel for the RIGHT pane — driven by /api/mcp/search
 * (the database agent), not the legacy document-chat pipeline.
 *
 * Shows the running discussion (question → answer, with generated SQL and
 * sources) plus a follow-up input. Theme-aware via the global .theme-* overrides.
 */

export interface DbTurn {
  id: string;
  query: string;
  answer: string;
  sql?: string;
  sqlError?: string | null;
  sources: { title: string; type?: string; connector?: string; score?: number }[];
}

interface DbChatPanelProps {
  turns: DbTurn[];
  pendingQuery: string | null;
  loading: boolean;
  onSubmit: (query: string) => void;
  onNewSearch: () => void;
}

const UserBubble: React.FC<{ text: string }> = ({ text }) => (
  <div className="flex justify-end">
    <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-gradient-to-br from-blue-600 to-purple-600 text-white px-3.5 py-2 text-sm whitespace-pre-wrap break-words">
      {text}
    </div>
  </div>
);

const AssistantTurn: React.FC<{ turn: DbTurn }> = ({ turn }) => {
  const [showSql, setShowSql] = useState(false);
  return (
    <div className="flex flex-col gap-2">
      <div className="max-w-[92%] rounded-2xl rounded-tl-sm bg-gray-50 border border-gray-100 px-3.5 py-2.5 text-sm text-gray-800">
        <MarkdownResponse content={turn.answer} />
      </div>

      {turn.sql && (
        <div className="max-w-[92%]">
          <button
            onClick={() => setShowSql((s) => !s)}
            className="text-[10px] font-semibold text-purple-600 hover:text-purple-700 uppercase tracking-wide inline-flex items-center gap-1"
          >
            <svg className={`w-3 h-3 transition-transform ${showSql ? 'rotate-90' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
            </svg>
            Live SQL
          </button>
          {showSql && (
            <pre className="mt-1 text-[11px] rounded-lg px-3 py-2 bg-gray-50 border border-gray-200 text-gray-700 overflow-x-auto"><code>{turn.sql}</code></pre>
          )}
        </div>
      )}

      {turn.sources.length > 0 && (
        <div className="flex flex-wrap gap-1 max-w-[92%]">
          {turn.sources.map((s, i) => (
            <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 border border-gray-200 truncate max-w-[160px]" title={s.title}>
              {s.title}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

const DbChatPanel: React.FC<DbChatPanelProps> = ({ turns, pendingQuery, loading, onSubmit, onNewSearch }) => {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [turns, pendingQuery, loading]);

  const submit = () => {
    const q = input.trim();
    if (!q || loading) return;
    onSubmit(q);
    setInput('');
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        <div className="flex items-center gap-2">
          <img src="/flexiAnalyseLogo_website.png" alt="" className="h-5 w-auto" />
          <span className="text-sm font-bold text-purple-600">Flexi</span>
        </div>
        <button
          onClick={onNewSearch}
          className="text-[11px] font-medium text-gray-500 hover:text-purple-600 inline-flex items-center gap-1 transition-colors"
          title="Start a new search"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
          New search
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4">
        {turns.map((turn) => (
          <div key={turn.id} className="flex flex-col gap-3">
            <UserBubble text={turn.query} />
            <AssistantTurn turn={turn} />
          </div>
        ))}

        {loading && pendingQuery && (
          <div className="flex flex-col gap-3">
            <UserBubble text={pendingQuery} />
            <div className="flex items-center gap-2 text-gray-400 text-sm px-1">
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" className="opacity-75" />
              </svg>
              Searching across your connectors…
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-3 flex-shrink-0 bg-white">
        <div className="flex items-end gap-2 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 focus-within:ring-2 focus-within:ring-purple-200 focus-within:border-purple-400 transition-all">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } }}
            placeholder="Ask a follow-up…"
            rows={1}
            className="flex-1 bg-transparent resize-none text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none max-h-32"
          />
          <button
            onClick={submit}
            disabled={!input.trim() || loading}
            className="flex-shrink-0 rounded-lg p-1.5 bg-gradient-to-br from-blue-600 to-purple-600 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:shadow-md transition-all"
            aria-label="Send"
          >
            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default DbChatPanel;
