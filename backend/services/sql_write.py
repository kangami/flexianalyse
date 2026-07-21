"""SQL write support — classify, guard and generate writes for the confirm flow.

Writes (UPDATE/INSERT/DELETE) are NEVER auto-executed. The controller runs a
two-step flow: preview (guard + dry-run, rolled back → impact) then confirm
(guard again + execute, committed). Both steps are plan-gated and audited.
"""
import re
import logging

logger = logging.getLogger(__name__)

_READ_KW = ("select", "with")
_WRITE_KW = ("update", "insert", "delete")
_DDL_KW = ("drop", "truncate", "alter", "create", "grant", "revoke", "merge", "exec")

# Above this many affected rows, the UI asks for a reinforced confirmation.
MASS_WRITE_THRESHOLD = 1000


def leading_keyword(text: str) -> str | None:
    """First SQL keyword of a raw statement (lowercased), or None if the input
    doesn't start with a SQL keyword (i.e. it's natural language)."""
    m = re.match(r"\s*([a-zA-Z]+)", text or "")
    if not m:
        return None
    kw = m.group(1).lower()
    return kw if kw in (_READ_KW + _WRITE_KW + _DDL_KW) else None


def statement_kind(sql: str) -> str:
    """'read' | 'write' | 'ddl' | 'nl' for the given input."""
    kw = leading_keyword(sql)
    if kw is None:
        return "nl"
    if kw in _READ_KW:
        return "read"
    if kw in _WRITE_KW:
        return "write"
    return "ddl"


def guard_write(sql: str) -> tuple[bool, str]:
    """Strict guards for a write statement. Returns (ok, error_message)."""
    cleaned = (sql or "").strip().rstrip(";").strip()
    lowered = cleaned.lower()
    kw = leading_keyword(cleaned)
    if kw not in _WRITE_KW:
        return False, "Seules les requêtes UPDATE / INSERT / DELETE sont autorisées ici."
    if ";" in cleaned.rstrip(";"):
        return False, "Une seule instruction à la fois (pas de chaînage)."
    if any(re.search(rf"\b{d}\b", lowered) for d in _DDL_KW):
        return False, "Le DDL (DROP/TRUNCATE/ALTER/…) est interdit."
    # WHERE required for UPDATE/DELETE — block accidental mass writes.
    if kw in ("update", "delete") and not re.search(r"\bwhere\b", lowered):
        return False, ("UPDATE/DELETE sans clause WHERE est bloqué (modification de "
                       "masse). Ajoute un WHERE qui cible les lignes voulues.")
    return True, ""


def _extract_write_sql(text: str) -> str:
    """Pull a single write statement out of the model's reply (strip fences/prose)."""
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    m = re.search(r"(?is)\b(update|insert|delete)\b", s)
    return s[m.start():].strip().rstrip(";").strip() if m else ""


def generate_write_sql(question: str, schema: str, model: str) -> str:
    """Translate a natural-language instruction into a single write statement."""
    from ai.observability import get_openai_client
    prompt = f"""Database schema. Each line is `table(column type, ...)` and may end
with `[FK: col -> other_table(col)]`:
{schema}

User instruction: {question}

Write a SINGLE data-modification statement (UPDATE, INSERT or DELETE — PostgreSQL
dialect) that performs it. Rules:
- Exactly ONE statement. Never DDL (no DROP/TRUNCATE/ALTER/CREATE).
- For UPDATE/DELETE you MUST include a WHERE clause scoping the change to the rows
  the instruction refers to — never modify all rows.
- Use only tables/columns in the schema; scope via the [FK: ...] relationships.
- No trailing semicolon.
- If the instruction isn't a clear, safe data change, return an empty string.

Return ONLY the SQL statement — no markdown, no explanation."""
    try:
        resp = get_openai_client().chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert text-to-SQL engine for WRITE operations. Return only the raw SQL statement."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000,
        )
        return _extract_write_sql(resp.choices[0].message.content)
    except Exception as e:
        logger.error("write SQL generation failed: %s", e)
        return ""
