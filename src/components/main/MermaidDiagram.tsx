import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

/**
 * Renders a Mermaid diagram (the database ER schema) to SVG, with zoom + pan.
 * Mermaid is loaded lazily (dynamic import) so it stays out of the main bundle.
 *
 * Mermaid emits a "responsive" SVG (max-width + 100% width) that shrinks to fit
 * its container — which makes large schemas unreadably small. We force the SVG
 * to its intrinsic pixel size (from viewBox) so zoom is absolute (scale 1 = 1:1,
 * readable) and fit-to-view the whole diagram on load.
 */

interface MermaidDiagramProps {
  chart: string;
}

const MIN_SCALE = 0.1;
const MAX_SCALE = 6;
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

let _seq = 0;

const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ chart }) => {
  const { theme } = useTheme();
  const [svg, setSvg] = useState('');
  const [dims, setDims] = useState<{ w: number; h: number } | null>(null);
  const [error, setError] = useState('');
  const [scale, setScale] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const idRef = useRef(`mermaid-${++_seq}`);
  const containerRef = useRef<HTMLDivElement>(null);
  const svgHostRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ sx: number; sy: number; ox: number; oy: number } | null>(null);

  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');

  // Parse the Mermaid ER source → the table list (for autocomplete) and the
  // adjacency graph (for highlighting a table + its direct relations).
  const graph = useMemo(() => {
    const entities = new Set<string>();
    const neighbors = new Map<string, Set<string>>();
    const link = (a: string, b: string) => {
      if (!neighbors.has(a)) neighbors.set(a, new Set());
      neighbors.get(a)!.add(b);
    };
    for (const raw of (chart || '').split('\n')) {
      const line = raw.trim();
      const ent = line.match(/^([A-Za-z_]\w*)\s*\{/);
      if (ent) { entities.add(ent[1]); continue; }
      const rel = line.match(/^([A-Za-z_]\w*)\s+[|}{o<>x.\-]+\s+([A-Za-z_]\w*)\s*:/);
      if (rel) { entities.add(rel[1]); entities.add(rel[2]); link(rel[1], rel[2]); link(rel[2], rel[1]); }
    }
    return { entities: Array.from(entities).sort(), neighbors };
  }, [chart]);

  // Render the chart → SVG, forced to intrinsic pixel size.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!chart?.trim()) { setSvg(''); setDims(null); setError(''); return; }
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
        const res = await mod.default.render(idRef.current, chart);
        if (cancelled) return;

        let out = res.svg;
        let w = 0, h = 0;
        const vb = out.match(/viewBox="[\d.\-]+ [\d.\-]+ ([\d.]+) ([\d.]+)"/);
        if (vb) {
          w = parseFloat(vb[1]); h = parseFloat(vb[2]);
          const styleAttr = `style="max-width:none;width:${w}px;height:${h}px;"`;
          out = /<svg[^>]*\sstyle="/.test(out)
            ? out.replace(/(<svg[^>]*?)\sstyle="[^"]*"/, `$1 ${styleAttr}`)
            : out.replace(/<svg /, `<svg ${styleAttr} `);
        }
        setSvg(out);
        setDims(w && h ? { w, h } : null);
        setError('');
      } catch (e) {
        if (!cancelled) setError((e as Error).message || 'Failed to render diagram');
      }
    })();
    return () => { cancelled = true; };
  }, [chart, theme]);

  // Fit the whole diagram into the view once it's rendered.
  useEffect(() => {
    if (!dims || !containerRef.current) return;
    const { width: cw, height: ch } = containerRef.current.getBoundingClientRect();
    if (!cw || !ch) return;
    const fit = clamp(Math.min((cw - 24) / dims.w, (ch - 24) / dims.h), MIN_SCALE, 1.5);
    setScale(fit);
    setPos({ x: Math.max(12, (cw - dims.w * fit) / 2), y: 12 });
  }, [dims]);

  // Wheel zoom around the cursor (native non-passive listener for preventDefault).
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const cx = e.clientX - rect.left;
      const cy = e.clientY - rect.top;
      setScale((prev) => {
        const next = clamp(prev * (e.deltaY < 0 ? 1.15 : 0.87), MIN_SCALE, MAX_SCALE);
        setPos((p) => ({ x: cx - (cx - p.x) * (next / prev), y: cy - (cy - p.y) * (next / prev) }));
        return next;
      });
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [svg]);

  const onMouseDown = (e: React.MouseEvent) => { dragRef.current = { sx: e.clientX, sy: e.clientY, ox: pos.x, oy: pos.y }; };
  const onMouseMove = useCallback((e: React.MouseEvent) => {
    const d = dragRef.current;
    if (!d) return;
    setPos({ x: d.ox + (e.clientX - d.sx), y: d.oy + (e.clientY - d.sy) });
  }, []);
  const endDrag = () => { dragRef.current = null; };

  const zoomBy = (f: number) => setScale((s) => clamp(s * f, MIN_SCALE, MAX_SCALE));
  const fitView = () => {
    if (!dims || !containerRef.current) { setScale(1); setPos({ x: 0, y: 0 }); return; }
    const { width: cw, height: ch } = containerRef.current.getBoundingClientRect();
    const fit = clamp(Math.min((cw - 24) / dims.w, (ch - 24) / dims.h), MIN_SCALE, 1.5);
    setScale(fit);
    setPos({ x: Math.max(12, (cw - dims.w * fit) / 2), y: 12 });
  };

  // ── Table search + highlight ──────────────────────────────────────────────
  // Map each entity name → its SVG group (found by its title text). Mermaid
  // renders each entity as a <g> containing a <text> label; we match by name.
  const entityGroups = useCallback((): Map<string, Element> => {
    const map = new Map<string, Element>();
    const host = svgHostRef.current;
    if (!host) return map;
    host.querySelectorAll('text').forEach((t) => {
      const name = (t.textContent || '').trim();
      if (!map.has(name) && graph.neighbors.has(name)) {
        const g = t.closest('g');
        if (g) map.set(name, g);
      }
      // entities with no relations aren't in `neighbors`; still allow a match
      if (!map.has(name) && graph.entities.includes(name)) {
        const g = t.closest('g');
        if (g) map.set(name, g);
      }
    });
    return map;
  }, [graph]);

  const clearHighlight = useCallback(() => {
    const host = svgHostRef.current;
    if (!host) return;
    host.querySelectorAll<HTMLElement>('[data-er-dim]').forEach((el) => {
      el.style.opacity = '';
      el.removeAttribute('data-er-dim');
    });
    host.querySelectorAll<SVGElement>('[data-er-hl]').forEach((el) => {
      el.style.filter = '';
      el.removeAttribute('data-er-hl');
    });
  }, []);

  const focusTable = useCallback((name: string) => {
    const host = svgHostRef.current;
    const cont = containerRef.current;
    if (!host || !cont) return;
    clearHighlight();
    const keep = new Set<string>([name, ...(graph.neighbors.get(name) || [])]);
    const groups = entityGroups();

    // Dim entities not in the highlight set…
    groups.forEach((g, n) => {
      if (!keep.has(n)) {
        (g as HTMLElement).style.opacity = '0.18';
        g.setAttribute('data-er-dim', '1');
      }
    });
    // …and dim all relationship edges (paths).
    host.querySelectorAll<SVGElement>('path').forEach((p) => {
      p.style.opacity = '0.12';
      p.setAttribute('data-er-dim', '1');
    });

    // Emphasize the searched table + recenter on it.
    const primary = groups.get(name);
    if (primary) {
      (primary as SVGElement).style.filter = 'drop-shadow(0 0 4px rgba(147,51,234,0.95))';
      primary.setAttribute('data-er-hl', '1');
      const label = Array.from(primary.querySelectorAll('text'))
        .find((t) => (t.textContent || '').trim() === name) || primary.querySelector('text');
      const lr = (label as Element | null)?.getBoundingClientRect();
      const cr = cont.getBoundingClientRect();
      if (lr && lr.width) {
        const dx = (cr.left + cr.width / 2) - (lr.left + lr.width / 2);
        const dy = (cr.top + cr.height / 2) - (lr.top + lr.height / 2);
        setPos((p) => ({ x: p.x + dx, y: p.y + dy }));
      }
    }
  }, [graph, clearHighlight, entityGroups]);

  // A new diagram (chart/theme change) resets the search.
  useEffect(() => { setQuery(''); setSearchOpen(false); }, [svg]);

  const onSearchChange = (v: string) => {
    setQuery(v);
    if (graph.entities.includes(v)) focusTable(v);
    else clearHighlight();
  };

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
      <div className="absolute top-2 right-2 z-10 flex flex-col rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
        <button onClick={() => zoomBy(1.25)} className="w-7 h-7 flex items-center justify-center text-gray-600 hover:bg-gray-100 border-b border-gray-100" title="Zoom in">+</button>
        <button onClick={() => zoomBy(0.8)} className="w-7 h-7 flex items-center justify-center text-gray-600 hover:bg-gray-100 border-b border-gray-100" title="Zoom out">−</button>
        <button onClick={fitView} className="w-7 h-7 flex items-center justify-center text-gray-500 hover:bg-gray-100 border-b border-gray-100" title="Fit to view">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 8V4h4M20 8V4h-4M4 16v4h4M20 16v4h-4" />
          </svg>
        </button>
        <button
          onClick={() => setSearchOpen((o) => { const n = !o; if (!n) { setQuery(''); clearHighlight(); } return n; })}
          className={`w-7 h-7 flex items-center justify-center hover:bg-gray-100 ${searchOpen ? 'text-purple-600 bg-purple-50' : 'text-gray-500'}`}
          title="Rechercher une table"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
          </svg>
        </button>
      </div>

      {/* Table search — autocompletes on the parsed table list, highlights the
          table + its direct relations and recenters on it. */}
      {searchOpen && (
        <div className="absolute top-2 right-11 z-10 flex items-center rounded-lg border border-gray-200 bg-white shadow-sm">
          <input
            list="er-table-list"
            value={query}
            autoFocus
            onChange={(e) => onSearchChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') { setQuery(''); clearHighlight(); setSearchOpen(false); }
              if (e.key === 'Enter' && graph.entities.includes(query)) focusTable(query);
            }}
            placeholder="Rechercher une table…"
            className="w-48 text-xs px-2.5 py-1.5 rounded-lg focus:outline-none bg-transparent text-gray-700 placeholder:text-gray-400"
          />
          <datalist id="er-table-list">
            {graph.entities.map((n) => <option key={n} value={n} />)}
          </datalist>
          {query && (
            <button
              onClick={() => { setQuery(''); clearHighlight(); }}
              className="w-6 h-6 mr-1 flex items-center justify-center text-gray-400 hover:text-gray-600"
              title="Effacer"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      )}

      <div
        ref={containerRef}
        className="w-full h-full cursor-grab active:cursor-grabbing select-none"
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={endDrag}
        onMouseLeave={endDrag}
      >
        <div
          ref={svgHostRef}
          className="inline-block"
          style={{ transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})`, transformOrigin: '0 0' }}
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
