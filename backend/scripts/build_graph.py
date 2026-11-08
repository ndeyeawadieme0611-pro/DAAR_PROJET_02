"""
build_graph.py — Calcule les distances de Jaccard entre tous les livres.

1. Pour chaque livre, garde ses K mots les plus caractéristiques (TF-IDF),
   en ignorant les mots trop rares (présents dans moins de MIN_DF livres).
2. Calcule la distance de Jaccard pondérée entre chaque paire de livres.
3. Stocke toutes les distances < 1 dans la table PostgreSQL 'jaccard'.
   Le graphe = les paires dont la distance est inférieure à un seuil,
   choisi ensuite grâce aux statistiques affichées à la fin.

Usage : python -u backend/scripts/build_graph.py
"""
import os
import time
from collections import Counter, defaultdict

import psycopg

DB_URL = os.environ["DATABASE_URL"]
K = 200        # mots gardés par livre
MIN_DF = 5     # un mot doit apparaître dans au moins 5 livres pour compter


def load_vectors(cur):
    """Renvoie {book_id: {mot: poids}}, avec pour chaque livre ses K mots
    de plus fort TF-IDF. Les poids sont des fréquences relatives (somme = 1)."""
    n_books = cur.execute("SELECT COUNT(*) FROM books").fetchone()[0]

    # Tout le calcul du TF-IDF et du top-K est fait par PostgreSQL :
    #   tf    = occurrences du mot / nb total de mots indexés du livre
    #   idf   = ln(N / df)
    #   rang  = position du mot dans le livre, par TF-IDF décroissant
    rows = cur.execute("""
        WITH totals AS (
            SELECT book_id, SUM(count) AS total FROM postings GROUP BY book_id
        ),
        scored AS (
            SELECT p.book_id, p.word, p.count,
                   ROW_NUMBER() OVER (
                       PARTITION BY p.book_id
                       ORDER BY (p.count::float / t.total) * LN(%s::float / v.df) DESC
                   ) AS rang
            FROM postings p
            JOIN totals t ON t.book_id = p.book_id
            JOIN vocab  v ON v.word = p.word
            WHERE v.df >= %s
        )
        SELECT book_id, word, count FROM scored WHERE rang <= %s
    """, (n_books, MIN_DF, K)).fetchall()

    vectors = defaultdict(dict)
    for book_id, word, count in rows:
        vectors[book_id][word] = count

    # Fréquences relatives : chaque vecteur est divisé par sa somme,
    # pour que les gros livres ne soient pas avantagés.
    for vec in vectors.values():
        total = sum(vec.values())
        for word in vec:
            vec[word] /= total
    return vectors


def jaccard(va, vb):
    """Distance de Jaccard pondérée : d = 1 - Σmin / Σmax.
    Comme chaque vecteur a une somme de 1 : Σmax = 2 - Σmin.
    Seuls les mots communs contribuent à Σmin."""
    smin = sum(min(va[w], vb[w]) for w in va.keys() & vb.keys())
    return 1 - smin / (2 - smin)


def main():
    t0 = time.time()
    with psycopg.connect(DB_URL) as con, con.cursor() as cur:
        # 1. Vecteurs des livres
        print("Calcul des vecteurs TF-IDF...")
        vectors = load_vectors(cur)
        ids = sorted(vectors)
        print(f"{len(ids)} vecteurs prêts ({time.time() - t0:.0f}s)")

        # 2. Distances entre toutes les paires (A < B) : n(n-1)/2 paires
        distances = []
        for i, a in enumerate(ids):
            va = vectors[a]
            for b in ids[i + 1:]:
                d = jaccard(va, vectors[b])
                if d < 1:                       # au moins un mot commun
                    distances.append((a, b, d))
            if (i + 1) % 100 == 0:
                print(f"{i + 1}/{len(ids)} livres traités ({time.time() - t0:.0f}s)")

        # 3. Stockage dans PostgreSQL
        print(f"Enregistrement de {len(distances)} distances...")
        cur.execute("""
            DROP TABLE IF EXISTS jaccard;
            CREATE TABLE jaccard(book_a INTEGER, book_b INTEGER, distance REAL);
        """)
        with cur.copy("COPY jaccard (book_a, book_b, distance) FROM STDIN") as copy:
            for row in distances:
                copy.write_row(row)
        cur.execute("""
            CREATE INDEX idx_jaccard_a ON jaccard(book_a, distance);
            CREATE INDEX idx_jaccard_b ON jaccard(book_b, distance);
            ANALYZE jaccard;
        """)

    # 4. Aide au choix du seuil : taille du graphe selon le seuil
    print(f"\nTerminé en {time.time() - t0:.0f}s.\n")
    print(" seuil |  arêtes  | degré moyen | livres isolés")
    for seuil in (0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95):
        degree = Counter()
        n_edges = 0
        for a, b, d in distances:
            if d < seuil:
                degree[a] += 1
                degree[b] += 1
                n_edges += 1
        isolated = len(ids) - len(degree)
        print(f"  {seuil:.2f} | {n_edges:8d} | {2 * n_edges / len(ids):11.1f} | {isolated:5d}")


if __name__ == "__main__":
    main()