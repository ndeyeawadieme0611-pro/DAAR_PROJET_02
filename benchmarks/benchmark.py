"""
benchmark.py — Tests de performance et figures du rapport.

Mesure, sur des bibliothèques de taille croissante (200, 500, 1000 livres,
puis toute la base) :
  1. la recherche par mot-clé avec l'index inversé (PostgreSQL) ;
  2. la recherche RegEx : automate du Projet 1 appliqué au vocabulaire,
     comparé au module `re` de Python ;
  3. la recherche d'un mot par KMP dans le texte brut, comparée à l'index.
Trace aussi les figures du graphe : histogramme des distances de Jaccard,
PageRank en fonction du degré, tableau « seuil -> taille du graphe ».

Les sous-bibliothèques sont des tables TEMPORAIRES : les vraies tables
(books, postings, vocab, jaccard) ne sont jamais modifiées.

Usage (à la racine du dépôt, base PostgreSQL locale démarrée) :
    python benchmarks/benchmark.py            # complet (environ 10 minutes)
    python benchmarks/benchmark.py --quick    # essai rapide, peu de répétitions

Résultats dans benchmarks/results/ : fichiers .png, mesures.csv et resume.txt.
"""
import csv
import os
import platform
import random
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT = ROOT / "benchmarks" / "results"

SEED = 2026
SIZES = [200, 500, 1000]              # + la base entière, ajoutée automatiquement
KMP_SIZES = [25, 50, 100, 200]        # le parcours du texte brut est lent : petites tailles
WORDS = ["love", "whale", "sargon"]   # mot très répandu, moyen, rare
KMP_WORDS = ["whale", "sargon"]
PATTERNS = ["s(a|g|r)+on", "wh.le", "colou*r"]
SEUIL = 0.91
QUICK = "--quick" in sys.argv
REP_INDEX = 5 if QUICK else 30
REP_REGEX = 2 if QUICK else 5
REP_KMP = 1 if QUICK else 3


# --------------------------------------------------------------------------
# Connexion : DATABASE_URL, sinon le fichier .env du dépôt (port local 5433)
# --------------------------------------------------------------------------
def database_url():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    env = {}
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip().strip('"').strip("'")
    if "POSTGRES_PASSWORD" not in env:
        sys.exit("Impossible de trouver la base : définissez DATABASE_URL, par exemple\n"
                 '  $env:DATABASE_URL="postgresql://daar:MOTDEPASSE@localhost:5433/library"')
    port = os.environ.get("PGPORT", "5433")
    return (f"postgresql://{env.get('POSTGRES_USER', 'daar')}:{env['POSTGRES_PASSWORD']}"
            f"@localhost:{port}/{env.get('POSTGRES_DB', 'library')}")


DB_URL = database_url()
os.environ["DATABASE_URL"] = DB_URL      # build_index.py la lit dès l'import

sys.path.insert(0, str(ROOT / "backend"))
import psycopg                                        # noqa: E402
from app.regex.engine import build_matcher            # noqa: E402  automate du Projet 1
from app.search.kmp import kmp_search                 # noqa: E402
from scripts.build_index import tokenize              # noqa: E402  même normalisation que l'index

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("Il manque matplotlib :  pip install matplotlib")


# --------------------------------------------------------------------------
# Outils
# --------------------------------------------------------------------------
def mean_std(values):
    """Moyenne et écart-type (0 s'il n'y a qu'une mesure)."""
    return statistics.mean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)


def timed(fn, repetitions):
    """Temps de `repetitions` appels de fn, en millisecondes (1 appel d'échauffement)."""
    fn()
    times = []
    for _ in range(repetitions):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return times


def make_tables(cur, ids, everything):
    """Prépare une bibliothèque réduite aux livres `ids`.
    Renvoie les noms des tables (livres, index) à interroger."""
    if everything:
        return "books", "postings"
    cur.execute("DROP TABLE IF EXISTS bench_postings")
    cur.execute("DROP TABLE IF EXISTS bench_books")
    cur.execute("CREATE TEMP TABLE bench_books (LIKE books)")
    cur.execute("INSERT INTO bench_books SELECT * FROM books WHERE id = ANY(%s)", (ids,))
    cur.execute("CREATE TEMP TABLE bench_postings (LIKE postings)")
    cur.execute("INSERT INTO bench_postings SELECT * FROM postings WHERE book_id = ANY(%s)", (ids,))
    cur.execute("CREATE INDEX bench_postings_word ON bench_postings(word)")   # même index B-tree
    cur.execute("ANALYZE bench_books")
    cur.execute("ANALYZE bench_postings")
    return "bench_books", "bench_postings"


