<script setup>
// Page d'un livre : en-tête et chiffres clés, graphe des voisins, liste des voisins, extrait.
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '../api'
import { cleanTitle, shortAuthor } from '../utils'
import NeighborGraph from '../components/NeighborGraph.vue'
import NeighborList from '../components/NeighborList.vue'
import BookArt from '../components/BookArt.vue'

const props = defineProps({ id: String })
const router = useRouter()
const book = ref(null)
const error = ref('')

// "watch" (et pas onMounted) : cliquer sur un voisin garde la même page
// mais change l'id ; il faut recharger à chaque changement.
watch(() => props.id, async (id) => {
  book.value = null
  error.value = ''
  try { book.value = await get(`/books/${id}`) } catch (e) { error.value = e.message }
}, { immediate: true })

const fr = (n) => n?.toLocaleString('fr-FR')
</script>

<template>
  <div class="page">
    <nav class="breadcrumb" aria-label="Fil d'Ariane">
      <button class="link-btn" @click="router.back()">← Résultats</button>
      <span aria-hidden="true">/</span>
      <span class="breadcrumb-current">{{ book ? cleanTitle(book.title) : 'Œuvre' }}</span>
    </nav>

    <div v-if="error" class="notice notice-error" role="alert"><strong>Œuvre introuvable.</strong> {{ error }}</div>

    <div v-else-if="!book" class="book-head">
      <div class="sk w35 thin"></div>
      <div class="sk w60 tall"></div>
      <div class="sk w15"></div>
    </div>

    <article v-else>
      <header class="book-head book-head-art">
        <BookArt :id="book.id" :title="book.title" size="lg" />
        <div class="book-head-text">
        <p class="book-eyebrow">Gutenberg n° {{ book.id }}</p>
        <h1 class="book-title">{{ cleanTitle(book.title) }}</h1>
        <p class="book-author">{{ shortAuthor(book.authors) }}</p>
        <a class="btn-secondary" :href="`https://www.gutenberg.org/ebooks/${book.id}`" target="_blank" rel="noopener">
          Lire sur gutenberg.org ↗
        </a>
        </div>
      </header>

      <dl class="kpis kpis-book">
        <div class="kpi kpi-1"><dt>Longueur</dt><dd>{{ fr(book.word_count) }} <small>mots</small></dd></div>
        <div class="kpi kpi-2"><dt>Rang PageRank</dt><dd>{{ book.pr_rank ? `n° ${book.pr_rank}` : '—' }}</dd></div>
        <div class="kpi kpi-3"><dt>Voisins (Jaccard)</dt><dd>{{ book.neighbors.length }}</dd></div>
      </dl>

      <div class="book-grid">
        <section class="panel">
          <header class="panel-head">
            <h2 class="panel-title">Graphe de similarité</h2>
            <p class="panel-hint">Plus un voisin est proche du centre et relié par un trait épais,
              plus son vocabulaire ressemble à celui de cette œuvre. Cliquez sur un nœud pour l'ouvrir.</p>
          </header>
          <NeighborGraph v-if="book.neighbors.length" :book="book" :neighbors="book.neighbors" />
          <p v-else class="panel-empty">Cette œuvre est isolée : aucune autre ne lui ressemble assez.</p>
        </section>

        <NeighborList :books="book.neighbors" title="À lire ensuite" hint="Classés par distance de Jaccard" />
      </div>

      <section class="panel">
        <header class="panel-head"><h2 class="panel-title">Extrait</h2></header>
        <pre class="excerpt">{{ book.excerpt }}</pre>
      </section>
    </article>
  </div>
</template>
