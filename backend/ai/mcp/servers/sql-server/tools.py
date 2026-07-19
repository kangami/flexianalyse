"""SQL Database Tools for fastMcp"""
import re
from typing import Any
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool
import logging

logger = logging.getLogger(__name__)


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

    def _connect(self):
        """Establish database connection (dialect-aware probe)."""
        try:
            self.engine = create_engine(self.database_url, poolclass=NullPool)
            # SQLAlchemy normalises the backend name: 'postgresql', 'mysql'
            # (also MariaDB), 'oracle', 'mssql', 'sqlite'.
            self.dialect = self.engine.dialect.name
            with self.engine.connect() as conn:
                conn.execute(text(self._probe_query()))
            logger.info("✓ Database connection established (%s)", self.dialect)
        except Exception as e:
            logger.error(f"✗ Database connection failed: {str(e)}")
            raise

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
