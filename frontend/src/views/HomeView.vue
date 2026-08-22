<template>
  <div>
    <!-- 首屏：数字美术馆 · 精选艺术品动态展示墙 -->
    <section class="relative overflow-hidden min-h-[85vh] flex items-center justify-center">
      <!-- 艺术品展示墙（纯展示，不可交互） -->
      <div class="absolute inset-0 pointer-events-none select-none z-0">
        <img v-for="(a, i) in heroArtworks" :key="a.id"
          :src="a.image_url || a.thumb_url" :alt="a.name" decoding="async"
          class="hero-art absolute inset-0 w-full h-full object-cover"
          :class="{ 'hero-active': i === heroIndex }" />
      </div>
      <!-- 宣纸柔光罩层：压低保真、保留纹理、护住文字 -->
      <div class="absolute inset-0 z-10 pointer-events-none"
        style="background: radial-gradient(ellipse at 50% 42%, rgba(245,241,232,0.72) 0%, rgba(245,241,232,0.48) 46%, rgba(245,241,232,0.58) 100%)"></div>

      <!-- 前景：品牌区直陈（无卡片） -->
      <div class="relative z-20 max-w-3xl mx-auto px-4 py-24 w-full flex flex-col items-center text-center rise-in">
        <!-- 品牌锁-up：左 logo，右平台名称，同行居中 -->
        <div class="flex items-center justify-center gap-6">
          <img src="/logo.png" alt="诗象万千印章" class="h-32 sm:h-36 w-auto"
            style="filter: drop-shadow(0 2px 10px rgba(245,241,232,0.6))" />
          <img src="/wanxiang-logo.png" alt="诗象万千" class="h-28 sm:h-32 w-auto"
            style="filter: drop-shadow(0 2px 10px rgba(245,241,232,0.6))" />
        </div>
        <p class="mt-7 font-kai text-xl sm:text-2xl tracking-[0.4em] text-moyan/85"
          style="text-shadow: 0 1px 8px rgba(245,241,232,0.8)">游心万象，一眼千年</p>
        <p class="mt-5 text-sm text-moyan/70 max-w-xl leading-7"
          style="text-shadow: 0 1px 8px rgba(245,241,232,0.8)">
          以古诗词意象为切口，集意象解读、诗画联动、演变可视化与AI智能问答于一体，
          直观呈现一个词语在千年诗史中的情感承载和演变轨迹。
        </p>
        <div class="mt-9 flex flex-wrap items-center justify-center gap-4">
          <router-link to="/concepts" class="hero-btn" :class="{ 'hero-btn--active': isActivePath('/concepts') }">意象漫游</router-link>
          <router-link to="/artworks" class="hero-btn" :class="{ 'hero-btn--active': isActivePath('/artworks') }">赏艺寻象</router-link>
          <button @click="randomConcept" class="hero-btn" :class="{ 'hero-btn--active': lotteryOpen }" title="随机探索一个意象">随缘一象</button>
        </div>
      </div>

      <!-- 底部渐隐入宣纸 -->
      <div class="absolute bottom-0 left-0 w-full h-16 z-10 pointer-events-none" style="background: linear-gradient(180deg, transparent, #F5F1E8)"></div>
      <!-- 下滑提示 -->
      <div class="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-1.5 pointer-events-none select-none">
        <span class="font-kai text-sm tracking-[0.42em] text-moyan/60"
              style="text-shadow: 0 1px 6px rgba(245,241,232,0.8)">向下滚动</span>
        <span class="scroll-hint flex flex-col items-center text-shiqing/75">
          <svg class="w-8 h-8 scroll-hint__chev" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
          <svg class="w-8 h-8 -mt-4 scroll-hint__chev scroll-hint__chev--ghost" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>
        </span>
      </div>
    </section>

    <!-- 意象精选 -->
    <section class="max-w-6xl mx-auto px-4 py-16">
      <div class="flex items-center justify-between">
        <SectionTitle sub="点击卡片进入意象详情">意象精选</SectionTitle>
        <button v-if="featuredPool.length > 8" @click="reshuffle" class="reshuffle-btn group">
          <svg class="w-3.5 h-3.5 transition-transform duration-500 group-hover:rotate-180" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>
          换一批
        </button>
      </div>
      <div v-if="loading" class="py-16 text-center text-qianhui">加载中…</div>
        <div v-else class="grid grid-cols-2 lg:grid-cols-4 gap-5 mt-8">
        <ConceptCard v-for="c in concepts" :key="c.id" :concept="c" class="rise-in" />
      </div>
    </section>

    <!-- 艺术品精选 -->
    <section class="bg-white/40 border-y border-shiqing/10">
      <div class="max-w-6xl mx-auto px-4 py-16">
        <div class="flex items-center justify-between">
          <SectionTitle sub="诗画互证 · 前往艺术展厅">艺术品精选</SectionTitle>
          <button v-if="artworkPool.length > 8" @click="reshuffleArtworks" class="reshuffle-btn group">
            <svg class="w-3.5 h-3.5 transition-transform duration-500 group-hover:rotate-180" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>
            换一批
          </button>
        </div>
        <div v-if="artworks.length" class="grid grid-cols-2 sm:grid-cols-4 gap-5 mt-8">
          <div v-for="(a, i) in artworks" :key="a.id" @click="openArtPreview(a)"
            class="card card-hover overflow-hidden cursor-pointer rise-in" :style="{ animationDelay: i * 0.06 + 's' }">
            <img :src="a.thumb_url || a.image_url" :alt="a.name" class="w-full h-40 object-cover" loading="lazy" />
            <div class="p-3">
              <h4 class="font-song font-semibold text-sm truncate">《{{ a.name }}》</h4>
              <p class="text-[11px] text-qianhui mt-0.5">{{ a.dynasty_period || a.dynasty_main }} · {{ a.artist }}</p>
            </div>
          </div>
        </div>
        <p v-else class="py-10 text-center text-qianhui text-sm">艺术品收录中…</p>
      </div>
    </section>

    <!-- 艺术品预览弹窗 -->
    <Teleport to="body">
      <div v-if="previewArt" class="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" @click.self="previewArt=null">
        <div class="bg-xuanzhi rounded-lg max-w-4xl w-full max-h-[90vh] shadow-2xl flex flex-col md:flex-row overflow-hidden relative">
          <button class="absolute top-3 right-3 w-8 h-8 flex items-center justify-center rounded-full bg-black/20 hover:bg-black/40 text-moyan/70 text-lg z-10" @click="previewArt=null">&times;</button>
          <div class="md:w-1/2 bg-black/5 flex items-center justify-center shrink-0">
            <img :src="previewArt.image_url" :alt="previewArt.name" class="w-full max-h-[60vh] object-contain" />
          </div>
          <div class="md:w-1/2 p-6 flex flex-col overflow-y-auto">
            <h3 class="font-song text-2xl font-bold pr-6">《{{ previewArt.name }}》</h3>
            <p class="text-sm text-qianhui mt-1">{{ previewArt.dynasty_period || previewArt.dynasty_main }} · {{ previewArt.artist }}</p>
            <div v-if="previewLoading" class="text-xs text-qianhui mt-4">加载详情中…</div>
            <div v-else class="grid grid-cols-2 gap-3 mt-4 text-sm">
              <div class="bg-white/50 rounded p-3"><span class="text-qianhui text-xs">材质</span><p class="mt-0.5">{{ previewArt.material || '—' }}</p></div>
              <div class="bg-white/50 rounded p-3"><span class="text-qianhui text-xs">尺寸</span><p class="mt-0.5">{{ previewArt.size || '—' }}</p></div>
            </div>
            <div class="mt-4" v-if="previewArt.description && !previewLoading">
              <span class="text-xs text-qianhui tracking-widest">作品介绍</span>
              <p class="text-sm leading-7 mt-2 text-moyan/85 whitespace-pre-line line-clamp-6">{{ previewArt.description }}</p>
            </div>
            <div class="flex-1"></div>
            <router-link :to="`/artworks?id=${previewArt.id}`" class="btn-primary mt-4 text-center" @click="previewArt=null">在艺术展厅中查看</router-link>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 诗意图鉴 -->
    <section class="bg-white/40 border-y border-shiqing/10">
      <div class="max-w-6xl mx-auto px-4 py-16">
        <div class="flex items-center justify-between">
          <SectionTitle sub="名画为卷 · 意象为点 · 点击画中圆点探寻诗情">诗意图鉴</SectionTitle>
          <router-link to="/atlas" class="reshuffle-btn group">
            进入诗意图鉴
            <svg class="w-3.5 h-3.5 transition-transform duration-300 group-hover:translate-x-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
          </router-link>
        </div>
        <template v-if="atlasPaintings.length">
          <div ref="atlasRow" class="atlas-row mt-8"
            @wheel.prevent="onAtlasWheel"
            @mousedown="onAtlasDragStart" @mousemove="onAtlasDrag" @mouseup="onAtlasDragEnd" @mouseleave="onAtlasDragEnd">
            <router-link v-for="(p, i) in atlasPaintings" :key="p.id" :to="'/atlas?id=' + (p.id ?? '') + '&i=' + i"
              class="atlas-card" :class="{ 'atlas-enter': atlasInView }"
              :style="{ animationDelay: (i * 0.07) + 's' }" @click="onAtlasCardClick">
              <div class="atlas-card__img">
                <img :src="p.src" :alt="p.title" loading="lazy" draggable="false" />
              </div>
              <div class="atlas-card__body">
                <h4 class="atlas-card__name">{{ p.title }}</h4>
                <p class="atlas-card__meta">{{ p.en }}</p>
                <p class="atlas-card__imagery">
                  <template v-for="(name, i) in imageryList(p)" :key="name">
                    <span v-if="i" class="atlas-card__sep">·</span>{{ name }}
                  </template>
                </p>
              </div>
            </router-link>
          </div>
          <div class="atlas-hint">
            <svg class="atlas-hint__arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>
            <span class="font-kai text-xs tracking-[0.3em]">滑动鼠标查看更多</span>
          </div>
        </template>
        <p v-else class="py-10 text-center text-qianhui text-sm">画卷收录中…</p>
      </div>
    </section>

    <!-- AI 助手入口 · 向灵犀提问 -->
    <section class="relative">
      <div class="max-w-6xl mx-auto px-4 pt-16">
        <div ref="aiHero" class="ai-hero" :class="{ 'ai-enter': aiInView }">
          <!-- 极淡东方装饰：淡墨点 -->
          <span class="ai-orn ai-orn--a"></span>
          <span class="ai-orn ai-orn--b"></span>
          <span class="ai-orn ai-orn--c"></span>

          <div class="ai-hero__inner">
            <!-- 标识：沿用现有 logo，外包淡青灰细环 -->
            <div class="ai-badge">
              <img src="/lingxi-logo.png" alt="灵犀助手" class="ai-badge__logo" />
            </div>

            <h3 class="ai-title">向灵犀助手提问</h3>
            <p class="ai-sub">不懂意象？不会赏析？一键唤起灵犀，随时陪你读诗、解诗、写诗。</p>

            <div class="ai-prompts">
              <button v-for="q in aiPrompts" :key="q" class="ai-prompt" @click="askAi(q)">
                <span class="ai-prompt__mark"></span>{{ q }}
              </button>
            </div>

            <div class="ai-cta-wrap">
              <router-link to="/agent" class="ai-cta">进入灵犀助手 <span class="ai-cta__arrow">→</span></router-link>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 三大核心价值 -->
    <section class="relative overflow-hidden">
      <div class="max-w-6xl mx-auto px-4 py-16">
        <SectionTitle>三大核心价值</SectionTitle>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          <div v-for="(f, i) in features" :key="f.title"
            class="feature-card rise-in" :style="{ animationDelay: i * 0.1 + 's', '--accent': f.color }">
            <span class="feature-card__wash"></span>
            <div class="feature-seal">{{ f.seal }}</div>
            <h3 class="feature-card__title">{{ f.title }}</h3>
            <p class="feature-card__slogan">{{ f.slogan }}</p>
            <p class="feature-card__desc">{{ f.desc }}</p>
            <span class="feature-card__line"></span>
          </div>
        </div>
      </div>
    </section>

    <!-- 随缘一象 · 竹筒寻象（仪式组件） -->
    <BambooLottery :open="lotteryOpen" :result="lotteryResult"
      @close="lotteryOpen = false" @explore="goLottery" @again="randomConcept" />
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getArtworkDetail, getArtworkList, getAtlasPaintings, getConceptList } from '../api'
import ConceptCard from '../components/ConceptCard.vue'
import BambooLottery from '../components/BambooLottery.vue'
import SectionTitle from '../components/SectionTitle.vue'

