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
import { useRoute } from 'vue-router'

const route = useRoute()
const navItems = [
  { to: '/', label: '首页' },
  { to: '/concepts', label: '意象画廊' },
  { to: '/artworks', label: '古画展厅' },
  { to: '/agent', label: '智能助手' },
]
const isActive = (to) => (to === '/' ? route.path === '/' : route.path.startsWith(to))
</script>
