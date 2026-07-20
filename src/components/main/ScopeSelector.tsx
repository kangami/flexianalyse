import React, { useEffect, useRef, useState } from 'react';
import { getDbEngine, DbEngineLogo } from '../../lib/dbEngines';

/**
 * Search-perimeter selector: pick a single database connector to search, or
 * "All context" (every connector). Replaces the old model dropdown. Shared by
 * the AppHome query form and the DbChatPanel follow-up input.
 */

export interface ScopeConnector {
  id: string;
  name: string;
  engine?: string | null;
  type: string;
}

interface ScopeSelectorProps {
  connectors: ScopeConnector[];
  value: string | null;               // null = All context, else connector id
  onChange: (id: string | null) => void;
  compact?: boolean;
}

const ScopeSelector: React.FC<ScopeSelectorProps> = ({ connectors, value, onChange, compact }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const selected = value ? connectors.find(c => c.id === value) : null;
  const selectedEngine = selected?.engine ? getDbEngine(selected.engine) : undefined;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        className={`flex items-center gap-1.5 rounded-md border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 transition-colors ${compact ? 'px-2 py-1 text-[11px]' : 'px-2.5 py-1.5 text-xs'}`}
        title="Search perimeter"
      >
        {selectedEngine ? (
          <DbEngineLogo engine={selectedEngine.id} size={compact ? 13 : 14} className="flex-shrink-0" />
        ) : (
          <svg className={compact ? 'w-3 h-3' : 'w-3.5 h-3.5'} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        )}
        <span className="font-medium truncate max-w-[140px]">{selected ? selected.name : 'All context'}</span>
        <svg className={`${compact ? 'w-3 h-3' : 'w-3.5 h-3.5'} text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute bottom-full mb-1 left-0 z-30 min-w-[220px] max-h-64 overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg py-1">
          <button
            type="button"
            onClick={() => { onChange(null); setOpen(false); }}
            className={`w-full flex items-center gap-2 px-3 py-1.5 text-xs text-left hover:bg-gray-50 ${value === null ? 'text-purple-600 font-medium' : 'text-gray-700'}`}
          >
            <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            All context
            {value === null && <span className="ml-auto text-purple-600">✓</span>}
          </button>

          {connectors.length > 0 && <div className="my-1 border-t border-gray-100" />}

          {connectors.map(c => {
            const engine = c.engine ? getDbEngine(c.engine) : undefined;
            const active = value === c.id;
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => { onChange(c.id); setOpen(false); }}
                className={`w-full flex items-center gap-2 px-3 py-1.5 text-xs text-left hover:bg-gray-50 ${active ? 'text-purple-600 font-medium' : 'text-gray-700'}`}
              >
                {engine ? <DbEngineLogo engine={engine.id} size={14} className="flex-shrink-0" /> : <span className="w-3.5" />}
                <span className="truncate">{c.name}</span>
                {active && <span className="ml-auto text-purple-600">✓</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ScopeSelector;
