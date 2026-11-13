
"""
deduplicate.py — Détection prudente des doublons.

Règle :
- comparaison des paires directes uniquement ;
- distance de Jaccard < 0.05 ;
- conservation du livre ayant le plus de mots ;
- exclusion des sections Webster (l'édition complète reste).

Les exclusions sont enregistrées sans doublons dans excluded.json.
"""

import json
import os
import shutil
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
EXCL_DIR = ROOT / "data" / "excluded"
META = ROOT / "data" / "processed" / "metadata.json"
EXCLUDED = ROOT / "data" / "processed" / "excluded.json"

DB_URL = os.environ["DATABASE_URL"]

SEUIL_CONTENU = 0.05
WEBSTER_COMPLET = 673


def main():
    # 1. Lecture des données PostgreSQL
    with psycopg.connect(DB_URL, connect_timeout=10) as con:
        with con.cursor() as cur:
            pairs = cur.execute("""
                SELECT j.book_a, j.book_b, j.distance
                FROM jaccard j
                WHERE j.distance < %s
                ORDER BY j.distance ASC
            """, (SEUIL_CONTENU,)).fetchall()

            books = {
                row[0]: {
                    "title": row[1],
                    "word_count": row[2]
                }
                for row in cur.execute(
                    "SELECT id, title, word_count FROM books"
                )
            }

            webster_sections = [
                row[0]
                for row in cur.execute("""
                    SELECT id
                    FROM books
                    WHERE title ILIKE %s AND id <> %s
                """, ("%webster%dictionary%", WEBSTER_COMPLET))
            ]

    # 2. Sélection des paires directes
    used = set()
    excluded = []

    for a, b, distance in pairs:
        if a in used or b in used:
            continue

        if a not in books or b not in books:
            continue

        kept = max(
            (a, b),
            key=lambda book_id: books[book_id]["word_count"]
        )
        removed = b if kept == a else a

        excluded.append({
            "id": removed,
            "title": books[removed]["title"],
            "reason": f"doublon direct (distance {distance:.4f})",
            "kept": kept
        })

        used.update((a, b))

    # 3. Ajouter les sections Webster encore présentes
    meta = json.loads(META.read_text(encoding="utf-8"))
    meta_ids = {int(book["id"]) for book in meta}

    for book_id in webster_sections:
        if book_id in meta_ids and book_id not in used:
            excluded.append({
                "id": book_id,
                "title": books[book_id]["title"],
                "reason": "section du dictionnaire Webster",
                "kept": WEBSTER_COMPLET
            })

    excluded_ids = {item["id"] for item in excluded}

    # 4. Vérifier les conflits avant tout déplacement
    EXCL_DIR.mkdir(parents=True, exist_ok=True)

    for book_id in excluded_ids:
        src = RAW_DIR / f"{book_id}.txt"
        dst = EXCL_DIR / f"{book_id}.txt"

        if src.exists() and dst.exists():
            raise FileExistsError(
                f"Les deux fichiers existent pour le livre {book_id}. "
                "Aucun fichier n'a été déplacé."
            )

    # 5. Déplacer les fichiers concernés
    for book_id in excluded_ids:
        src = RAW_DIR / f"{book_id}.txt"
        dst = EXCL_DIR / f"{book_id}.txt"

        if src.exists():
            shutil.move(str(src), str(dst))

    # 6. Mettre à jour les métadonnées
    meta = [
        book for book in meta
        if int(book["id"]) not in excluded_ids
    ]

    # 7. Mettre à jour l'historique sans doublons
    previous = (
        json.loads(EXCLUDED.read_text(encoding="utf-8"))
        if EXCLUDED.exists()
        else []
    )

    history = {int(item["id"]): item for item in previous}

    for item in excluded:
        history[item["id"]] = item

    EXCLUDED.write_text(
        json.dumps(
            list(history.values()),
            indent=1,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    META.write_text(
        json.dumps(meta, indent=1, ensure_ascii=False),
        encoding="utf-8"
    )

    # 8. Bilan
    print(f"Paires candidates : {len(pairs)}")
    print(f"Doublons directs retenus : {len(excluded)}")
    print(f"Bibliothèque restante : {len(meta)} livres")
    print(f"Sections Webster déjà exclues : {len(webster_sections)}")

    for item in excluded:
        print(
            f"Exclu : {item['id']} - {item['title']} "
            f"(conservé : {item['kept']})"
        )


if __name__ == "__main__":
    main()
