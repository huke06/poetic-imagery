<template>
  <div v-if="detail" class="max-w-6xl mx-auto px-4 py-10 space-y-16">
    <!-- ═══ 1. 头部概览 ═══ -->
    <section class="relative rounded-xl overflow-hidden">
      <!-- 意象主题氛围层 -->
      <div class="absolute inset-0 -mx-4 -my-6 pointer-events-none"
        :style="{ background: `radial-gradient(ellipse 60% 55% at 18% 40%, ${detail.theme_color}14, transparent 70%)` }"></div>
      <div class="absolute inset-0 -mx-4 -my-6"><ParticleCanvas :mode="particleMode" :density="0.9" /></div>
      <div class="relative grid grid-cols-1 lg:grid-cols-5 gap-8 items-center py-4">
      <div class="lg:col-span-3 rise-in">
        <div class="flex items-end gap-4">
          <h1 class="font-song text-7xl font-bold concept-glow" :style="{ color: detail.theme_color, textShadow: `0 0 34px ${detail.theme_color}55` }">{{ detail.name }}</h1>
          <span class="tag mb-3" :style="{ color: detail.theme_color, borderColor: detail.theme_color + '55' }">{{ detail.category_main }} · {{ detail.category_sub }}</span>
        </div>
        <p class="mt-2 text-xs text-qianhui tracking-wider">别称：{{ detail.aliases.join('、') || '—' }}</p>
        <p class="mt-5 text-moyan/90 leading-8">{{ detail.original_meaning }}</p>
        <p class="mt-2 text-moyan/75 leading-8 text-sm">{{ detail.poetic_meaning }}</p>
        <div class="flex flex-wrap gap-2 mt-5">
          <span v-for="t in detail.emotion_tags" :key="t" class="tag !text-sm !px-3 !py-1"
            :style="{ color: detail.theme_color, borderColor: detail.theme_color + '66', background: detail.theme_color + '0F' }">{{ t }}</span>
        </div>
        <div class="flex gap-6 mt-6 text-sm text-qianhui">
          <span>起源 <b class="text-moyan">{{ detail.origin_dynasty }}</b></span>
          <span>鼎盛 <b class="text-moyan">{{ detail.peak_dynasty }}</b></span>
          <span>收录诗文 <b class="text-moyan">{{ detail.poetry_count }}</b> 首</span>
          <span>古画 <b class="text-moyan">{{ detail.artwork_count }}</b> 幅</span>
        </div>
      </div>
      <div class="lg:col-span-2 card p-4 rise-in" style="animation-delay:.1s">
        <h3 class="text-sm text-qianhui text-center tracking-widest">情感分布</h3>
        <VChart :option="emotionOption" height="280px" />
      </div>
      </div>
    </section>

    <div class="ink-divider"></div>

    <!-- ═══ 2. 演变脉络 ═══ -->
    <section>
      <SectionTitle :color="detail.theme_color" sub="点击朝代可筛选下方名句">演变脉络</SectionTitle>
      <div class="card p-5 mt-6">
        <VChart :option="dynastyOption" height="300px" @click="onDynastyClick" ref="dynastyChart" />
        <p class="text-xs text-qianhui text-center mt-1">意象关联作品在各朝代的数量分布</p>
      </div>
      <p class="mt-5 text-sm leading-8 text-moyan/80 indent-8">{{ detail.description }}</p>
    </section>

    <!-- ═══ 3. 经典名句 ═══ -->
    <section>
      <SectionTitle :color="detail.theme_color" :sub="`共 ${poetryTotal} 条关联句读`">经典名句</SectionTitle>
      <!-- 筛选 -->
      <div class="flex flex-wrap gap-2 mt-5 text-sm">
        <button v-for="d in ['', ...dynasties]" :key="d"
          class="px-3 py-1 rounded-full border transition-all"
          :class="filterDynasty === d ? 'text-white' : 'hover:bg-black/5'"
          :style="filterDynasty === d
            ? { background: detail.theme_color, borderColor: detail.theme_color }
            : { borderColor: detail.theme_color + '44', color: detail.theme_color }"
          @click="filterDynasty = d; page = 1; loadPoetries()">
          {{ d || '全部朝代' }}
        </button>
        <span class="w-px bg-black/10 mx-1"></span>
        <button v-for="e in ['', ...detail.emotion_tags]" :key="e"
          class="px-3 py-1 rounded-full border transition-all"
          :class="filterEmotion === e ? 'text-white' : 'hover:bg-black/5'"
          :style="filterEmotion === e
            ? { background: detail.theme_color, borderColor: detail.theme_color }
            : { borderColor: detail.theme_color + '44', color: detail.theme_color }"
          @click="filterEmotion = e; page = 1; loadPoetries()">
          {{ e || '全部情感' }}
        </button>
      </div>
      <!-- 列表 -->
      <div class="space-y-3 mt-5">
        <div v-for="(item, i) in poetryItems" :key="item.rel_id"
          class="card card-hover p-5 cursor-pointer rise-in" :style="{ animationDelay: i * 0.05 + 's' }"
          @click="$router.push(`/poetry/${item.poetry.id}`)">
          <div class="flex items-start justify-between gap-4">
            <p class="verse-text text-xl leading-relaxed" :style="{ color: detail.theme_color }">{{ item.clause }}</p>
            <span v-if="item.is_classic" class="tag shrink-0 border-zhusha/40 text-zhusha bg-zhusha/5">经典名句</span>
          </div>
          <div class="flex items-center gap-3 mt-3 text-sm text-qianhui">
            <span>{{ item.poetry.dynasty }} · {{ item.poetry.author }} 《{{ item.poetry.title }}》</span>
            <span class="tag" :style="{ color: detail.theme_color, borderColor: detail.theme_color + '44' }">{{ item.emotion }}</span>
          </div>
        </div>
      </div>
      <Pagination :page="page" :page-size="pageSize" :total="poetryTotal" @change="(p) => { page = p; loadPoetries() }" />
    </section>

    <!-- ═══ 4. 对仗与意象关联 ═══ -->
    <section>
      <SectionTitle :color="detail.theme_color">对仗与意象关联</SectionTitle>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <!-- 对仗词组 -->
        <div class="card p-5">
          <h3 class="text-sm text-qianhui tracking-widest mb-4">高频对仗</h3>
          <div v-if="detail.couplets.length" class="space-y-4">
            <div v-for="c in detail.couplets" :key="c.verse" class="border-l-2 pl-4 py-1" :style="{ borderColor: detail.theme_color }">
              <div class="flex items-center gap-3 font-kai text-lg">
                <span :style="{ color: detail.theme_color }">{{ c.word_a }}</span>
                <span class="text-qianhui text-sm">对</span>
                <span class="text-zheshi">{{ c.word_b }}</span>
              </div>
              <p class="verse-text text-moyan/80 mt-1">{{ c.verse }}</p>
              <p class="text-xs text-qianhui mt-0.5">{{ c.source }}</p>
            </div>
          </div>
          <p v-else class="text-sm text-qianhui/70 py-8 text-center">对仗词组待补充（可在管理后台-对仗管理中添加）</p>
        </div>
        <!-- 关联图谱 -->
        <div class="card p-5">
          <h3 class="text-sm text-qianhui tracking-widest mb-2">关联意象</h3>
          <VChart v-if="relationOption" :option="relationOption" height="330px" @click="onNodeClick" />
          <div v-if="relationEdges.length" class="mt-2 space-y-2">
            <p v-for="e in relationEdges" :key="e.description" class="text-xs leading-6 text-qianhui border-t border-black/5 pt-2">
              <b :style="{ color: detail.theme_color }">「{{ e.relation_type }}」</b>{{ e.description }}
              <span class="text-[10px] text-qianhui/60 ml-1"
                v-if="e.cooccurrence?.npmi !== undefined">NPMI={{ e.cooccurrence.npmi.toFixed(3) }}·共{{ e.cooccurrence.same_poem }}篇</span>
              <span v-if="e.auto" class="tag border-zheshi/40 text-zheshi !text-[10px] ml-1">数据推导</span>
            </p>
            <p class="text-[10px] text-qianhui/70 pt-1">实线为人工标注关系，虚线为共现作品自动推导</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ 5. 诗画相映 ═══ -->
    <section v-if="artworks.length">
      <SectionTitle :color="detail.theme_color" sub="点击画作查看详情">诗画相映</SectionTitle>
      <div class="flex gap-5 mt-6 overflow-x-auto pb-3">
        <div v-for="a in artworks" :key="a.rel_id"
          class="card card-hover shrink-0 w-72 cursor-pointer overflow-hidden"
          @click="activeArtwork = a">
          <img :src="a.artwork.thumb_url" :alt="a.artwork.name" class="w-full h-44 object-cover" loading="lazy" />
          <div class="p-4">
            <div class="flex items-baseline justify-between">
              <h4 class="font-song font-semibold">《{{ a.artwork.name }}》</h4>
              <span class="text-xs text-qianhui">{{ a.artwork.dynasty }} · {{ a.artwork.artist }}</span>
            </div>
            <p class="text-xs text-qianhui leading-6 mt-2 line-clamp-2">{{ a.relation_desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ 6. 扩展工具 ═══ -->
    <section class="card p-6 flex flex-wrap items-center gap-4">
      <span class="text-sm text-qianhui tracking-widest mr-2">扩展工具</span>
      <a :href="shareCardUrl(detail.id)" target="_blank" class="btn-outline !py-1.5 !px-4 !text-xs">生成分享卡片</a>
      <router-link to="/agent" class="btn-outline !py-1.5 !px-4 !text-xs">向智能助手提问「{{ detail.name }}」</router-link>
      <router-link :to="`/artworks`" class="btn-outline !py-1.5 !px-4 !text-xs">前往古画展厅</router-link>
    </section>

    <!-- 古画弹窗 -->
    <Teleport to="body">
      <div v-if="activeArtwork" class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
        @click.self="activeArtwork = null">
        <div class="bg-xuanzhi rounded-lg max-w-2xl w-full overflow-hidden shadow-2xl rise-in">
          <img :src="activeArtwork.artwork.image_url" :alt="activeArtwork.artwork.name" class="w-full max-h-[50vh] object-cover bg-black/5" />
          <div class="p-6">
            <h3 class="font-song text-xl font-bold">《{{ activeArtwork.artwork.name }}》</h3>
            <p class="text-sm text-qianhui mt-1">{{ activeArtwork.artwork.dynasty }} · {{ activeArtwork.artwork.artist }}</p>
            <p class="text-sm leading-7 mt-3 text-moyan/85">{{ activeArtwork.relation_desc }}</p>
            <div class="mt-5 text-right">
              <button class="btn-primary !py-1.5 !text-xs" @click="$router.push(`/artworks?id=${activeArtwork.artwork.id}`)">查看作品详情</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>

  <div v-else class="py-32 text-center text-qianhui">加载中…</div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getConceptArtworks, getConceptDetail, getConceptPoetries, getConceptRelations, shareCardUrl,
} from '../api'
import Pagination from '../components/Pagination.vue'
import ParticleCanvas from '../components/ParticleCanvas.vue'
import SectionTitle from '../components/SectionTitle.vue'
import VChart from '../components/VChart.vue'

const route = useRoute()
const router = useRouter()
const conceptId = Number(route.params.id)

const detail = ref(null)
const artworks = ref([])
const relationEdges = ref([])
const relationNodes = ref([])
const activeArtwork = ref(null)

const page = ref(1)
const pageSize = 6
const poetryTotal = ref(0)
const poetryItems = ref([])
const filterDynasty = ref('')
const filterEmotion = ref('')

const PALETTE = ['#2B4C7E', '#9B4423', '#5B7C5F', '#8A6D3B', '#6E4A7E', '#3A7A7C']

/** 意象名/分类 → 粒子主题 */
const particleMode = computed(() => {
  const name = detail.value?.name || ''
  const cat = detail.value?.category_main || ''
  if (/月|霜|雪|星|夜/.test(name)) return 'moon'
  if (/夕阳|日|霞|暮/.test(name)) return 'sunset'
  if (/柳|絮|杨/.test(name)) return 'willow'
  if (cat === '自然类') return 'moon'
  if (cat === '人类自身类') return 'petal'
  return 'ink'
})

const dynasties = computed(() => (detail.value?.dynasty_stats || []).map((s) => s.dynasty))

const emotionOption = computed(() => {
  const stats = detail.value?.emotion_stats || []
  return {
    tooltip: { trigger: 'item', formatter: '{b}：{c} 句（{d}%）' },
    legend: { bottom: 0, textStyle: { color: '#6B6B6B', fontSize: 12 }, itemWidth: 14 },
    series: [{
      type: 'pie', radius: ['48%', '72%'], center: ['50%', '44%'],
      itemStyle: { borderColor: '#F5F1E8', borderWidth: 2, borderRadius: 4 },
      label: { show: true, formatter: '{b}\n{c}句', fontSize: 11, color: '#2C2C2C' },
      data: stats.map((s, i) => ({ name: s.emotion, value: s.count, itemStyle: { color: PALETTE[i % PALETTE.length] } })),
    }],
  }
})

const dynastyOption = computed(() => {
  const stats = detail.value?.dynasty_stats || []
  const color = detail.value?.theme_color || '#2B4C7E'
  return {
    grid: { left: 40, right: 20, top: 30, bottom: 40 },
    tooltip: { trigger: 'axis', formatter: '{b}：{c} 首' },
    xAxis: {
      type: 'category', data: stats.map((s) => s.dynasty),
      axisLine: { lineStyle: { color: '#00000022' } },
      axisLabel: { color: '#6B6B6B', fontFamily: 'Kaiti SC, KaiTi, serif', fontSize: 13 },
    },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#0000000D' } }, axisLabel: { color: '#9A9A9A' } },
    series: [{
      type: 'line', smooth: true, symbol: 'circle', symbolSize: 9,
      data: stats.map((s) => s.count),
      lineStyle: { width: 2.5, color },
      itemStyle: { color, borderColor: '#F5F1E8', borderWidth: 2 },
      areaStyle: {
        color: {
          type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [{ offset: 0, color: color + '55' }, { offset: 1, color: color + '05' }],
        },
      },
    }],
  }
})

const relationOption = computed(() => {
  if (!relationNodes.value.length) return null
  return {
    tooltip: { show: false },
    series: [{
      type: 'graph', layout: 'force', roam: false,
      force: { repulsion: 400, edgeLength: 120 },
      label: { show: true, fontSize: 15, fontFamily: 'Kaiti SC, KaiTi, serif', color: '#F5F1E8' },
      data: relationNodes.value.map((n) => ({
        id: String(n.id), name: n.name, symbolSize: n.id === conceptId ? 74 : 62,
        itemStyle: { color: n.theme_color, borderColor: '#F5F1E8', borderWidth: 2, shadowBlur: 8, shadowColor: '#0003' },
      })),
      links: relationEdges.value.map((e) => {
        const shared = e.cooccurrence?.same_poem || 0  // 共现诗数 → 线宽
        const width = Math.max(0.5, Math.min(6, 1 + shared * 1.2))
        return {
          source: String(e.from_id), target: String(e.to_id),
          lineStyle: e.auto
            ? { color: '#9B442366', width: Math.max(1, width * 0.7), type: 'dashed', curveness: 0.15 }
            : { color: '#2B4C7E55', width, curveness: 0.15 },
        }
      }),
    }],
  }
})

async function loadPoetries() {
  const data = await getConceptPoetries(conceptId, {
    dynasty: filterDynasty.value, emotion: filterEmotion.value,
    page: page.value, page_size: pageSize,
  })
  poetryTotal.value = data.total
  poetryItems.value = data.items
}

function onDynastyClick(params) {
  const dyn = params.name
  filterDynasty.value = filterDynasty.value === dyn ? '' : dyn
  page.value = 1
  loadPoetries()
  document.querySelector('section:nth-of-type(3)')?.scrollIntoView({ behavior: 'smooth' })
}

function onNodeClick(params) {
  if (params.dataType === 'node' && Number(params.data.id) !== conceptId) {
    router.push(`/concept/${params.data.id}`)
  }
}

onMounted(async () => {
  try {
    if (!Number.isFinite(conceptId)) throw new Error('invalid id')
    detail.value = await getConceptDetail(conceptId)
    const [arts, rels] = await Promise.all([getConceptArtworks(conceptId), getConceptRelations(conceptId)])
    artworks.value = arts
    relationNodes.value = rels.nodes
    relationEdges.value = rels.edges
    await loadPoetries()
  } catch {
    router.replace({ name: 'not-found' })
  }
})
</script>
