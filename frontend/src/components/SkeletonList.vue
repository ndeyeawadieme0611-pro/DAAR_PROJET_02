<!-- Squelettes animés affichés pendant le chargement -->
<script setup>
defineProps({ count: { type: Number, default: 5 } })
</script>

<template>
  <div class="skeletons" aria-busy="true" aria-label="Chargement">
    <div v-for="i in count" :key="i" class="card result skeleton">
      <div class="sk sk-cover"></div>
      <div class="result-body">
        <div class="sk sk-line w60"></div>
        <div class="sk sk-line w35"></div>
        <div class="sk sk-line w80"></div>
      </div>
    </div>
  </div>
</template>
