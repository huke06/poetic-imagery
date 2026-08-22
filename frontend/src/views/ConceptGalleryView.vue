<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <SectionTitle sub="意象知识库总览">意象画廊</SectionTitle>

    <!-- 筛选栏 -->
    <div class="space-y-3 mt-6">
      <!-- 模式切换 -->
      <div class="mode-switch" :class="{ 'is-emotion': filterMode === 'emotion' }">
        <span class="mode-switch__thumb" aria-hidden="true"></span>
        <button type="button" class="mode-switch__btn" :class="{ 'is-on': filterMode === 'category' }"
          @click="filterMode='category';activeCategory='';activeSub='';activeEmotionMain='';load()">按意象性质</button>
        <button type="button" class="mode-switch__btn" :class="{ 'is-on': filterMode === 'emotion' }"
          @click="filterMode='emotion';activeCategory='';activeSub='';activeEmotionMain='';load()">按意象情感</button>
      </div>
      <div v-show="filterMode==='category'" class="flex flex-wrap items-center gap-2">
        <button v-for="cat in categories" :key="cat"
          class="px-4 py-1.5 text-sm rounded-full border transition-all tracking-wider"
          :class="activeCategory === cat
            ? 'bg-shiqing text-white border-shiqing'
            : 'border-shiqing/30 text-shiqing hover:bg-shiqing/5'"
          @click="activeCategory = cat; activeSub = ''; load()">
          {{ cat || '全部' }}
        </button>
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
      <!-- 二级类目 -->
      <div v-show="filterMode==='category' && subCats.length" class="flex flex-wrap gap-1.5">
        <button v-for="s in subCats" :key="s"
          class="px-3 py-1 text-xs rounded-full border transition-all"
          :class="activeSub === s
            ? 'bg-zhuqing text-white border-zhuqing'
            : 'border-zhuqing/30 text-zhuqing hover:bg-zhuqing/5'"
          @click="activeSub = activeSub === s ? '' : s; load()">
          {{ s }}
        </button>
      </div>

      <!-- 一级情感 -->
      <div v-show="filterMode==='emotion'" class="flex flex-wrap items-center gap-2 pt-1">
        <button v-for="m in emotionMains" :key="m"
          class="px-4 py-1.5 text-sm rounded-full border transition-all"
          :class="activeEmotionMain === m ? 'text-white' : 'hover:bg-black/5'"
          :style="activeEmotionMain === m
            ? { background: emotionColor(m), borderColor: emotionColor(m) }
            : { borderColor: emotionColor(m) + '55', color: emotionColor(m) }"
          @click="toggleEmotionMain(m)">
          {{ m }}
        </button>
        <button v-if="activeEmotionMain || activeEmotion"
          class="px-3 py-1 text-xs rounded-full border border-qianhui/30 text-qianhui hover:bg-black/5 transition-all"
          @click="activeEmotionMain = ''; activeEmotion = ''; load()">清除情感</button>
      </div>
    </div>

    <!-- 卡片网格 -->
    <div v-if="loading" class="py-20 text-center text-qianhui">加载中…</div>
    <div v-else-if="!items.length" class="py-20 text-center text-qianhui">未找到匹配的意象</div>
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
      <ConceptCard v-for="(c, i) in items" :key="c.id" :concept="c" :data-concept-id="c.id" class="rise-in" :style="{ animationDelay: i * 0.06 + 's' }" />
    </div>
    <BackToTop />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { getConceptList } from '../api'
import BackToTop from '../components/BackToTop.vue'
import ConceptCard from '../components/ConceptCard.vue'
import SectionTitle from '../components/SectionTitle.vue'

const categories = ['', '自然类', '社会生活类', '人类自身类', '人造物类', '虚拟类']
const subCategories = {
  '自然类': ['天文气象', '山水地理', '文化地标', '植物', '动物', '自然景观'],
  '社会生活类': ['战争军事', '仕途游宦', '农耕渔猎', '交通迁徙', '节日民俗'],
  '人类自身类': ['身体器官', '情感心理', '人格精神'],
  '人造物类': ['建筑空间', '生活器物', '服饰装饰', '交通工具', '城市与文化空间'],
  '虚拟类': ['神仙仙境', '神话传说', '鬼怪灵异', '宗教', '概念'],
}
const filterMode = ref('category')  // 'category' | 'emotion'
const activeCategory = ref('')
const activeSub = ref('')
const keyword = ref('')
const items = ref([])
const loading = ref(true)

