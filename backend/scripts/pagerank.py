"""
pagerank.py — Calcule le PageRank de chaque livre dans le graphe de Jaccard.

1. Charge le graphe : une arête entre deux livres si leur distance de
   Jaccard est inférieure à SEUIL (table 'jaccard').
2. Calcule le PageRank par itérations successives jusqu'à convergence.
3. Enregistre le score dans la colonne books.pagerank.

Usage : python -u backend/scripts/pagerank.py
"""
import os
import time

import psycopg

DB_URL = os.environ["DATABASE_URL"]
SEUIL = 0.91      # seuil choisi d'après les statistiques de build_graph.py
ALPHA = 0.85      # facteur d'amortissement (probabilité de suivre une arête)
EPS = 1e-6        # critère de convergence
MAX_ITER = 100

# Livres à surveiller dans l'affichage final (vérification des hypothèses)
WATCH = {673: "Webster's Dictionary", 15: "Moby Dick",
         10: "Bible King James", 1581: "Bible Douay-Rheims"}


def load_graph(cur):
    """Renvoie {livre: [voisins]} pour les 1700 livres (graphe non orienté).
    Un livre sans arête a une liste vide : c'est un livre isolé."""
    neighbors = {book_id: [] for (book_id,) in cur.execute("SELECT id FROM books")}
    for a, b in cur.execute(
            "SELECT book_a, book_b FROM jaccard WHERE distance < %s", (SEUIL,)):
        neighbors[a].append(b)
        neighbors[b].append(a)
    return neighbors


def pagerank(neighbors):
    """PageRank par itérations :
       PR(v) = (1-α)/N + α·perdu/N + α · Σ PR(u)/degré(u)   (u voisin de v)
    'perdu' = score des livres isolés, redistribué à tous (dangling nodes)."""
    n = len(neighbors)
    pr = {v: 1 / n for v in neighbors}                 # départ uniforme
    isolated = [v for v, nb in neighbors.items() if not nb]

    for iteration in range(1, MAX_ITER + 1):
        lost = sum(pr[v] for v in isolated)
        base = (1 - ALPHA) / n + ALPHA * lost / n      # téléportation + isolés
        new = {v: base + ALPHA * sum(pr[u] / len(neighbors[u]) for u in nb)
               for v, nb in neighbors.items()}
        delta = sum(abs(new[v] - pr[v]) for v in pr)   # variation totale
        pr = new
        if delta < EPS:                                # convergence atteinte
            break
    return pr, iteration, delta


def correlation(xs, ys):
    """Coefficient de corrélation de Pearson entre deux listes."""
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (vx * vy)


def main():
    t0 = time.time()
    with psycopg.connect(DB_URL) as con, con.cursor() as cur:
        # 1. Graphe
        neighbors = load_graph(cur)
        n_edges = sum(len(nb) for nb in neighbors.values()) // 2
        print(f"Graphe : {len(neighbors)} livres, {n_edges} arêtes (seuil {SEUIL})")

        # 2. PageRank
        pr, iterations, delta = pagerank(neighbors)
        print(f"Convergence en {iterations} itérations (variation {delta:.1e}), "
              f"somme des scores = {sum(pr.values()):.6f}, {time.time() - t0:.1f}s")

        # 3. Enregistrement dans books.pagerank
        cur.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS pagerank DOUBLE PRECISION")
        cur.executemany("UPDATE books SET pagerank = %s WHERE id = %s",
                        [(score, book_id) for book_id, score in pr.items()])

        titles = dict(cur.execute("SELECT id, title FROM books"))

    # 4. Affichage : top 10 et livres surveillés
    ranking = sorted(pr, key=pr.get, reverse=True)
    rank_of = {book_id: r for r, book_id in enumerate(ranking, 1)}

    print("\nTop 10 des livres les plus centraux :")
    print(" rang | degré | pagerank  | titre")
    for book_id in ranking[:10]:
        print(f" {rank_of[book_id]:4d} | {len(neighbors[book_id]):5d} | "
              f"{pr[book_id]:.6f} | {titles[book_id][:55]}")

    print("\nLivres surveillés :")
    for book_id, name in WATCH.items():
        if book_id in pr:
            print(f"  {name:22s} rang {rank_of[book_id]:4d}/{len(pr)}, "
                  f"degré {len(neighbors[book_id])}")

    # Lien PageRank / degré (limite discutée dans le rapport)
    ids = list(pr)
    r = correlation([pr[v] for v in ids], [len(neighbors[v]) for v in ids])
    print(f"\nCorrélation PageRank / degré : {r:.3f}")


if __name__ == "__main__":
    main()