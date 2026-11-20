<!--
  Couverture dessinée, façon reliure en toile : couleur sourde et décor doré
  propres à chaque livre (calculés à partir de son identifiant, donc toujours
  les mêmes), initiales dorées, tranche des pages et ruban de marque-page.
-->
<script setup>
import { computed } from 'vue'
import { bookColor, bookPattern, initials } from '../utils'

const props = defineProps({
  id: { type: Number, required: true },
  title: { type: String, default: '' },
  size: { type: String, default: 'sm' },     // 'xs' | 'sm' | 'lg'
})
const color = computed(() => bookColor(props.id))
const pattern = computed(() => bookPattern(props.id))
const letters = computed(() => initials(props.title))
const GOLD = '#c9a45c'
</script>

<template>
  <svg class="book-art" :class="`book-art-${size}`" viewBox="0 0 120 170" aria-hidden="true">
    <!-- tranche des pages -->
    <rect x="12" y="7" width="103" height="148" rx="3" fill="#efe6d4" />
    <g stroke="#ddd0b8" stroke-width="1"><path d="M110 14 V150" /><path d="M106 12 V152" /></g>
    <!-- couverture -->
    <rect x="4" y="4" width="104" height="150" rx="4" :fill="color" />
    <rect x="4" y="4" width="15" height="150" rx="3" fill="#000" opacity=".18" />
    <rect x="19" y="4" width="1.5" height="150" fill="#fff" opacity=".12" />

    <!-- décor doré -->
    <g :stroke="GOLD" fill="none" stroke-width="1.6">
      <template v-if="pattern === 0">
        <path d="M26 20 H98 M26 25 H98 M26 133 H98 M26 138 H98" />
      </template>
      <template v-else-if="pattern === 1">
        <rect x="27" y="15" width="70" height="128" rx="2" />
        <rect x="31" y="19" width="62" height="120" rx="1" stroke-width=".8" />
      </template>
      <template v-else-if="pattern === 2">
        <path d="M62 22 l8 8 -8 8 -8 -8 z M62 120 l8 8 -8 8 -8 -8 z" />
        <path d="M30 30 H48 M76 30 H94 M30 128 H48 M76 128 H94" stroke-width="1" />
      </template>
      <template v-else>
        <rect x="20" y="54" width="88" height="50" :fill="GOLD" fill-opacity=".14" stroke="none" />
        <path d="M20 54 H108 M20 104 H108" />
      </template>
    </g>

    <!-- initiales dorées -->
    <text x="62" y="90" text-anchor="middle" class="book-art-letters" :fill="GOLD">{{ letters }}</text>

    <!-- ruban de marque-page -->
    <path d="M86 150 v16 l5 -4 5 4 v-16 z" fill="#7a2633" />
  </svg>
</template>
