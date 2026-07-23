import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ReactFlow, ReactFlowProvider, Background, Controls, MiniMap,
  Handle, Position, useReactFlow, BaseEdge, EdgeLabelRenderer, getSmoothStepPath,
  type Node, type Edge, type NodeProps, type EdgeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from '@dagrejs/dagre';
import { useTheme } from '../../contexts/ThemeContext';

/**
 * Interactive ER diagram on React Flow. Unlike Mermaid (one giant static SVG that
 * re-rasterizes on every pan), React Flow renders nodes as components and only
 * mounts those in the viewport (`onlyRenderVisibleElements`) — so a 500-table
 * schema stays smooth to drag. Tables render collapsed (name + column/row counts);
 * the full column list is fetched on click via the existing detail panel.
 */

export interface DiagramTable {
  name: string;
  columns: string[];
  pk: string[];
  row_estimate: number | null;
  fks: string[];            // referred table names
}

interface SchemaFlowProps {
  tables: DiagramTable[];
  onTableSelect?: (name: string) => void;
}

const NODE_W = 190;
const NODE_H = 56;

type TableData = {
  label: string;
  cols: number;
  rows: number | null;
  hasPk: boolean;
  junction: boolean;                 // link table → its two parents are many-to-many
  state: 'normal' | 'focus' | 'dim';
};

function TableNode({ data }: NodeProps<Node<TableData>>) {
  const base =
    'rounded-lg border px-3 py-2 shadow-sm transition-opacity select-none cursor-pointer';
  const tone =
    data.state === 'focus'
      ? 'border-purple-500 ring-2 ring-purple-400/60 bg-white'
      : 'border-gray-200 bg-white hover:border-purple-300';
  const dim = data.state === 'dim' ? 'opacity-25' : 'opacity-100';
  return (
    <div className={`${base} ${tone} ${dim}`} style={{ width: NODE_W, height: NODE_H }} title={data.label}>
      <Handle type="target" position={Position.Left} className="!bg-purple-400 !w-1.5 !h-1.5" />
      <div className="flex items-center gap-1.5 min-w-0">
        <i className="bi bi-table text-[11px] text-purple-500 flex-shrink-0" />
        <span className="text-xs font-semibold text-gray-800 truncate">{data.label}</span>
        {data.junction
          ? <span className="text-[8px] font-bold text-indigo-600 bg-indigo-50 rounded px-1 flex-shrink-0" title="Table de jonction (relation N:N)">N:N</span>
          : data.hasPk && <span className="text-[8px] font-bold text-amber-600 flex-shrink-0">PK</span>}
      </div>
      <div className="mt-0.5 text-[9px] text-gray-400 tabular-nums">
        {data.cols} col{data.cols === 1 ? '' : 's'}
        {data.rows != null && <> · ~{data.rows.toLocaleString()} lignes</>}
      </div>
      <Handle type="source" position={Position.Right} className="!bg-purple-400 !w-1.5 !h-1.5" />
    </div>
  );
}

const nodeTypes = { table: TableNode };

/**
 * FK edge with crow's-foot cardinality: an "N" badge on the child (FK) end and a
 * "1" on the parent (PK) end, so every link reads as one-to-many / many-to-one at
 * a glance. Two such edges into an N:N-badged junction table = many-to-many.
 */
function RelEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style, data }: EdgeProps) {
  const [path] = getSmoothStepPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, borderRadius: 8 });
  const on = !!(data as { on?: boolean } | undefined)?.on;
  // Nudge badges just inside each endpoint so they don't sit under the nodes.
  const nx = sourceX + (targetX - sourceX) * 0.14, ny = sourceY + (targetY - sourceY) * 0.14;
  const ox = sourceX + (targetX - sourceX) * 0.86, oy = sourceY + (targetY - sourceY) * 0.86;
  const chip = (txt: string, x: number, y: number) => (
    <div
      className={`nodrag nopan ${on ? 'text-purple-700 bg-purple-100' : 'text-gray-500 bg-white'} border border-gray-200 rounded-full`}
      style={{
        position: 'absolute', transform: `translate(-50%,-50%) translate(${x}px,${y}px)`,
        fontSize: 8, fontWeight: 700, lineHeight: 1, padding: '1px 4px', pointerEvents: 'none',
      }}
    >{txt}</div>
  );
  return (
    <>
      <BaseEdge id={id} path={path} style={style} />
      <EdgeLabelRenderer>
        {chip('N', nx, ny)}
        {chip('1', ox, oy)}
      </EdgeLabelRenderer>
    </>
  );
}

const edgeTypes = { rel: RelEdge };

/** A pure link table (its rows exist only to connect two others) → many-to-many. */
function isJunction(t: DiagramTable): boolean {
  return t.fks.length >= 2 && t.columns.length <= t.fks.length + 2;
}

