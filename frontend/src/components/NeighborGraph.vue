<script setup>
// Mini-graphe : le livre au centre, ses voisins de Jaccard autour.
// Plus un voisin est proche (distance faible), plus il est près du centre
// et plus son arête est épaisse.
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { cleanTitle, hueOf, initials } from '../utils'

const props = defineProps({
  book: { type: Object, required: true },
  neighbors: { type: Array, default: () => [] },
})
const router = useRouter()

const W = 640, H = 340, CX = W / 2, CY = H / 2
const R_MIN = 80, R_MAX = 135

const nodes = computed(() => {
  const ds = props.neighbors.map((n) => n.distance)
  const lo = Math.min(...ds), hi = Math.max(...ds)
  return props.neighbors.map((n, i) => {
    const t = hi > lo ? (n.distance - lo) / (hi - lo) : 0.5      // 0 = le plus proche
    const r = R_MIN + t * (R_MAX - R_MIN)
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / props.neighbors.length
    const x = CX + r * Math.cos(a), y = CY + r * Math.sin(a)
    const label = cleanTitle(n.title)
    // Étiquette à l'extérieur du cercle : à gauche des nœuds de gauche,
    // à droite des nœuds de droite, au-dessus/dessous pour ceux du milieu.
    const side = x < CX - 15 ? 'left' : x > CX + 15 ? 'right' : y < CY ? 'top' : 'bottom'
    const lx = side === 'left' ? x - 24 : side === 'right' ? x + 24 : x
    const ly = side === 'top' ? y - 25 : side === 'bottom' ? y + 33 : y + 4
    const anchor = side === 'left' ? 'end' : side === 'right' ? 'start' : 'middle'
    return {
      ...n, x, y, lx, ly, anchor,
      width: 4 - 3 * t,                                     // arête de 4 px à 1 px
      label: label.length > 24 ? label.slice(0, 23) + '…' : label,
    }
  })
})
const color = (id) => `hsl(${hueOf(id)} 38% 40%)`
</script>

<template>
  <svg :viewBox="`0 0 ${W} ${H}`" class="graph" role="img"
       :aria-label="`Graphe des ${neighbors.length} livres voisins`">
    <line v-for="n in nodes" :key="'e' + n.id" :x1="CX" :y1="CY" :x2="n.x" :y2="n.y"
          class="graph-edge" :stroke-width="n.width" />

    <g v-for="n in nodes" :key="'n' + n.id" class="graph-node" tabindex="0"
       @click="router.push(`/books/${n.id}`)" @keydown.enter="router.push(`/books/${n.id}`)">
      <title>{{ cleanTitle(n.title) }} — distance {{ n.distance.toFixed(2) }}</title>
      <circle :cx="n.x" :cy="n.y" r="17" :fill="color(n.id)" />
      <text :x="n.x" :y="n.y + 4" class="graph-initials">{{ initials(n.title) }}</text>
      <text :x="n.lx" :y="n.ly" :text-anchor="n.anchor" class="graph-label">{{ n.label }}</text>
    </g>

    <circle :cx="CX" :cy="CY" r="27" :fill="color(book.id)" class="graph-center" />
    <text :x="CX" :y="CY + 6" class="graph-initials graph-initials-lg">{{ initials(book.title) }}</text>
  </svg>
</template>
