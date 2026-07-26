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
        "max_databases": 1,        # connecteurs (cloud OU on-prem)
        "monthly_questions": 50,   # plafond fair-use (questions IA / mois)
    },
    "pro": {
        "catalog_max": 150,
        "inline_threshold": 15,
        "retrieval_top_k": 12,
        "fk_expand": True,
        "sql_model": "gpt-4o",
        "max_rows": 500,
        "max_databases": 1,
        "monthly_questions": 500,
    },
    "business": {
        "catalog_max": 500,
        "inline_threshold": 15,
        "retrieval_top_k": 15,
        "fk_expand": True,
        "sql_model": "gpt-4o",
        "max_rows": 2000,
        "max_databases": 5,
        "monthly_questions": 2500,
    },
    "enterprise": {
        "catalog_max": None,   # illimité — crawl paginé en tâche de fond
        "inline_threshold": 15,
        "retrieval_top_k": 15,
        "fk_expand": True,
        "sql_model": "gpt-4o",
        "max_rows": 5000,
        "max_databases": None,     # illimité
        "monthly_questions": None, # illimité (sur devis)
    },
}

# Features on/off par palier. Chaque palier hérite implicitement des précédents
# via PLAN_ORDER (voir plan_allows) : on ne liste ici que ce qu'AJOUTE le palier.
# NB : l'agent on-prem (dial-home) est disponible sur TOUS les paliers — il n'est
# donc pas une feature gated ; c'est `max_databases` qui limite l'échelle.
PLAN_FEATURE_ADDS = {
    "free":       set(),
    "pro":        {"chat_history", "data_dictionary", "csv_export"},
    "business":   {"scheduled_insights", "writes", "audit_full", "roles_advanced"},
    "enterprise": {"sso", "priority_support", "multi_agent"},
}

# Catalogue d'affichage (page Plans). Prix en USD ; `price=None` = sur devis.
# Facturation annuelle = 2 mois offerts (price_year). L'agent on-prem est inclus
# partout ; le nombre de bases distingue les paliers.
PLAN_CATALOG = {
    "free": {
        "name": "Free",
        "price": 0,
        "price_year": 0,
        "currency": "USD",
        "period": "month",
        "tagline": "Pour essayer l'agent base de données",
        "features": [
            "1 base de données (cloud ou on-prem)",
            "Jusqu'à 15 tables",
            "50 questions IA / mois",
            "Database Report + Schema explorer",
            "1 siège",
        ],
        "cta": "Commencer",
    },
    "pro": {
        "name": "Pro",
        "price": 29,
        "price_year": 290,
        "currency": "USD",
        "period": "month",
        "tagline": "Pour un usage individuel régulier",
        "features": [
            "1 base de données (cloud ou on-prem)",
            "Jusqu'à 150 tables",
            "500 questions IA / mois",
            "Modèle avancé (gpt-4o)",
            "3 sièges inclus (+12 $/siège)",
            "Historique + questions de suivi",
        ],
        "cta": "Passer à Pro",
    },
    "business": {
        "name": "Business",
        "price": 99,
        "price_year": 990,
        "currency": "USD",
        "period": "month",
        "tagline": "Pour les équipes",
        "features": [
            "5 bases de données",
            "Jusqu'à 500 tables par base",
            "2 500 questions IA / mois",
            "Écritures avec confirmation",
            "Journaux d'audit",
            "10 sièges inclus (+15 $/siège)",
        ],
        "cta": "Passer à Business",
    },
    "enterprise": {
        "name": "Enterprise",
        "price": None,
        "price_year": None,
        "currency": "USD",
        "period": "",
        "tagline": "Pour les grands comptes",
        "features": [
            "Tout Business, plus :",
            "Bases & tables illimitées",
            "Agents on-prem multiples",
            "SSO / SAML · SLA",
            "Support dédié",
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
            "max_databases": limits.get("max_databases"),
            "monthly_questions": limits.get("monthly_questions"),
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
