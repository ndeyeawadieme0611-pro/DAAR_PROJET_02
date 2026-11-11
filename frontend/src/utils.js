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

// Couleur propre à chaque livre : l'id est multiplié par l'angle d'or (137,5°),
// ce qui répartit les teintes sur le cercle chromatique sans répétition visible.
export const hueOf = (id) => Math.round((id * 137.508) % 360)

export function coverStyle(id) {
  const h = hueOf(id)
  return {
    background: `linear-gradient(145deg, hsl(${h} 38% 42%), hsl(${(h + 30) % 360} 44% 25%))`,
  }
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
