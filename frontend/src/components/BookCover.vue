<script setup>
// Couverture générée : dégradé propre au livre + initiales du titre.
import { computed } from 'vue'
import { coverStyle, initials } from '../utils'

const props = defineProps({
  id: { type: Number, required: true },
  title: { type: String, default: '' },
  size: { type: String, default: 'md' },   // 'sm' | 'md' | 'lg'
})
const style = computed(() => coverStyle(props.id))
const letters = computed(() => initials(props.title))
</script>

<template>
  <div class="cover" :class="`cover-${size}`" :style="style" aria-hidden="true">
    <span class="cover-letters">{{ letters }}</span>
    <span class="cover-spine"></span>
  </div>
</template>
