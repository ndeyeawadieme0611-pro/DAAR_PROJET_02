<script setup>
// Une ligne du tableau de résultats : rang, ouvrage (couverture dessinée, titre, auteur),
// occurrences, taille, rang PageRank et barre de pertinence relative.
// Sur mobile, la ligne se replie en bloc (voir style.css, .results-table).
import { useRouter } from 'vue-router'
import { cleanTitle, shortAuthor, compact } from '../utils'
import BookArt from './BookArt.vue'

const props = defineProps({
  book: { type: Object, required: true },
  rank: { type: Number, required: true },
  relative: { type: Number, default: 0 },   // score relatif au 1er résultat (0-100)
})
const router = useRouter()
const open = () => router.push(`/books/${props.book.id}`)
</script>

<template>
  <tr class="row" @click="open">
    <td class="col-rank">{{ rank }}</td>
    <td class="col-work">
      <div class="work">
        <BookArt :id="book.id" :title="book.title" size="xs" />
        <span class="work-text">
          <RouterLink :to="`/books/${book.id}`" class="work-title" @click.stop>{{ cleanTitle(book.title) }}</RouterLink>
          <span class="work-author">{{ shortAuthor(book.authors) }}</span>
        </span>
      </div>
    </td>
    <td class="col-num" data-label="Occurrences">{{ book.occurrences?.toLocaleString('fr-FR') }}</td>
    <td class="col-num" data-label="Mots">{{ compact(book.word_count) }}</td>
    <td class="col-num" data-label="PageRank">{{ book.pr_rank ? `n° ${book.pr_rank}` : '—' }}</td>
    <td class="col-score" data-label="Pertinence">
      <span class="meter" role="img" :aria-label="`Pertinence ${relative} sur 100`">
        <span class="meter-fill" :style="{ width: relative + '%' }"></span>
      </span>
      <span class="meter-num">{{ relative }}</span>
    </td>
  </tr>
</template>
