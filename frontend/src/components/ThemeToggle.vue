<script setup>
// Bouton clair / sombre. Le choix est mémorisé dans le navigateur (localStorage).
import { ref } from 'vue'

const dark = ref(document.documentElement.dataset.theme === 'dark')

function toggle() {
  dark.value = !dark.value
  document.documentElement.dataset.theme = dark.value ? 'dark' : 'light'
  try { localStorage.setItem('theme', dark.value ? 'dark' : 'light') } catch { /* navigation privée */ }
}
</script>

<template>
  <button class="icon-btn" @click="toggle" :aria-label="dark ? 'Passer en mode clair' : 'Passer en mode sombre'">
    {{ dark ? '☀' : '☾' }}
  </button>
</template>
