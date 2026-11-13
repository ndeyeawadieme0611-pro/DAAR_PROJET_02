<script setup>
import ThemeToggle from './components/ThemeToggle.vue'
</script>

<template>
  <header class="topbar">
    <RouterLink to="/" class="brand">
      <span class="brand-mark">❦</span>
      <span>Bibliothèque <em>DAAR</em></span>
    </RouterLink>
    <ThemeToggle />
  </header>

  <main class="container">
    <RouterView v-slot="{ Component }">
      <Transition name="fade" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
  </main>

  <footer class="footer">
    Textes issus du <a href="https://www.gutenberg.org" target="_blank" rel="noopener">Projet Gutenberg</a>
    · UE DAAR, Sorbonne Université
  </footer>
</template>
