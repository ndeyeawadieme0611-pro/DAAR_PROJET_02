<script setup>
// Page principale.
//  - sans requête : accueil (bandeau de recherche, chiffres clés, fonctionnement)
//  - avec requête : console de recherche en trois colonnes
//      filtres (type, classement, détails de la requête) | tableau des résultats | ouvrages voisins
// La recherche vit dans l'URL (?q=whale&mode=keyword&sort=score) :
// bouton "retour", liens partageables, rechargement de page.
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { get } from '../api'
import ResultRow from '../components/ResultRow.vue'
import NeighborList from '../components/NeighborList.vue'
import SkeletonList from '../components/SkeletonList.vue'
import ShelfScene from '../components/ShelfScene.vue'
import OpenBook from '../components/OpenBook.vue'

const route = useRoute()
const router = useRouter()

const input = ref('')
const mode = ref('keyword')          // 'keyword' | 'regex'
const sort = ref('score')            // 'score' | 'occurrences' | 'pagerank'
const data = ref(null)
const loading = ref(false)
const error = ref('')
const stats = ref(null)

// Affichage progressif : 15 résultats, puis 15 de plus à chaque clic
const PAGE = 15
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
const MODES = [
  { value: 'keyword', label: 'Mot-clé', desc: "Mot exact dans l'index inversé" },
  { value: 'regex', label: 'Expression régulière', desc: 'Automate appliqué au vocabulaire' },
]
const SORTS = [
  { value: 'score', label: 'Pertinence', desc: '(occurrences / taille) × PageRank' },
  { value: 'occurrences', label: 'Occurrences', desc: "Nombre d'apparitions du terme" },
  { value: 'pagerank', label: 'PageRank', desc: 'Centralité dans le graphe de Jaccard' },
]
const sortLabel = computed(() => SORTS.find((s) => s.value === sort.value)?.label)

function go(q = input.value, m = mode.value, s = sort.value) {
  if (!q.trim()) return
  router.push({ path: '/', query: { q: q.trim(), mode: m, sort: s } })
}
// Sur la page de résultats, changer le type ou le tri relance la recherche
function setMode(m) { hasQuery.value ? go(input.value, m) : (mode.value = m) }

// Score relatif : le 1er résultat vaut 100 (plus lisible que 0.0000042)
const metric = computed(() => (sort.value === 'pagerank' ? 'pagerank' : sort.value))
const maxValue = computed(() => {
  const r = data.value?.results || []
  return r.length ? Math.max(...r.map((b) => b[metric.value] || 0)) : 0
})
const relative = (b) => (maxValue.value ? Math.round((100 * (b[metric.value] || 0)) / maxValue.value) : 0)

