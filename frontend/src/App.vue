<template>
  <div class="min-h-screen flex flex-col">
    <!-- 顶部导航 -->
    <header class="sticky top-0 z-40 bg-xuanzhi/85 backdrop-blur-md border-b border-shiqing/10">
      <nav class="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <router-link to="/" class="flex items-center gap-3 group">
          <span class="seal group-hover:scale-105 transition-transform">诗象</span>
          <div class="leading-tight">
            <div class="font-song text-xl font-bold tracking-[0.3em] text-shiqing">诗象志</div>
            <div class="text-[10px] text-qianhui tracking-wider">一字藏万象 · 一诗见千年</div>
          </div>
        </router-link>
        <div class="flex items-center gap-1 sm:gap-2 text-sm">
          <router-link v-for="item in navItems" :key="item.to" :to="item.to"
            class="px-3 py-2 rounded-md text-moyan/80 hover:text-shiqing hover:bg-shiqing/5 transition-colors tracking-wider"
            :class="{ 'text-shiqing font-semibold bg-shiqing/5': isActive(item.to) }">
            {{ item.label }}
          </router-link>
          <router-link v-if="!auth.loggedIn" to="/auth" class="px-3 py-2 text-xs text-qianhui hover:text-shiqing tracking-wider">登录</router-link>
          <div v-else class="flex items-center gap-2 text-xs">
            <router-link to="/auth" class="text-moyan/80 hover:text-shiqing tracking-wider">个人中心</router-link>
            <span class="tag border-shiqing/40 text-shiqing !text-[10px]" v-if="auth.user?.role==='admin'">管理员</span>
          </div>
          <!-- 诗文搜索 -->
          <div class="relative ml-1">
            <input v-model="searchQ" @keyup.enter="doSearch" @focus="showSearch = true"
              placeholder="搜诗/作者…" class="w-32 sm:w-40 pl-8 pr-3 py-1.5 text-xs rounded-full border border-shiqing/20 bg-white/50
              focus:outline-none focus:border-shiqing focus:w-48 transition-all" />
            <svg class="absolute left-2.5 top-2 w-3.5 h-3.5 text-qianhui" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
            </svg>
            <!-- 搜索结果下拉 -->
            <div v-if="showSearch && searchResults.length" class="absolute right-0 top-10 w-80 max-h-72 overflow-y-auto card shadow-xl z-50 py-1">
              <div v-for="r in searchResults" :key="r.id"
                class="px-4 py-2.5 text-sm hover:bg-shiqing/5 cursor-pointer border-b border-black/5 last:border-0"
                @click="$router.push(`/poetry/${r.id}`); showSearch = false; searchQ = ''">
                <b class="font-song">{{ r.title }}</b>
                <span class="text-xs text-qianhui ml-2">{{ r.dynasty }} · {{ r.author }}</span>
              </div>
              <div class="px-4 py-2 text-xs text-qianhui text-center">共 {{ searchTotal }} 条，回车查看更多…</div>
            </div>
          </div>
        </div>
      </nav>
    </header>

    <!-- 主体（fullPath 作 key：路径/参数/查询变化时强制重建页面组件，
         修复 /concept/1→/concept/2 组件复用不刷新、/artworks?id=N 不 reopen 的问题） -->
    <main class="flex-1">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" :key="$route.fullPath" />
        </transition>
      </router-view>
    </main>

    <!-- 金叶集：探索记录悬浮面板 -->
    <GoldenLeafPanel />
    <!-- AI 助手悬浮窗 -->
    <AiFloatingWidget />
    <!-- 新手引导 -->
    <OnboardingGuide />

    <!-- 页脚 -->
    <footer class="mt-20 border-t border-shiqing/10 bg-white/30">
      <div class="max-w-6xl mx-auto px-4 py-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-qianhui">
        <div class="flex items-center gap-2">
          <span class="seal !w-7 !h-7 !text-[10px]">诗象</span>
          <span>诗象志 · 古诗词意象智能体</span>
        </div>
        <div class="text-center sm:text-right leading-5">
          <div>数据来源：上海图书馆开放数据（诗文库 / 古代艺术品图文库）</div>
          <div>本库意象与诗文经人工精选标注 · 仅供学习交流 · <router-link to="/admin" class="hover:text-shiqing transition-colors">管理后台</router-link></div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { searchPoetry } from './api'
import { auth } from './stores/auth'
import AiFloatingWidget from './components/AiFloatingWidget.vue'
import GoldenLeafPanel from './components/GoldenLeafPanel.vue'
import OnboardingGuide from './components/OnboardingGuide.vue'

onMounted(() => auth.init())

const route = useRoute()
const navItems = [
  { to: '/', label: '首页' },
  { to: '/concepts', label: '意象画廊' },
  { to: '/atlas', label: '诗意图鉴' },
  { to: '/artworks', label: '艺术展厅' },
  { to: '/agent', label: '灵犀助手' },
]
const isActive = (to) => (to === '/' ? route.path === '/' : route.path.startsWith(to))

const searchQ = ref('')
const searchResults = ref([])
const searchTotal = ref(0)
const showSearch = ref(false)

async function doSearch() {
  const q = searchQ.value.trim()
  if (!q) { searchResults.value = []; return }
  try {
    const data = await searchPoetry({ key: q, page: 1, page_size: 6 })
    searchResults.value = data.items
    searchTotal.value = data.total
    showSearch.value = true
  } catch { searchResults.value = [] }
}
</script>