const route = useRoute()
// 功能按钮激活态：点到谁谁变蓝（路由前缀匹配；「随缘一象」由 lotteryOpen 驱动）
const isActivePath = (p) => route.path.startsWith(p)

const concepts = ref([])        // 当前展示的8个精选（4列×2行）
const featuredPool = ref([])     // 全部精选池
const allConcepts = ref([])
const artworks = ref([])
const artworkPool = ref([])        // 全部精选池
const lastArtworkIndices = ref([])  // 上一批索引，避免重复
const previewArt = ref(null)
const previewLoading = ref(false)
// 诗意图鉴：画卷横卷展陈（复用「诗画相映」动画）
const atlasPaintings = ref([])
const atlasInView = ref(false)
const atlasRow = ref(null)
const atlasDrag = { active: false, moved: false, startX: 0, startLeft: 0 }
// AI 助手入口：滚入视口触发逐级入场
const aiHero = ref(null)
const aiInView = ref(false)
let atlasScrollRaf = null
let atlasTargetLeft = null

// 本地测试画卷（后台无数据时兜底展示，便于预览「诗画相映」动画）
const ATLAS_FALLBACK = [
  { id: 'fb-shanju', title: '山居春晓图', en: 'Spring Dawn in the Mountain Residence', src: '/shanju-chunxiao.png', imageries: { 竹: {}, 拱桥: {}, 樱花: {}, 溪流: {}, 古楼: {}, 远山: {}, 晨雾: {} } },
  { id: 'fb-xiyang', title: '夕阳山色图', en: 'Sunset Glow over Mountain Pavilion', src: '/xiyang-shanse.png', imageries: { 落日: {}, 远山: {}, 楼阁: {}, 湖水: {}, 飞鸟: {}, 烟岚: {} } },
  { id: 'fb-changying', title: '长缨破阵图', en: 'The Spear-Maiden Breaking the Ranks', src: '/changying-pozhen.png', imageries: { 女将: {}, 长枪: {}, 战旗: {}, 黑云: {}, 战甲: {}, 红袍: {}, 士卒: {} } },
  { id: 'fb-zhongkui', title: '钟馗斩鬼图', en: 'Zhong Kui Subduing the Demons', src: '/zhongkui-zhangui.png', imageries: { 钟馗: {}, 鬼: {}, 道袍: {}, 魔影: {} } },
]
// 首屏艺术品展示墙：标注精选作品 + 轮播序号（纯展示，不可交互）
const heroArtworks = ref([])
const heroIndex = ref(0)
let heroTimer = null
// 预览弹窗打开时锁定背景滚动
watch(previewArt, (v) => { document.body.style.overflow = v ? 'hidden' : '' })
async function openArtPreview(a) {
  previewArt.value = a; previewLoading.value = true
  try { const d = await getArtworkDetail(a.id); if (d) previewArt.value = { ...a, ...d } } catch {}
  finally { previewLoading.value = false }
}
const loading = ref(true)
const lastIndices = ref([])      // 上一批展示的索引，避免重复

