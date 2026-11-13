<script setup>
// Une ligne de résultat : couverture, titre, auteur, badges, barre de score.
import BookCover from './BookCover.vue'
import { cleanTitle, shortAuthor, compact } from '../utils'

defineProps({
  book: { type: Object, required: true },
  rank: { type: Number, required: true },
  relative: { type: Number, default: 0 },   // score relatif au 1er résultat (0-100)
})
</script>

<template>
  <RouterLink :to="`/books/${book.id}`" class="card result">
    <span class="rank">{{ rank }}</span>
    <BookCover :id="book.id" :title="book.title" size="sm" />
    <div class="result-body">
      <h3 class="result-title">{{ cleanTitle(book.title) }}</h3>
      <p class="result-author">{{ shortAuthor(book.authors) }}</p>
      <div class="badges">
        <span class="badge badge-accent">{{ book.occurrences }} occurrence{{ book.occurrences > 1 ? 's' : '' }}</span>
        <span v-if="book.word_count" class="badge">{{ compact(book.word_count) }} mots</span>
        <span v-if="book.pr_rank" class="badge">PageRank n° {{ book.pr_rank }}</span>
      </div>
      <div class="score">
        <div class="score-bar"><div class="score-fill" :style="{ width: relative + '%' }"></div></div>
        <span class="score-num">{{ relative }}</span>
      </div>
    </div>
  </RouterLink>
</template>
