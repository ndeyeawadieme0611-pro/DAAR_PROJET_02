// utils.js — Petites fonctions d'affichage partagées par les composants.

// Certains titres du catalogue contiennent des retours à la ligne (\r\n)
export const cleanTitle = (title) => (title || '').replace(/\s+/g, ' ').trim()

// "Melville, Herman, 1819-1891; Stedman, Arthur [Editor]"  ->  "Herman Melville"
export function shortAuthor(authors) {
  if (!authors) return 'Auteur inconnu'
  const first = authors.split(';')[0].replace(/\[.*?\]/g, '')
  const parts = first.split(',').map((p) => p.trim()).filter((p) => p && !/\d/.test(p))
  if (parts.length >= 2) return `${parts[1].replace(/\(.*?\)/g, '').trim()} ${parts[0]}`
  return parts[0] || 'Auteur inconnu'
}

// Distance de Jaccard -> libellé lisible. Les voisins ont tous d < 0,91 ;
// un pourcentage "1 - d" (ex. 17 %) laisserait croire qu'ils se ressemblent peu.
export function closeness(distance) {
  if (distance < 0.8) return 'Très proche'
  if (distance < 0.87) return 'Proche'
  return 'Voisin'
}

// Initiales du titre, en ignorant les articles : "The Time Machine" -> "TM"
const ARTICLES = new Set(['the', 'a', 'an', 'of', 'and', 'or', 'on', 'in', 'to'])
export function initials(title) {
  const words = cleanTitle(title).replace(/[^\p{L}\s]/gu, ' ').split(/\s+/)
  const kept = words.filter((w) => w && !ARTICLES.has(w.toLowerCase()))
  return (kept.length ? kept : words).slice(0, 2).map((w) => w[0].toUpperCase()).join('')
}

// 215384 -> "215 k" ; 7777551 -> "7,8 M"
export function compact(n) {
  if (n == null) return '—'
  if (n >= 1e6) return `${(n / 1e6).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} M`
  if (n >= 1e3) return `${Math.round(n / 1e3)} k`
  return String(n)
}

// Couleurs des reliures dessinées (toile sourde) : une par livre, toujours la même.
export const BOOK_COLORS = ['#2f5d46', '#7a2633', '#2a3d5c', '#a8773a', '#56677a', '#5b3a55', '#2e5e63', '#9a4e36']
export const bookColor = (id) => BOOK_COLORS[Math.abs(id * 7 + 3) % BOOK_COLORS.length]
// Décor doré de la couverture : 0 = filets, 1 = cadre, 2 = losange, 3 = bandeau
export const bookPattern = (id) => Math.abs(id * 13 + 5) % 4