const aiPrompts = [
  '“月”在古诗里有哪些含义？',
  '夕阳为何总与离愁相伴？',
  '用“柳”写一首七言绝句',
]
function askAi(q) {
  window.dispatchEvent(new CustomEvent('sxz-ask', { detail: q }))
}

const features = [
  { seal: '解', color: '#2B4C7E', title: '意象解读', slogan: '一词一象，读懂诗意', desc: '多维解析古诗词意象的含义、情感与文化内涵。' },
  { seal: '联', color: '#9B4423', title: '关联探索', slogan: '一象万联，洞见诗脉', desc: '关联意象、诗句、情感与诗词，发现隐藏的诗意关系。' },
  { seal: '探', color: '#5B7C5F', title: '智能交互', slogan: '一问一探，沉浸诗境', desc: '通过智能交互与可视化探索，让古诗词意象由静态知识变成可探索的文化体验。' },
]

function pickBatch(pool, count, excludeIndices) {
  // 从 pool 中随机选取 count 个，排除 excludeIndices 的项
  const available = pool
    .map((item, i) => ({ item, i }))
    .filter(p => !excludeIndices.includes(p.i))
  if (available.length < count) {
    // 不够时重洗全部
    const shuffled = [...pool].sort(() => Math.random() - 0.5)
    return { batch: shuffled.slice(0, count), indices: shuffled.slice(0, count).map(item => pool.indexOf(item)) }
  }
  const shuffled = available.sort(() => Math.random() - 0.5)
  const batch = shuffled.slice(0, count).map(p => p.item)
  const indices = shuffled.slice(0, count).map(p => p.i)
  return { batch, indices }
}

