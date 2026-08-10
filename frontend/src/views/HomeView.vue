<template>
  <div>
    <!-- 首屏：夜航山水意境 -->
    <section class="relative overflow-hidden min-h-[78vh] flex items-center">
      <!-- 层叠夜空 -->
      <div class="absolute inset-0" style="background: linear-gradient(180deg, #16283F 0%, #2B4C7E 46%, #7A89A0 78%, #F5F1E8 100%)"></div>
      <!-- 明月 -->
      <div class="absolute right-[26%] md:right-[30%] top-[14%] w-28 h-28 sm:w-36 sm:h-36 rounded-full moon-breathe"
        style="background: radial-gradient(circle at 38% 34%, #FDF9E7 0%, #F2E8C9 58%, #E3D5A8 100%);
               box-shadow: 0 0 60px 26px rgba(245, 236, 200, 0.35), 0 0 140px 60px rgba(245, 236, 200, 0.16)"></div>
      <!-- 淡墨群山 -->
      <svg class="absolute bottom-0 left-0 w-full pointer-events-none" preserveAspectRatio="none" viewBox="0 0 1200 260" style="height: 42%">
        <path d="M0 160 Q150 60 320 130 T640 110 Q760 40 900 120 T1200 90 L1200 260 L0 260 Z" fill="#1D3450" opacity="0.55"/>
        <path d="M0 205 Q200 130 420 180 T840 160 Q1000 120 1200 175 L1200 260 L0 260 Z" fill="#16283F" opacity="0.8"/>
        <path d="M0 245 Q260 200 520 232 T1200 220 L1200 260 L0 260 Z" fill="#0F1E33"/>
      </svg>
      <!-- 月辉粒子 -->
      <ParticleCanvas mode="moon" :density="1.2" />

      <div class="relative max-w-6xl mx-auto px-4 py-24 w-full">
        <div class="flex items-center justify-between">
          <div class="rise-in max-w-2xl">
            <h1 class="font-song text-7xl sm:text-8xl font-bold tracking-[0.42em] text-xuanzhi drop-shadow-lg">诗象志</h1>
            <div class="mt-7 flex items-center gap-4">
              <span class="h-px w-14 bg-xuanzhi/50"></span>
              <p class="font-kai text-xl sm:text-2xl tracking-[0.3em] text-xuanzhi/90">一字藏万象，一诗见千年</p>
            </div>
            <p class="mt-6 text-sm text-xuanzhi/70 max-w-xl leading-7">
              以古典诗词意象为切口，集意象知识图谱、诗画联动、演变可视化与智能问答于一体，
              直观呈现一个词语在千年诗词中的情感承载与演变轨迹。
            </p>
            <div class="mt-10 flex items-center gap-5">
              <router-link to="/concepts" class="btn-primary !bg-xuanzhi !text-shiqing hover:!bg-white shadow-lg">意象漫游</router-link>
              <router-link to="/artworks" class="btn-outline !border-xuanzhi/70 !text-xuanzhi hover:!bg-xuanzhi hover:!text-shiqing">古画寻诗</router-link>
              <button @click="randomConcept" class="btn-outline !border-xuanzhi/50 !text-xuanzhi/80 hover:!bg-xuanzhi/10 hover:!text-xuanzhi group flex items-center gap-2" title="随机探索一个意象">
                <svg class="w-4 h-4 transition-transform group-hover:rotate-12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="12" r="10" stroke-dasharray="4 2"/>
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke-width="1" opacity="0.5"/>
                </svg>
                随缘一象
              </button>
            </div>
          </div>
          <!-- 竖排题句 -->
          <div class="hidden md:flex flex-col items-center gap-6 select-none rise-in" style="animation-delay:.3s">
            <span class="vertical-verse text-xuanzhi/85">明月出天山</span>
            <span class="w-px h-10 bg-xuanzhi/30"></span>
            <span class="vertical-verse text-xuanzhi/85">苍茫云海间</span>
            <span class="seal mt-2">诗象</span>
          </div>
        </div>
      </div>
      <!-- 底部渐隐入宣纸 -->
      <div class="absolute bottom-0 left-0 w-full h-16" style="background: linear-gradient(180deg, transparent, #F5F1E8)"></div>
    </section>

    <div class="ink-divider max-w-4xl mx-auto"></div>

    <!-- 意象精选 -->
    <section class="max-w-6xl mx-auto px-4 py-16">
      <div class="flex items-center justify-between">
        <SectionTitle sub="点击卡片进入意象详情">意象精选</SectionTitle>
        <button v-if="featuredPool.length > 6" @click="reshuffle"
          class="btn-outline !py-1.5 !px-4 !text-xs flex items-center gap-1.5 group">
          <svg class="w-3.5 h-3.5 transition-transform group-hover:rotate-180" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/></svg>
          换一批
        </button>
      </div>
      <div v-if="loading" class="py-16 text-center text-qianhui">加载中…</div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-8">
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

    <!-- 项目简介 -->
    <section class="bg-white/40 border-y border-shiqing/10">
      <div class="max-w-6xl mx-auto px-4 py-16">
        <SectionTitle>三大核心价值</SectionTitle>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          <div v-for="(f, i) in features" :key="f.title" class="card card-hover p-6 rise-in" :style="{ animationDelay: i * 0.1 + 's' }">
            <div class="w-11 h-11 rounded-md flex items-center justify-center text-xl text-xuanzhi font-kai" :style="{ background: f.color }">{{ f.icon }}</div>
            <h3 class="font-song text-lg font-semibold mt-4">{{ f.title }}</h3>
            <p class="text-sm text-qianhui leading-7 mt-2">{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- AI 助手入口 -->
    <section class="max-w-6xl mx-auto px-4 py-16 text-center">
      <p class="font-kai text-2xl text-moyan/80">「月」在古诗里有哪些含义？</p>
      <p class="font-kai text-2xl text-moyan/80 mt-2">「夕阳」为何总与离愁相伴？</p>
      <router-link to="/agent" class="btn-primary mt-8">向灵犀助手提问</router-link>
    </section>

    <!-- 随缘一象 · 竹筒求签 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="lotteryOpen" class="fixed inset-0 z-[80] flex flex-col items-center justify-center gap-6 select-none"
          style="background: radial-gradient(ellipse at 50% 25%, #1F2D42 0%, #0D1524 70%)"
          @click.self="lotteryOpen = false">
          <p class="font-kai text-xuanzhi/30 text-sm tracking-[0.5em]">— 诚心祈象 · 随缘一签 —</p>
          <!-- 签筒区域 -->
          <div class="relative flex flex-col items-center" style="margin-top: 24px">
            <!-- 竹筒 -->
            <div class="relative flex flex-col items-center"
              :class="lotteryRunning ? 'animate-shake' : ''"
              style="width: 200px">
              <!-- 筒口上沿 -->
              <div class="rounded-t-full border-2 border-b-0 border-amber-700/40 z-20"
                style="width: 160px; height: 22px; background: linear-gradient(180deg, #8B6914, #6B4F10); box-shadow: 0 -2px 6px rgba(0,0,0,0.3)"></div>
              <!-- 筒身 -->
              <div class="border-l-2 border-r-2 border-amber-700/30 relative overflow-hidden z-10"
                style="width: 160px; height: 160px; background: linear-gradient(180deg, #A07828 0%, #8B6914 28%, #7A5C12 55%, #6B4F10 100%); box-shadow: inset 3px 0 12px rgba(0,0,0,0.2), inset -3px 0 12px rgba(0,0,0,0.2)">
                <!-- 竹节纹 -->
                <div class="absolute left-0 right-0 bg-amber-800/40" style="top: 40%; height: 3px; box-shadow: 0 1px 2px rgba(0,0,0,0.2)"></div>
                <div class="absolute left-0 right-0 bg-amber-800/30" style="top: 75%; height: 2px"></div>
                <!-- 筒内签条 -->
                <div class="absolute inset-x-3 bottom-0 flex justify-center gap-2 items-end" style="height: 80%">
                  <template v-if="lotteryRunning">
                    <div v-for="i in 9" :key="i" class="w-3 rounded-t-sm transition-all duration-75"
                      :style="{ height: (14 + Math.random()*10) + 'px', background: bambooColor(i), transform: `rotate(${(i-5)*2}deg) translateY(${Math.random()*5-2}px)` }"></div>
                  </template>
                  <template v-else-if="lotteryResult">
                    <div v-for="i in 9" :key="i" class="w-3 rounded-t-sm"
                      :style="{ height: (12 + i*2) + 'px', background: bambooColor(i), transform: `rotate(${(i-5)*1.5}deg)`, opacity: i === 5 ? 0 : 0.6 }"></div>
                  </template>
                  <template v-else>
                    <div v-for="i in 9" :key="i" class="w-3 rounded-t-sm"
                      :style="{ height: (12 + i*2) + 'px', background: bambooColor(i), transform: `rotate(${(i-5)*1.5}deg)`, opacity: 0.6 }"></div>
                  </template>
                </div>
              </div>
              <!-- 筒底 -->
              <div class="rounded-b-full border-2 border-t-0 border-amber-700/40"
                style="width: 160px; height: 20px; background: linear-gradient(180deg, #4A3510, #3A2A0E); box-shadow: 0 3px 8px rgba(0,0,0,0.4)"></div>
              <!-- 底座 -->
              <div class="rounded-full border border-amber-700/30 -mt-1"
                style="width: 200px; height: 28px; background: linear-gradient(180deg, #6B4F10, #4A3510); box-shadow: 0 6px 20px rgba(0,0,0,0.5), 0 0 30px rgba(139,105,20,0.15)"></div>
            </div>

            <!-- 弹出签条 -->
            <Transition name="stick">
              <div v-if="!lotteryRunning && lotteryResult" class="absolute flex flex-col items-center"
                style="bottom: 78%; z-index: 30; animation: stickRise 0.8s cubic-bezier(0.22, 0.61, 0.36, 1) forwards">
                <div class="rounded-t-sm" style="width: 18px; height: 14px; background: linear-gradient(180deg, #D4A84B, #B8861E)"></div>
                <div class="border border-amber-600/30 flex items-center justify-center relative"
                  style="width: 28px; height: 140px; background: linear-gradient(180deg, #F0E6C8 0%, #E0D0A0 15%, #D0BC88 50%, #E0D0A0 85%, #F0E6C8 100%); box-shadow: 3px 0 10px rgba(0,0,0,0.3)">
                  <span class="font-song text-amber-900 text-xl tracking-widest vertical-rl leading-relaxed"
                    style="text-shadow: 1px 1px 0 rgba(255,255,255,0.2)">{{ lotteryResult.name }}</span>
                </div>
                <div class="rounded-b-sm" style="width: 18px; height: 14px; background: linear-gradient(180deg, #B8861E, #D4A84B)"></div>
              </div>
            </Transition>
          </div>
          <!-- 按钮 -->
          <div style="min-height: 52px; margin-top: 56px">
            <button v-if="lotteryRunning" disabled class="btn-outline !border-amber-600/15 !text-amber-500/25 !py-2.5 !px-10 !text-base">
              <span class="animate-pulse">摇晃求签中…</span>
            </button>
            <div v-else-if="lotteryResult" class="flex items-center gap-6">
              <button @click="goLottery" class="btn-primary !bg-amber-600 !text-xuanzhi hover:!bg-amber-500 shadow-lg !py-3 !px-12 !text-base !rounded-full transition-all duration-300 tracking-wider font-song"
                style="box-shadow: 0 0 30px rgba(217,169,72,0.3)">
                解签 · {{ lotteryResult.name }}
              </button>
              <button @click="randomConcept" class="btn-outline !border-amber-600/30 !text-amber-400/60 hover:!bg-amber-600/10 !py-2.5 !px-7 !text-sm !rounded-full transition-all duration-300">
                再求一签
              </button>
            </div>
          </div>
          <p class="text-amber-700/15 text-xs tracking-widest">轻触空白处 · 合上签筒</p>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getArtworkDetail, getArtworkList, getConceptList } from '../api'
