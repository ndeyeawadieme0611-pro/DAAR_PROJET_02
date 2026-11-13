// api.js — Appels à l'API FastAPI, via le proxy Vite (/api -> localhost:8000).
// Un seul port à exposer : le téléphone parle au front, qui relaie vers l'API.
export const API_URL = import.meta.env.VITE_API_URL || `${window.location.origin}/api`

export async function get(path, params = {}) {
  const url = new URL(API_URL + path, window.location.origin)
  for (const [key, value] of Object.entries(params)) url.searchParams.set(key, value)

  let res
  try {
    res = await fetch(url)
  } catch {
    throw new Error("L'API est injoignable. Le serveur est-il lancé ?")
  }
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch { /* pas de JSON */ }
    throw new Error(`Erreur ${res.status} : ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`)
  }
  return res.json()
}
