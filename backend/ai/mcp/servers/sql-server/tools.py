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
        self.database_url = database_url
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

            # Validate it's a SELECT query
            if not cleaned.upper().startswith("SELECT"):
                return {
                    "status": "error",
                    "message": "Only SELECT queries are allowed"
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
                    "rows": [dict(row._mapping) for row in rows],
                    "row_count": len(rows)
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
