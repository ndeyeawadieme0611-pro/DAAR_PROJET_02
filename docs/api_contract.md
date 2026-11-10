# Contrat d'API — Moteur de recherche Gutenberg

Ce document fixe **ce que le frontend envoie** et **ce que le backend répond**.
Maissa (données) et Awa (FastAPI) s'engagent dessus ; le frontend Vue peut être
développé sur des données factices qui respectent exactement ces formats.

Base : `/api` (Nginx redirige `/api/*` vers FastAPI). Format : JSON, UTF-8.

## Objet `Book` (résumé d'un livre)

```json
{
  "id": 1342,
  "title": "Pride and Prejudice",
  "authors": "Austen, Jane",
  "word_count": 122000,
  "pagerank": 0.00231
}
```

## 1. Recherche classique — `GET /api/search?q=<mot>&limit=20`

Recherche d'un mot (ou facteur) dans l'index inversé / par KMP.
Résultats triés par **pertinence** (nombre d'occurrences pondéré) puis **pagerank**.

```json
{
  "query": "love",
  "mode": "classic",
  "total": 312,
  "took_ms": 14,
  "results": [
    { "book": { "id": 1342, "title": "...", "authors": "...", "word_count": 122000, "pagerank": 0.0023 },
      "occurrences": 94,
      "score": 0.87 }
  ]
}
```

## 2. Recherche avancée — `GET /api/advanced-search?regex=<RegEx>&limit=20`

Expression régulière (cours : concaténation, `|`, `*`, `.`, parenthèses) via l'automate.

```json
{
  "query": "S(a|g|r)+on",
  "mode": "regex",
  "total": 12,
  "took_ms": 230,
  "results": [ { "book": { ... }, "occurrences": 5, "score": 0.5 } ]
}
```

## 3. Suggestions — `GET /api/books/{id}/suggestions?limit=5`

Livres proches d'un livre, selon le graphe de Jaccard.

**Sémantique de `distance`** : plus la valeur est **petite**, plus les livres
sont **similaires**. Une arête existe seulement si `distance < 0.91`.
La table SQL `jaccard(book_a, book_b, distance)` est stockée dans **un seul
sens** (`book_a < book_b`) ; le backend doit donc interroger les deux colonnes :

```sql
SELECT CASE WHEN book_a = %s THEN book_b ELSE book_a END AS voisin, distance
FROM jaccard WHERE book_a = %s OR book_b = %s
ORDER BY distance LIMIT 5;
```

```json
{
  "book_id": 1342,
  "suggestions": [
    { "book": { "id": 158, "title": "Emma", "authors": "Austen, Jane", "word_count": 160000, "pagerank": 0.0019 },
      "distance": 0.42 }
  ]
}
```

Si le livre n'a aucun voisin : `"suggestions": []`.

## 4. Détail d'un livre — `GET /api/books/{id}`

Retourne un objet `Book`. `404` si inconnu.

## Erreurs

```json
{ "error": "regex_invalid", "message": "Parenthèse non fermée en position 4" }
```

| Code | Cas |
|------|-----|
| 400  | paramètre manquant ou regex invalide |
| 404  | livre inconnu |
| 500  | erreur serveur |

## Santé — `GET /api/health` → `{"status": "ok"}`
