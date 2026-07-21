"""Paliers de facturation (plans) : limites techniques, features et tarifs.

Le plan est porté par l'organisation (`Organization.plan`). Trois choses ici :

  PLAN_LIMITS   — limites techniques qui pilotent le catalogue de schéma et le
                  Text-to-SQL (catalog_max, inline_threshold, retrieval_top_k,
                  fk_expand, sql_model, max_rows).
  PLAN_FEATURES — capacités on/off par palier (historique, dictionnaire,
                  écritures, audit, on-prem…) pour le feature-gating.
  PLAN_CATALOG  — métadonnées d'affichage (prix, accroche, puces) pour la page
                  Plans côté frontend.

NB : le paiement (Stripe) n'est pas encore branché — le plan se change pour
l'instant en base (Flask-Admin). Le gating est prêt à être appliqué au fur et à
mesure des features (les écritures #5 s'appuieront sur `plan_allows`).
"""

DEFAULT_PLAN = "free"

# Ordre croissant — sert au classement et à l'affichage.
PLAN_ORDER = ["free", "pro", "business", "enterprise"]

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
    "business": {
        "catalog_max": 500,
        "inline_threshold": 15,
        "retrieval_top_k": 15,
        "fk_expand": True,
        "sql_model": "gpt-4o",
        "max_rows": 2000,
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

# Features on/off par palier. Chaque palier hérite implicitement des précédents
# via PLAN_ORDER (voir plan_allows) : on ne liste ici que ce qu'AJOUTE le palier.
PLAN_FEATURE_ADDS = {
    "free":       set(),
    "pro":        {"chat_history", "data_dictionary", "csv_export"},
    "business":   {"scheduled_insights", "writes", "audit_full", "roles_advanced"},
    "enterprise": {"self_hosted", "sso", "priority_support"},
}

# Catalogue d'affichage (page Plans). Prix en euros ; `price=None` = sur devis.
PLAN_CATALOG = {
    "free": {
        "name": "Free",
        "price": 0,
        "currency": "EUR",
        "period": "mois",
        "tagline": "Pour essayer l'agent base de données",
        "features": [
            "1 connexion base de données",
            "Jusqu'à 15 tables cataloguées",
            "50 questions / mois",
            "Diagramme ER + questions anticipées",
        ],
        "cta": "Commencer",
    },
    "pro": {
        "name": "Pro",
        "price": 39,
        "currency": "EUR",
        "period": "utilisateur / mois",
        "tagline": "Pour un usage individuel régulier",
        "features": [
            "3 connexions base de données",
            "Jusqu'à 150 tables cataloguées",
            "1 000 questions / mois",
            "Historique de conversations + questions de suivi",
            "Dictionnaire de données",
            "Export CSV",
        ],
        "cta": "Passer à Pro",
    },
    "business": {
        "name": "Business",
        "price": 299,
        "currency": "EUR",
        "period": "mois",
        "tagline": "Pour les équipes",
        "features": [
            "Connexions illimitées",
            "Tables illimitées (crawl en tâche de fond)",
            "Écritures avec confirmation",
            "Insights planifiés",
            "Journaux d'audit complets",
            "Rôles & permissions avancés",
        ],
        "cta": "Passer à Business",
    },
    "enterprise": {
        "name": "Enterprise",
        "price": None,
        "currency": "EUR",
        "period": "",
        "tagline": "Pour les grands comptes",
        "features": [
            "Tout Business, plus :",
            "Agent auto-hébergé (on-premise)",
            "SSO / SAML",
            "Support dédié & SLA",
        ],
        "cta": "Nous contacter",
    },
}


def plan_limits(plan: str | None) -> dict:
    """Limites techniques du plan, avec repli sur le plan par défaut si inconnu."""
    return PLAN_LIMITS.get((plan or DEFAULT_PLAN), PLAN_LIMITS[DEFAULT_PLAN])


def plan_features(plan: str | None) -> set:
    """Ensemble des features du plan (cumule les paliers inférieurs)."""
    plan = plan if plan in PLAN_ORDER else DEFAULT_PLAN
    feats: set = set()
    for p in PLAN_ORDER:
        feats |= PLAN_FEATURE_ADDS.get(p, set())
        if p == plan:
            break
    return feats


def plan_allows(plan: str | None, feature: str) -> bool:
    """True si le plan donne accès à la feature nommée."""
    return feature in plan_features(plan)


def plan_public(plan: str | None) -> dict:
    """Vue exposable au frontend pour le plan courant (sans secrets)."""
    plan = plan if plan in PLAN_ORDER else DEFAULT_PLAN
    limits = plan_limits(plan)
    return {
        "plan": plan,
        "name": PLAN_CATALOG.get(plan, {}).get("name", plan.title()),
        "features": sorted(plan_features(plan)),
        "limits": {
            "catalog_max": limits["catalog_max"],
            "max_rows": limits["max_rows"],
            "retrieval": bool(limits["retrieval_top_k"]),
        },
    }


def plans_catalog() -> list:
    """Catalogue ordonné des paliers pour la page Plans."""
    out = []
    for plan in PLAN_ORDER:
        info = dict(PLAN_CATALOG.get(plan, {}))
        info["id"] = plan
        info["feature_flags"] = sorted(plan_features(plan))
        out.append(info)
    return out
