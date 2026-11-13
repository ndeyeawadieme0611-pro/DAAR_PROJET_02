-- Charge excerpts.csv dans books.excerpt (à lancer sur la base du serveur).
ALTER TABLE books ADD COLUMN IF NOT EXISTS excerpt TEXT;
UPDATE books b SET excerpt = e.excerpt FROM books_excerpt_tmp e WHERE b.id = e.id;
DROP TABLE books_excerpt_tmp;
SELECT count(*) AS livres, count(excerpt) AS avec_extrait FROM books;