/** Dagre left-to-right layout → node positions + edges (deduped, present-only). */
function buildGraph(tables: DiagramTable[]): { nodes: Node<TableData>[]; edges: Edge[] } {
  const present = new Set(tables.map((t) => t.name));
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'LR', nodesep: 24, ranksep: 90, marginx: 20, marginy: 20 });
  g.setDefaultEdgeLabel(() => ({}));
  tables.forEach((t) => g.setNode(t.name, { width: NODE_W, height: NODE_H }));

  const edges: Edge[] = [];
  const seen = new Set<string>();
  tables.forEach((t) =>
    t.fks.forEach((ref) => {
      if (!present.has(ref) || ref === t.name) return;
      const id = `${t.name}__${ref}`;
      if (seen.has(id)) return;
      seen.add(id);
      g.setEdge(t.name, ref);
      edges.push({
        id, source: t.name, target: ref,
        type: 'rel', animated: false,
        data: { on: false },
        style: { stroke: '#c4b5fd', strokeWidth: 1.5 },
      });
    })
  );

  dagre.layout(g);
  const nodes: Node<TableData>[] = tables.map((t) => {
    const p = g.node(t.name);
    return {
      id: t.name,
      type: 'table',
      position: { x: (p?.x ?? 0) - NODE_W / 2, y: (p?.y ?? 0) - NODE_H / 2 },
      data: {
        label: t.name,
        cols: t.columns.length,
        rows: t.row_estimate ?? null,
        hasPk: t.pk.length > 0,
        junction: isJunction(t),
        state: 'normal',
      },
      width: NODE_W,
      height: NODE_H,
    };
  });
  return { nodes, edges };
}

function Flow({ tables, onTableSelect }: SchemaFlowProps) {
  const { theme } = useTheme();
  const dark = theme !== 'white';
  const { fitView } = useReactFlow();

  const { nodes: baseNodes, edges: baseEdges } = useMemo(() => buildGraph(tables), [tables]);

  // Adjacency (both directions) for "highlight a table + its direct relations".
  const neighbors = useMemo(() => {
    const m = new Map<string, Set<string>>();
    const link = (a: string, b: string) => {
      if (!m.has(a)) m.set(a, new Set());
      m.get(a)!.add(b);
    };
    baseEdges.forEach((e) => { link(e.source, e.target); link(e.target, e.source); });
    return m;
  }, [baseEdges]);

  const [query, setQuery] = useState('');
  const [focused, setFocused] = useState<string | null>(null);

  // The active focus set = the focused/searched table(s) + their neighbours.
  const focusSet = useMemo(() => {
    const q = query.trim().toLowerCase();
    const seeds = new Set<string>();
    if (focused) seeds.add(focused);
    if (q) baseNodes.forEach((n) => { if (n.id.toLowerCase().includes(q)) seeds.add(n.id); });
    if (!seeds.size) return null;
    const set = new Set(seeds);
    seeds.forEach((s) => neighbors.get(s)?.forEach((n) => set.add(n)));
    return { seeds, set };
  }, [query, focused, baseNodes, neighbors]);

  const nodes = useMemo(() => {
    if (!focusSet) return baseNodes;
    return baseNodes.map((n) => ({
      ...n,
      data: {
        ...n.data,
        state: focusSet.seeds.has(n.id) ? 'focus' : focusSet.set.has(n.id) ? 'normal' : 'dim',
      } as TableData,
    }));
  }, [baseNodes, focusSet]);

  const edges = useMemo(() => {
    if (!focusSet) return baseEdges;
    return baseEdges.map((e) => {
      const on = focusSet.set.has(e.source) && focusSet.set.has(e.target);
      return {
        ...e,
        data: { on },
        style: { stroke: on ? '#8b5cf6' : '#e5e7eb', strokeWidth: on ? 2 : 1 },
        animated: on && (focusSet.seeds.has(e.source) || focusSet.seeds.has(e.target)),
      };
    });
  }, [baseEdges, focusSet]);

  // Recenter on the focus set whenever it changes.
  useEffect(() => {
    if (!focusSet) return;
    const ids = [...focusSet.seeds];
    const t = setTimeout(() => fitView({ nodes: ids.map((id) => ({ id })), duration: 400, padding: 0.35 }), 30);
    return () => clearTimeout(t);
  }, [focusSet, fitView]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setFocused(node.id);
      onTableSelect?.(node.id);
    },
    [onTableSelect]
  );

  return (
    <div className="w-full h-full relative">
      {/* Search box */}
      <div className="absolute top-2 left-2 z-10 flex items-center gap-1 bg-white/95 border border-gray-200 rounded-lg shadow-sm px-2 py-1">
        <i className="bi bi-search text-[11px] text-gray-400" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Rechercher une table…"
          className="w-40 text-xs bg-transparent focus:outline-none text-gray-700 placeholder:text-gray-400"
        />
        {(query || focused) && (
          <button
            onClick={() => { setQuery(''); setFocused(null); fitView({ duration: 400, padding: 0.2 }); }}
            className="text-gray-400 hover:text-gray-600"
            title="Réinitialiser"
          >
            <i className="bi bi-x text-sm" />
          </button>
        )}
      </div>

      {/* Cardinality legend */}
      <div className="absolute bottom-2 left-2 z-10 bg-white/95 border border-gray-200 rounded-lg shadow-sm px-2.5 py-1.5 text-[9px] text-gray-500 leading-relaxed pointer-events-none">
        <div className="flex items-center gap-1.5">
          <span className="font-bold text-gray-600">1</span>—<span className="font-bold text-gray-600">N</span>
          <span>relation clé étrangère (un → plusieurs)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="font-bold text-indigo-600 bg-indigo-50 rounded px-1">N:N</span>
          <span>table de jonction (plusieurs ↔ plusieurs)</span>
        </div>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodeClick={onNodeClick}
        onPaneClick={() => setFocused(null)}
        onlyRenderVisibleElements
        fitView
        minZoom={0.05}
        maxZoom={2.5}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable
      >
        <Background color={dark ? '#334155' : '#e5e7eb'} gap={20} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable nodeStrokeWidth={2} nodeColor={() => '#c4b5fd'} />
      </ReactFlow>
    </div>
  );
}

const SchemaFlow: React.FC<SchemaFlowProps> = (props) => (
  <ReactFlowProvider>
    <Flow {...props} />
  </ReactFlowProvider>
);

export default SchemaFlow;
