# DAAR — Projet 2 : moteur de recherche d'une bibliothèque

Moteur de recherche sur **1 678 livres** du Projet Gutenberg : recherche par mot-clé
(index inversé), recherche avancée par RegEx (automate du Projet 1), classement par
PageRank dans un graphe de Jaccard, suggestions de livres voisins.

- **Application en ligne** : http://13.49.215.251 (taper `http://` devant l'adresse)
- **Auteures** : Maïssa Saad, Ndeye Awa Dieme — M2 Sorbonne Université, 2026-2027

## Architecture

```
Navigateur ──HTTP:80──> Nginx (site Vue + relais /api) ──> API FastAPI ──> PostgreSQL
```

| Dossier | Contenu |
|---------|---------|
| `backend/scripts/` | préparation des données : téléchargement, déduplication, index, graphe, PageRank |
| `backend/app/` | API FastAPI (`main.py`), automate RegEx (`regex/`), KMP (`search/kmp.py`) |
| `backend/tests/` | tests unitaires (KMP, automate) |
| `frontend/` | interface Vue 3 (Vite) |
| `benchmarks/` | tests de performance et figures du rapport |
| `deploy/`, `docker-compose.prod.yml` | déploiement (Docker Compose, Nginx) |
| `docs/` | contrat d'API |
| `.github/workflows/` | intégration continue (tests, construction des images Docker) |

## Données : provenance

Tous les textes viennent du [Projet Gutenberg](https://www.gutenberg.org) :
catalogue `https://www.gutenberg.org/cache/epub/feeds/pg_catalog.csv`, textes
`https://www.gutenberg.org/cache/epub/<id>/pg<id>.txt`. Seuls les livres en anglais
d'au moins 10 000 mots sont gardés.

Les textes et la base (environ 916 Mo) ne sont **pas** dans l'archive : les scripts
ci-dessous les reconstruisent.

## Lancer le projet en local

Prérequis : Python 3.10 ou plus, Docker, Node.js 20.

### 1. Base PostgreSQL

Créer un fichier `.env` à la racine :

```
POSTGRES_DB=library
POSTGRES_USER=daar
POSTGRES_PASSWORD=un_mot_de_passe
```

```bash
docker compose up -d                 # PostgreSQL 18, joignable sur localhost:5433
pip install -r backend/requirements.txt
```

Les scripts et l'API lisent la variable `DATABASE_URL` :

```bash
# Linux / macOS
export DATABASE_URL="postgresql://daar:un_mot_de_passe@localhost:5433/library"
# Windows PowerShell
$env:DATABASE_URL="postgresql://daar:un_mot_de_passe@localhost:5433/library"
```

### 2. Reconstruire les données

À lancer dans cet ordre, depuis la racine du dépôt :

```bash
python -u backend/scripts/download_books.py 1700   # télécharge les livres dans data/raw
python -u backend/scripts/build_index.py           # tables books, postings, vocab
python -u backend/scripts/build_graph.py           # table jaccard (distances entre livres)
python -u backend/scripts/deduplicate.py           # écarte les doublons (distance < 0,05)
python -u backend/scripts/download_books.py 1700   # complète après la déduplication
python -u backend/scripts/build_index.py           # index définitif
python -u backend/scripts/build_graph.py           # graphe définitif
python -u backend/scripts/pagerank.py              # colonne books.pagerank
```

Attention : `build_index.py` supprime et recrée les tables `books`, `postings` et `vocab`.

Dernière étape, l'extrait affiché sur la page d'un livre (colonne `books.excerpt`) :

```bash
python backend/scripts/export_excerpts.py          # crée data/processed/excerpts.csv
docker compose exec -T db psql -U daar -d library -c "CREATE TABLE books_excerpt_tmp(id int, excerpt text);"
docker compose exec -T db psql -U daar -d library -c "\copy books_excerpt_tmp FROM STDIN CSV HEADER" < data/processed/excerpts.csv
docker compose exec -T db psql -U daar -d library < deploy/load_excerpts.sql
```

### 3. API et interface

```bash
cd backend
uvicorn app.main:app --reload --port 8000          # API : http://localhost:8000/docs
```

```bash
cd frontend
npm install
npm run dev                                        # site : http://localhost:5173
```

En développement, Vite relaie `/api` vers `http://localhost:8000`.

## Tests

```bash
pip install pytest
python -m pytest backend -q                        # 19 tests : KMP et automate RegEx
```

## Tests de performance

```bash
pip install matplotlib
python benchmarks/benchmark.py                     # environ 10 minutes
```

Résultats dans `benchmarks/results/` : cinq figures, `mesures.csv` et `resume.txt`.
Le script travaille sur des tables temporaires et ne modifie pas la base.

## Déploiement

Sur le serveur (Docker installé, fichier `.env` comme ci-dessus), les trois conteneurs
(PostgreSQL, API, Nginx) se lancent avec :

```bash
docker compose -f docker-compose.prod.yml --env-file ~/daar/.env up -d --build
```

Seul le port 80 est ouvert ; la base n'est pas joignable depuis Internet. La base est
transférée depuis une machine de développement avec `pg_dump -Fc` puis `pg_restore`.

Vérification : `curl http://localhost/api/stats` doit renvoyer
`{"books":1678,"words":495384,"edges":16929}`.

## API

Quatre routes, décrites dans [`docs/api_contract.md`](docs/api_contract.md) :
`/search`, `/regex`, `/books/{id}` et `/stats`.