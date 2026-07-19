"""Construction d'URL SQLAlchemy à partir de champs de connexion structurés.

Le formulaire côté client collecte host / port / database / user / password
(façon DBeaver) plutôt qu'une URL brute. On assemble ici l'URL, ce qui garde la
logique de dialecte côté serveur et gère l'encodage du mot de passe (caractères
spéciaux) proprement.

Moteurs supportés — tous stockés en type connecteur 'sql' :
  postgresql, mysql, mariadb (via le pilote mysql), oracle (thin), mssql (pymssql).
"""
from urllib.parse import quote_plus

# engine → schéma SQLAlchemy (pilote inclus, versions installées côté serveur MCP)
DB_SCHEMES = {
    "postgresql": "postgresql",
    "mysql": "mysql+mysqlconnector",
    "mariadb": "mysql+mysqlconnector",   # MariaDB parle le protocole MySQL
    "oracle": "oracle+oracledb",          # python-oracledb en mode thin
    "mssql": "mssql+pymssql",
}

DEFAULT_PORTS = {
    "postgresql": 5432,
    "mysql": 3306,
    "mariadb": 3306,
    "oracle": 1521,
    "mssql": 1433,
}

SUPPORTED_ENGINES = tuple(DB_SCHEMES.keys())


def build_database_url(
    engine: str,
    host: str,
    port: str | int | None = None,
    database: str | None = None,
    username: str | None = None,
    password: str | None = None,
    service_name: str | None = None,
) -> str:
    """Assemble une URL SQLAlchemy pour le moteur donné.

    Oracle utilise `?service_name=` (le champ `database` sert de repli). Lève
    ValueError si le moteur est inconnu ou l'hôte manquant.
    """
    scheme = DB_SCHEMES.get(engine)
    if not scheme:
        raise ValueError(f"Moteur non supporté : {engine!r}")
    if not host:
        raise ValueError("host requis")

    user = quote_plus(username) if username else ""
    pwd = quote_plus(password) if password else ""
    auth = f"{user}:{pwd}@" if (user or pwd) else ""
    port = port or DEFAULT_PORTS[engine]

    if engine == "oracle":
        svc = service_name or database
        if not svc:
            raise ValueError("service_name (ou database) requis pour Oracle")
        return f"{scheme}://{auth}{host}:{port}/?service_name={quote_plus(str(svc))}"

    db_part = database or ""
    return f"{scheme}://{auth}{host}:{port}/{db_part}"