import ConceptCard from '../components/ConceptCard.vue'
import ParticleCanvas from '../components/ParticleCanvas.vue'
import SectionTitle from '../components/SectionTitle.vue'

const concepts = ref([])        // 当前展示的6个精选
const featuredPool = ref([])     // 全部精选池
const allConcepts = ref([])
const artworks = ref([])
const previewArt = ref(null)
const previewLoading = ref(false)
async function openArtPreview(a) {
  previewArt.value = a; previewLoading.value = true
  try { const d = await getArtworkDetail(a.id); if (d) previewArt.value = { ...a, ...d } } catch {}
  finally { previewLoading.value = false }
}
const loading = ref(true)
const lastIndices = ref([])      // 上一批展示的索引，避免重复

const features = [
  { icon: '变', color: '#2B4C7E', title: '意象演变', desc: '朝代时间轴 × 频次折线 × 情感环形图，用数据讲清一个意象的兴衰流变与情感变迁。' },
  { icon: '画', color: '#9B4423', title: '诗画互证', desc: '每个意象匹配对应古画，见意象知画意，观古画品诗情，打通诗文库与艺术品库。' },
  { icon: '问', color: '#5B7C5F', title: '智能问答', desc: '基于自建意象知识库的轻量 RAG 问答与格律创诗，回答全部锚定本地权威数据。' },
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
  if (featuredPool.value.length <= 6) return
  const { batch, indices } = pickBatch(featuredPool.value, 6, lastIndices.value)
  concepts.value = batch
  lastIndices.value = indices
}

