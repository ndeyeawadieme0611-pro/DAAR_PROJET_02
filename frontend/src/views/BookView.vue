<script setup>
// Page d'un livre : couverture, métadonnées, mini-graphe des voisins, extrait.
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { get } from '../api'
import { cleanTitle, shortAuthor } from '../utils'
import BookCover from '../components/BookCover.vue'
import NeighborGraph from '../components/NeighborGraph.vue'
import SuggestionCarousel from '../components/SuggestionCarousel.vue'

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
  <button class="back" @click="router.back()">← Retour</button>

  <p v-if="error" class="alert">{{ error }}</p>

  <div v-else-if="!book" class="book-hero skeleton">
    <div class="sk sk-cover-lg"></div>
    <div class="result-body">
      <div class="sk sk-line w60 tall"></div>
      <div class="sk sk-line w35"></div>
      <div class="sk sk-line w80"></div>
    </div>
  </div>

  <article v-else>
    <header class="book-hero">
      <BookCover :id="book.id" :title="book.title" size="lg" />
      <div>
        <p class="eyebrow">Gutenberg n° {{ book.id }}</p>
        <h1 class="book-title">{{ cleanTitle(book.title) }}</h1>
        <p class="book-author">{{ shortAuthor(book.authors) }}</p>
        <dl class="stats stats-inline">
          <div><dt>{{ fr(book.word_count) }}</dt><dd>mots</dd></div>
          <div v-if="book.pr_rank"><dt>n° {{ book.pr_rank }}</dt><dd>au PageRank</dd></div>
          <div><dt>{{ book.neighbors.length }}</dt><dd>voisins</dd></div>
        </dl>
        <a class="button-link" :href="`https://www.gutenberg.org/ebooks/${book.id}`" target="_blank" rel="noopener">
          Lire sur gutenberg.org ↗
        </a>
      </div>
    </header>

    <section class="panel">
      <h2>Livres voisins</h2>
      <p class="muted small">
        Graphe de Jaccard : plus un livre est proche du centre et relié par un trait épais,
        plus son vocabulaire ressemble à celui-ci. Cliquez sur un nœud pour l'ouvrir.
      </p>
      <NeighborGraph v-if="book.neighbors.length" :book="book" :neighbors="book.neighbors" />
      <p v-else class="empty-state small">Ce livre est isolé : aucun autre livre ne lui ressemble assez.</p>
    </section>

    <SuggestionCarousel :books="book.neighbors" title="À lire ensuite" />

    <section class="panel">
      <h2>Extrait</h2>
      <pre class="excerpt">{{ book.excerpt }}</pre>
    </section>
  </article>
</template>
