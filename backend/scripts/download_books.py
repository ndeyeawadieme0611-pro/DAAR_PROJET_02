"""
download_books.py — Construction de la bibliothèque (couche data).

Récupère des livres en anglais du Projet Gutenberg via l'API Gutendex,
retire l'en-tête et le pied de page de licence Gutenberg, et ne garde
que les livres d'au moins 10 000 mots (contrainte de l'énoncé).

Le script est REPRENABLE : si la connexion coupe, on le relance et les
livres déjà présents dans data/raw/ ne sont pas re-téléchargés.

Usage (depuis la racine du dépôt) :
    python backend/scripts/download_books.py --target 1700

Sources :
    - Catalogue : https://gutendex.com (API JSON du catalogue Gutenberg)
    - Textes    : https://www.gutenberg.org/cache/epub/<id>/pg<id>.txt
"""

import argparse
import json
import csv
import io
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --------------------------------------------------------------------------
# Chemins et constantes
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]           # racine du dépôt
RAW_DIR = ROOT / "data" / "raw"                      # textes nettoyés
META_FILE = ROOT / "data" / "processed" / "metadata.json"

CATALOG_URL = "https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv"
CATALOG_CACHE = ROOT / "data" / "processed" / "pg_catalog.csv"
TEXT_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
MIN_WORDS = 10_000

# Marqueurs de début / fin du contenu réel d'un livre Gutenberg.
# Exemple : "*** START OF THE PROJECT GUTENBERG EBOOK MOBY DICK ***"
START_RE = re.compile(
    r"\*\*\* ?START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.I | re.S
)
END_RE = re.compile(r"\*\*\* ?END OF (THE|THIS) PROJECT GUTENBERG EBOOK", re.I)

# Un "mot" = une suite de lettres. Même définition que pour l'indexation.
WORD_RE = re.compile(r"[A-Za-z]+")


# --------------------------------------------------------------------------
# Réseau : une session HTTP par thread, avec ré-essais automatiques
# --------------------------------------------------------------------------
_local = threading.local()


def get_session() -> requests.Session:
    """Session HTTP propre au thread courant (requests.Session n'est pas
    garanti thread-safe). Ré-essaie automatiquement en cas d'erreur réseau
    (DNS instable, timeout) ou de surcharge du serveur (429, 5xx)."""
    if not hasattr(_local, "session"):
        s = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1,          # attentes : 1s, 2s, 4s, 8s, 16s
            status_forcelist=[429, 500, 502, 503, 504],
        )
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.headers["User-Agent"] = "DAAR-Projet2-Sorbonne (student project)"
        _local.session = s
    return _local.session


# --------------------------------------------------------------------------
# Étape 1 : parcourir le catalogue Gutendex page par page
# --------------------------------------------------------------------------
def iter_catalog_pages(page_size=32):
    """Lit le catalogue officiel Gutenberg (CSV, ~75 000 entrées) et génère
    des paquets de livres en anglais. Le CSV est mis en cache localement
    pour ne pas le re-télécharger à chaque relance."""
    if not CATALOG_CACHE.exists():
        print("Téléchargement du catalogue Gutenberg...")
        r = get_session().get(CATALOG_URL, timeout=120)
        r.raise_for_status()
        r.encoding = "utf-8"
        CATALOG_CACHE.write_text(r.text, encoding="utf-8")

    with open(CATALOG_CACHE, encoding="utf-8", newline="") as f:
        page = []
        for row in csv.DictReader(f):
            # On ne garde que les livres texte en anglais
            if row["Type"] != "Text" or row["Language"] != "en":
                continue
            page.append({
                "id": int(row["Text#"]),
                "title": row["Title"],
                "authors": [a.strip() for a in row["Authors"].split(";") if a.strip()],
            })
            if len(page) == page_size:
                yield page
                page = []
        if page:
            yield page


# --------------------------------------------------------------------------
# Étape 2 : télécharger, nettoyer et filtrer un livre
# --------------------------------------------------------------------------
def strip_gutenberg(text: str) -> str:
    """Garde uniquement le texte entre les marqueurs START et END."""
    start = START_RE.search(text)
    end = END_RE.search(text)
    begin = start.end() if start else 0
    finish = end.start() if end else len(text)
    return text[begin:finish].strip()


def fetch_book(book: dict) -> dict | None:
    """Télécharge un livre et renvoie ses métadonnées s'il fait au moins
    MIN_WORDS mots, sinon None."""
    book_id = book["id"]
    path = RAW_DIR / f"{book_id}.txt"

    if path.exists():                       # déjà téléchargé : on relit
        text = path.read_text(encoding="utf-8")
    else:
        r = get_session().get(TEXT_URL.format(id=book_id), timeout=60)
        if r.status_code != 200:
            return None
        r.encoding = "utf-8"
        text = strip_gutenberg(r.text)

    n_words = len(WORD_RE.findall(text))
    if n_words < MIN_WORDS:
        return None                         # trop court : rejeté

    if not path.exists():
        path.write_text(text, encoding="utf-8")

    return {
        "id": book_id,
        "title": book["title"],
        "authors": book["authors"],
        "word_count": n_words,
    }


# --------------------------------------------------------------------------
# Programme principal
# --------------------------------------------------------------------------
def load_metadata() -> dict:
    if META_FILE.exists():
        books = json.loads(META_FILE.read_text(encoding="utf-8"))
        return {b["id"]: b for b in books}
    return {}


def save_metadata(accepted: dict) -> None:
    META_FILE.write_text(
        json.dumps(list(accepted.values()), indent=1, ensure_ascii=False),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description="Télécharge la bibliothèque.")
    parser.add_argument("--target", type=int, default=1700,
                        help="nombre de livres à obtenir (min. 1664)")
    parser.add_argument("--workers", type=int, default=4,
                        help="téléchargements en parallèle")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    META_FILE.parent.mkdir(parents=True, exist_ok=True)

    accepted = load_metadata()
    print(f"Reprise : {len(accepted)} livres déjà validés.")
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for page in iter_catalog_pages():
            if len(accepted) >= args.target:
                break

            todo = [b for b in page if b["id"] not in accepted]
            futures = [pool.submit(fetch_book, b) for b in todo]

            for f in as_completed(futures):
                try:
                    meta = f.result()
                except requests.RequestException as e:
                    print(f"  ! erreur réseau ignorée : {e}")
                    continue
                if meta:
                    accepted[meta["id"]] = meta

            save_metadata(accepted)          # sauvegarde après chaque page
            print(f"{len(accepted)}/{args.target} livres "
                  f"({time.time() - t0:.0f}s)")
            time.sleep(1)                    # politesse envers les serveurs

    print(f"Terminé : {len(accepted)} livres dans {RAW_DIR}")


if __name__ == "__main__":
    main()