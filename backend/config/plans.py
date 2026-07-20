"""Limites par palier de facturation (plan).

Le plan est porté par l'organisation (`Organization.plan`). Ces limites pilotent
le catalogue de schéma et le retrieval de tables du Text-to-SQL :

  catalog_max       nombre max de tables cataloguées (None = illimité, crawl async)
  inline_threshold  au-dessous, on envoie TOUTES les tables au LLM (pas de retrieval)
  retrieval_top_k   nombre de tables récupérées par requête au-dessus du seuil (0 = off)
  fk_expand         étend la sélection le long des FK (1 saut) pour ne pas casser les jointures
  sql_model         modèle OpenAI pour la génération SQL
  max_rows          plafond de lignes ramenées dans la réponse
"""

DEFAULT_PLAN = "free"

PLAN_LIMITS = {
    "free": {
        "catalog_max": 15,
        "inline_threshold": 15,
        "retrieval_top_k": 0,
        "fk_expand": False,
        "sql_model": "gpt-4o-mini",
        "max_rows": 50,
    },
    "pro": {
        "catalog_max": 150,
        "inline_threshold": 15,
        "retrieval_top_k": 12,
        "fk_expand": True,
        "sql_model": "gpt-4o",
        "max_rows": 500,
    },
    "enterprise": {
        "catalog_max": None,   # illimité — crawl paginé en tâche de fond
        "inline_threshold": 15,
        "retrieval_top_k": 15,
        "fk_expand": True,
        "sql_model": "gpt-4o",
        "max_rows": 5000,
    },
}


def plan_limits(plan: str | None) -> dict:
    """Limites du plan donné, avec repli sur le plan par défaut si inconnu."""
    return PLAN_LIMITS.get((plan or DEFAULT_PLAN), PLAN_LIMITS[DEFAULT_PLAN])
