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
  <button class="icon-btn" @click="toggle" :aria-label="dark ? 'Passer en mode clair' : 'Passer en mode sombre'"
          :title="dark ? 'Mode clair' : 'Mode sombre'">
    <svg v-if="dark" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.5" />
      <path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8" /></svg>
    <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" /></svg>
  </button>
</template>
