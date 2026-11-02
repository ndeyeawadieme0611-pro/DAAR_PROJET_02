"""
download_books.py — Construit la bibliothèque (couche data).

1. Lit le catalogue officiel du Projet Gutenberg (fichier CSV).
2. Télécharge les livres en anglais, 4 en parallèle (threads).
3. Retire la licence Gutenberg et garde les livres de 10 000 mots ou plus.

Le script est reprenable : relancé, il saute les livres déjà validés.

Usage   : python -u backend/scripts/download_books.py 1700
Sources : https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv
          https://www.gutenberg.org/cache/epub/<id>/pg<id>.txt
"""
import csv
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]            # racine du dépôt
RAW_DIR = ROOT / "data" / "raw"                       # un fichier .txt par livre
CATALOG = ROOT / "data" / "processed" / "pg_catalog.csv"
META = ROOT / "data" / "processed" / "metadata.json"

CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
TEXT_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
MIN_WORDS = 10_000
WORKERS = 4                                           # téléchargements simultanés
BATCH = 32                                            # livres par paquet

WORD_RE = re.compile(r"[A-Za-z]+")                    # définition d'un "mot"
START_RE = re.compile(r"\*\*\* ?START OF.*\n", re.I)  # ligne de début du livre
END_RE = re.compile(r"\*\*\* ?END OF", re.I)          # ligne de fin du livre


def download(url):
    """Renvoie le texte de l'URL, ou None. Fait 3 essais si le réseau coupe.
    requests.get (sans Session) peut être appelé depuis plusieurs threads."""
    for _ in range(3):
        try:
            r = requests.get(url, timeout=60)
            r.encoding = "utf-8"
            return r.text if r.status_code == 200 else None
        except requests.RequestException:
            time.sleep(2)
    return None


def clean(text):
    """Garde uniquement le livre, entre les lignes START et END de Gutenberg."""
    start = START_RE.search(text)
    end = END_RE.search(text)
    return text[start.end() if start else 0 : end.start() if end else len(text)].strip()


def process_book(row):
    """Télécharge, nettoie et filtre UN livre.
    Renvoie ses métadonnées, ou None s'il est rejeté."""
    book_id = int(row["Text#"])
    text = download(TEXT_URL.format(id=book_id))
    if text is None:
        return None
    text = clean(text)
    n_words = len(WORD_RE.findall(text))
    if n_words < MIN_WORDS:
        return None
    (RAW_DIR / f"{book_id}.txt").write_text(text, encoding="utf-8")
    return {"id": book_id, "title": row["Title"],
            "authors": row["Authors"], "word_count": n_words}


def save(books):
    META.write_text(json.dumps(books, indent=1, ensure_ascii=False), encoding="utf-8")


def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 1700
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG.parent.mkdir(parents=True, exist_ok=True)

    # 1. Catalogue : téléchargé une seule fois, puis relu depuis le disque
    if not CATALOG.exists():
        catalog = download(CATALOG_URL)
        if catalog is None:
            sys.exit("Impossible de télécharger le catalogue.")
        CATALOG.write_text(catalog, encoding="utf-8")

    # Reprise : on repart des livres déjà validés
    books = json.loads(META.read_text(encoding="utf-8")) if META.exists() else []
    done = {b["id"] for b in books}
    one = {b["id"] for b in books}
    excluded = ROOT / "data" / "processed" / "excluded.json"
    if excluded.exists():   # livres écartés comme doublons : ne pas les reprendre
        done |= {e["id"] for e in json.loads(excluded.read_text(encoding="utf-8"))}
    print(f"Reprise : {len(books)} livres déjà validés.")

    # 2. Liste des livres candidats (texte, anglais, pas encore traités)
    with open(CATALOG, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f)
                if r["Type"] == "Text" and r["Language"] == "en"
                and int(r["Text#"]) not in done]
        # Un seul livre par titre : on ignore les rééditions d'un titre déjà présent
        def norm(title):
            return " ".join(title.lower().split())
        seen = {norm(b["title"]) for b in books}
        unique_rows = []
        for r in rows:
            if norm(r["Title"]) not in seen:
                seen.add(norm(r["Title"]))
                unique_rows.append(r)
        rows = unique_rows

    # 3. Traitement par paquets, avec WORKERS téléchargements en parallèle
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for i in range(0, len(rows), BATCH):
            if len(books) >= target:
                break
            for meta in pool.map(process_book, rows[i:i + BATCH]):
                if meta:
                    books.append(meta)
            save(books)                   # sauvegarde après chaque paquet
            print(f"{len(books)}/{target} livres ({time.time() - t0:.0f}s)")

    print(f"Terminé : {len(books)} livres dans {RAW_DIR}")


if __name__ == "__main__":
    main()