<script setup>
// Liste des ouvrages voisins dans le graphe de Jaccard (suggestions).
// La barre montre la similarité : plus la distance est faible, plus elle est longue.
import { cleanTitle, shortAuthor, closeness } from '../utils'
import BookArt from './BookArt.vue'

defineProps({
  books: { type: Array, default: () => [] },
  title: { type: String, default: 'Ouvrages voisins' },
  hint: { type: String, default: '' },
})

// Les voisins ont tous une distance < 0,91 : on étale [0,6 ; 0,91] sur la barre
const similarity = (d) => Math.max(6, Math.min(100, Math.round(((0.91 - d) / 0.31) * 100)))
</script>

<template>
  <section class="panel neighbors">
    <header class="panel-head">
      <h2 class="panel-title">{{ title }}</h2>
      <p v-if="hint" class="panel-hint">{{ hint }}</p>
    </header>
    <ol v-if="books.length" class="neighbor-list">
      <li v-for="b in books" :key="b.id">
        <RouterLink :to="`/books/${b.id}`" class="neighbor">
          <BookArt :id="b.id" :title="b.title" size="xs" />
          <span class="neighbor-body">
          <span class="neighbor-title">{{ cleanTitle(b.title) }}</span>
          <span class="neighbor-author">{{ shortAuthor(b.authors) }}</span>
          <span class="neighbor-sim" :title="`Distance de Jaccard : ${b.distance.toFixed(3)}`">
            <span class="sim-bar"><span class="sim-fill" :style="{ width: similarity(b.distance) + '%' }"></span></span>
            <span class="sim-label" :class="{ strong: b.distance < 0.8 }">{{ closeness(b.distance) }}</span>
            <span class="sim-dist">d = {{ b.distance.toFixed(2) }}</span>
          </span>
          </span>
        </RouterLink>
      </li>
    </ol>
    <p v-else class="panel-empty">Aucun ouvrage voisin pour ces résultats.</p>
  </section>
</template>
