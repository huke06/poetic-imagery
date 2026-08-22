<template>
  <div class="min-h-screen flex flex-col">
    <!-- 顶部导航 -->
    <header class="sticky top-0 z-40 bg-xuanzhi/85 backdrop-blur-md border-b border-shiqing/10">
      <nav class="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
        <router-link to="/" class="flex items-center gap-3 group">
          <img src="/logo.png" alt="诗象万千" class="h-12 w-auto group-hover:scale-105 transition-transform" />
          <div class="hidden sm:flex flex-col justify-center">
            <img src="/wanxiang-logo.png" alt="诗象万千" class="h-7 w-auto self-start" />
            <span class="mt-1 text-[10px] tracking-[0.2em] text-moyan/60 whitespace-nowrap">古诗词意象解读智能交互平台</span>
          </div>
        </router-link>
        <div class="flex items-center gap-1 sm:gap-2 text-sm">
          <router-link v-for="item in navItems" :key="item.to" :to="item.to"
            class="nav-link" :class="{ 'is-active': isActive(item.to) }">
            {{ item.label }}
          </router-link>
          <router-link v-if="!auth.loggedIn" to="/auth" class="auth-link">登录</router-link>
          <div v-else class="flex items-center gap-2 text-xs">
            <router-link to="/auth" class="nav-link">个人中心</router-link>
            <span class="tag border-shiqing/40 text-shiqing !text-[10px]" v-if="auth.user?.role==='admin'">管理员</span>
          </div>
          <!-- 诗文搜索 -->
          <div class="relative ml-1">
            <input v-model="searchQ" @keyup.enter="doSearch" @focus="showSearch = true"
              placeholder="搜诗 / 作者"
              class="search-input w-32 sm:w-40 pl-8 pr-3 py-1.5 text-xs rounded-full border transition-all focus:w-48" />
            <svg class="absolute left-2.5 top-2 w-3.5 h-3.5 text-shiqing/55" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
            </svg>
            <!-- 搜索结果下拉 -->
            <div v-if="showSearch && searchResults.length" class="absolute right-0 top-10 w-80 max-h-72 overflow-y-auto card shadow-xl z-50 py-1" @wheel="onSearchWheel">
              <div v-for="r in searchResults" :key="r.id"
                class="px-4 py-2.5 text-sm hover:bg-shiqing/5 cursor-pointer border-b border-black/5 last:border-0"
                @click="$router.push(`/poetry/${r.id}`); collapseSearch(); searchQ = ''">
                <b class="font-song">{{ r.title }}</b>
                <span class="text-xs text-qianhui ml-2">{{ r.dynasty }} · {{ r.author }}</span>
              </div>
              <div class="flex items-center justify-between px-4 py-2 text-xs text-qianhui border-t border-black/5">
                <span>{{ hasMore ? `共 ${searchTotal} 条，回车查看更多…` : `共 ${searchTotal} 条，已全部显示` }}</span>
                <button class="ml-2 shrink-0 hover:text-shiqing transition-colors" @click="collapseSearch">收起 ▲</button>
              </div>
            </div>
          </div>
        </div>
      </nav>
    </header>

    <!-- 主体（fullPath 作 key：路径/参数/查询变化时强制重建页面组件，
         修复 /concept/1→/concept/2 组件复用不刷新、/artworks?id=N 不 reopen 的问题） -->
    <main class="flex-1">
      <router-view v-slot="{ Component }">
        <component :is="Component" :key="$route.fullPath" />
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
          <img src="/logo.png" alt="诗象万千" class="h-10 w-auto" />
          <span>诗象万千 · 古诗词意象解读智能交互平台</span>
        </div>
        <div class="text-center sm:text-right leading-5">
          <div>数据来源：上海图书馆开放数据（搜韵诗文库/Artlib世界艺术鉴赏库/CBDB中国历代人物传记资料库）</div>
          <div>意象知识库经人工精选标注 · 仅供学习交流 · <router-link to="/admin" class="hover:text-shiqing transition-colors">管理后台</router-link></div>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
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
const searchPage = ref(1)
const lastSearchQ = ref('')

