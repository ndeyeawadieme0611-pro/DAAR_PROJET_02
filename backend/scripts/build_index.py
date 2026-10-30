"""
build_index.py — Construit l'index inversé de la bibliothèque.

Pour chaque livre de data/raw/, compte les occurrences de chaque mot,
puis stocke tout dans une base SQLite (data/processed/library.db) :

    books(id, title, authors, word_count)   métadonnées des livres
    postings(word, book_id, count)          index inversé : mot -> livres
    vocab(word, df)                         vocabulaire + nb de livres
                                            contenant le mot (df)

Usage : python -u backend/scripts/build_index.py
"""
import json
import re
import sqlite3
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
META = ROOT / "data" / "processed" / "metadata.json"
DB = ROOT / "data" / "processed" / "library.db"

WORD_RE = re.compile(r"[a-z]+")   # appliqué après passage en minuscules

# Mots trop fréquents pour être utiles à la recherche (anglais).
STOPWORDS = set("""
a about above after again against all am an and any are as at be because been
before being below between both but by can could did do does doing down during
each few for from further had has have having he her here hers herself him
himself his how i if in into is it its itself just me more most my myself no nor
not now of off on once only or other our ours ourselves out over own same she
should so some such than that the their theirs them themselves then there these
they this those through to too under until up very was we were what when where
which while who whom why will with would you your yours yourself yourselves
""".split())


def tokenize(text):
    """Texte -> liste de mots normalisés (minuscules, sans stopwords).
    La recherche devra utiliser EXACTEMENT cette même fonction."""
    return [w for w in WORD_RE.findall(text.lower())
            if len(w) > 1 and w not in STOPWORDS]


def main():
    if DB.exists():
        DB.unlink()                       # on reconstruit l'index de zéro
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode = OFF")   # construction plus rapide :
    con.execute("PRAGMA synchronous = OFF")    # la base est régénérable

    con.executescript("""
        CREATE TABLE books(id INTEGER PRIMARY KEY, title TEXT,
                           authors TEXT, word_count INTEGER);
        CREATE TABLE postings(word TEXT, book_id INTEGER, count INTEGER);
    """)

    # 1. Métadonnées des livres
    books = json.loads(META.read_text(encoding="utf-8"))
    for b in books:   # anciennes entrées : auteurs en liste -> texte
        if isinstance(b["authors"], list):
            b["authors"] = "; ".join(b["authors"])
    con.executemany(
        "INSERT INTO books VALUES (:id, :title, :authors, :word_count)", books)

    # 2. Index inversé : pour chaque livre, compter ses mots
    t0 = time.time()
    for i, book in enumerate(books, 1):
        text = (RAW_DIR / f"{book['id']}.txt").read_text(encoding="utf-8")
        counts = Counter(tokenize(text))          # {mot: nb d'occurrences}
        con.executemany("INSERT INTO postings VALUES (?, ?, ?)",
                        ((w, book["id"], c) for w, c in counts.items()))
        if i % 100 == 0:
            print(f"{i}/{len(books)} livres indexés ({time.time() - t0:.0f}s)")

    # 3. Index B-tree sur 'word' : c'est lui qui rend la recherche rapide.
    #    Créé à la fin (un tri global) plutôt qu'à chaque insertion.
    print("Création de l'index B-tree sur les mots...")
    con.execute("CREATE INDEX idx_postings_word ON postings(word)")

    # 4. Vocabulaire : liste des mots distincts (servira à la recherche RegEx)
    con.executescript("""
        CREATE TABLE vocab(word TEXT PRIMARY KEY, df INTEGER);
        INSERT INTO vocab SELECT word, COUNT(*) FROM postings GROUP BY word;
    """)
    con.commit()

    n_words = con.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
    n_post = con.execute("SELECT COUNT(*) FROM postings").fetchone()[0]
    print(f"Terminé en {time.time() - t0:.0f}s : {n_words} mots distincts, "
          f"{n_post} entrées (mot, livre).")
    con.close()


if __name__ == "__main__":
    main()