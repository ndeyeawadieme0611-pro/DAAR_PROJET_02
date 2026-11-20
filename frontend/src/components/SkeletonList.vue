<!-- Lignes animées affichées pendant le chargement -->
<script setup>
defineProps({ count: { type: Number, default: 6 } })
</script>

<template>
  <div class="skeletons" aria-busy="true" aria-label="Chargement">
    <div v-for="i in count" :key="i" class="sk-row">
      <span class="sk sk-num"></span>
      <span class="sk-stack"><span class="sk w60"></span><span class="sk w35 thin"></span></span>
      <span class="sk w15"></span>
    </div>
  </div>
</template>