const hasMore = computed(() => searchResults.value.length < searchTotal.value)

// 清空输入即清空结果，不保留搜索记录
watch(searchQ, (q) => {
  if (!q.trim()) {
    searchResults.value = []
    searchTotal.value = 0
    searchPage.value = 1
    lastSearchQ.value = ''
    showSearch.value = false
  }
})

function collapseSearch() { showSearch.value = false }

// 鼠标在结果下拉上滚动时，阻止滚动链传播到背后页面；下拉自身可正常滚动
function onSearchWheel(e) {
  const el = e.currentTarget
  const canScroll = el.scrollHeight > el.clientHeight
  if (!canScroll) { e.preventDefault(); return }
  const atTop = el.scrollTop <= 0 && e.deltaY < 0
  const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 1 && e.deltaY > 0
  if (atTop || atBottom) e.preventDefault()
}

async function doSearch() {
  const q = searchQ.value.trim()
  if (!q) {
    searchResults.value = []
    searchTotal.value = 0
    searchPage.value = 1
    lastSearchQ.value = ''
    showSearch.value = false
    return
  }
  // 查询词未变且还有更多 → 回车加载下一页；否则全新搜索
  const sameQuery = q === lastSearchQ.value
  const more = searchResults.value.length < searchTotal.value
  searchPage.value = (sameQuery && more) ? searchPage.value + 1 : 1
  if (!(sameQuery && more)) lastSearchQ.value = q
  try {
    const data = await searchPoetry({ key: q, page: searchPage.value, page_size: 6 })
    searchResults.value = searchPage.value === 1
      ? data.items
      : [...searchResults.value, ...data.items]
    searchTotal.value = data.total
    showSearch.value = true
  } catch { if (searchPage.value === 1) searchResults.value = [] }
}
</script>

<style scoped>
/* ── 导航链接：宋体 + 滑动下划线 ── */
.nav-link {
  position: relative; display: inline-block;
  padding: 0.5rem 0.75rem;
  font-family: 'Noto Serif SC', 'Songti SC', STSong, 'SimSun', serif;
  letter-spacing: 0.12em; color: rgba(44, 44, 44, 0.75);
  transition: color 0.2s; white-space: nowrap;
}
.nav-link::after {
  content: ''; position: absolute;
  left: 0.75rem; right: 0.75rem; bottom: 0.15rem;
  height: 2px; border-radius: 2px; background: #2B4C7E;
  transform: scaleX(0); transform-origin: center;
  transition: transform 0.25s ease;
}
.nav-link:hover { color: #2B4C7E; }
.nav-link:hover::after, .nav-link.is-active::after { transform: scaleX(1); }
.nav-link.is-active { color: #2B4C7E; font-weight: 600; }

/* ── 登录按钮：石青描边药丸 ── */
.auth-link {
  display: inline-flex; align-items: center;
  padding: 5px 16px; font-size: 12px; letter-spacing: 0.15em;
  color: #2B4C7E; border: 1px solid rgba(43, 76, 126, 0.35);
  border-radius: 999px; background: rgba(255, 255, 255, 0.5);
  transition: all 0.2s; white-space: nowrap;
}
.auth-link:hover {
  background: #2B4C7E; color: #F5F1E8; border-color: #2B4C7E;
  transform: translateY(-1px);
}

/* ── 搜索输入 ── */
.search-input {
  font-family: 'Noto Serif SC', 'Songti SC', STSong, serif;
  border-color: rgba(43, 76, 126, 0.22); background: rgba(255, 255, 255, 0.6);
  color: #2C2C2C;
}
.search-input::placeholder { color: rgba(107, 107, 107, 0.6); }
.search-input:focus {
  outline: none; border-color: #2B4C7E;
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 0 0 3px rgba(43, 76, 126, 0.08);
}
</style>
