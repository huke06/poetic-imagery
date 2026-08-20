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
      <div class="absolute bottom-5 left-1/2 -translate-x-1/2 z-20 text-moyan/50 flex flex-col items-center gap-1 pointer-events-none">
        <span class="text-[10px] tracking-[0.3em]">向下滚动</span>
        <svg class="w-4 h-4 animate-bounce" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg>
      </div>
    </section>

    <div class="ink-divider max-w-4xl mx-auto mt-10"></div>

    <!-- 意象精选 -->
    <section class="max-w-6xl mx-auto px-4 py-16">
      <div class="flex items-center justify-between">
        <SectionTitle sub="点击卡片进入意象详情">意象精选</SectionTitle>
        <button v-if="featuredPool.length > 8" @click="reshuffle"
          class="btn-outline !py-1.5 !px-4 !text-xs flex items-center gap-1.5 group">
          <svg class="w-3.5 h-3.5 transition-transform group-hover:rotate-180" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>
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
        <SectionTitle sub="诗画互证 · 前往艺术展厅">艺术品精选</SectionTitle>
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

    <!-- 诗意图鉴入口 -->
    <section class="max-w-6xl mx-auto px-4 py-14">
      <div class="card card-hover p-8 flex flex-col sm:flex-row items-center justify-between gap-5 rise-in">
        <div class="flex items-center gap-5">
          <span class="seal !w-14 !h-14 !text-lg shrink-0">鉴</span>
          <div>
            <h3 class="font-song text-xl font-bold tracking-wider">诗意图鉴 · 画中诗境</h3>
            <p class="text-sm text-qianhui mt-1 leading-6">名画为卷，意象为点 —— 左右翻阅画卷，点击画中圆点，探寻每一处诗情。</p>
          </div>
        </div>
        <router-link to="/atlas" class="btn-primary shrink-0">进入诗意图鉴</router-link>
      </div>
    </section>

    <!-- 三大核心价值 -->
    <section class="relative overflow-hidden">
      <div class="max-w-6xl mx-auto px-4 py-16">
        <SectionTitle>三大核心价值</SectionTitle>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          <div v-for="(f, i) in features" :key="f.title"
            class="feature-card rise-in" :style="{ animationDelay: i * 0.1 + 's', '--accent': f.color }">
            <div class="feature-card__watermark font-kai">{{ f.watermark }}</div>
            <div class="w-12 h-12 rounded-lg flex items-center justify-center text-2xl text-xuanzhi font-kai shadow-lg"
              :style="{ background: 'linear-gradient(135deg,' + f.color + ',' + f.color + 'cc)' }">{{ f.icon }}</div>
            <h3 class="font-song text-lg font-semibold mt-4">{{ f.title }}</h3>
            <p class="text-sm text-qianhui leading-7 mt-2">{{ f.desc }}</p>
            <div class="mt-4 h-0.5 w-8 rounded-full" :style="{ background: f.color, opacity: 0.5 }"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- AI 助手入口 · 向灵犀提问 -->
    <section class="relative overflow-hidden">
      <div class="max-w-5xl mx-auto px-4">
        <div class="ai-hero rounded-2xl px-6 py-12 sm:px-12 text-center relative overflow-hidden">
          <div class="absolute -top-16 -right-16 w-64 h-64 rounded-full opacity-20" style="background: radial-gradient(circle, #F5F1E8, transparent 70%)"></div>
          <div class="absolute -bottom-20 -left-10 w-56 h-56 rounded-full opacity-10" style="background: radial-gradient(circle, #F5F1E8, transparent 70%)"></div>
          <img src="/lingxi-logo.png" alt="灵犀助手" class="w-12 h-12 object-contain mx-auto" />
          <h3 class="font-song text-2xl sm:text-3xl font-bold mt-5 text-xuanzhi">向灵犀助手提问</h3>
          <p class="text-sm text-xuanzhi/70 mt-3 leading-6">不懂意象？不会赏析？一键唤起灵犀，随时陪你读诗、解诗、写诗。</p>
          <div class="flex flex-wrap justify-center gap-2.5 mt-6">
            <button v-for="q in aiPrompts" :key="q" @click="askAi(q)"
              class="px-4 py-2 rounded-full text-sm text-xuanzhi/90 border border-xuanzhi/30 hover:bg-xuanzhi hover:text-shiqing transition-all">
              {{ q }}
            </button>
          </div>
          <div class="mt-8">
            <router-link to="/agent" class="btn-primary !bg-xuanzhi !text-shiqing hover:!bg-white shadow-lg !px-8">进入灵犀助手 →</router-link>
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
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getArtworkDetail, getArtworkList, getConceptList } from '../api'
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
const previewArt = ref(null)
const previewLoading = ref(false)
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
  '「月」在古诗里有哪些含义？',
  '夕阳为何总与离愁相伴？',
  '用「柳」写一首七言绝句',
]
function askAi(q) {
  window.dispatchEvent(new CustomEvent('sxz-ask', { detail: q }))
}

const features = [
  { icon: '变', color: '#2B4C7E', watermark: '变', title: '意象演变', desc: '朝代时间轴 × 频次折线 × 情感环形图，用数据讲清一个意象的兴衰流变与情感变迁。' },
  { icon: '画', color: '#9B4423', watermark: '画', title: '诗画互证', desc: '每个意象匹配对应古画，见意象知画意，观古画品诗情，打通诗文库与艺术品库。' },
  { icon: '问', color: '#5B7C5F', watermark: '问', title: '智能问答', desc: '基于自建意象知识库的轻量 RAG 问答与格律创诗，回答全部锚定本地权威数据。' },
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
  // 艺术品精选：取精选池
  try {
    const art = await getArtworkList({ featured: true, page_size: 8 })
    artworks.value = art.items
    // 无精选时降级为最新8幅
    if (!artworks.value.length) {
      const fallback = await getArtworkList({ page: 1, page_size: 8 })
      artworks.value = fallback.items
    }
  } catch { artworks.value = [] }
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
onBeforeUnmount(() => clearInterval(heroTimer))

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
  background: rgba(255,255,255,0.6); border: 1px solid rgba(0,0,0,0.05);
  border-radius: 10px; padding: 24px; cursor: default;
  box-shadow: 0 2px 12px rgba(44,44,44,0.06);
  transition: transform 0.35s, box-shadow 0.35s, border-color 0.35s;
}
.feature-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 16px 34px rgba(44,44,44,0.13);
  border-color: var(--accent);
}
.feature-card__watermark {
  position: absolute; right: -6px; top: -14px; font-size: 96px; line-height: 1;
  color: var(--accent); opacity: 0.06; pointer-events: none; user-select: none;
}

/* ── AI 助手入口 ── */
.ai-hero {
  background: linear-gradient(135deg, #16283F 0%, #2B4C7E 55%, #3A5A8C 100%);
  box-shadow: 0 18px 48px rgba(43,76,126,0.35);
}
</style>
