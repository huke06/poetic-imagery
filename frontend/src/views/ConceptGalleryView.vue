<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <SectionTitle sub="意象知识库总览">意象画廊</SectionTitle>

    <!-- 筛选栏 -->
    <div class="flex flex-wrap items-center gap-3 mt-6">
      <div class="flex gap-2">
        <button v-for="cat in categories" :key="cat"
          class="px-4 py-1.5 text-sm rounded-full border transition-all tracking-wider"
          :class="activeCategory === cat
            ? 'bg-shiqing text-white border-shiqing'
            : 'border-shiqing/30 text-shiqing hover:bg-shiqing/5'"
          @click="activeCategory = cat; load()">
          {{ cat || '全部' }}
        </button>
      </div>
      <div class="flex-1"></div>
      <div class="relative">
        <input v-model="keyword" @keyup.enter="load" placeholder="检索意象名称…"
          class="w-56 pl-9 pr-4 py-2 text-sm rounded-full border border-shiqing/25 bg-white/70
                 focus:outline-none focus:border-shiqing focus:ring-2 focus:ring-shiqing/10 transition-all" />
        <svg class="absolute left-3 top-2.5 w-4 h-4 text-qianhui" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
        </svg>
      </div>
    </div>

    <!-- 卡片网格 -->
    <div v-if="loading" class="py-20 text-center text-qianhui">加载中…</div>
    <div v-else-if="!items.length" class="py-20 text-center text-qianhui">未找到匹配的意象</div>
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
      <ConceptCard v-for="(c, i) in items" :key="c.id" :concept="c" class="rise-in" :style="{ animationDelay: i * 0.06 + 's' }" />
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getConceptList } from '../api'
import ConceptCard from '../components/ConceptCard.vue'
import SectionTitle from '../components/SectionTitle.vue'

const categories = ['', '自然类', '社会生活类', '人类自身类', '人造物类', '虚拟类']
const activeCategory = ref('')
const keyword = ref('')
const items = ref([])
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const data = await getConceptList({ category: activeCategory.value, keyword: keyword.value })
    items.value = data.items
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