function reshuffle() {
  if (featuredPool.value.length <= 8) return
  const { batch, indices } = pickBatch(featuredPool.value, 8, lastIndices.value)
  concepts.value = batch
  lastIndices.value = indices
}

function reshuffleArtworks() {
  if (artworkPool.value.length <= 8) return
  const { batch, indices } = pickBatch(artworkPool.value, 8, lastArtworkIndices.value)
  artworks.value = batch
  lastArtworkIndices.value = indices
}

// ── 诗意图鉴：画卷横向拖拽 / 滚轮平移 / 点击抑制 ──
function imageryList(p) { return Object.keys(p?.imageries || {}) }
function scheduleAtlasScroll(left) {
  atlasTargetLeft = left
  if (atlasScrollRaf == null) {
    atlasScrollRaf = requestAnimationFrame(() => {
      atlasScrollRaf = null
      const t = atlasTargetLeft
      atlasTargetLeft = null
      if (t != null && atlasRow.value) atlasRow.value.scrollLeft = t
    })
  }
}
function onAtlasDragStart(e) {
  atlasDrag.active = true
  atlasDrag.moved = false
  atlasDrag.startX = e.clientX
  atlasDrag.startLeft = atlasRow.value.scrollLeft
  atlasRow.value.classList.add('is-dragging')
}
function onAtlasDrag(e) {
  if (!atlasDrag.active) return
  const dx = e.clientX - atlasDrag.startX
  if (Math.abs(dx) > 4) atlasDrag.moved = true
  scheduleAtlasScroll(atlasDrag.startLeft - dx)
}
function onAtlasDragEnd() {
  atlasDrag.active = false
  if (atlasRow.value) atlasRow.value.classList.remove('is-dragging')
}
function onAtlasWheel(e) {
  scheduleAtlasScroll(atlasRow.value.scrollLeft + e.deltaY)
}
function onAtlasCardClick(e) {
  if (atlasDrag.moved) e.preventDefault()
}

// 读取图片原始宽高比（后端无宽高字段，前端预加载筛选）
function loadRatio(url) {
  return new Promise((resolve) => {
    const img = new Image()
    img.onload = () => resolve(img.naturalWidth / img.naturalHeight)
    img.onerror = () => resolve(0)
    img.src = url
  })
}