// 情感筛选（一二级）
const emotionTree = ref({})
const activeEmotionMain = ref('')
const activeEmotion = ref('')
const EMOTION_COLORS = {
  '情感心绪类': '#6E4A7E', '交往离别类': '#9B4423', '人生感悟类': '#8A6D3B',
  '自然山水类': '#5B7C5F', '历史文化类': '#2B4C7E', '志向抱负类': '#9B2C1F',
  '超脱境界类': '#3A7A7C',
}
const emotionColor = (m) => EMOTION_COLORS[m] || '#8A6D3B'
const emotionMains = computed(() => Object.keys(emotionTree.value))
const emotionSubs = computed(() => activeEmotionMain.value ? (emotionTree.value[activeEmotionMain.value] || []) : [])

function toggleEmotionMain(m) {
  if (activeEmotionMain.value === m) { activeEmotionMain.value = ''; activeEmotion.value = '' }
  else { activeEmotionMain.value = m; activeEmotion.value = '' }
  load()
}

const subCats = computed(() => activeCategory.value ? subCategories[activeCategory.value] || [] : [])

async function load() {
  loading.value = true
  try {
    const data = await getConceptList({
      category: activeCategory.value, keyword: keyword.value,
      emotion_main: activeEmotionMain.value, emotion: activeEmotion.value,
    })
    if (data.emotion_tree) emotionTree.value = data.emotion_tree
    // 前端按二级类目过滤
    items.value = activeSub.value
      ? data.items.filter((c) => (c.category_sub || '').split(/\s+/).includes(activeSub.value))
      : data.items
  } finally {
    loading.value = false
  }
}
// 进入详情前，记录画廊筛选状态 + 目标卡片 ID + 滚动位置，返回时恢复
onBeforeRouteLeave((to) => {
  if (to.name === 'concept-detail') {
    sessionStorage.setItem('gallery:return', JSON.stringify({
      conceptId: to.params.id,
      scrollY: window.scrollY,
      filterMode: filterMode.value,
      activeCategory: activeCategory.value,
      activeSub: activeSub.value,
      keyword: keyword.value,
      activeEmotionMain: activeEmotionMain.value,
      activeEmotion: activeEmotion.value,
    }))
  }
})

onMounted(async () => {
  const saved = sessionStorage.getItem('gallery:return')
  if (saved) {
    sessionStorage.removeItem('gallery:return')
    try {
      const s = JSON.parse(saved)
      filterMode.value = s.filterMode
      activeCategory.value = s.activeCategory
      activeSub.value = s.activeSub
      keyword.value = s.keyword
      activeEmotionMain.value = s.activeEmotionMain
      activeEmotion.value = s.activeEmotion
      await load()
      await nextTick()
      const el = document.querySelector(`[data-concept-id="${s.conceptId}"]`)
      if (el) {
        const r = el.getBoundingClientRect()
        const y = r.top - (window.innerHeight - r.height) / 2
        window.scrollTo(0, Math.max(0, y)) // 目标卡片居中（早于绘制，无「先到顶再跳」闪烁）
        el.classList.add('is-highlighted')
        setTimeout(() => el.classList.remove('is-highlighted'), 1500)
      } else if (s.scrollY) {
        window.scrollTo(0, s.scrollY)
      }
      return
    } catch { /* 解析失败则走首次加载 */ }
  }
  await load()
})
</script>

<style scoped>
/* 返回画廊时的目标卡片高亮：主题色淡描边 + 柔光晕（--tc 由卡片注入，随其主题色） */
:deep(.concept-card.is-highlighted) {
  box-shadow:
    0 0 0 2px color-mix(in srgb, var(--tc) 50%, transparent),
    0 0 28px color-mix(in srgb, var(--tc) 26%, transparent);
}

/* ── 模式切换：滑动胶囊 ── */
.mode-switch {
  position: relative;
  display: inline-flex;
  padding: 2px;
  background: rgba(43, 76, 126, 0.06);
  border-radius: 999px;
}
.mode-switch__thumb {
  position: absolute;
  top: 2px; bottom: 2px; left: 2px;
  width: calc(50% - 2px);            /* 两按钮等宽 → 恰为一个按钮宽 */
  background: #2B4C7E;
  border-radius: 999px;
  box-shadow: 0 1px 4px rgba(43, 76, 126, 0.35);
  transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}
.mode-switch.is-emotion .mode-switch__thumb { transform: translateX(100%); }
.mode-switch__btn {
  position: relative; z-index: 1;
  padding: 6px 16px; font-size: 12px; letter-spacing: 0.06em; line-height: 1.5;
  color: #6B6B6B; background: transparent; border: none; cursor: pointer;
  white-space: nowrap; transition: color 0.28s ease;
}
.mode-switch__btn:hover { color: #2B4C7E; }
.mode-switch__btn.is-on { color: #FFFFFF; }
.mode-switch__btn.is-on:hover { color: #FFFFFF; }
</style>
