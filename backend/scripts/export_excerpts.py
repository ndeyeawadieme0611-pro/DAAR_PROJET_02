"""
export_excerpts.py — Écrit data/processed/excerpts.csv (id, excerpt).

excerpt = les 3000 premiers caractères du texte du livre, EXACTEMENT comme
l'API les renvoie aujourd'hui (text[:3000], valeur par défaut de /books/{id}).
Le CSV est ensuite chargé dans la colonne books.excerpt de la base.

Usage (à la racine du projet) :  python backend/scripts/export_excerpts.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
META = ROOT / "data" / "processed" / "metadata.json"
OUT = ROOT / "data" / "processed" / "excerpts.csv"
CHARS = 3000


def main():
    meta = json.loads(META.read_text(encoding="utf-8"))
    books = meta.values() if isinstance(meta, dict) else meta
    ids = sorted(int(b["id"]) for b in books)

    missing = 0
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "excerpt"])
        for book_id in ids:
            path = RAW_DIR / f"{book_id}.txt"
            if not path.exists():
                missing += 1
                continue
            text = path.read_text(encoding="utf-8")[:CHARS]
            w.writerow([book_id, text.replace("\x00", "")])  # PostgreSQL refuse \x00
    print(f"{len(ids) - missing} extraits écrits dans {OUT} ({missing} textes manquants)")


if __name__ == "__main__":
    main()
