"""
Hybrid retrieval for enterprise-grade RAG precision (deterministic).

Goal:
- Combine semantic retrieval (FAISS) + lexical scoring (BM25-ish) + exact match boosts
- Avoid LLM-based reranking (expensive + can drift)
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

from langchain.schema import Document


_STOPWORDS = {
    # EN
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "by", "is", "are", "was", "were",
    "be", "been", "being", "as", "at", "from", "that", "this", "these", "those", "it", "its", "into", "about",
    "what", "which", "who", "whom", "when", "where", "why", "how",
    # FR
    "le", "la", "les", "un", "une", "des", "de", "du", "d", "et", "ou", "à", "au", "aux", "en", "dans", "pour",
    "par", "avec", "sans", "sur", "sous", "est", "sont", "été", "être", "ce", "cet", "cette", "ces", "qui", "que",
    "quoi", "quand", "où", "comment", "pourquoi",
    # ES
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "y", "o", "a", "en", "para", "por",
    "con", "sin", "sobre", "es", "son", "ser", "estar", "que", "qué", "cuándo", "dónde", "cómo", "porqué",
}


def _normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _normalize_filename(name: str) -> str:
    """
    Normalize filenames for robust matching across UI/backend variations:
    - drop paths
    - lowercase
    - strip trailing " (1)", " (2)", ...
    """
    base = (name or "").replace("\\", "/").split("/")[-1].strip().lower()
    base = re.sub(r"\s*\(\d+\)\s*$", "", base).strip()
    return base


def _split_name_ext(name: str) -> Tuple[str, str]:
    n = _normalize_filename(name)
    m = re.match(r"^(.*?)(\.[a-z0-9]+)?$", n)
    if not m:
        return n, ""
    base = (m.group(1) or "").strip()
    ext = (m.group(2) or "").strip()
    return base, ext


def _source_matches(doc_source: str, preferred_sources: List[str]) -> bool:
    """
    Match by base name, and enforce extension match when extension is present.
    """
    doc_base, doc_ext = _split_name_ext(doc_source)
    for s in preferred_sources:
        pref_base, pref_ext = _split_name_ext(s)
        if not pref_base:
            continue
        if pref_ext and doc_ext and pref_ext != doc_ext:
            continue
        if doc_base == pref_base or doc_base in pref_base or pref_base in doc_base:
            return True
    return False


def _tokenize(s: str) -> List[str]:
    s = _normalize_text(s)
    # Keep letters/numbers and accents; split on non-word-ish.
    tokens = re.findall(r"[a-z0-9àâäçéèêëîïôöùûüÿñ]+", s, flags=re.IGNORECASE)
    tokens = [t for t in tokens if len(t) >= 2 and t not in _STOPWORDS]
    return tokens


def _is_date_query(q: str) -> bool:
    ql = _normalize_text(q)
    return any(k in ql for k in ["date", "start date", "begin", "début", "embauche", "commence", "commencement"])


def _is_money_query(q: str) -> bool:
    ql = _normalize_text(q)
    return any(k in ql for k in ["salary", "salaire", "remuneration", "rémunération", "€", "eur", "usd", "$", "pay"])


def _has_date_evidence(text: str) -> bool:
    t = _normalize_text(text)
    # Very tolerant date patterns (EU + ISO)
    if re.search(r"\b\d{1,2}\s+(janv|janvier|févr|fevr|février|mars|avr|avril|mai|juin|juil|juillet|août|aout|sept|septembre|oct|octobre|nov|novembre|déc|dec|décembre)\b", t):
        return True
    if re.search(r"\b\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4}\b", t):
        return True
    if re.search(r"\b\d{4}[\/\.-]\d{1,2}[\/\.-]\d{1,2}\b", t):
        return True
    return False


def _has_money_evidence(text: str) -> bool:
    t = _normalize_text(text)
    # Currency signs or common patterns
    if re.search(r"(\€|\$|\beur\b|\busd\b)", t):
        return True
    if re.search(r"\b\d{1,3}(?:[ \u00A0.,]\d{3})*(?:[.,]\d{2})?\b", t) and any(k in t for k in ["salaire", "salary", "remuneration", "rémunération", "€", "eur", "$"]):
        return True
    return False


def _distance_to_similarity(distance: float) -> float:
    # FAISS (LangChain) typically returns L2 distance: smaller is better.
    # Map to (0, 1] with a smooth curve.
    try:
        d = float(distance)
    except Exception:
        d = 1e9
    if d < 0:
        d = 0.0
    return 1.0 / (1.0 + d)


def _minmax(values: List[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 1.0
    mn = min(values)
    mx = max(values)
    if mx - mn < 1e-9:
        return mn, mn + 1e-9
    return mn, mx


def _bm25_score(query_tokens: List[str], doc_tokens: List[str], df: Dict[str, int], N: int) -> float:
    # BM25-ish with conservative constants (no external dep)
    if not query_tokens or not doc_tokens or N <= 0:
        return 0.0
    k1 = 1.2
    b = 0.75
    tf = Counter(doc_tokens)
    dl = len(doc_tokens)
    avgdl = 1.0  # will be handled outside by normalization; keep stable
    score = 0.0
    for t in query_tokens:
        f = tf.get(t, 0)
        if f <= 0:
            continue
        n = df.get(t, 0)
        # add-one smoothing
        idf = math.log((N - n + 0.5) / (n + 0.5) + 1.0)
        denom = f + k1 * (1 - b + b * (dl / max(avgdl, 1.0)))
        score += idf * ((f * (k1 + 1.0)) / max(denom, 1e-9))
    return float(score)


def hybrid_retrieve_documents(
    vector_store: Any,
    query: str,
    k_candidates: int = 60,
    k_final: int = 12,
    semantic_weight: float = 0.60,
    bm25_weight: float = 0.30,
    exact_weight: float = 0.10,
    preferred_sources: Optional[List[str]] = None,
) -> Tuple[List[Document], Dict[str, Any]]:
    """
    Returns: (top_docs, debug)
    """
    q = query or ""
    query_tokens = _tokenize(q)
    is_date = _is_date_query(q)
    is_money = _is_money_query(q)

    # 1) Semantic candidates (FAISS)
    raw: List[Tuple[Document, float]] = []
    try:
        raw = vector_store.similarity_search_with_score(q, k=k_candidates) or []
    except Exception:
        raw = []

    # Deduplicate by (source, first 200 chars)
    candidates: List[Tuple[Document, float]] = []
    seen = set()
    for doc, dist in raw:
        src = (doc.metadata.get("source") or doc.metadata.get("fileName") or doc.metadata.get("file_name") or "").strip()
        key = (src.lower(), _normalize_text(doc.page_content)[:200])
        if key in seen:
            continue
        seen.add(key)
        candidates.append((doc, dist))

    # Optional: restrict to preferred sources (used for "selected file first" retrieval)
    if preferred_sources:
        pref = [p for p in preferred_sources if (p or "").strip()]
        if pref:
            filtered = []
            for doc, dist in candidates:
                src = (doc.metadata.get("source") or doc.metadata.get("fileName") or doc.metadata.get("file_name") or "").strip()
                if _source_matches(src, pref):
                    filtered.append((doc, dist))
            candidates = filtered

    if not candidates:
        return [], {"reason": "no_candidates", "k_candidates": k_candidates, "preferred_sources": preferred_sources}

    # 2) Lexical stats (BM25-ish over candidates)
    doc_tokens_list: List[List[str]] = []
    df: Dict[str, int] = {}
    for doc, _dist in candidates:
        toks = _tokenize(doc.page_content)
        doc_tokens_list.append(toks)
        for t in set(toks):
            df[t] = df.get(t, 0) + 1

    N = len(candidates)
    bm25_scores = []
    sem_scores = []
    exact_scores = []

    # Precompute for min-max normalization
    for (doc, dist), doc_toks in zip(candidates, doc_tokens_list):
        sem = _distance_to_similarity(dist)
        sem_scores.append(sem)

        bm25 = _bm25_score(query_tokens, doc_toks, df, N)
        bm25_scores.append(bm25)

        # Exact-ish: keywords in filename + phrase presence
        meta_name = (doc.metadata.get("fileName") or doc.metadata.get("file_name") or doc.metadata.get("source") or "")
        name_l = _normalize_text(meta_name)
        content_l = _normalize_text(doc.page_content)
        exact = 0.0
        if query_tokens:
            hits_name = sum(1 for t in query_tokens if t in name_l)
            hits_content = sum(1 for t in query_tokens if t in content_l)
            exact += min(hits_name * 0.15, 0.6)
            exact += min(hits_content * 0.05, 0.4)
        # Evidence boosts (date/money)
        if is_date and _has_date_evidence(content_l):
            exact += 0.25
        if is_money and _has_money_evidence(content_l):
            exact += 0.25
        exact_scores.append(min(exact, 1.0))

    sem_min, sem_max = _minmax(sem_scores)
    bm_min, bm_max = _minmax(bm25_scores)
    ex_min, ex_max = _minmax(exact_scores)

    ranked: List[Tuple[Document, float, Dict[str, float]]] = []
    for (doc, dist), sem, bm, ex in zip(candidates, sem_scores, bm25_scores, exact_scores):
        sem_n = (sem - sem_min) / (sem_max - sem_min)
        bm_n = (bm - bm_min) / (bm_max - bm_min)
        ex_n = (ex - ex_min) / (ex_max - ex_min)
        final = semantic_weight * sem_n + bm25_weight * bm_n + exact_weight * ex_n
        ranked.append((doc, float(final), {"semantic": sem_n, "bm25": bm_n, "exact": ex_n}))

    ranked.sort(key=lambda x: x[1], reverse=True)
    top = ranked[: max(1, int(k_final))]
    docs = [d for d, _s, _parts in top]

    debug = {
        "query_tokens": query_tokens[:20],
        "is_date_query": is_date,
        "is_money_query": is_money,
        "candidate_count": len(candidates),
        "k_final": k_final,
        "top": [
            {
                "source": (d.metadata.get("source") or d.metadata.get("fileName") or d.metadata.get("file_name")),
                "score": round(s, 4),
                "parts": {k: round(v, 4) for k, v in parts.items()},
                "preview": (d.page_content or "")[:160],
            }
            for (d, s, parts) in top[:5]
        ],
    }
    return docs, debug


