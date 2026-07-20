import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

/**
 * Renders a Mermaid diagram (the database ER schema) to SVG, with zoom + pan.
 * Mermaid is loaded lazily (dynamic import) so it stays out of the main bundle
 * until the user actually opens the diagram.
 */

interface MermaidDiagramProps {
  chart: string;
}

const MIN_SCALE = 0.3;
const MAX_SCALE = 4;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

let _seq = 0;

const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ chart }) => {
  const { theme } = useTheme();
  const [svg, setSvg] = useState('');
  const [error, setError] = useState('');
  const [scale, setScale] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const idRef = useRef(`mermaid-${++_seq}`);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ sx: number; sy: number; ox: number; oy: number } | null>(null);

  // Render the chart to SVG (and reset the view when the chart changes).
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!chart?.trim()) { setSvg(''); setError(''); return; }
      try {
        const mod = await import('mermaid') as unknown as {
          default: {
            initialize: (o: Record<string, unknown>) => void;
            render: (id: string, text: string) => Promise<{ svg: string }>;
          };
        };
        mod.default.initialize({
          startOnLoad: false,
          theme: theme === 'white' ? 'neutral' : 'dark',
          securityLevel: 'strict',
        });
        const { svg } = await mod.default.render(idRef.current, chart);
        if (!cancelled) { setSvg(svg); setError(''); setScale(1); setPos({ x: 0, y: 0 }); }
      } catch (e) {
        if (!cancelled) setError((e as Error).message || 'Failed to render diagram');
      }
    })();
    return () => { cancelled = true; };
  }, [chart, theme]);

  // Wheel zoom around the cursor. Native non-passive listener so preventDefault works.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      setScale((prev) => {
        const next = clamp(prev * (e.deltaY < 0 ? 1.12 : 0.89), MIN_SCALE, MAX_SCALE);
        // Keep the point under the cursor stable while zooming.
        setPos((p) => ({
          x: cx - (cx - p.x) * (next / prev),
          y: cy - (cy - p.y) * (next / prev),
        }));
        return next;
      });
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [svg]);

  const onMouseDown = (e: React.MouseEvent) => {
    dragRef.current = { sx: e.clientX, sy: e.clientY, ox: pos.x, oy: pos.y };
  };
  const onMouseMove = useCallback((e: React.MouseEvent) => {
    const d = dragRef.current;
    if (!d) return;
    setPos({ x: d.ox + (e.clientX - d.sx), y: d.oy + (e.clientY - d.sy) });
  }, []);
  const endDrag = () => { dragRef.current = null; };

  const zoomBy = (f: number) => setScale((s) => clamp(s * f, MIN_SCALE, MAX_SCALE));
  const reset = () => { setScale(1); setPos({ x: 0, y: 0 }); };

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
    <div className="relative w-full h-full overflow-hidden bg-white">
      {/* Zoom controls */}
      <div className="absolute top-2 right-2 z-10 flex flex-col rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
        <button onClick={() => zoomBy(1.2)} className="w-7 h-7 flex items-center justify-center text-gray-600 hover:bg-gray-100 border-b border-gray-100" title="Zoom in">+</button>
        <button onClick={() => zoomBy(0.83)} className="w-7 h-7 flex items-center justify-center text-gray-600 hover:bg-gray-100 border-b border-gray-100" title="Zoom out">−</button>
        <button onClick={reset} className="w-7 h-7 flex items-center justify-center text-gray-500 hover:bg-gray-100" title="Reset view">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Pannable / zoomable canvas */}
      <div
        ref={containerRef}
        className="w-full h-full cursor-grab active:cursor-grabbing select-none"
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={endDrag}
        onMouseLeave={endDrag}
      >
        <div
          className="origin-top-left [&_svg]:max-w-none"
          style={{ transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})`, transformOrigin: '0 0', width: 'max-content' }}
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      </div>

      <div className="absolute bottom-2 left-2 text-[10px] text-gray-400 bg-white/70 rounded px-1.5 py-0.5 pointer-events-none">
        Scroll to zoom · drag to pan
      </div>
    </div>
  );
};

export default MermaidDiagram;
