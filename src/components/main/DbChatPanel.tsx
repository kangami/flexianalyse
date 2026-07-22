import React, { useEffect, useRef, useState } from 'react';
import MarkdownResponse from './MarkdownResponse';
import ScopeSelector, { ScopeConnector } from './ScopeSelector';
import SuggestionChips from './SuggestionChips';
import SearchProgress from './SearchProgress';

/**
 * Clean conversation panel for the RIGHT pane — driven by /api/mcp/search
 * (the database agent), not the legacy document-chat pipeline.
 *
 * Shows the running discussion (question → answer, with generated SQL and
 * sources) plus a follow-up input. Theme-aware via the global .theme-* overrides.
 */

export interface WritePreview {
  sql: string;
  rowsAffected: number | null;
  requiresExtraConfirm: boolean;
  connectorId: string | null;
  status: 'pending' | 'confirming' | 'confirmed' | 'cancelled' | 'error';
  resultMessage?: string;
}

export interface DbTurn {
  id: string;
  query: string;
  answer: string;
  sql?: string;
  sqlError?: string | null;
  sources: { title: string; type?: string; connector?: string; score?: number }[];
  // Present when this turn is a pending/decided write awaiting confirmation.
  write?: WritePreview;
}

interface DbChatPanelProps {
  turns: DbTurn[];
  pendingQuery: string | null;
  loading: boolean;
  onSubmit: (query: string) => void;
  onNewSearch: () => void;
  connectors: ScopeConnector[];
  scope: string | null;
  onScopeChange: (id: string | null) => void;
  questions: string[];
  insightsLoading: boolean;
  onShowDiagram: () => void;
  history?: { id: string; title: string | null; updated_at: string | null }[];
  activeConversationId?: string | null;
  onOpenConversation?: (id: string) => void;
  onConfirmWrite?: (turnId: string) => void;
  onCancelWrite?: (turnId: string) => void;
}

const UserBubble: React.FC<{ text: string }> = ({ text }) => (
  <div className="flex justify-end">
    <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-gradient-to-br from-blue-600 to-purple-600 text-white px-3.5 py-2 text-sm whitespace-pre-wrap break-words">
      {text}
    </div>
  </div>
);

// Reveals the answer progressively (typing effect) for the latest turn, then
// renders the full markdown. Earlier turns render immediately.
const TypingMarkdown: React.FC<{ text: string; animate: boolean }> = ({ text, animate }) => {
  const [shown, setShown] = useState(animate ? '' : text);
  const doneRef = useRef(!animate);
  useEffect(() => {
    if (!animate || doneRef.current) { setShown(text); return; }
    let i = 0;
    const step = Math.max(2, Math.round(text.length / 120)); // ~120 ticks whatever the length
    const id = setInterval(() => {
      i = Math.min(i + step, text.length);
      setShown(text.slice(0, i));
      if (i >= text.length) { clearInterval(id); doneRef.current = true; }
    }, 18);
    return () => clearInterval(id);
  }, [text, animate]);
  return <MarkdownResponse content={shown} />;
};

