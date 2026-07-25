"""SQL Database Tools for fastMcp"""
import os
import re
from typing import Any
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool
import logging

logger = logging.getLogger(__name__)

# Seconds to wait for the initial TCP/handshake before giving up. Keeps an
# unreachable host (firewall not whitelisting us, wrong port, DB down) from
# hanging until the caller's HTTP timeout — it fails fast with a real error.
CONNECT_TIMEOUT = int(os.getenv("SQL_CONNECT_TIMEOUT", "8"))

# Max characters kept per result cell. A table that stores files / long text
# (e.g. a "basefileentity") returns megabytes per row on SELECT *, which is slow to
# ship over the agent socket and useless in a chat grid — so we truncate.
CELL_MAX_CHARS = int(os.getenv("SQL_CELL_MAX_CHARS", "2000"))


def _slim_value(v):
    """Make one DB value JSON-safe and bounded.

    Binary columns can't be JSON-serialized (json.dumps would raise and the agent
    would never send a response → the caller times out), and huge text bloats the
    payload. Elide bytes, truncate long strings, and normalize Decimal/date/time so
    every cell is safe to serialize regardless of the driver's Python types.
    """
    import datetime as _dt
    from decimal import Decimal
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        return v if len(v) <= CELL_MAX_CHARS else v[:CELL_MAX_CHARS] + f"… (+{len(v) - CELL_MAX_CHARS} chars)"
    if isinstance(v, (bytes, bytearray, memoryview)):
        return f"<binary {len(bytes(v))} bytes>"
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (_dt.datetime, _dt.date, _dt.time)):
        return v.isoformat()
    s = str(v)
    return s if len(s) <= CELL_MAX_CHARS else s[:CELL_MAX_CHARS] + f"… (+{len(s) - CELL_MAX_CHARS} chars)"


def dispatch_tool(tools: "SQLTools", tool_name: str, params: dict) -> dict:
    """Run a named tool against a SQLTools instance. Shared by the HTTP MCP server
    (/execute) and the dial-home agent (over WebSocket). Returns a dict result;
    unknown tools yield an error dict rather than raising."""
    params = params or {}
    if tool_name == "test_connection":
        return tools.test_connection()
    if tool_name == "show_tables":
        return tools.show_tables()
    if tool_name == "show_full_schema":
        return tools.show_full_schema(params.get("limit"))
    if tool_name == "query_database":
        return tools.query_database(params.get("sql_query", ""), params.get("limit", 1000))
    if tool_name == "execute_write":
        return tools.execute_write(params.get("sql_query", ""), params.get("dry_run", True))
    if tool_name == "show_table_schema":
        return tools.show_table_schema(params.get("table_name", ""))
    if tool_name == "get_table_row_count":
        return tools.get_table_row_count(params.get("table_name", ""))
    if tool_name == "get_table_indexes":
        return tools.get_table_indexes(params.get("table_name", ""))
    if tool_name == "database_stats":
        return tools.database_stats()
    return {"status": "error", "message": f"Tool '{tool_name}' not found"}


# Map bare URL schemes to the drivers actually installed in this image, so a
# customer can paste a plain "mysql://…" / "postgres://…" URL and it just works.
_SCHEME_FIXUPS = {
    "mysql://": "mysql+mysqlconnector://",
    "mariadb://": "mysql+mysqlconnector://",
    "postgres://": "postgresql://",      # psycopg2 (default)
    "mssql://": "mssql+pymssql://",
    "sqlserver://": "mssql+pymssql://",
    "oracle://": "oracle+oracledb://",
}


def _normalize_db_url(url: str) -> str:
    for bare, full in _SCHEME_FIXUPS.items():
        if url.startswith(bare):
            return full + url[len(bare):]
    return url


