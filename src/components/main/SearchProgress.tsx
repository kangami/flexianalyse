import React, { useEffect, useState } from 'react';

/**
 * Expressive loading indicator for a search. The backend runs a multi-step agent
 * (understand → retrieve → generate SQL → run → compose), which takes a few
 * seconds; this steps through those phases so the user sees what's happening.
 *
 * The steps are client-paced (the endpoint returns a single response, no live
 * progress), so it advances on a timer and holds on the last phase until the
 * request actually finishes and the parent unmounts it.
 */

const PHASES = [
  'Understanding your question',
  'Reading the database schema',
  'Generating the SQL query',
  'Running the live query',
  'Composing the answer',
];

const SearchProgress: React.FC = () => {
  const [i, setI] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setI((prev) => Math.min(prev + 1, PHASES.length - 1)), 1700);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex flex-col gap-2 px-1">
      <div className="flex items-center gap-2 text-sm text-gray-600">
        <svg className="animate-spin h-4 w-4 text-purple-500 flex-shrink-0" fill="none" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
          <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" className="opacity-75" />
        </svg>
        <span className="transition-opacity">{PHASES[i]}…</span>
      </div>
      <div className="flex gap-1 pl-6">
        {PHASES.map((_, k) => (
          <span
            key={k}
            className={`h-1 rounded-full transition-all duration-300 ${k < i ? 'bg-purple-400 w-4' : k === i ? 'bg-purple-500 w-6 animate-pulse' : 'bg-gray-200 w-3'}`}
          />
        ))}
      </div>
    </div>
  );
};

export default SearchProgress;