onMounted(async () => {
  try {
    const data = await getConceptList({ page_size: 200 })
    allConcepts.value = data.items
    // 取管理后台勾选的精选意象 → 存入池
    const featured = data.items.filter(c => c.is_featured)
    if (featured.length) {
      featuredPool.value = featured
      const { batch, indices } = pickBatch(featured, Math.min(8, featured.length), [])
      concepts.value = batch
      lastIndices.value = indices
    } else {
      // 无精选时降级为 poetry_count 前6
      concepts.value = [...data.items].sort((a, b) => b.poetry_count - a.poetry_count).slice(0, 8)
    }
  } finally {
    loading.value = false
  }
  // 艺术品精选：取全部精选池，再挑 8 幅
  try {
    const art = await getArtworkList({ featured: true, page_size: 300 })
    const pool = art.items || []
    if (!pool.length) {
      // 无精选时降级为最新 8 幅（不显示换一批）
      const fallback = await getArtworkList({ page: 1, page_size: 8 })
      artworks.value = fallback.items
      artworkPool.value = []
    } else {
      artworkPool.value = pool
      const { batch, indices } = pickBatch(pool, Math.min(8, pool.length), [])
      artworks.value = batch
      lastArtworkIndices.value = indices
    }
  } catch { artworks.value = []; artworkPool.value = [] }
  // 诗意图鉴：画卷横卷（滚入视口触发逐张淡入；后台无数据时回落到本地测试画卷）
  try {
    const at = await getAtlasPaintings()
    atlasPaintings.value = at.paintings?.length ? at.paintings : ATLAS_FALLBACK
  } catch { atlasPaintings.value = ATLAS_FALLBACK }
  if (atlasPaintings.value.length) {
    await nextTick()
    if (atlasRow.value) {
      const atlasObs = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) { atlasInView.value = true; atlasObs.disconnect() }
      }, { threshold: 0.15 })
      atlasObs.observe(atlasRow.value)
    }
  }
  // 灵犀助手入口：滚入视口触发逐级入场
  if (aiHero.value) {
    const aiObs = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting) { aiInView.value = true; aiObs.disconnect() }
    }, { threshold: 0.15 })
    aiObs.observe(aiHero.value)
  }
  // 首屏展示墙：优先「精选」标注艺术品，不足时补最新
  try {
    const feat = await getArtworkList({ featured: true, page_size: 16 })
    let pool = feat.items && feat.items.length ? feat.items : []
    if (pool.length < 8) {
      const more = await getArtworkList({ page: 1, page_size: 16 })
      const seen = new Set(pool.map((a) => a.id))
      for (const a of more.items) {
        if (!seen.has(a.id)) { pool.push(a); seen.add(a.id) }
      }
    }
    // 比例筛选：只保留横幅且比例贴近封面的作品（可完整铺满、裁切极小）
    const checked = await Promise.all(pool.map(async (a) => {
      const r = await loadRatio(a.image_url || a.thumb_url)
      return { a, ok: r >= 1.3 && r <= 2.8 }
    }))
    let fit = checked.filter(x => x.ok).map(x => x.a)
    if (fit.length < 4) fit = pool        // 合格者太少时兜底，避免展示墙空转
    heroArtworks.value = fit.slice(0, 10)
  } catch { heroArtworks.value = artworks.value }
  // 5秒淡切一幅，循环无跳变
  heroTimer = setInterval(() => {
    if (heroArtworks.value.length) heroIndex.value = (heroIndex.value + 1) % heroArtworks.value.length
  }, 5000)
})
onBeforeUnmount(() => {
  clearInterval(heroTimer)
  if (atlasScrollRaf != null) cancelAnimationFrame(atlasScrollRaf)
})

const lotteryOpen = ref(false)
const lotteryResult = ref(null)

function randomConcept() {
  if (!allConcepts.value.length) return
  lotteryResult.value = allConcepts.value[Math.floor(Math.random() * allConcepts.value.length)]
  lotteryOpen.value = true
}

