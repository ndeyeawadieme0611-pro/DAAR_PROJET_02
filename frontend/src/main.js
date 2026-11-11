import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import SearchView from './views/SearchView.vue'
import BookView from './views/BookView.vue'
import './style.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: SearchView },
    { path: '/books/:id', component: BookView, props: true },
  ],
  // Retour en haut de page à chaque navigation (sauf bouton "retour")
  scrollBehavior: (to, from, saved) => saved || { top: 0 },
})

createApp(App).use(router).mount('#app')
