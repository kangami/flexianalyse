"""
Connexion PostgreSQL — point d'entrée unique pour la base de données.
Configure la connexion via variables d'environnement.
"""
import os
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())


class Database:
    """Gestionnaire de connexion PostgreSQL avec pool."""

    def __init__(self):
        self._pool: ConnectionPool | None = None

    @property
    def conninfo(self) -> str:
        return (
            f"host={os.getenv('PG_HOST', 'localhost')} "
            f"port={os.getenv('PG_PORT', '5432')} "
            f"dbname={os.getenv('PG_DATABASE', 'flexianalyse')} "
            f"user={os.getenv('PG_USER', 'postgres')} "
            f"password={os.getenv('PG_PASSWORD', '')}"
        )

    def init_pool(self, min_size: int = 2, max_size: int = 10):
        """Initialise le pool de connexions."""
        if self._pool is not None:
            return
        self._pool = ConnectionPool(
            conninfo=self.conninfo,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
        )

    def fetch_one(self, query: str, params: tuple = None):
        """Exécute une requête et retourne une seule ligne (dict)."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()

    def fetch_all(self, query: str, params: tuple = None):
        """Exécute une requête et retourne toutes les lignes (list[dict])."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def execute(self, query: str, params: tuple = None):
        """Exécute une requête INSERT/UPDATE/DELETE."""
        with self._pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                rowcount = cur.rowcount
        return type("ExecResult", (), {"rowcount": rowcount})()

    def close(self):
        """Ferme le pool de connexions."""
        if self._pool is not None:
            self._pool.close()
            self._pool = None


# Instance globale
db = Database()