function goLottery() {
  if (lotteryResult.value) {
    lotteryOpen.value = false
    window.location.href = `/concept/${lotteryResult.value.id}`
  }
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.35s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── 首屏艺术品展示墙 ── */
.hero-art {
  opacity: 0;
  transition: opacity 1.8s ease-in-out;
  will-change: opacity, transform;
  /* 所有图层常设漂移动画；非活动层仅暂停（保留进度，切换类时无 transform 跳变 → 消除卡顿） */
  animation: heroDrift 22s ease-in-out infinite alternate;
  animation-play-state: paused;
  /* 低饱和低对比 + 轻微柔化，突出氛围而非信息 */
  filter: saturate(0.72) contrast(0.92) brightness(0.94) blur(2px);
}
.hero-art.hero-active {
  opacity: 1;
  animation-play-state: running;
}
@keyframes heroDrift {
  from { transform: scale(1.06) translate3d(-1.6%, 0, 0); }
  to   { transform: scale(1.06) translate3d(1.6%, 0, 0); }
}
@media (prefers-reduced-motion: reduce) {
  .hero-art { animation: none; }
}

/* ── 首屏玻璃功能按钮 ── */
.hero-btn {
  padding: 0.625rem 1.75rem;
  border-radius: 9999px;
  font-family: 'Kaiti SC', STKaiti, KaiTi, 'Noto Serif SC', serif;
  font-size: 1rem;
  letter-spacing: 0.25em;
  color: #2B4C7E;
  background: rgba(255, 255, 255, 0.30);
  border: 1px solid rgba(43, 76, 126, 0.25);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  cursor: pointer;
  transition: all 0.3s ease;
}
.hero-btn:hover {
  background: rgba(43, 76, 126, 0.9);
  color: #F5F1E8;
  border-color: rgba(43, 76, 126, 0.6);
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(43, 76, 126, 0.28);
}
/* 激活态：点到谁谁变蓝（石青填充常驻） */
.hero-btn--active {
  background: #2B4C7E;
  color: #F5F1E8;
  border-color: #2B4C7E;
}
.hero-btn--active:hover { background: #1D3450; }

/* ── 三大核心价值卡片 ── */
.feature-card {
  position: relative; overflow: hidden;
  display: flex; flex-direction: column; align-items: flex-start;
  background: rgba(251,248,241,0.62); border: 1px solid rgba(44,44,44,0.06);
  border-radius: 10px; padding: 26px 26px 24px; cursor: default;
  box-shadow: 0 2px 12px rgba(44,44,44,0.05);
  transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
}
.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 14px 30px rgba(44,44,44,0.12);
  border-color: color-mix(in srgb, var(--accent) 45%, rgba(44,44,44,0.06));
}
/* 角落极淡主题色墨晕（替代右上角大字水印） */
.feature-card__wash {
  position: absolute; right: -32px; top: -32px; width: 120px; height: 120px;
  border-radius: 50%; pointer-events: none;
  background: radial-gradient(circle, var(--accent), transparent 70%);
  opacity: 0.06;
}
/* 方形印章字（主题色底 + 内圈细描边，仿篆刻印面） */
.feature-seal {
  display: inline-flex; align-items: center; justify-content: center;
  width: 40px; height: 40px; border-radius: 6px;
  background: var(--accent); color: #F5F1E8;
  font-family: 'Kaiti SC', STKaiti, KaiTi, 'Noto Serif SC', serif;
  font-size: 22px; line-height: 1;
  box-shadow: inset 0 0 0 1.5px rgba(245,241,232,0.5);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.feature-card:hover .feature-seal {
  transform: scale(1.06);
  box-shadow: inset 0 0 0 1.5px rgba(245,241,232,0.5), 0 0 0 5px color-mix(in srgb, var(--accent) 12%, transparent);
}
.feature-card__title {
  margin-top: 18px;
  font-family: 'Noto Serif SC', 'Songti SC', STSong, SimSun, serif;
  font-weight: 600; font-size: 19px; line-height: 1.4;
  color: #2C2C2C; letter-spacing: 0.05em;
}
.feature-card__slogan {
  margin-top: 9px;
  font-family: 'Noto Serif SC', 'Songti SC', STSong, SimSun, serif;
  font-weight: 600; font-size: 15px; line-height: 1.5;
  color: var(--accent); letter-spacing: 0.03em;
}
.feature-card__desc {
  margin-top: 10px;
  font-size: 13px; line-height: 1.85; color: #6B6B6B;
}
/* 底部主题色装饰线，hover 缓慢延伸 */
.feature-card__line {
  margin-top: 20px;
  display: block; height: 2px; width: 22px; border-radius: 1px;
  background: var(--accent); opacity: 0.55;
  transition: width 0.3s ease, opacity 0.3s ease;
}
.feature-card:hover .feature-card__line { width: 40px; opacity: 0.85; }
/* 桌面端：卡片间极淡递进连接线（暗示「理解 → 关联 → 探索」） */
@media (min-width: 768px) {
  .feature-card:not(:last-child)::after {
    content: ''; position: absolute; right: -18px; top: 50%;
    width: 12px; height: 1px; transform: translateY(-50%);
    background: linear-gradient(90deg, rgba(44,44,44,0.18), transparent);
  }
}
@media (prefers-reduced-motion: reduce) {
  .feature-card, .feature-seal, .feature-card__line { transition: none; }
  .feature-card:hover { transform: none; }
  .feature-card:hover .feature-seal { transform: none; box-shadow: inset 0 0 0 1.5px rgba(245,241,232,0.5); }
  .feature-card:hover .feature-card__line { width: 22px; opacity: 0.55; }
}

/* ── AI 助手入口 · 古典数字人文质感 ── */
.ai-hero {
  position: relative; overflow: hidden;
  border-radius: 12px;
  background: linear-gradient(150deg, #EEF3EE 0%, #DFE9E1 50%, #D1E1D6 100%);
  border: 1px solid rgba(91, 124, 95, 0.20);
  box-shadow: 0 6px 28px rgba(91, 124, 95, 0.12);
}
/* 宣纸肌理（噪点压至极低透明度） */
.ai-hero::before {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3CfeColorMatrix values='0 0 0 0 0.17 0 0 0 0 0.17 0 0 0 0 0.15 0 0 0 0.035 0'/%3E%3C/filter%3E%3Crect width='200' height='200' filter='url(%23n)'/%3E%3C/svg%3E");
  opacity: 0.35;
}
/* 淡墨 / 浅青灰晕染 */
.ai-hero::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background:
    radial-gradient(circle at 18% 12%, rgba(91, 124, 95, 0.08), transparent 55%),
    radial-gradient(circle at 85% 90%, rgba(155, 68, 35, 0.05), transparent 60%);
}
.ai-hero__inner {
  position: relative; z-index: 1;
  max-width: 720px; margin: 0 auto;
  padding: 44px 24px 40px;
  text-align: center;
}
@media (min-width: 640px) { .ai-hero__inner { padding: 52px 40px 48px; } }

/* 标识：沿用 logo + 淡青灰细环，与标题形成「徽记 + 标题」层级 */
.ai-badge {
  width: 64px; height: 64px; margin: 0 auto;
  display: flex; align-items: center; justify-content: center;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(91, 124, 95, 0.16);
  box-shadow: 0 1px 6px rgba(44, 44, 44, 0.06);
}
.ai-badge__logo { width: 42px; height: 42px; object-fit: contain; animation: ai-breathe 3.6s ease-in-out infinite; }
@keyframes ai-breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.03); }
}

