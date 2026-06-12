"""SQL Database Tools for fastMcp"""
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
                - oracle://user:password@localhost:1521/dbname
        """
        self.database_url = database_url
        self.engine = None
        self._connect()
    
    def _connect(self):
        """Establish database connection"""
        try:
            self.engine = create_engine(self.database_url, poolclass=NullPool)
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection established")
        except Exception as e:
            logger.error(f"✗ Database connection failed: {str(e)}")
            raise
    
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
                "primary_keys": primary_keys.get("constrained_columns", [])
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
            # Validate it's a SELECT query
            query_upper = sql_query.strip().upper()
            if not query_upper.startswith("SELECT"):
                return {
                    "status": "error",
                    "message": "Only SELECT queries are allowed"
                }
            
            with self.engine.connect() as conn:
                result = conn.execute(text(f"{sql_query} LIMIT {limit}"))
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
