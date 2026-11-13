<script setup>
// Page principale.
//  - sans requête : page d'accueil (grand titre, recherche centrée, exemples)
//  - avec requête : résultats classés + carrousel de suggestions
// La recherche vit dans l'URL (?q=whale&mode=keyword&sort=score) :
// bouton "retour", liens partageables, rechargement de page.
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get } from '../api'
import BookCard from '../components/BookCard.vue'
import SuggestionCarousel from '../components/SuggestionCarousel.vue'
import SkeletonList from '../components/SkeletonList.vue'

const route = useRoute()
const router = useRouter()

const input = ref('')
const mode = ref('keyword')          // 'keyword' | 'regex'
const sort = ref('score')            // 'score' | 'occurrences' | 'pagerank'
const data = ref(null)
const loading = ref(false)
const error = ref('')
const stats = ref(null)

// Affichage progressif : 10 résultats, puis 10 de plus à chaque clic
const PAGE = 10
const visible = ref(PAGE)
const shown = computed(() => data.value?.results.slice(0, visible.value) || [])

const hasQuery = computed(() => !!route.query.q)

const EXAMPLES = [
  { q: 'whale', mode: 'keyword' },
  { q: 'love', mode: 'keyword' },
  { q: 'sherlock', mode: 'keyword' },
  { q: 'wh.le', mode: 'regex' },
  { q: 'colou*r', mode: 'regex' },
]
const SORTS = [
  { value: 'score', label: 'Pertinence' },
  { value: 'occurrences', label: 'Occurrences' },
  { value: 'pagerank', label: 'PageRank' },
]

function go(q = input.value, m = mode.value, s = sort.value) {
  if (!q.trim()) return
  router.push({ path: '/', query: { q: q.trim(), mode: m, sort: s } })
}

// Score relatif : le 1er résultat vaut 100 (plus lisible que 0.0000042)
const maxValue = computed(() => {
  const r = data.value?.results || []
  return r.length ? Math.max(...r.map((b) => b[sort.value === 'pagerank' ? 'pagerank' : sort.value] || 0)) : 0
})
const relative = (b) => {
  const v = b[sort.value === 'pagerank' ? 'pagerank' : sort.value] || 0
  return maxValue.value ? Math.round((100 * v) / maxValue.value) : 0
}

// Chaque changement d'URL relance la recherche.
// requestId : si l'utilisateur enchaîne deux recherches, on ignore la réponse
// de la plus ancienne si elle arrive en retard (condition de course).
let requestId = 0
watch(() => route.query, async (query) => {
  visible.value = PAGE          // nouvelle recherche : on repart à 10
  input.value = query.q || ''
  mode.value = query.mode === 'regex' ? 'regex' : 'keyword'
  sort.value = SORTS.some((s) => s.value === query.sort) ? query.sort : 'score'
  if (!query.q) { data.value = null; error.value = ''; return }

  const id = ++requestId
  loading.value = true
  error.value = ''
  try {
    const res = mode.value === 'regex'
      ? await get('/regex', { pattern: query.q, sort: sort.value })
      : await get('/search', { q: query.q, sort: sort.value })
    if (id === requestId) data.value = res
  } catch (e) {
    if (id === requestId) { error.value = e.message; data.value = null }
  } finally {
    if (id === requestId) loading.value = false
  }
}, { immediate: true })

// Chiffres de la page d'accueil (facultatifs : masqués si l'API ne répond pas)
onMounted(async () => {
  try { stats.value = await get('/stats') } catch { /* sans importance */ }
})
const fr = (n) => n?.toLocaleString('fr-FR')
</script>