.ai-title {
  margin-top: 18px;
  font-family: 'Noto Serif SC', 'Songti SC', STSong, SimSun, serif;
  font-weight: 600; font-size: 20px; line-height: 1.5;
  letter-spacing: 0.12em; color: #2C2C2C;
}
@media (min-width: 640px) { .ai-title { font-size: 24px; } }

.ai-sub {
  margin-top: 10px;
  font-size: 12px; line-height: 1.7; color: #6B6B6B;
}
@media (min-width: 640px) { .ai-sub { font-size: 14px; } }

/* 示例问题：轻量诗签卡片 */
.ai-prompts {
  margin-top: 26px;
  display: grid; grid-template-columns: 1fr; gap: 12px;
}
@media (min-width: 640px) { .ai-prompts { grid-template-columns: repeat(3, 1fr); } }
.ai-prompt {
  position: relative; text-align: left;
  min-height: 56px;
  padding: 13px 15px 13px 18px;
  background: rgba(255, 255, 255, 0.60);
  border: 1px solid rgba(91, 124, 95, 0.16);
  border-radius: 8px;
  font-family: 'Noto Serif SC', 'Songti SC', STSong, SimSun, serif;
  font-size: 14px; line-height: 1.6; color: rgba(44, 44, 44, 0.85);
  cursor: pointer;
  transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
}
.ai-prompt__mark {
  position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  border-radius: 8px 0 0 8px;
  background: rgba(155, 68, 35, 0.55);
  transition: background 0.25s ease;
}
.ai-prompt:hover {
  transform: translateY(-2px);
  border-color: rgba(155, 68, 35, 0.35);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 8px 22px rgba(44, 44, 44, 0.10);
}
.ai-prompt:hover .ai-prompt__mark { background: #9B4423; }

/* CTA：朱砂红小面积行动入口 */
.ai-cta-wrap { margin-top: 30px; }
.ai-cta {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 11px 30px;
  border-radius: 7px;
  background: #9B4423; color: #F5F1E8;
  font-family: 'Noto Serif SC', 'Songti SC', STSong, SimSun, serif;
  font-size: 14px; letter-spacing: 0.15em;
  transition: background 0.25s ease, box-shadow 0.25s ease;
}
.ai-cta__arrow { display: inline-block; transition: transform 0.25s ease; }
.ai-cta:hover { background: #8A3A1E; box-shadow: 0 6px 18px rgba(155, 68, 35, 0.28); }
.ai-cta:hover .ai-cta__arrow { transform: translateX(3px); }

/* 极淡东方装饰：淡墨点 */
.ai-orn {
  position: absolute; border-radius: 9999px; pointer-events: none;
  background: radial-gradient(circle, rgba(44, 44, 44, 0.30), transparent 70%);
}
.ai-orn--a { width: 6px; height: 6px; left: 8%; top: 18%; opacity: 0.35; }
.ai-orn--b { width: 4px; height: 4px; right: 11%; top: 30%; opacity: 0.28; }
.ai-orn--c { width: 5px; height: 5px; right: 18%; bottom: 16%; opacity: 0.30; }

/* 入场：滚入视口后逐级淡入 + 上移（总时长约 800ms） */
.ai-hero .ai-badge,
.ai-hero .ai-title,
.ai-hero .ai-sub,
.ai-hero .ai-prompts,
.ai-hero .ai-cta-wrap { opacity: 0; }
.ai-hero.ai-enter .ai-badge    { animation: ai-rise 0.5s ease both; }
.ai-hero.ai-enter .ai-title    { animation: ai-rise 0.5s ease 0.08s both; }
.ai-hero.ai-enter .ai-sub      { animation: ai-rise 0.5s ease 0.16s both; }
.ai-hero.ai-enter .ai-prompts  { animation: ai-rise 0.5s ease 0.26s both; }
.ai-hero.ai-enter .ai-cta-wrap { animation: ai-rise 0.5s ease 0.38s both; }
@keyframes ai-rise {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .ai-badge__logo { animation: none; }
  .ai-hero .ai-badge, .ai-hero .ai-title, .ai-hero .ai-sub,
  .ai-hero .ai-prompts, .ai-hero .ai-cta-wrap { opacity: 1; }
  .ai-hero.ai-enter .ai-badge, .ai-hero.ai-enter .ai-title,
  .ai-hero.ai-enter .ai-sub, .ai-hero.ai-enter .ai-prompts,
  .ai-hero.ai-enter .ai-cta-wrap { animation: none; }
}

/* ── 下滑提示双箭头：逐层循环下沉 ── */
.scroll-hint__chev { animation: scroll-drift 1.6s ease-in-out infinite; }
.scroll-hint__chev--ghost { animation-delay: 0.6s; }
@keyframes scroll-drift {
  0%   { opacity: 0; transform: translateY(-8px); }
  35%  { opacity: 1; }
  100% { opacity: 0; transform: translateY(6px); }
}
@media (prefers-reduced-motion: reduce) {
  .scroll-hint__chev { animation: none; }
}

/* ── 换一批：石青胶囊 · 楷体（意象精选 / 艺术品精选共用） ── */
.reshuffle-btn {
  display: inline-flex; align-items: center; gap: 6px;
  border-radius: 9999px;
  font-family: 'Kaiti SC', STKaiti, KaiTi, 'Noto Serif SC', serif;
  font-size: 13px; letter-spacing: 0.2em;
  color: #2B4C7E; background: rgba(255,255,255,0.40);
  border: 1px solid rgba(43,76,126,0.30);
  backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
  padding: 0.375rem 1.25rem;
  transition: all 0.3s ease;
}
.reshuffle-btn:hover { background: #2B4C7E; color: #F5F1E8; border-color: #2B4C7E; box-shadow: 0 6px 18px rgba(43,76,126,0.22); }
.reshuffle-btn:active { transform: scale(0.97); }

/* ── 诗意图鉴：横卷画卷展陈（复用「诗画相映」动画） ── */
.atlas-row {
  display: flex; gap: 20px;
  overflow-x: auto;
  scrollbar-width: none; -ms-overflow-style: none;
  overscroll-behavior-x: contain;
  cursor: grab; user-select: none;
  padding: 8px 2px 18px;
}
.atlas-row::-webkit-scrollbar { display: none; }
.atlas-row:active { cursor: grabbing; }
.atlas-row.is-dragging .atlas-card,
.atlas-row.is-dragging .atlas-card__img img { transition: none; }

.atlas-card {
  display: flex; flex-direction: column; flex-shrink: 0;
  width: 260px; aspect-ratio: 3 / 4;
  overflow: hidden; border-radius: 6px;
  background: #FBF8F1;
  border: 1px solid rgba(44, 44, 44, 0.08);
  box-shadow: 0 1px 6px rgba(44, 44, 44, 0.05);
  cursor: pointer;
  transition: transform 0.35s ease-out, box-shadow 0.35s ease-out, border-color 0.35s ease-out;
}
.atlas-card__img { height: 56%; flex-shrink: 0; overflow: hidden; background: #F3EEE2; }
.atlas-card__img img { width: 100%; height: 100%; object-fit: cover; object-position: center; transition: transform 0.4s ease-out; }
.atlas-card__body { flex: 1; padding: 15px 18px; display: flex; flex-direction: column; gap: 10px; }
.atlas-card__name { font-family: 'Noto Serif SC', 'Songti SC', STSong, SimSun, serif; font-weight: 600; font-size: 18px; line-height: 1.4; color: #2C2C2C; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; transition: color 0.35s ease-out; }
.atlas-card__meta { font-size: 12px; line-height: 1.6; color: #6B6B6B; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.atlas-card__imagery {
  padding-top: 8px;
  border-top: 1px solid rgba(44, 44, 44, 0.07);
  font-family: 'Noto Serif SC', 'Kaiti SC', serif;
  font-size: 12px; line-height: 1.9; letter-spacing: 0.05em;
  color: #6B6B6B;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.atlas-card__sep { color: #9B4423; opacity: 0.5; }

/* 悬停：古画缓缓展开（微放大 + 上浮 + 名称现朱砂） */
.atlas-card:hover { transform: translateY(-4px); box-shadow: 0 10px 26px rgba(44, 44, 44, 0.10); border-color: rgba(155, 68, 35, 0.40); }
.atlas-card:hover .atlas-card__img img { transform: scale(1.04); }
.atlas-card:hover .atlas-card__name { color: #9B4423; }

/* 进入动画：滚入视口时自下方 10px 淡入，逐张级差 */
@keyframes atlas-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
.atlas-card.atlas-enter { animation: atlas-rise 0.5s ease-out both; }

/* 滑动提示 */
.atlas-hint {
  display: flex; align-items: center; justify-content: center;
  gap: 8px; margin-top: 6px;
  color: #9B4423; opacity: 0.55;
  user-select: none; pointer-events: none;
}
.atlas-hint__arrow { width: 15px; height: 15px; animation: atlas-hint-drift 1.6s ease-in-out infinite; }
@keyframes atlas-hint-drift {
  0% { opacity: 0; transform: translateX(-6px); }
  40% { opacity: 1; }
  100% { opacity: 0; transform: translateX(6px); }
}

@media (prefers-reduced-motion: reduce) {
  .atlas-card.atlas-enter { animation: none; }
  .atlas-hint__arrow { animation: none; }
}
</style>
