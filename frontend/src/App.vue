<script setup>
import ThemeToggle from './components/ThemeToggle.vue'
import BrandMark from './components/BrandMark.vue'
</script>

<template>
  <header class="appbar">
    <div class="appbar-inner">
      <RouterLink to="/" class="brand" aria-label="Marque-page — accueil">
        <BrandMark />
        <span class="brand-text">
          <span class="brand-name">Marque-page</span>
          <span class="brand-tag">Retrouvez le bon livre</span>
        </span>
      </RouterLink>
      <nav class="appbar-nav">
        <a href="https://www.gutenberg.org" target="_blank" rel="noopener" class="appbar-link">Gutenberg ↗</a>
        <ThemeToggle />
      </nav>
    </div>
  </header>

  <main class="main">
    <RouterView v-slot="{ Component }">
      <Transition name="fade" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
  </main>

  <footer class="footer">
    <span><strong>Marque-page</strong> — UE DAAR, Sorbonne Université · Maïssa Saad &amp; Ndeye Awa Dieme</span>
    <span>Textes issus du <a href="https://www.gutenberg.org" target="_blank" rel="noopener">Projet Gutenberg</a></span>
  </footer>
</template>