def search(cur, books_t, postings_t, words, limit=50):
    """La requête de l'API (/search, tri par score), sur les tables données."""
    return cur.execute(f"""
        WITH ranks AS (
            SELECT id, RANK() OVER (ORDER BY pagerank DESC) AS pr_rank FROM {books_t}
        )
        SELECT b.id, b.title, SUM(p.count) AS occurrences, r.pr_rank,
               SUM(p.count)::float / b.word_count * b.pagerank AS score
        FROM {postings_t} p
        JOIN {books_t} b ON b.id = p.book_id
        JOIN ranks r ON r.id = b.id
        WHERE p.word = ANY(%s)
        GROUP BY b.id, b.title, b.word_count, b.pagerank, r.pr_rank
        ORDER BY score DESC
        LIMIT %s
    """, (words, limit)).fetchall()


def vocabulary(cur, postings_t):
    """Vocabulaire de la bibliothèque, du mot le plus répandu au plus rare."""
    if postings_t == "postings":
        rows = cur.execute("SELECT word FROM vocab ORDER BY df DESC, word").fetchall()
    else:
        rows = cur.execute(f"SELECT word FROM {postings_t} GROUP BY word "
                           "ORDER BY COUNT(*) DESC, word").fetchall()
    return [str(r[0]) for r in rows]


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs) ** 0.5
    vy = sum((y - my) ** 2 for y in ys) ** 0.5
    return cov / (vx * vy) if vx and vy else float("nan")