// Chaque changement d'URL relance la recherche.
// requestId : si l'utilisateur enchaîne deux recherches, on ignore la réponse
// de la plus ancienne si elle arrive en retard (condition de course).
let requestId = 0
watch(() => route.query, async (query) => {
  visible.value = PAGE          // nouvelle recherche : on repart au début
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
  <!-- ======================= Accueil ======================= -->
  <div v-if="!hasQuery" class="home">
    <section class="hero">
      <div class="hero-inner">
        <div class="hero-text">
        <p class="hero-eyebrow"><span class="rule" aria-hidden="true"></span>{{ stats ? fr(stats.books) : '1 678' }} classiques du Projet Gutenberg</p>
        <h1 class="hero-title">Quel livre cherchez-vous <em>aujourd'hui</em> ?</h1>
        <p class="hero-sub">Tapez un mot ou une expression régulière : Marque-page parcourt toute la bibliothèque
          et vous propose aussi des livres qui lui ressemblent.</p>

        <form class="query query-hero" @submit.prevent="go()" role="search">
          <div class="query-mode" role="radiogroup" aria-label="Type de recherche">
            <button v-for="m in MODES" :key="m.value" type="button" role="radio" :aria-checked="mode === m.value"
                    :class="{ active: mode === m.value }" @click="setMode(m.value)">
              {{ m.value === 'regex' ? 'RegEx' : m.label }}
            </button>
          </div>
          <svg class="query-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4.5 4.5" /></svg>
          <input v-model="input" :class="{ mono: mode === 'regex' }"
                 :placeholder="mode === 'regex' ? 'Expression régulière, ex. wh.le' : 'Mot-clé, ex. whale'"
                 aria-label="Recherche" autofocus autocomplete="off" spellcheck="false" />
          <button type="submit" class="btn-primary">Rechercher</button>
        </form>

        <p class="hero-examples">
          <span>Exemples</span>
          <button v-for="ex in EXAMPLES" :key="ex.q" class="example" :class="{ mono: ex.mode === 'regex' }"
                  @click="go(ex.q, ex.mode, 'score')">{{ ex.q }}</button>
        </p>
        </div>
        <ShelfScene class="hero-art" />
      </div>
    </section>

    <section class="home-body">
      <dl v-if="stats" class="kpis">
        <div class="kpi kpi-1"><dt>Œuvres indexées</dt><dd>{{ fr(stats.books) }}</dd></div>
        <div class="kpi kpi-2"><dt>Mots distincts</dt><dd>{{ fr(stats.words) }}</dd></div>
        <div class="kpi kpi-3"><dt>Liens de similarité</dt><dd>{{ fr(stats.edges) }}</dd></div>
      </dl>

      <h2 class="section-label">Fonctionnement</h2>
      <div class="features">
        <article class="feature">
          <span class="feature-icon" aria-hidden="true">I</span>
          <h3>Index inversé</h3>
          <p>Chaque mot est associé aux livres qui le contiennent et à son nombre d'occurrences :
             une recherche par mot-clé ne lit jamais les textes.</p>
        </article>
        <article class="feature">
          <span class="feature-icon" aria-hidden="true">II</span>
          <h3>Automate pour les RegEx</h3>
          <p>L'expression est compilée en automate (NFA, puis DFA minimisé) et testée sur le vocabulaire
             de l'index, puis les livres correspondants sont rassemblés.</p>
        </article>
        <article class="feature">
          <span class="feature-icon" aria-hidden="true">III</span>
          <h3>PageRank sur le graphe de Jaccard</h3>
          <p>Deux livres sont reliés quand leurs vocabulaires sont proches. Le PageRank mesure la
             centralité de chaque livre et sert au classement et aux suggestions.</p>
        </article>
      </div>
    </section>
  </div>

  <!-- ======================= Résultats ======================= -->
  <div v-else class="workspace">
    <form class="query query-bar" @submit.prevent="go()" role="search">
      <svg class="query-icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4.5 4.5" /></svg>
      <input v-model="input" :class="{ mono: mode === 'regex' }" aria-label="Recherche" autocomplete="off" spellcheck="false" />
      <button type="submit" class="btn-primary">Rechercher</button>
    </form>

    <div class="console">
      <!-- Colonne de gauche : réglages et détails de la requête -->
      <aside class="filters">
        <fieldset class="filter-group">
          <legend>Type de recherche</legend>
          <label v-for="m in MODES" :key="m.value" class="option" :class="{ active: mode === m.value }">
            <input type="radio" name="mode" :value="m.value" :checked="mode === m.value" @change="setMode(m.value)" />
            <span class="option-text"><span class="option-label">{{ m.label }}</span><span class="option-desc">{{ m.desc }}</span></span>
          </label>
        </fieldset>

        <fieldset class="filter-group">
          <legend>Classement</legend>
          <label v-for="s in SORTS" :key="s.value" class="option" :class="{ active: sort === s.value }">
            <input type="radio" name="sort" :value="s.value" :checked="sort === s.value" @change="go(input, mode, s.value)" />
            <span class="option-text"><span class="option-label">{{ s.label }}</span><span class="option-desc">{{ s.desc }}</span></span>
          </label>
        </fieldset>

        <div v-if="data" class="filter-group">
          <p class="legend">Requête</p>
          <dl class="facts">
            <div><dt>Résultats</dt><dd>{{ fr(data.results.length) }}</dd></div>
            <div><dt>Temps total</dt><dd>{{ data.time_ms }} ms</dd></div>
            <template v-if="mode === 'regex'">
              <div><dt>Mots reconnus</dt><dd>{{ fr(data.n_matched_words) }}</dd></div>
              <div><dt>Automate</dt><dd>{{ data.regex_ms }} ms</dd></div>
            </template>
          </dl>
          <div v-if="mode === 'regex' && data.matched_words?.length" class="tokens">
            <code v-for="w in data.matched_words.slice(0, 12)" :key="w" class="token">{{ w }}</code>
            <span v-if="data.truncated" class="option-desc">limité aux 500 plus fréquents</span>
          </div>
        </div>
      </aside>

      <!-- Colonne centrale : tableau des résultats -->
      <section class="results-main">
        <div v-if="error" class="notice notice-error" role="alert">
          <strong>La recherche a échoué.</strong> {{ error }}
        </div>

        <SkeletonList v-else-if="loading && !data" />

        <template v-else-if="data">
          <header class="results-head" :class="{ dim: loading }">
            <h1 class="results-title">
              {{ fr(data.results.length) }} œuvre{{ data.results.length > 1 ? 's' : '' }}
              pour <span class="q" :class="{ mono: mode === 'regex' }">{{ route.query.q }}</span>
            </h1>
            <p class="results-sub">Classées par {{ sort === 'pagerank' ? 'PageRank' : sortLabel?.toLowerCase() }} · {{ data.time_ms }} ms</p>
          </header>

          <div v-if="!data.results.length" class="empty">
            <OpenBook />
            <p class="empty-title">Aucune œuvre ne correspond à cette recherche.</p>
            <p>Essayez un autre mot, ou une expression régulière plus large.</p>
          </div>

          <div v-else class="table-card" :class="{ dim: loading }">
            <table class="results-table">
              <thead>
                <tr>
                  <th class="col-rank">#</th>
                  <th>Œuvre</th>
                  <th class="col-num">Occ.</th>
                  <th class="col-num">Mots</th>
                  <th class="col-num">PageRank</th>
                  <th class="col-score">Pertinence</th>
                </tr>
              </thead>
              <TransitionGroup name="list" tag="tbody">
                <ResultRow v-for="(book, i) in shown" :key="book.id" :book="book" :rank="i + 1"
                           :relative="relative(book)" :style="{ '--i': Math.min(i % PAGE, 12) }" />
              </TransitionGroup>
            </table>
            <button v-if="visible < data.results.length" class="more" @click="visible += PAGE">
              Afficher plus · {{ shown.length }} sur {{ data.results.length }}
            </button>
          </div>
        </template>
      </section>

      <!-- Colonne de droite : suggestions -->
      <NeighborList v-if="data && data.results.length" class="suggestions" :books="data.suggestions"
                    title="Suggestions"
                    hint="Voisins des 3 premiers résultats dans le graphe de Jaccard" />
    </div>
  </div>
</template>