const AssistantTurn: React.FC<{ turn: DbTurn; animate: boolean }> = ({ turn, animate }) => {
  const [showSql, setShowSql] = useState(false);
  return (
    <div className="flex flex-col gap-2">
      <div className="max-w-[92%] rounded-2xl rounded-tl-sm bg-gray-50 border border-gray-100 px-3.5 py-2.5 text-sm text-gray-800">
        <TypingMarkdown text={turn.answer} animate={animate} />
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

// Confirmation card for a write (UPDATE/INSERT/DELETE) — shows the SQL and the
// dry-run impact; nothing is executed until the user clicks Confirm.
const WriteCard: React.FC<{ turn: DbTurn; onConfirm: () => void; onCancel: () => void }> = ({ turn, onConfirm, onCancel }) => {
  const w = turn.write!;
  const n = w.rowsAffected;
  const busy = w.status === 'confirming';
  return (
    <div className="max-w-[92%] rounded-2xl rounded-tl-sm border px-3.5 py-3 text-sm bg-amber-50 border-amber-200 text-gray-800">
      <div className="flex items-center gap-1.5 mb-1.5 text-amber-700 font-semibold text-[11px] uppercase tracking-wide">
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        </svg>
        Écriture — confirmation requise
      </div>
      <pre className="text-[11px] rounded-lg px-3 py-2 bg-white/70 border border-amber-200 text-gray-700 overflow-x-auto mb-2"><code>{w.sql}</code></pre>
      {w.status === 'pending' || w.status === 'confirming' ? (
        <>
          <p className="text-[12px] mb-2">
            {n === null ? 'Impact inconnu.' : <>Cette opération modifiera <strong>{n} ligne{n === 1 ? '' : 's'}</strong>.</>}
            {w.requiresExtraConfirm && (
              <span className="block text-red-600 font-medium mt-1">⚠️ Impact important (&gt; 1000 lignes) — vérifie bien avant de confirmer.</span>
            )}
          </p>
          <div className="flex gap-2">
            <button disabled={busy} onClick={onConfirm} className="text-xs px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 font-medium transition-colors">
              {busy ? 'Exécution…' : 'Confirmer & exécuter'}
            </button>
            <button disabled={busy} onClick={onCancel} className="text-xs px-3 py-1.5 rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-50 disabled:opacity-50 transition-colors">
              Annuler
            </button>
          </div>
        </>
      ) : w.status === 'confirmed' ? (
        <p className="text-[12px] text-green-700 font-medium">✓ {w.resultMessage}</p>
      ) : w.status === 'cancelled' ? (
        <p className="text-[12px] text-gray-500">Annulé — aucune modification.</p>
      ) : (
        <p className="text-[12px] text-red-600">⚠️ {w.resultMessage || 'Échec.'}</p>
      )}
    </div>
  );
};

const DbChatPanel: React.FC<DbChatPanelProps> = ({ turns, pendingQuery, loading, onSubmit, onNewSearch, connectors, scope, onScopeChange, questions, insightsLoading, onShowDiagram, history = [], activeConversationId, onOpenConversation, onConfirmWrite, onCancelWrite }) => {
  const [input, setInput] = useState('');
  const [showHistory, setShowHistory] = useState(false);
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
      <div className="relative flex items-center justify-between px-4 py-2.5 border-b border-gray-200 bg-gray-50 flex-shrink-0">
        <div className="flex items-center gap-2">
          <img src="/flexiAnalyseLogo_website.png" alt="" className="h-5 w-auto" />
          <span className="text-sm font-bold text-purple-600">Flexi</span>
        </div>
        <div className="flex items-center gap-3">
          {/* Conversation history */}
          <button
            onClick={() => setShowHistory(s => !s)}
            className="text-[11px] font-medium text-gray-500 hover:text-purple-600 inline-flex items-center gap-1 transition-colors"
            title="Conversation history"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            History
          </button>
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

        {showHistory && (
          <div className="absolute right-3 top-11 z-20 w-64 max-h-80 overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg py-1">
            {history.length === 0 ? (
              <p className="px-3 py-2 text-[11px] text-gray-400">No past conversations.</p>
            ) : (
              history.map(h => (
                <button
                  key={h.id}
                  onClick={() => { onOpenConversation?.(h.id); setShowHistory(false); }}
                  className={`w-full text-left px-3 py-1.5 text-[11px] truncate hover:bg-purple-50 ${
                    h.id === activeConversationId ? 'text-purple-700 font-semibold bg-purple-50' : 'text-gray-600'
                  }`}
                  title={h.title || 'Untitled'}
                >
                  {h.title || 'Untitled'}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 flex flex-col gap-4">
        {turns.map((turn) => (
          <div key={turn.id} className="flex flex-col gap-3">
            <UserBubble text={turn.query} />
            {/* Answer text arrives live via SSE now, so the client-side typewriter
                is disabled — animating on top would fight the streaming updates. */}
            {turn.write ? (
              <WriteCard turn={turn} onConfirm={() => onConfirmWrite?.(turn.id)} onCancel={() => onCancelWrite?.(turn.id)} />
            ) : (
              <AssistantTurn turn={turn} animate={false} />
            )}
          </div>
        ))}

        {loading && pendingQuery && (
          <div className="flex flex-col gap-3">
            <UserBubble text={pendingQuery} />
            <SearchProgress />
          </div>
        )}
      </div>

      {/* Input — mirrors the main AppHome query box: suggestion chips on top, a
          textarea, then a control row with the perimeter selector and send. */}
      <div className="border-t border-gray-200 p-3 flex-shrink-0 bg-white">
        <SuggestionChips
          questions={questions}
          loading={insightsLoading}
          onPick={onSubmit}
          onShowDiagram={onShowDiagram}
          compact
        />
        <div className="rounded-xl border border-gray-200 bg-gray-50 focus-within:ring-2 focus-within:ring-purple-200 focus-within:border-purple-400 transition-all">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(); } }}
            placeholder="Ask a follow-up…"
            rows={2}
            className="w-full bg-transparent resize-none text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none px-3 pt-2.5 max-h-40"
          />
          <div className="flex items-center justify-between gap-2 px-2 pb-2">
            <ScopeSelector connectors={connectors} value={scope} onChange={onScopeChange} compact />
            <button
              onClick={submit}
              disabled={!input.trim() || loading}
              className="flex-shrink-0 rounded-lg p-1.5 bg-gradient-to-br from-blue-600 to-purple-600 text-white disabled:opacity-40 disabled:cursor-not-allowed hover:shadow-md active:scale-90 transition-all"
              aria-label="Send"
            >
              {loading ? (
                <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                  <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" className="opacity-75" />
                </svg>
              ) : (
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DbChatPanel;