# --------------------------------------------------------------------------
# Programme principal
# --------------------------------------------------------------------------
def main():
    try:                                   # accents lisibles même si la sortie est redirigée
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []          # lignes de mesures.csv
    summary = []       # lignes de resume.txt

    def note(line=""):
        print(line)
        summary.append(line)

    host = DB_URL.split("@")[-1]
    print(f"Connexion à la base {host} ...")
    try:
        con = psycopg.connect(DB_URL, autocommit=True)
    except Exception as e:                                   # base arrêtée, mauvais port...
        sys.exit(f"Connexion impossible ({e}).\nLa base locale est-elle démarrée (Docker Desktop) ?")

    with con, con.cursor() as cur:
        all_ids = [int(r[0]) for r in cur.execute("SELECT id FROM books ORDER BY id").fetchall()]
        total = len(all_ids)
        n_vocab = int(cur.execute("SELECT COUNT(*) FROM vocab").fetchone()[0])
        order = all_ids[:]
        random.Random(SEED).shuffle(order)         # sous-bibliothèques emboîtées, tirage fixe
        sizes = [n for n in SIZES if n < total] + [total]
        kmp_sizes = [n for n in KMP_SIZES if n <= total]

        note("=== Contexte ===")
        note(f"Date : {time.strftime('%Y-%m-%d %H:%M')}   mode : {'rapide' if QUICK else 'complet'}")
        note(f"Machine : {platform.system()} {platform.release()}, {platform.processor() or platform.machine()}, "
             f"{os.cpu_count()} coeurs logiques, Python {platform.python_version()}")
        note(f"Base : {total} livres, {n_vocab} mots dans le vocabulaire")
        note(f"Répétitions : index {REP_INDEX}, RegEx {REP_REGEX}, KMP {REP_KMP}   graine : {SEED}")

        # ---------------- 1 et 2 : index et RegEx selon la taille ----------------
        index_res = {w: [] for w in WORDS}             # mot -> [(n, moyenne, écart-type)]
        regex_res = {p: [] for p in PATTERNS}          # motif -> [(n, moyenne, écart-type)]
        re_res = []                                    # [(n, moyenne, écart-type)] module re
        vocab_sizes = []
        note("\n=== 1. Recherche par mot-clé (index inversé) : temps en ms ===")
        note(" livres | " + " | ".join(f"{w:>18s}" for w in WORDS))
        regex_lines = []
        for n in sizes:
            ids = order[:n]
            books_t, postings_t = make_tables(cur, ids, n == total)
            cells = []
            for w in WORDS:
                words = tokenize(w)
                times = timed(lambda: search(cur, books_t, postings_t, words), REP_INDEX)
                m, s = mean_std(times)
                found = len(search(cur, books_t, postings_t, words, limit=100000))
                index_res[w].append((n, m, s))
                rows.append(["index", n, w, f"{m:.3f}", f"{s:.3f}", REP_INDEX, f"{found} livres"])
                cells.append(f"{m:7.2f} ± {s:5.2f} ({found:4d})")
            note(f" {n:6d} | " + " | ".join(cells))

            vocab = vocabulary(cur, postings_t)
            vocab_sizes.append((n, len(vocab)))
            re_all = []
            cells = []
            for p in PATTERNS:
                def run_automaton():
                    matches = build_matcher(p)
                    return [w for w in vocab if matches(w)]

                def run_re():
                    compiled = re.compile(p)
                    return [w for w in vocab if compiled.fullmatch(w)]

                found_a, found_r = run_automaton(), run_re()
                if found_a != found_r:
                    note(f"   ATTENTION : l'automate et re diffèrent sur {p} ({len(found_a)} / {len(found_r)})")
                times = timed(run_automaton, REP_REGEX)
                m, s = mean_std(times)
                regex_res[p].append((n, m, s))
                rows.append(["regex_automate", n, p, f"{m:.3f}", f"{s:.3f}", REP_REGEX,
                             f"{len(found_a)} mots sur {len(vocab)}"])
                times_re = timed(run_re, REP_REGEX)
                mr, sr = mean_std(times_re)
                rows.append(["regex_re", n, p, f"{mr:.3f}", f"{sr:.3f}", REP_REGEX, ""])
                re_all.extend(times_re)
                cells.append(f"{m:8.1f} ± {s:5.1f} ({len(found_a):3d})")
            mr, sr = mean_std(re_all)
            re_res.append((n, mr, sr))
            regex_lines.append(f" {n:6d} | {len(vocab):10d} | " + " | ".join(cells) + f" | {mr:7.1f} ± {sr:4.1f}")
        note("  (entre parenthèses : nombre de livres trouvés)")

        note("\n=== 2. Recherche RegEx sur le vocabulaire : temps en ms ===")
        note(" livres | vocabulaire | " + " | ".join(f"{p:>22s}" for p in PATTERNS) + " | module re (moy.)")
        for line in regex_lines:
            note(line)
        note("  (entre parenthèses : nombre de mots reconnus ; temps = construction de l'automate + filtrage)")

        # ---------------- 3 : KMP sur le texte brut, comparé à l'index ----------------
        kmp_res, kmp_index_res = [], []
        missing = [b for b in order[:max(kmp_sizes, default=0)] if not (RAW_DIR / f"{b}.txt").exists()]
        if "--no-kmp" in sys.argv or not kmp_sizes:
            note("\n=== 3. KMP : non lancé ===")
        elif missing:
            note(f"\n=== 3. KMP : non lancé, {len(missing)} textes absents de data/raw ===")
        else:
            note("\n=== 3. Mot cherché par KMP dans le texte brut, comparé à l'index : temps en ms ===")
            sample = order[:max(kmp_sizes)]
            texts = [(RAW_DIR / f"{b}.txt").read_text(encoding="utf-8").lower() for b in sample]
            n_chars = [len(t) for t in texts]
            # temps par livre et par répétition ; les tailles étant emboîtées, on additionne ensuite
            per_book = {w: [[0.0] * len(texts) for _ in range(REP_KMP)] for w in KMP_WORDS}
            hits = {w: [0] * len(texts) for w in KMP_WORDS}
            t_start = time.time()
            for w in KMP_WORDS:
                for rep in range(REP_KMP):
                    for i, text in enumerate(texts):
                        t0 = time.perf_counter()
                        positions = kmp_search(text, w)
                        per_book[w][rep][i] = (time.perf_counter() - t0) * 1000
                        hits[w][i] = len(positions)
                    print(f"   KMP « {w} » passe {rep + 1}/{REP_KMP} ({time.time() - t_start:.0f}s)")
            note(" livres | caractères |        KMP (texte brut) |  index (PostgreSQL) | rapport")
            for n in kmp_sizes:
                totals = [sum(per_book[w][rep][:n]) for w in KMP_WORDS for rep in range(REP_KMP)]
                mk, sk = mean_std(totals)
                books_t, postings_t = make_tables(cur, order[:n], n == total)
                idx_times = []
                for w in KMP_WORDS:
                    idx_times.extend(timed(lambda: search(cur, books_t, postings_t, tokenize(w)), REP_INDEX))
                mi, si = mean_std(idx_times)
                kmp_res.append((n, mk, sk))
                kmp_index_res.append((n, mi, si))
                rows.append(["kmp_texte", n, "+".join(KMP_WORDS), f"{mk:.3f}", f"{sk:.3f}", REP_KMP,
                             f"{sum(n_chars[:n])} caracteres"])
                rows.append(["index_meme_taille", n, "+".join(KMP_WORDS), f"{mi:.3f}", f"{si:.3f}", REP_INDEX, ""])
                note(f" {n:6d} | {sum(n_chars[:n]):10d} | {mk:10.1f} ± {sk:8.1f} | {mi:8.2f} ± {si:6.2f} | x{mk / mi:,.0f}")
            speed = sum(n_chars) * len(KMP_WORDS) * REP_KMP / (sum(sum(sum(r) for r in per_book[w]) for w in KMP_WORDS) / 1000)
            note(f"  Vitesse de KMP en Python : {speed / 1e6:.2f} million(s) de caractères par seconde")
            for w in KMP_WORDS:
                n_max = max(kmp_sizes)
                by_kmp = sum(1 for h in hits[w][:n_max] if h)
                make_tables(cur, order[:n_max], n_max == total)
                tables = ("books", "postings") if n_max == total else ("bench_books", "bench_postings")
                by_index = len(search(cur, tables[0], tables[1], tokenize(w), limit=100000))
                note(f"  « {w} » sur {n_max} livres : {by_kmp} livres par KMP (sous-chaîne), {by_index} par l'index (mot entier)")

        # ---------------- 4 : graphe de Jaccard ----------------
        note("\n=== 4. Graphe de Jaccard ===")
        n_pairs = total * (total - 1) // 2
        n_stored = int(cur.execute("SELECT COUNT(*) FROM jaccard").fetchone()[0])
        note(f"Paires de livres : {n_pairs} ; distances < 1 stockées : {n_stored} ; "
             f"paires sans mot commun : {n_pairs - n_stored}")
        hist = [(int(b), int(c)) for b, c in cur.execute(
            "SELECT width_bucket(distance::float8, 0, 1, 50) AS b, COUNT(*) FROM jaccard GROUP BY b ORDER BY b"
        ).fetchall()]
        close = [(int(a), int(b), float(d)) for a, b, d in cur.execute(
            "SELECT book_a, book_b, distance FROM jaccard WHERE distance < 0.96").fetchall()]
        note(" seuil |  arêtes | degré moyen | livres isolés")
        for seuil in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, SEUIL, 0.95):
            degree = {}
            edges = 0
            for a, b, d in close:
                if d < seuil:
                    degree[a] = degree.get(a, 0) + 1
                    degree[b] = degree.get(b, 0) + 1
                    edges += 1
            mark = "  <- seuil retenu" if seuil == SEUIL else ""
            note(f"  {seuil:.2f} | {edges:7d} | {2 * edges / total:11.1f} | {total - len(degree):6d}{mark}")

        degree = {b: 0 for b in all_ids}
        for a, b, d in close:
            if d < SEUIL:
                degree[a] += 1
                degree[b] += 1
        pr = {int(i): float(p) for i, p in cur.execute("SELECT id, pagerank FROM books").fetchall()}
        degs = [degree[b] for b in all_ids]
        prs = [pr[b] for b in all_ids]
        r = pearson(prs, degs)
        note(f"Degré : max {max(degs)}, moyenne {statistics.mean(degs):.1f}, médiane {statistics.median(degs)}, "
             f"isolés {sum(1 for d in degs if d == 0)}")
        note(f"PageRank : min {min(prs):.6f}, max {max(prs):.6f}, uniforme = {1 / total:.6f}")
        note(f"Corrélation de Pearson PageRank / degré : {r:.3f}")

        # ---------------- 5 : exemples de classement (pertinence) ----------------
        note("\n=== 5. Exemples de résultats (tri par score) ===")
        for q in ["whale", "sherlock", "love"]:
            best = search(cur, "books", "postings", tokenize(q), limit=3)
            note(f"« {q} » :")
            for book_id, title, occ, pr_rank, score in best:
                note(f"   {str(title)[:60]:60s} | {int(occ):5d} occ. | PageRank n° {int(pr_rank)}")
            if best:
                top = [int(b[0]) for b in best]
                sugg = cur.execute("""
                    SELECT b.title, MIN(j.distance) AS distance
                    FROM jaccard j
                    JOIN books b ON b.id = CASE WHEN j.book_a = ANY(%s) THEN j.book_b ELSE j.book_a END
                    WHERE (j.book_a = ANY(%s) OR j.book_b = ANY(%s)) AND j.distance < %s AND b.id <> ALL(%s)
                    GROUP BY b.id, b.title ORDER BY distance LIMIT 3
                """, (top, top, top, SEUIL, top)).fetchall()
                for title, distance in sugg:
                    note(f"      suggestion : {str(title)[:55]:55s} (distance {float(distance):.3f})")

        cur.execute("DROP TABLE IF EXISTS bench_postings")
        cur.execute("DROP TABLE IF EXISTS bench_books")

    # ---------------- Fichiers et figures ----------------
    with open(OUT / "mesures.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["test", "livres", "parametre", "moyenne_ms", "ecart_type_ms", "repetitions", "detail"])
        writer.writerows(rows)
    (OUT / "resume.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")

    plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.3})

    fig, ax = plt.subplots(figsize=(6, 4))
    for w in WORDS:
        ns, ms, ss = zip(*index_res[w])
        ax.errorbar(ns, ms, yerr=ss, marker="o", capsize=4, label=f"« {w} »")
    ax.set_xlabel("Nombre de livres dans la bibliothèque")
    ax.set_ylabel("Temps de réponse (ms)")
    ax.set_title("Recherche par mot-clé avec l'index inversé")
    ax.set_ylim(bottom=0)
    ax.legend(title="Mot cherché")
    fig.tight_layout()
    fig.savefig(OUT / "1_index.png", dpi=200)

    fig, ax = plt.subplots(figsize=(6, 4))
    for p in PATTERNS:
        ns, ms, ss = zip(*regex_res[p])
        ax.errorbar(ns, ms, yerr=ss, marker="o", capsize=4, label=f"automate : {p}")
    ns, ms, ss = zip(*re_res)
    ax.errorbar(ns, ms, yerr=ss, marker="s", capsize=4, linestyle="--", color="gray",
                label="module re (moyenne des motifs)")
    ax.set_xlabel("Nombre de livres dans la bibliothèque")
    ax.set_ylabel("Temps de filtrage du vocabulaire (ms)")
    ax.set_title("Recherche RegEx : automate du Projet 1 et module re")
    ax.set_ylim(bottom=0)
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "2_regex.png", dpi=200)

    if kmp_res:
        fig, ax = plt.subplots(figsize=(6, 4))
        xs = range(len(kmp_res))
        width = 0.38
        ax.bar([x - width / 2 for x in xs], [m for _, m, _ in kmp_res], width,
               yerr=[s for _, _, s in kmp_res], capsize=4, label="KMP sur le texte brut (Python)")
        ax.bar([x + width / 2 for x in xs], [m for _, m, _ in kmp_index_res], width,
               yerr=[s for _, _, s in kmp_index_res], capsize=4, label="Index inversé (PostgreSQL)")
        ax.set_xticks(list(xs))
        ax.set_xticklabels([str(n) for n, _, _ in kmp_res])
        ax.set_yscale("log")
        ax.set_xlabel("Nombre de livres parcourus")
        ax.set_ylabel("Temps pour un mot (ms, échelle logarithmique)")
        ax.set_title("Chercher un mot : parcours du texte ou index")
        ax.set_ylim(top=ax.get_ylim()[1] * 15)          # place pour la légende
        ax.legend(fontsize=9, loc="upper left")
        fig.tight_layout()
        fig.savefig(OUT / "3_kmp_index.png", dpi=200)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar([(b - 0.5) / 50 for b, _ in hist], [c for _, c in hist], width=1 / 50, color="tab:blue")
    ax.axvline(SEUIL, color="tab:red", linestyle="--", label=f"seuil du graphe : {SEUIL}")
    ax.set_yscale("log")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Distance de Jaccard entre deux livres")
    ax.set_ylabel("Nombre de paires (échelle logarithmique)")
    ax.set_title("Répartition des distances de Jaccard")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "4_distances.png", dpi=200)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(degs, prs, s=8, alpha=0.5)
    ax.axhline(1 / total, color="gray", linestyle=":", label="score uniforme 1/N")
    ax.set_xlabel("Degré du livre dans le graphe (nombre de voisins)")
    ax.set_ylabel("PageRank")
    ax.set_title(f"PageRank et degré (corrélation r = {r:.2f})")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "5_pagerank_degre.png", dpi=200)

    print(f"\nTerminé. Résultats dans {OUT} :")
    for name in sorted(p.name for p in OUT.iterdir()):
        print("  ", name)


if __name__ == "__main__":
    main()