<template>
  <!-- ===== Accueil ===== -->
  <section v-if="!hasQuery" class="hero">
    <p class="eyebrow">Moteur de recherche · Projet Gutenberg</p>
    <h1 class="hero-title">Trouvez votre prochain <em>livre</em>.</h1>
    <p class="hero-sub">
      Cherchez un mot ou une expression régulière dans toute la bibliothèque.
      Les résultats sont classés par pertinence et PageRank.
    </p>

    <form class="searchbox searchbox-lg" @submit.prevent="go()">
      <span class="searchbox-icon">⌕</span>
      <input v-model="input" :placeholder="mode === 'regex' ? 'Expression régulière : wh.le' : 'Un mot : whale, love…'"
             aria-label="Recherche" autofocus />
      <button type="submit">Rechercher</button>
    </form>
    <div class="segmented" role="radiogroup" aria-label="Type de recherche">
      <button :class="{ active: mode === 'keyword' }" @click="mode = 'keyword'">Mot-clé</button>
      <button :class="{ active: mode === 'regex' }" @click="mode = 'regex'">RegEx</button>
    </div>

    <div class="chips">
      <span class="muted small">Essayez :</span>
      <button v-for="ex in EXAMPLES" :key="ex.q" class="chip" :class="{ 'chip-regex': ex.mode === 'regex' }"
              @click="go(ex.q, ex.mode, 'score')">
        {{ ex.q }}
      </button>
    </div>

    <dl v-if="stats" class="stats">
      <div><dt>{{ fr(stats.books) }}</dt><dd>livres</dd></div>
      <div><dt>{{ fr(stats.words) }}</dt><dd>mots indexés</dd></div>
      <div><dt>{{ fr(stats.edges) }}</dt><dd>liens de similarité</dd></div>
    </dl>
  </section>

  <!-- ===== Résultats ===== -->
  <section v-else>
    <form class="searchbox" @submit.prevent="go()">
      <span class="searchbox-icon">⌕</span>
      <input v-model="input" aria-label="Recherche" />
      <button type="submit">Rechercher</button>
    </form>

    <div class="toolbar">
      <div class="segmented" role="radiogroup" aria-label="Type de recherche">
        <button :class="{ active: mode === 'keyword' }" @click="go(input, 'keyword')">Mot-clé</button>
        <button :class="{ active: mode === 'regex' }" @click="go(input, 'regex')">RegEx</button>
      </div>
      <div class="segmented" role="radiogroup" aria-label="Tri">
        <button v-for="s in SORTS" :key="s.value" :class="{ active: sort === s.value }"
                @click="go(input, mode, s.value)">{{ s.label }}</button>
      </div>
    </div>

    <p v-if="error" class="alert">{{ error }}</p>

    <SkeletonList v-else-if="loading && !data" />

    <template v-else-if="data">
      <p class="summary" :class="{ dim: loading }">
        <strong>{{ data.results.length }}</strong> livre{{ data.results.length > 1 ? 's' : '' }}
        <span class="dot">·</span> {{ data.time_ms }} ms
        <template v-if="mode === 'regex'">
          <span class="dot">·</span> {{ fr(data.n_matched_words) }} mot{{ data.n_matched_words > 1 ? 's' : '' }}
          du vocabulaire reconnu{{ data.n_matched_words > 1 ? 's' : '' }} par l'automate ({{ data.regex_ms }} ms)
        </template>
      </p>
      <div v-if="mode === 'regex' && data.matched_words?.length" class="chips chips-tight">
        <span v-for="w in data.matched_words.slice(0, 12)" :key="w" class="chip chip-static">{{ w }}</span>
        <span v-if="data.truncated" class="muted small">… limité aux 500 plus fréquents</span>
      </div>

      <div v-if="!data.results.length" class="empty-state">
        <p class="empty-icon">📖</p>
        <p>Aucun livre ne contient « {{ route.query.q }} ».</p>
        <p class="muted small">Essayez un autre mot, ou une RegEx plus large.</p>
      </div>

            <!-- Résultats d'abord, puis suggestions, sur tous les écrans -->
      <div v-else class="results-layout">
        <div class="results-block">
          <h2 class="section-title">Résultats</h2>
          <TransitionGroup name="list" tag="ol" class="results" :class="{ dim: loading }">
            <li v-for="(book, i) in shown" :key="book.id" :style="{ '--i': Math.min(i % PAGE, 10) }">
              <BookCard :book="book" :rank="i + 1" :relative="relative(book)" />
            </li>
          </TransitionGroup>
          <button v-if="visible < data.results.length" class="more" @click="visible += PAGE">
            Voir plus · {{ shown.length }} sur {{ data.results.length }}
          </button>
        </div>
        <SuggestionCarousel class="suggest-block" :books="data.suggestions"
                            hint="Livres voisins des 3 premiers résultats dans le graphe de Jaccard" />
      </div>
    </template>
  </section>
</template>