onMounted(async () => {
  try {
    const data = await getConceptList({ page_size: 200 })
    allConcepts.value = data.items
    // 取管理后台勾选的精选意象 → 存入池
    const featured = data.items.filter(c => c.is_featured)
    if (featured.length) {
      featuredPool.value = featured
      const { batch, indices } = pickBatch(featured, Math.min(6, featured.length), [])
      concepts.value = batch
      lastIndices.value = indices
    } else {
      // 无精选时降级为 poetry_count 前6
      concepts.value = [...data.items].sort((a, b) => b.poetry_count - a.poetry_count).slice(0, 6)
    }
  } finally {
    loading.value = false
  }
  // 艺术品精选：取精选池
  try {
    const art = await getArtworkList({ featured: true, page_size: 4 })
    artworks.value = art.items
    // 无精选时降级为最新4幅
    if (!artworks.value.length) {
      const fallback = await getArtworkList({ page: 1, page_size: 4 })
      artworks.value = fallback.items
    }
  } catch { artworks.value = [] }
})

const lotteryOpen = ref(false)
const lotteryRunning = ref(false)
const lotteryResult = ref(null)
const lotteryDisplay = ref('')

function randomConcept() {
  if (!allConcepts.value.length) return
  lotteryOpen.value = true
  lotteryResult.value = null
  lotteryRunning.value = true
  const pool = allConcepts.value
  const steps = 18 + Math.floor(Math.random() * 12) // 18-30步
  let step = 0
  let delay = 60
  function tick() {
    lotteryDisplay.value = pool[Math.floor(Math.random() * pool.length)].name
    step++
    if (step < steps) {
      delay = step > steps * 0.6 ? delay + 25 : delay + 5
      setTimeout(tick, delay)
    } else {
      const pick = pool[Math.floor(Math.random() * pool.length)]
      lotteryDisplay.value = pick.name
      lotteryResult.value = pick
      lotteryRunning.value = false
    }
  }
  tick()
}

