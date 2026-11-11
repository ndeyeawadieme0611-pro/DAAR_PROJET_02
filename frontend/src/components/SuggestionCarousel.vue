<script setup>
// Suggestions : cartes qui défilent horizontalement (glisser au doigt sur mobile).
import { ref } from 'vue'
import BookCover from './BookCover.vue'
import { cleanTitle, shortAuthor, closeness } from '../utils'

defineProps({
  books: { type: Array, default: () => [] },
  title: { type: String, default: 'Vous aimerez aussi' },
  hint: { type: String, default: '' },
})

const track = ref(null)
const scroll = (dir) => track.value?.scrollBy({ left: dir * track.value.clientWidth * 0.8, behavior: 'smooth' })
</script>

<template>
  <section v-if="books.length" class="carousel">
    <div class="carousel-head">
      <div>
        <h2>{{ title }}</h2>
        <p v-if="hint" class="muted small">{{ hint }}</p>
      </div>
      <div class="carousel-nav">
        <button class="icon-btn" @click="scroll(-1)" aria-label="Précédent">‹</button>
        <button class="icon-btn" @click="scroll(1)" aria-label="Suivant">›</button>
      </div>
    </div>
    <div class="carousel-track" ref="track">
      <RouterLink v-for="b in books" :key="b.id" :to="`/books/${b.id}`" class="card mini">
        <BookCover :id="b.id" :title="b.title" size="md" />
        <h3 class="mini-title">{{ cleanTitle(b.title) }}</h3>
        <p class="muted small">{{ shortAuthor(b.authors) }}</p>
        <span class="badge" :class="{ 'badge-accent': b.distance < 0.8 }"
              :title="`Distance de Jaccard : ${b.distance.toFixed(2)}`">{{ closeness(b.distance) }}</span>
      </RouterLink>
    </div>
  </section>
</template>
