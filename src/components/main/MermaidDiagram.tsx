import React, { useEffect, useRef, useState } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

/**
 * Renders a Mermaid diagram (here, the database ER schema) to SVG.
 * Mermaid is loaded lazily (dynamic import) so it stays out of the main bundle
 * until the user actually opens the diagram.
 */

interface MermaidDiagramProps {
  chart: string;
}

let _seq = 0;

const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ chart }) => {
  const { theme } = useTheme();
  const [svg, setSvg] = useState('');
  const [error, setError] = useState('');
  const idRef = useRef(`mermaid-${++_seq}`);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!chart?.trim()) { setSvg(''); setError(''); return; }
      try {
        // Typed inline so we don't depend on mermaid's shipped .d.ts resolving.
        const mod = await import('mermaid') as unknown as {
          default: {
            initialize: (o: Record<string, unknown>) => void;
            render: (id: string, text: string) => Promise<{ svg: string }>;
          };
        };
        const mermaid = mod.default;
        mermaid.initialize({
          startOnLoad: false,
          theme: theme === 'white' ? 'neutral' : 'dark',
          securityLevel: 'strict',
        });
        const { svg } = await mermaid.render(idRef.current, chart);
        if (!cancelled) { setSvg(svg); setError(''); }
      } catch (e) {
        if (!cancelled) setError((e as Error).message || 'Failed to render diagram');
      }
    })();
    return () => { cancelled = true; };
  }, [chart, theme]);

  if (error) {
    return <div className="p-4 text-xs text-red-500">Diagram error: {error}</div>;
  }
  if (!svg) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400 text-xs gap-2">
        <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
          <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" className="opacity-75" />
        </svg>
        Rendering diagram…
      </div>
    );
  }
  return (
    <div
      className="mermaid-diagram w-full h-full overflow-auto p-4 [&_svg]:max-w-none"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

export default MermaidDiagram;
