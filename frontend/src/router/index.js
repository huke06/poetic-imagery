import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue'), meta: { title: '首页' } },
  { path: '/concepts', name: 'concepts', component: () => import('../views/ConceptGalleryView.vue'), meta: { title: '意象画廊' } },
  { path: '/concept/:id', name: 'concept-detail', component: () => import('../views/ConceptDetailView.vue'), meta: { title: '意象详情' } },
  { path: '/atlas', name: 'atlas', component: () => import('../views/PoeticAtlasView.vue'), meta: { title: '诗意图鉴' } },
  { path: '/artworks', name: 'artworks', component: () => import('../views/ArtworkGalleryView.vue'), meta: { title: '古画展厅' } },
  { path: '/agent', name: 'agent', component: () => import('../views/AgentView.vue'), meta: { title: '智能助手' } },
  { path: '/poetry/:id', name: 'poetry-detail', component: () => import('../views/PoetryDetailView.vue'), meta: { title: '诗文详情' } },
  { path: '/auth', name: 'auth', component: () => import('../views/AuthView.vue'), meta: { title: '登录' } },
  { path: '/admin', name: 'admin', component: () => import('../views/AdminView.vue'), meta: { title: '管理后台' } },
  { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../views/NotFoundView.vue'), meta: { title: '页面不存在' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 诗象志` : '诗象志 · 一字藏万象，一诗见千年'
})

export default router