const _bambooPalette = ['#D4C08A','#C8B880','#D0BC84','#CCB478','#D8C490','#C4B07C','#D0B880']
function bambooColor(i) { return _bambooPalette[i % _bambooPalette.length] }

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
@keyframes shake {
  0%,100% { transform: rotate(0deg) translateY(0); }
  8%  { transform: rotate(-5deg) translateY(-1px); }
  25% { transform: rotate(4deg) translateY(-2px); }
  42% { transform: rotate(-3deg) translateY(0); }
  58% { transform: rotate(2deg) translateY(-1px); }
  75% { transform: rotate(-1deg) translateY(0); }
  92% { transform: rotate(0.5deg) translateY(0); }
}
@keyframes stickRise {
  0%   { transform: translateY(0) scale(0.8); opacity: 0; }
  30%  { transform: translateY(-120px) scale(1.08); opacity: 1; }
  50%  { transform: translateY(-140px) scale(1.02); }
  70%  { transform: translateY(-130px) scale(1.05); }
  85%  { transform: translateY(-138px) scale(1.01); }
  100% { transform: translateY(-135px) scale(1); opacity: 1; }
}
.animate-shake { animation: shake 0.55s ease-in-out infinite; transform-origin: bottom center; }
.stick-enter-active { transition: all 0.5s ease-out; }
.stick-leave-active { transition: all 0.2s ease-in; }
.stick-enter-from, .stick-leave-to { opacity: 0; transform: translateY(20px); }
.vertical-rl { writing-mode: vertical-rl; }
</style>
