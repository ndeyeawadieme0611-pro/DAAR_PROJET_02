<!--
  Illustration de l'accueil : une étagère en noyer avec une plante dans un
  pot en céramique, des reliures en toile à nervures dorées, un livre penché,
  une pile de livres et, au sommet, un livre ouvert avec son marque-page.
  Dessin original en SVG ; les reliures sont générées à partir d'une petite liste.
-->
<script setup>
import { BOOK_COLORS } from '../utils'

const SHELF_Y = 262
const GOLD = '#c9a45c'
// [largeur, hauteur, couleur] pour chaque livre debout
const SPINES = [
  [26, 156, 1], [22, 132, 2], [30, 176, 0], [20, 140, 3], [28, 162, 5],
  [22, 128, 4], [26, 180, 6], [24, 148, 7], [20, 136, 2],
]
let x = 104
const spines = SPINES.map(([w, h, c]) => {
  const s = { x, w, h, y: SHELF_Y - h, color: BOOK_COLORS[c] }
  x += w + 2
  return s
})
const leanX = x + 4
// pile : [largeur, couleur]
const STACK = [[152, 2], [142, 7], [148, 0], [138, 1], [146, 4]]
const stack = STACK.map(([w, c], i) => ({ w, color: BOOK_COLORS[c], y: SHELF_Y - 21 * (i + 1), x: 384 + (152 - w) / 2 + (i % 2 ? 4 : -2) }))
const stackTop = SHELF_Y - 21 * STACK.length
</script>

<template>
  <svg class="shelf-scene" viewBox="0 0 560 300" role="img"
       aria-label="Une étagère de livres reliés, une pile de livres et un livre ouvert avec son marque-page">
    <!-- plante -->
    <g class="plant">
      <path d="M58 200 C56 172 50 152 42 136" />
      <path d="M58 200 C60 170 68 150 80 134" />
      <path d="M58 200 C58 172 58 144 60 118" />
      <ellipse cx="40" cy="132" rx="13" ry="7" transform="rotate(-35 40 132)" />
      <ellipse cx="82" cy="130" rx="13" ry="7" transform="rotate(30 82 130)" />
      <ellipse cx="60" cy="112" rx="7" ry="13" />
      <ellipse cx="46" cy="162" rx="12" ry="6.5" transform="rotate(25 46 162)" />
      <ellipse cx="72" cy="156" rx="12" ry="6.5" transform="rotate(-25 72 156)" />
    </g>
    <path d="M28 198 H90 L84 256 Q83 262 78 262 H40 Q35 262 34 256 Z" class="pot" />
    <path d="M28 198 H90" :stroke="GOLD" stroke-width="2" />
    <path d="M31 214 H87" :stroke="GOLD" stroke-width="1" opacity=".6" />

    <!-- reliures debout, nervures et filets dorés -->
    <g v-for="(s, i) in spines" :key="i">
      <rect :x="s.x" :y="s.y" :width="s.w" :height="s.h" rx="2" :fill="s.color" />
      <rect :x="s.x" :y="s.y" :width="s.w * .3" :height="s.h" rx="2" fill="#fff" opacity=".07" />
      <g :stroke="GOLD" stroke-width="1.3">
        <path :d="`M${s.x + 2} ${s.y + 14} H${s.x + s.w - 2} M${s.x + 2} ${s.y + 18} H${s.x + s.w - 2}`" />
        <path :d="`M${s.x + 2} ${s.y + s.h - 18} H${s.x + s.w - 2} M${s.x + 2} ${s.y + s.h - 14} H${s.x + s.w - 2}`" />
      </g>
      <rect :x="s.x + 4" :y="s.y + 34" :width="s.w - 8" height="16" rx="1" :fill="GOLD" opacity=".22" />
    </g>

    <!-- livre penché -->
    <g :transform="`rotate(14 ${leanX} ${SHELF_Y})`">
      <rect :x="leanX" :y="SHELF_Y - 166" width="26" height="166" rx="2" :fill="BOOK_COLORS[3]" />
      <rect :x="leanX + 26" :y="SHELF_Y - 164" width="7" height="162" rx="1" fill="#efe6d4" />
      <path :d="`M${leanX + 2} ${SHELF_Y - 150} H${leanX + 24} M${leanX + 2} ${SHELF_Y - 146} H${leanX + 24} M${leanX + 2} ${SHELF_Y - 20} H${leanX + 24}`" :stroke="GOLD" stroke-width="1.3" />
    </g>

    <!-- pile de livres -->
    <g v-for="(b, i) in stack" :key="'p' + i">
      <rect :x="b.x" :y="b.y" :width="b.w" height="21" rx="2" :fill="b.color" />
      <rect :x="b.x + 8" :y="b.y + 4" :width="b.w - 13" height="13" rx="1" fill="#f3ead8" />
      <path :d="`M${b.x + 10} ${b.y + 8} H${b.x + b.w - 7} M${b.x + 10} ${b.y + 12} H${b.x + b.w - 7}`" stroke="#e0d3ba" stroke-width="1" />
      <path :d="`M${b.x + 2} ${b.y + 3} V${b.y + 18}`" :stroke="GOLD" stroke-width="1.2" />
    </g>

    <!-- livre ouvert au sommet, avec son marque-page -->
    <g :transform="`translate(392 ${stackTop - 64})`">
      <path d="M0 22 Q34 8 68 24 L68 66 Q34 52 0 62 Z" :fill="BOOK_COLORS[1]" />
      <path d="M136 22 Q102 8 68 24 L68 66 Q102 52 136 62 Z" :fill="BOOK_COLORS[1]" />
      <path d="M6 18 Q37 6 68 20 L68 60 Q37 48 6 56 Z" fill="#fbf6ea" />
      <path d="M130 18 Q99 6 68 20 L68 60 Q99 48 130 56 Z" fill="#f2eadb" />
      <g stroke="#ddd0b8" stroke-width="1.2" fill="none">
        <path d="M16 28 Q40 20 60 28" /><path d="M16 36 Q40 28 60 36" /><path d="M16 44 Q40 36 60 44" />
        <path d="M120 28 Q96 20 76 28" /><path d="M120 36 Q96 28 76 36" />
      </g>
      <path d="M96 12 v62 l6 -5 6 5 v-64 z" fill="#7a2633" />
    </g>

    <!-- étagère -->
    <rect x="10" y="262" width="540" height="16" rx="2" class="shelf-top" />
    <rect x="10" y="274" width="540" height="9" rx="2" class="shelf-edge" />
  </svg>
</template>
