"""In-memory foreign-key graph of a connector's schema.

The schema catalog already stores each table's foreign keys, which *is* a graph
(nodes = tables, edges = FKs). We use it to:
  - give the SQL generator the exact join path between the tables a question needs
    (so it can't shortcut with a fabricated FK like messages.user_id), and
  - re-teach the model the real columns / join path when a query references a
    column or relation that doesn't exist.

Exact and cheap: rebuilt in memory from the catalog, no LLM, no extra crawl.
"""
from collections import defaultdict, deque


class SchemaGraph:
    def __init__(self, tables):
        # tables: [{name, columns:[{name,type,pk}], foreign_keys:[{columns, referred_table, referred_columns}]}]
        self._cols: dict[str, list] = {}
        self._fks: dict[str, list] = {}
        self._adj: dict[str, list] = defaultdict(list)

        for t in tables:
            name = t.get("name")
            if not name:
                continue
            self._cols[name] = t.get("columns", []) or []
            self._fks[name] = [fk for fk in (t.get("foreign_keys", []) or []) if fk.get("referred_table")]

        present = set(self._cols)
        for child, fks in self._fks.items():
            for fk in fks:
                parent = fk.get("referred_table")
                if parent not in present:
                    continue
                pairs = list(zip(fk.get("columns", []) or [], fk.get("referred_columns", []) or []))
                if not pairs:
                    continue
                self._adj[child].append((parent, pairs))
                self._adj[parent].append((child, [(p, c) for c, p in pairs]))

    # ── lookups ──────────────────────────────────────────────────────────────
    def tables(self) -> list:
        return list(self._cols)

    def has_table(self, name: str) -> bool:
        return name in self._cols

    def has_column(self, table: str, col: str) -> bool:
        return any(c.get("name") == col for c in self._cols.get(table, []))

    def table_line(self, name: str) -> str:
        """Render one table as `name(col type, ...) [FK: col -> other(col)]`."""
        cols = ", ".join(f"{c['name']} {c.get('type', '')}".strip() for c in self._cols.get(name, []))
        line = f"{name}({cols})"
        fk_str = "; ".join(
            f"{','.join(fk.get('columns', []))} -> {fk['referred_table']}({','.join(fk.get('referred_columns', []))})"
            for fk in self._fks.get(name, [])
        )
        if fk_str:
            line += f"  [FK: {fk_str}]"
        return line

    # ── paths ────────────────────────────────────────────────────────────────
    def shortest_path(self, a: str, b: str):
        """Ordered edges [(u, v, [(u_col, v_col), ...]), ...] from a to b, or None."""
        if a not in self._cols or b not in self._cols:
            return None
        if a == b:
            return []
        prev = {a: None}
        q = deque([a])
        while q:
            u = q.popleft()
            for v, pairs in self._adj.get(u, []):
                if v in prev:
                    continue
                prev[v] = (u, pairs)
                if v == b:
                    edges = []
                    cur = b
                    while prev[cur] is not None:
                        pu, ppairs = prev[cur]
                        edges.append((pu, cur, ppairs))
                        cur = pu
                    edges.reverse()
                    return edges
                q.append(v)
        return None

    def connect(self, targets: list):
        """Union of shortest paths connecting the target tables (anchored on the
        first one). Returns (edges, tables_on_paths)."""
        known = [t for t in targets if t in self._cols]
        if len(known) < 2:
            return [], set(known)
        anchor = known[0]
        seen, edges, on = set(), [], set(known)
        for t in known[1:]:
            path = self.shortest_path(anchor, t)
            if not path:
                continue
            for (u, v, pairs) in path:
                key = tuple(sorted((u, v)))
                if key in seen:
                    continue
                seen.add(key)
                edges.append((u, v, pairs))
                on.update((u, v))
        return edges, on

    def render_join_path(self, targets: list):
        """Return (join_conditions_text, tables_on_paths) for the target tables."""
        edges, on = self.connect(targets)
        conds = [f"{u}.{uc} = {v}.{vc}" for (u, v, pairs) in edges for (uc, vc) in pairs]
        return "; ".join(conds), on

    # ── structural analysis (for the database report) ────────────────────────
    def referenced_by(self) -> dict:
        """table -> number of DISTINCT other tables whose FK points at it (in-degree).
        This is the "referenced by N tables" of the critical-tables ranking."""
        counts = {name: set() for name in self._cols}
        for child, fks in self._fks.items():
            for fk in fks:
                parent = fk.get("referred_table")
                if parent in counts and parent != child:
                    counts[parent].add(child)
        return {name: len(refs) for name, refs in counts.items()}

    def fk_out_count(self) -> dict:
        """table -> number of foreign keys it declares (out-degree)."""
        return {name: len(fks) for name, fks in self._fks.items()}

    def orphans(self) -> list:
        """Tables with no foreign key in or out (isolated in the graph)."""
        connected = set(self._adj)
        return [t for t in self._cols if t not in connected]

    def junctions(self) -> list:
        """Pure link tables: >=2 FKs and few other columns → many-to-many bridges."""
        out = []
        for name, fks in self._fks.items():
            ncols = len(self._cols.get(name, []))
            if len(fks) >= 2 and ncols <= len(fks) + 2:
                out.append(name)
        return out

    def components(self) -> list:
        """Connected components (undirected) → rough business domains. Returns a list
        of table-name lists, largest first."""
        seen, comps = set(), []
        for start in self._cols:
            if start in seen:
                continue
            comp, q = [], deque([start])
            seen.add(start)
            while q:
                u = q.popleft()
                comp.append(u)
                for v, _ in self._adj.get(u, []):
                    if v not in seen:
                        seen.add(v)
                        q.append(v)
            comps.append(comp)
        comps.sort(key=len, reverse=True)
        return comps
