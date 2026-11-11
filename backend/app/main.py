"""
main.py — API du moteur de recherche (couche serveur).

Endpoints :
    GET /search?q=whale&sort=score        recherche par mot-clé + suggestions
    GET /regex?pattern=wh.le&sort=score   recherche avancée par RegEx
    GET /books/{id}                       détail d'un livre (+ extrait, voisins)

Lancement (depuis le dossier backend/) :
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Documentation interactive : http://localhost:8000/docs
"""
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Literal

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row

from app.regex.engine import build_matcher
from scripts.build_index import tokenize      # MÊME normalisation que l'index

DB_URL = os.environ.get("DATABASE_URL", "postgresql://daar@localhost/library")
RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
SEUIL = 0.91              # seuil du graphe de Jaccard (même valeur que pagerank.py)
N_SOURCES = 3             # nb de meilleurs résultats dont on suggère les voisins
MAX_REGEX_WORDS = 500     # nb max de mots du vocabulaire retenus pour une RegEx

Sort = Literal["score", "occurrences", "pagerank"]
ORDER = {                 # liste blanche : jamais de texte utilisateur dans le SQL
    "score": "score DESC",
    "occurrences": "occurrences DESC",
    "pagerank": "b.pagerank DESC",
}

app = FastAPI(title="DAAR — Moteur de recherche de bibliothèque")
app.add_middleware(       # autorise le front (autre port / autre machine)
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def connect():
    return psycopg.connect(DB_URL, row_factory=dict_row)


# --------------------------------------------------------------------------
# Briques communes
# --------------------------------------------------------------------------
def ranked_books(cur, words, sort, limit):
    """Livres contenant au moins un des mots, classés selon 'sort'.
        occurrences = somme des occurrences des mots dans le livre
        score       = (occurrences / taille du livre) × PageRank
    """
    return cur.execute(f"""
        WITH ranks AS (
            SELECT id, RANK() OVER (ORDER BY pagerank DESC) AS pr_rank FROM books
        )
        SELECT b.id, b.title, b.authors, b.word_count,
               SUM(p.count)                                    AS occurrences,
               b.pagerank, r.pr_rank,
               SUM(p.count)::float / b.word_count * b.pagerank AS score
        FROM postings p
        JOIN books b ON b.id = p.book_id
        JOIN ranks r ON r.id = b.id
        WHERE p.word = ANY(%s)
        GROUP BY b.id, r.pr_rank
        ORDER BY {ORDER[sort]}
        LIMIT %s
    """, (words, limit)).fetchall()


def neighbors_of(cur, sources, exclude, limit=10):
    """Voisins des livres 'sources' dans le graphe de Jaccard, hors 'exclude',
    du plus proche au plus lointain."""
    return cur.execute("""
        SELECT b.id, b.title, b.authors, MIN(j.distance) AS distance
        FROM jaccard j
        JOIN books b ON b.id = CASE WHEN j.book_a = ANY(%(src)s)
                                    THEN j.book_b ELSE j.book_a END
        WHERE (j.book_a = ANY(%(src)s) OR j.book_b = ANY(%(src)s))
          AND j.distance < %(seuil)s
          AND b.id <> ALL(%(excl)s)
        GROUP BY b.id
        ORDER BY distance
        LIMIT %(limit)s
    """, {"src": sources, "excl": exclude, "seuil": SEUIL, "limit": limit}).fetchall()


def with_suggestions(cur, results):
    """Suggestions = voisins des N_SOURCES meilleurs résultats."""
    if not results:
        return []
    top = [r["id"] for r in results[:N_SOURCES]]
    return neighbors_of(cur, top, [r["id"] for r in results])


@lru_cache(maxsize=1)
def vocabulary():
    """Tout le vocabulaire, du mot le plus répandu au plus rare.
    Chargé une seule fois, puis gardé en mémoire (cache)."""
    with connect() as con:
        return [r["word"] for r in con.execute(
            "SELECT word FROM vocab ORDER BY df DESC")]


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------
@app.get("/search")
def search(q: str, sort: Sort = "score", limit: int = Query(50, ge=1, le=500)):
    """Recherche par mot-clé : livres dont l'index contient le(s) mot(s)."""
    t0 = time.perf_counter()
    words = tokenize(q)
    if not words:                      # requête vide ou uniquement des stopwords
        return {"query": q, "words": [], "results": [], "suggestions": [], "time_ms": 0}

    with connect() as con, con.cursor() as cur:
        results = ranked_books(cur, words, sort, limit)
        suggestions = with_suggestions(cur, results)

    return {"query": q, "words": words, "sort": sort,
            "results": results, "suggestions": suggestions,
            "time_ms": round((time.perf_counter() - t0) * 1000, 1)}


@app.get("/regex")
def regex_search(pattern: str, sort: Sort = "score",
                 limit: int = Query(50, ge=1, le=500)):
    """Recherche avancée : livres dont l'index contient un mot qui vérifie la RegEx."""
    t0 = time.perf_counter()
    try:
        matches = build_matcher(pattern)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"RegEx invalide : {e}")

    # 1. Mots du vocabulaire qui vérifient la RegEx (les plus répandus d'abord)
    matched = [w for w in vocabulary() if matches(w)]
    t_regex = time.perf_counter()
    words = matched[:MAX_REGEX_WORDS]

    # 2. Livres qui contiennent ces mots, classés + suggestions
    with connect() as con, con.cursor() as cur:
        results = ranked_books(cur, words, sort, limit) if words else []
        suggestions = with_suggestions(cur, results)

    return {"pattern": pattern, "sort": sort,
            "n_matched_words": len(matched),
            "matched_words": words[:20],
            "truncated": len(matched) > MAX_REGEX_WORDS,
            "results": results, "suggestions": suggestions,
            "regex_ms": round((t_regex - t0) * 1000, 1),
            "time_ms": round((time.perf_counter() - t0) * 1000, 1)}


@app.get("/books/{book_id}")
def book(book_id: int, chars: int = Query(3000, ge=0, le=20000)):
    """Détail d'un livre : métadonnées, début du texte et livres voisins."""
    with connect() as con, con.cursor() as cur:
        info = cur.execute(
            """SELECT id, title, authors, word_count, pagerank,
                      (SELECT COUNT(*) + 1 FROM books b2 WHERE b2.pagerank > books.pagerank) AS pr_rank
               FROM books WHERE id = %s""",
            (book_id,)).fetchone()
        if info is None:
            raise HTTPException(status_code=404, detail="Livre introuvable")
        info["neighbors"] = neighbors_of(cur, [book_id], [book_id], limit=8)

    text = (RAW_DIR / f"{book_id}.txt").read_text(encoding="utf-8")
    info["excerpt"] = text[:chars]
    return info

@app.get("/stats")
@lru_cache(maxsize=1)
def stats():
    """Chiffres de la page d'accueil (calculés une fois, puis gardés en cache)."""
    with connect() as con:
        return con.execute("""
            SELECT (SELECT COUNT(*) FROM books) AS books,
                   (SELECT COUNT(*) FROM vocab) AS words,
                   (SELECT COUNT(*) FROM jaccard WHERE distance < %s) AS edges
        """, (SEUIL,)).fetchone()