class SQLTools:
    """Tools for querying various SQL databases"""

    def __init__(self, database_url: str):
        """
        Initialize SQL tools with database connection

        Args:
            database_url: SQLAlchemy-compatible connection string
                Examples:
                - postgresql://user:password@localhost/dbname
                - mysql+mysqlconnector://user:password@localhost/dbname
                - oracle+oracledb://user:password@host:1521/?service_name=XEPDB1
                - mssql+pymssql://user:password@host:1433/dbname
        """
        self.database_url = _normalize_db_url(database_url)
        self.engine = None
        self.dialect = ""
        self._connect()

    def _connect_args(self) -> dict:
        """Per-driver connect-timeout kwargs so a dead host fails in ~CONNECT_TIMEOUT
        seconds instead of hanging. Each DBAPI names the option differently."""
        try:
            backend = make_url(self.database_url).get_backend_name()
        except Exception:
            backend = ""
        t = CONNECT_TIMEOUT
        return {
            "postgresql": {"connect_timeout": t},
            "mysql":      {"connection_timeout": t},   # mysql-connector-python
            "oracle":     {"tcp_connect_timeout": t},  # python-oracledb (thin)
            "mssql":      {"login_timeout": t, "timeout": t},  # pymssql
        }.get(backend, {})

    def _connect(self):
        """Establish database connection (dialect-aware probe)."""
        try:
            self.engine = create_engine(
                self.database_url, poolclass=NullPool, connect_args=self._connect_args()
            )
            # SQLAlchemy normalises the backend name: 'postgresql', 'mysql'
            # (also MariaDB), 'oracle', 'mssql', 'sqlite'.
            self.dialect = self.engine.dialect.name
            with self.engine.connect() as conn:
                conn.execute(text(self._probe_query()))
            logger.info("✓ Database connection established (%s)", self.dialect)
        except Exception as e:
            logger.error(f"✗ Database connection failed: {str(e)}")
            raise

    def test_connection(self) -> dict[str, Any]:
        """Fast connectivity check for the pre-save 'Test connection' button.

        The constructor already opened the connection and ran the liveness probe,
        so if we got here the DB is reachable and the credentials work; we just
        report the dialect and how many tables were found.
        """
        try:
            tables = inspect(self.engine).get_table_names()
            return {"status": "success", "dialect": self.dialect, "table_count": len(tables)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _probe_query(self) -> str:
        """Trivial liveness query — Oracle has no bare `SELECT 1`."""
        return "SELECT 1 FROM DUAL" if self.dialect == "oracle" else "SELECT 1"

    def _apply_limit(self, sql: str, limit: int) -> str:
        """Cap a SELECT to `limit` rows using the target dialect's syntax.

        LIMIT is Postgres/MySQL/SQLite only. Oracle uses ROWNUM and MSSQL uses
        TOP; for those we wrap the query in a subselect (valid even if the inner
        query already limits itself), so ingestion sampling works everywhere.
        """
        if self.dialect == "oracle":
            return f"SELECT * FROM ({sql}) WHERE ROWNUM <= {int(limit)}"
        if self.dialect == "mssql":
            return f"SELECT TOP {int(limit)} * FROM ({sql}) AS _limited"
        if re.search(r"\blimit\b", sql, re.IGNORECASE):
            return sql
        return f"{sql} LIMIT {int(limit)}"
    
    def show_tables(self) -> dict[str, Any]:
        """List all tables in the database"""
        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names()
            return {
                "status": "success",
                "tables": tables,
                "count": len(tables)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    @staticmethod
    def _by_table(multi_result, name_set: set) -> dict:
        """Normalise get_multi_* output ({(schema, table): value}) to {table: value},
        keeping only the tables we asked for (default schema)."""
        out: dict = {}
        for key, value in dict(multi_result).items():
            table = key[1] if isinstance(key, tuple) else key
            if table in name_set and table not in out:
                out[table] = value
        return out

    def _row_estimates(self, names: set) -> dict:
        """Approximate row count per table from the engine's catalog statistics —
        instant (no table scan), unlike COUNT(*). Estimates can be stale/zero
        before the DB has gathered stats; callers treat <0 / None as unknown.
        Best-effort: any failure returns {} and the schema still loads."""
        d = self.dialect
        if d == "postgresql":
            q = ("SELECT c.relname AS t, c.reltuples::bigint AS n "
                 "FROM pg_class c JOIN pg_namespace nsp ON nsp.oid = c.relnamespace "
                 "WHERE c.relkind IN ('r','p') "
                 "AND nsp.nspname NOT IN ('pg_catalog','information_schema')")
        elif d in ("mysql", "mariadb"):
            q = ("SELECT table_name AS t, table_rows AS n FROM information_schema.tables "
                 "WHERE table_schema = DATABASE()")
        elif d == "mssql":
            q = ("SELECT t.name AS t, SUM(p.rows) AS n FROM sys.tables t "
                 "JOIN sys.partitions p ON p.object_id = t.object_id "
                 "WHERE p.index_id IN (0,1) GROUP BY t.name")
        elif d == "oracle":
            q = "SELECT table_name AS t, num_rows AS n FROM user_tables"
        else:
            return {}   # sqlite & others: no catalog stats — skip (tables are small)
        try:
            out = {}
            with self.engine.connect() as conn:
                for row in conn.execute(text(q)):
                    name, n = row[0], row[1]
                    if name in names and n is not None and int(n) >= 0:
                        out[name] = int(n)
            return out
        except Exception as e:
            logger.warning("row-estimate query failed (%s): %s", d, e)
            return {}

    def _scalar(self, conn, sql: str):
        """Run a single-value query; return the value or None (best-effort, so one
        unsupported metric never breaks the whole stats collection)."""
        try:
            row = conn.execute(text(sql)).first()
            return None if row is None else row[0]
        except Exception as e:
            logger.debug("stat query failed (%s): %s", self.dialect, e)
            return None

    def database_stats(self) -> dict[str, Any]:
        """Catalog-level metrics for the Database Report — counts + size + comment
        coverage + FK-without-index. Per-dialect; unavailable metrics come back as
        None (n/a) rather than a fabricated 0. Instant: no table scans."""
        d = self.dialect
        # Per-dialect scalar queries. Missing key = the concept doesn't exist for
        # that engine → the metric stays None.
        Q = {
            "postgresql": {
                "version": "SELECT current_setting('server_version')",
                "schemas": "SELECT count(*) FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog','information_schema') AND schema_name NOT LIKE 'pg_%'",
                "tables": "SELECT count(*) FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema NOT IN ('pg_catalog','information_schema')",
                "columns": "SELECT count(*) FROM information_schema.columns WHERE table_schema NOT IN ('pg_catalog','information_schema')",
                "views": "SELECT count(*) FROM information_schema.views WHERE table_schema NOT IN ('pg_catalog','information_schema')",
                "materialized_views": "SELECT count(*) FROM pg_matviews",
                "sequences": "SELECT count(*) FROM information_schema.sequences",
                "functions": "SELECT count(*) FROM information_schema.routines WHERE routine_type='FUNCTION' AND specific_schema NOT IN ('pg_catalog','information_schema')",
                "procedures": "SELECT count(*) FROM information_schema.routines WHERE routine_type='PROCEDURE' AND specific_schema NOT IN ('pg_catalog','information_schema')",
                "triggers": "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal",
                "foreign_keys": "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_type='FOREIGN KEY' AND table_schema NOT IN ('pg_catalog','information_schema')",
                "indexes": "SELECT count(*) FROM pg_indexes WHERE schemaname NOT IN ('pg_catalog','information_schema')",
                "db_size_bytes": "SELECT pg_database_size(current_database())",
                "documented_tables": "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_%' AND obj_description(c.oid,'pg_class') IS NOT NULL",
                "documented_columns": "SELECT count(*) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND a.attnum>0 AND NOT a.attisdropped AND n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname NOT LIKE 'pg_%' AND col_description(c.oid,a.attnum) IS NOT NULL",
                "fk_without_index": (
                    "SELECT count(*) FROM pg_constraint c WHERE c.contype='f' AND NOT EXISTS ("
                    "  SELECT 1 FROM pg_index i WHERE i.indrelid=c.conrelid "
                    "  AND (i.indkey::int2[])[0:array_length(c.conkey,1)-1] @> c.conkey "
                    "  AND c.conkey @> (i.indkey::int2[])[0:array_length(c.conkey,1)-1])"
                ),
            },
            "mysql": {
                "version": "SELECT version()",
                "schemas": "SELECT count(*) FROM information_schema.schemata WHERE schema_name = DATABASE()",
                "tables": "SELECT count(*) FROM information_schema.tables WHERE table_type='BASE TABLE' AND table_schema = DATABASE()",
                "columns": "SELECT count(*) FROM information_schema.columns WHERE table_schema = DATABASE()",
                "views": "SELECT count(*) FROM information_schema.views WHERE table_schema = DATABASE()",
                "functions": "SELECT count(*) FROM information_schema.routines WHERE routine_type='FUNCTION' AND routine_schema = DATABASE()",
                "procedures": "SELECT count(*) FROM information_schema.routines WHERE routine_type='PROCEDURE' AND routine_schema = DATABASE()",
                "triggers": "SELECT count(*) FROM information_schema.triggers WHERE trigger_schema = DATABASE()",
                "foreign_keys": "SELECT count(*) FROM information_schema.table_constraints WHERE constraint_type='FOREIGN KEY' AND table_schema = DATABASE()",
                "indexes": "SELECT count(DISTINCT table_name, index_name) FROM information_schema.statistics WHERE table_schema = DATABASE()",
                "db_size_bytes": "SELECT COALESCE(SUM(data_length+index_length),0) FROM information_schema.tables WHERE table_schema = DATABASE()",
                "documented_tables": "SELECT count(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_comment <> ''",
                "documented_columns": "SELECT count(*) FROM information_schema.columns WHERE table_schema = DATABASE() AND column_comment <> ''",
                "fk_without_index": (
                    "SELECT count(*) FROM information_schema.table_constraints tc "
                    "WHERE tc.constraint_type='FOREIGN KEY' AND tc.table_schema = DATABASE() "
                    "AND NOT EXISTS (SELECT 1 FROM information_schema.key_column_usage k "
                    "  JOIN information_schema.statistics s ON s.table_schema=k.table_schema "
                    "   AND s.table_name=k.table_name AND s.column_name=k.column_name AND s.seq_in_index=1 "
                    "  WHERE k.constraint_name=tc.constraint_name AND k.table_schema=tc.table_schema)"
                ),
            },
            "mssql": {
                "version": "SELECT CAST(SERVERPROPERTY('ProductVersion') AS varchar(64))",
                "schemas": "SELECT count(*) FROM sys.schemas WHERE schema_id < 16384",
                "tables": "SELECT count(*) FROM sys.tables",
                "columns": "SELECT count(*) FROM sys.columns c JOIN sys.tables t ON t.object_id=c.object_id",
                "views": "SELECT count(*) FROM sys.views",
                "sequences": "SELECT count(*) FROM sys.sequences",
                "functions": "SELECT count(*) FROM sys.objects WHERE type IN ('FN','IF','TF')",
                "procedures": "SELECT count(*) FROM sys.procedures",
                "triggers": "SELECT count(*) FROM sys.triggers",
                "foreign_keys": "SELECT count(*) FROM sys.foreign_keys",
                "indexes": "SELECT count(*) FROM sys.indexes WHERE index_id > 0 AND is_hypothetical = 0",
                "db_size_bytes": "SELECT CAST(SUM(size) AS bigint)*8192 FROM sys.database_files",
                "documented_tables": "SELECT count(*) FROM sys.extended_properties WHERE name='MS_Description' AND minor_id=0 AND class=1",
                "documented_columns": "SELECT count(*) FROM sys.extended_properties WHERE name='MS_Description' AND minor_id>0 AND class=1",
            },
            "oracle": {
                "version": "SELECT version FROM product_component_version WHERE ROWNUM=1",
                "schemas": "SELECT 1 FROM dual",
                "tables": "SELECT count(*) FROM user_tables",
                "columns": "SELECT count(*) FROM user_tab_columns",
                "views": "SELECT count(*) FROM user_views",
                "materialized_views": "SELECT count(*) FROM user_mviews",
                "sequences": "SELECT count(*) FROM user_sequences",
                "functions": "SELECT count(*) FROM user_objects WHERE object_type='FUNCTION'",
                "procedures": "SELECT count(*) FROM user_objects WHERE object_type='PROCEDURE'",
                "triggers": "SELECT count(*) FROM user_triggers",
                "foreign_keys": "SELECT count(*) FROM user_constraints WHERE constraint_type='R'",
                "indexes": "SELECT count(*) FROM user_indexes",
                "db_size_bytes": "SELECT SUM(bytes) FROM user_segments",
                "documented_tables": "SELECT count(*) FROM user_tab_comments WHERE comments IS NOT NULL",
                "documented_columns": "SELECT count(*) FROM user_col_comments WHERE comments IS NOT NULL",
            },
        }
        # mariadb shares MySQL's catalog.
        queries = Q.get("mysql" if d == "mariadb" else d, {})
        metric_keys = [
            "schemas", "tables", "columns", "views", "materialized_views", "sequences",
            "functions", "procedures", "triggers", "foreign_keys", "indexes",
            "db_size_bytes", "documented_tables", "documented_columns", "fk_without_index",
        ]
        version = None
        metrics = {k: None for k in metric_keys}
        try:
            with self.engine.connect() as conn:
                version = self._scalar(conn, queries["version"]) if "version" in queries else None
                for k in metric_keys:
                    if k in queries:
                        v = self._scalar(conn, queries[k])
                        metrics[k] = int(v) if v is not None else None
        except Exception as e:
            return {"status": "error", "message": str(e)}
        return {"status": "success", "engine": d, "version": (str(version) if version else None), "metrics": metrics}

    def show_full_schema(self, limit: int | None = None) -> dict[str, Any]:
        """Every table's columns + PK + FK.

        On large schemas the old per-table reflection issued 3×N catalog queries
        (get_columns / get_pk_constraint / get_foreign_keys per table) and blew
        past the client HTTP timeout. This uses SQLAlchemy 2.0 **bulk reflection**
        (get_multi_*) — a handful of catalog queries for ALL tables at once — and
        honours `limit` so a huge database (thousands of tables) still answers
        quickly, since the caller only renders the first N. Falls back to per-table
        reflection when the bulk API is unavailable.
        """
        try:
            inspector = inspect(self.engine)
            names = inspector.get_table_names()
            if limit is not None and limit >= 0:
                names = names[:limit]
            name_set = set(names)

            # Bulk path — one query per metadata kind for all requested tables.
            cols_by = pk_by = fk_by = None
            try:
                cols_by = self._by_table(inspector.get_multi_columns(filter_names=names), name_set)
                pk_by   = self._by_table(inspector.get_multi_pk_constraint(filter_names=names), name_set)
                fk_by   = self._by_table(inspector.get_multi_foreign_keys(filter_names=names), name_set)
            except Exception as e:
                logger.warning("bulk reflection unavailable (%s) — per-table fallback", e)
                cols_by = None

            estimates = self._row_estimates(name_set)

            out = []
            for table_name in names:
                try:
                    if cols_by is not None:
                        columns = cols_by.get(table_name, [])
                        pk_cols = (pk_by.get(table_name) or {}).get("constrained_columns", []) if pk_by else []
                        fks     = fk_by.get(table_name, []) if fk_by else []
                    else:
                        columns = inspector.get_columns(table_name)
                        pk_cols = inspector.get_pk_constraint(table_name).get("constrained_columns", [])
                        try:
                            fks = inspector.get_foreign_keys(table_name)
                        except Exception:
                            fks = []
                    out.append({
                        "table": table_name,
                        "row_estimate": estimates.get(table_name),
                        "columns": [
                            {
                                "name": c["name"],
                                "type": str(c["type"]),
                                "nullable": c.get("nullable"),
                                "is_primary_key": c["name"] in pk_cols,
                            }
                            for c in columns
                        ],
                        "primary_keys": list(pk_cols),
                        "foreign_keys": [
                            {
                                "columns": fk.get("constrained_columns", []),
                                "referred_table": fk.get("referred_table"),
                                "referred_columns": fk.get("referred_columns", []),
                            }
                            for fk in fks
                        ],
                    })
                except Exception as e:
                    logger.warning("full schema: table %s failed: %s", table_name, e)
            return {"status": "success", "tables": out, "count": len(out)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def show_table_schema(self, table_name: str) -> dict[str, Any]:
        """Get schema/columns for a specific table"""
        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table_name)
            primary_keys = inspector.get_pk_constraint(table_name)

            try:
                foreign_keys = inspector.get_foreign_keys(table_name)
            except Exception:
                foreign_keys = []

            schema = {
                "table": table_name,
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "is_primary_key": col["name"] in primary_keys.get("constrained_columns", [])
                    }
                    for col in columns
                ],
                "primary_keys": primary_keys.get("constrained_columns", []),
                "foreign_keys": [
                    {
                        "columns": fk.get("constrained_columns", []),
                        "referred_table": fk.get("referred_table"),
                        "referred_columns": fk.get("referred_columns", []),
                    }
                    for fk in foreign_keys
                ],
            }
            return {"status": "success", "schema": schema}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def query_database(self, sql_query: str, limit: int = 1000) -> dict[str, Any]:
        """
        Execute a SELECT query on the database
        
        Args:
            sql_query: SQL SELECT statement
            limit: Maximum number of rows to return
        """
        try:
            # Normalize: drop trailing semicolons/whitespace before any rewriting
            cleaned = sql_query.strip().rstrip(";").strip()
            lowered = cleaned.lower()

            # Allow read-only SELECT and CTE (WITH ... SELECT) queries — the latter
            # is needed for window-function / month-over-month analytics.
            if not (lowered.startswith("select") or lowered.startswith("with")):
                return {
                    "status": "error",
                    "message": "Only read-only SELECT / WITH queries are allowed",
                }
            # Defense in depth: block DML/DDL even inside a CTE (WITH x AS (...) DELETE ...).
            _forbidden = ("insert ", "update ", "delete ", "drop ", "alter ",
                          "truncate ", "create ", "grant ", "revoke ", "merge ", "exec ")
            if any(f in lowered for f in _forbidden):
                return {
                    "status": "error",
                    "message": "Read-only queries only (no INSERT/UPDATE/DELETE/DDL)",
                }

            # Cap rows with the target dialect's syntax (LIMIT / ROWNUM / TOP).
            final_query = self._apply_limit(cleaned, limit)

            with self.engine.connect() as conn:
                result = conn.execute(text(final_query))
                rows = result.fetchall()
                columns = list(result.keys())
                
                return {
                    "status": "success",
                    "columns": columns,
                    "rows": [
                        {k: _slim_value(v) for k, v in row._mapping.items()}
                        for row in rows
                    ],
                    "row_count": len(rows)
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def execute_write(self, sql_query: str, dry_run: bool = True) -> dict[str, Any]:
        """Execute a single write (UPDATE / INSERT / DELETE) in a transaction.

        dry_run=True  → run then ROLLBACK, returning rows_affected (impact preview).
        dry_run=False → run then COMMIT.

        Defense in depth (the API guards too): only a single UPDATE/INSERT/DELETE,
        no DDL, no statement chaining.
        """
        try:
            cleaned = sql_query.strip().rstrip(";").strip()
            lowered = cleaned.lower()

            if not (lowered.startswith("update") or lowered.startswith("insert")
                    or lowered.startswith("delete")):
                return {"status": "error", "message": "Only UPDATE / INSERT / DELETE are allowed"}
            if ";" in cleaned.rstrip(";"):
                return {"status": "error", "message": "Multiple statements are not allowed"}
            _ddl = ("drop ", "truncate ", "alter ", "create ", "grant ", "revoke ", "merge ", "exec ")
            if any(k in lowered for k in _ddl):
                return {"status": "error", "message": "DDL is not allowed"}

            with self.engine.connect() as conn:
                trans = conn.begin()
                try:
                    result = conn.execute(text(cleaned))
                    affected = result.rowcount
                    if dry_run:
                        trans.rollback()
                    else:
                        trans.commit()
                except Exception:
                    trans.rollback()
                    raise

            return {
                "status": "success",
                "rows_affected": int(affected) if affected is not None else None,
                "committed": (not dry_run),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_table_row_count(self, table_name: str) -> dict[str, Any]:
        """Get the number of rows in a table"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) as count FROM {table_name}"))
                count = result.scalar()
                return {
                    "status": "success",
                    "table": table_name,
                    "row_count": count
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_table_indexes(self, table_name: str) -> dict[str, Any]:
        """Get indexes for a specific table"""
        try:
            inspector = inspect(self.engine)
            indexes = inspector.get_indexes(table_name)
            
            return {
                "status": "success",
                "table": table_name,
                "indexes": [
                    {
                        "name": idx["name"],
                        "columns": idx["column_names"],
                        "unique": idx.get("unique", False)
                    }
                    for idx in indexes
                ]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
