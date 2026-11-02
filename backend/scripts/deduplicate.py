"""
deduplicate.py — Détecte et écarte les doublons de la bibliothèque.

Règle (choisie d'après l'analyse des distances de Jaccard) :
    doublon si  distance < SEUIL_CONTENU
           OU  (même titre ET distance < SEUIL_TITRE)
Les doublons sont regroupés (union-find : si A≈B et B≈C, alors A, B, C
forment un seul groupe) ; on garde le livre le plus long de chaque groupe.
On écarte aussi les sections du dictionnaire Webster (l'édition complète reste).

Les livres écartés sont :
    - retirés de data/processed/metadata.json,
    - déplacés de data/raw/ vers data/excluded/,
    - listés dans data/processed/excluded.json (pour ne pas les re-télécharger).

Ensuite : relancer download_books.py pour compléter la bibliothèque,
puis build_index.py, build_graph.py, pagerank.py.

Usage : python -u backend/scripts/deduplicate.py
"""
import json
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
EXCL_DIR = ROOT / "data" / "excluded"
META = ROOT / "data" / "processed" / "metadata.json"
EXCLUDED = ROOT / "data" / "processed" / "excluded.json"
DB_URL = os.environ.get("DATABASE_URL", "postgresql://daar@localhost/library")

SEUIL_CONTENU = 0.35   # contenu quasi identique, quel que soit le titre
SEUIL_TITRE = 0.92     # même titre : coupure naturelle entre 0.90 et 0.946
WEBSTER_COMPLET = 673  # édition complète du dictionnaire, à garder


# --------------------------------------------------------------------------
# Union-find : regroupe les éléments reliés, même indirectement
# --------------------------------------------------------------------------
parent = {}


def find(x):
    """Renvoie le représentant du groupe de x (avec compression de chemin)."""
    parent.setdefault(x, x)
    if parent[x] != x:
        parent[x] = find(parent[x])
    return parent[x]


def union(a, b):
    parent[find(a)] = find(b)


def main():
    with psycopg.connect(DB_URL) as con, con.cursor() as cur:
        # 1. Paires de doublons selon la règle
        pairs = cur.execute("""
            SELECT j.book_a, j.book_b
            FROM jaccard j
            JOIN books a ON a.id = j.book_a
            JOIN books b ON b.id = j.book_b
            WHERE j.distance < %s
               OR (lower(trim(a.title)) = lower(trim(b.title)) AND j.distance < %s)
        """, (SEUIL_CONTENU, SEUIL_TITRE)).fetchall()

        books = {row[0]: row[1:] for row in cur.execute(
            "SELECT id, title, word_count FROM books")}

        webster_sections = [r[0] for r in cur.execute(
            "SELECT id FROM books WHERE title ILIKE %s AND id <> %s",
            ("%webster%dictionary%", WEBSTER_COMPLET))]

    # 2. Regroupement des doublons
    for a, b in pairs:
        union(a, b)
    groups = {}
    for book_id in parent:
        groups.setdefault(find(book_id), []).append(book_id)

    # 3. Dans chaque groupe, on garde le livre le plus long
    excluded = []
    for members in groups.values():
        kept = max(members, key=lambda i: books[i][1])
        for i in members:
            if i != kept:
                excluded.append({"id": i, "title": books[i][0],
                                 "reason": "doublon", "kept": kept})
    for i in webster_sections:
        if all(e["id"] != i for e in excluded):
            excluded.append({"id": i, "title": books[i][0],
                             "reason": "section du dictionnaire", "kept": WEBSTER_COMPLET})

    # 4. Mise à jour des fichiers
    excluded_ids = {e["id"] for e in excluded}
    previous = json.loads(EXCLUDED.read_text(encoding="utf-8")) if EXCLUDED.exists() else []
    EXCLUDED.write_text(json.dumps(previous + excluded, indent=1, ensure_ascii=False),
                        encoding="utf-8")

    meta = json.loads(META.read_text(encoding="utf-8"))
    meta = [b for b in meta if b["id"] not in excluded_ids]
    META.write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")

    EXCL_DIR.mkdir(parents=True, exist_ok=True)
    for i in excluded_ids:
        src = RAW_DIR / f"{i}.txt"
        if src.exists():
            src.rename(EXCL_DIR / f"{i}.txt")

    # 5. Bilan
    print(f"{len(pairs)} paires de doublons -> {len(groups)} groupes")
    print(f"{len(excluded)} livres écartés "
          f"(dont {len(webster_sections)} sections du dictionnaire)")
    print(f"Bibliothèque : {len(meta)} livres restants")
    if len(meta) < 1700:
        print(f"-> relancer download_books.py 1700 pour en ajouter {1700 - len(meta)}")

    print("\nExemples de groupes :")
    for members in sorted(groups.values(), key=len, reverse=True)[:5]:
        print("  " + " | ".join(f"{i}:{books[i][0][:30]}" for i in members))


if __name__ == "__main__":
    main()