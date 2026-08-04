<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <SectionTitle sub="古代艺术品图文库 · 诗画互证">艺术展厅</SectionTitle>

    <!-- 朝代检索：全部朝代（下拉）+ 唐 + 宋 -->
    <div class="flex flex-wrap items-center gap-2 mt-6 text-sm">
      <div class="relative">
        <select v-model="dynasty" @change="page = 1; load()"
          class="appearance-none pl-3 pr-8 py-1.5 rounded-full border cursor-pointer transition-all focus:outline-none"
          :class="dynasty ? 'border-shiqing bg-shiqing/10 text-shiqing font-semibold' : 'border-shiqing/40 text-shiqing'">
          <option value="">全部朝代（{{ totalCount }}）</option>
          <option v-for="d in filters.dynasties" :key="d.name" :value="d.name">{{ d.name }}（{{ d.count }}）</option>
        </select>
        <svg class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3 h-3 pointer-events-none text-shiqing" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>
      </div>
      <button v-for="d in ['唐', '宋']" :key="d" @click="toggleDynasty(d)" :disabled="!dynastyCount(d)"
        class="px-4 py-1.5 rounded-full border transition-all"
        :class="dynasty === d
          ? 'text-white !bg-shiqing !border-shiqing'
          : dynastyCount(d) ? 'hover:bg-black/5 border-shiqing/30 text-shiqing' : 'opacity-40 cursor-not-allowed border-shiqing/20 text-shiqing'">
        {{ d }}<span v-if="dynastyCount(d)" class="text-xs opacity-70">（{{ dynastyCount(d) }}）</span>
      </button>
    </div>

    <!-- 主题 / 关键词 -->
    <div class="flex flex-wrap items-center gap-3 mt-3 text-sm">
      <select v-model="subject" @change="page = 1; load()"
        class="px-4 py-2 rounded-full border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing">
        <option value="">全部主题</option>
        <option v-for="s in filters.subjects" :key="s" :value="s">{{ s }}</option>
      </select>
      <div class="flex-1"></div>
      <input v-model="keyword" @keyup.enter="page = 1; load()" placeholder="检索作品名 / 作者…"
        class="w-52 px-4 py-2 rounded-full border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing" />
    </div>

    <!-- 瀑布网格 -->
    <div v-if="loading" class="py-20 text-center text-qianhui">加载中…</div>
    <div v-else-if="!items.length" class="py-20 text-center text-qianhui">未找到匹配的艺术品</div>
    <div v-else class="columns-1 sm:columns-2 lg:columns-3 gap-6 mt-8 [&>div]:mb-6">
      <div v-for="(a, i) in items" :key="a.id"
        class="card card-hover overflow-hidden cursor-pointer break-inside-avoid rise-in"
        :style="{ animationDelay: (i % 6) * 0.06 + 's' }"
        @click="openDetail(a.id)">
        <!-- 封面自动匹配作品图，加载失败回退大图 -->
        <img :src="a.thumb_url || a.image_url" :alt="a.name" class="w-full object-cover" loading="lazy"
          @error="(e) => { if (e.target.src !== a.image_url) e.target.src = a.image_url }" />
        <div class="p-4">
          <h3 class="font-song font-semibold">《{{ a.name }}》</h3>
          <p class="text-xs text-qianhui mt-1">{{ a.dynasty_period || a.dynasty_main }} · {{ a.artist }}</p>
        </div>
      </div>
    </div>
    <Pagination :page="page" :page-size="pageSize" :total="total" @change="(p) => { page = p; load() }" />

    <!-- 详情弹窗 -->
    <Teleport to="body">
      <div v-if="detail" class="fixed inset-0 z-50 bg-black/55 backdrop-blur-sm flex items-center justify-center p-4"
        @click.self="closeDetail">
        <!-- 全屏欣赏（滚轮缩放 + 拖拽平移 + 放大镜） -->
        <div v-if="fullscreen" class="fixed inset-0 z-[60] bg-black flex items-center justify-center" @dblclick="exitFullscreen">
          <div class="relative w-full h-full overflow-hidden" ref="zoomBox"
            @wheel.prevent="onWheel" @mousedown="startPan" @mousemove="onPan" @mouseup="endPan" @mouseleave="endPan">
            <img :src="detail.image_url" :alt="detail.name" class="absolute select-none max-w-none" draggable="false"
              :style="{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, left: '50%', top: '50%', marginLeft: '-25vw', marginTop: '-25vh', width: '50vw' }" />
            <div v-if="lens.on" class="absolute pointer-events-none rounded-full border-2 border-xuanzhi/70 shadow-2xl overflow-hidden"
              :style="{ left: lens.x - 90 + 'px', top: lens.y - 90 + 'px', width: '180px', height: '180px' }">
              <img :src="detail.image_url" class="absolute max-w-none"
                :style="{ width: '50vw', transform: `translate(${-(lens.imgX) * 2.5 + 90}px, ${-(lens.imgY) * 2.5 + 90}px) scale(${zoom * 2.5})`, transformOrigin: 'top left' }" />
            </div>
          </div>
          <button class="fixed top-4 right-4 w-12 h-12 z-[61] flex items-center justify-center rounded-full bg-white/20 hover:bg-white/35 text-white text-2xl transition-all" @click="exitFullscreen">×</button>
          <div class="fixed bottom-4 left-1/2 -translate-x-1/2 z-[61] flex items-center gap-3 bg-black/50 rounded-full px-4 py-2 text-white/70 text-xs">
            <span>滚轮缩放 · 拖拽平移 · 按住 L 放大镜 · 双击退出</span>
            <button class="px-3 py-1 rounded-full bg-white/20 hover:bg-white/35 transition-all" @click.stop="zoom = 1; pan = { x: 0, y: 0 }">重置</button>
          </div>
        </div>

        <!-- 详情卡片：左图右介绍 -->
        <div class="bg-xuanzhi rounded-lg max-w-5xl w-full max-h-[90vh] shadow-2xl rise-in relative flex flex-col md:flex-row overflow-hidden">
          <button class="absolute top-3 right-3 w-10 h-10 z-20 flex items-center justify-center rounded-full bg-black/25 hover:bg-black/45 text-white text-xl transition-all"
            @click="detail = null" title="关闭">×</button>
          <!-- 左侧：作品图片（双击全屏） -->
          <div class="md:w-1/2 relative cursor-zoom-in bg-black/5 flex items-center justify-center shrink-0"
            @dblclick="enterFullscreen" title="双击全屏欣赏">
            <img :src="detail.image_url" :alt="detail.name" class="w-full max-h-[42vh] md:max-h-[85vh] object-contain" />
            <span class="absolute bottom-3 right-3 bg-black/40 text-white/70 text-[10px] px-2 py-0.5 rounded">双击全屏</span>
          </div>
          <!-- 右侧：作品介绍 -->
          <div class="md:w-1/2 p-6 md:max-h-[85vh] overflow-y-auto">
            <h3 class="font-song text-2xl font-bold pr-10">《{{ detail.name }}》</h3>
            <p class="text-sm text-qianhui mt-1">{{ detail.dynasty_period }} · {{ detail.artist }}</p>
            <div class="flex gap-1.5 mt-3 flex-wrap">
              <span v-for="s in detail.subject_names" :key="s" class="tag border-shiqing/30 text-shiqing">{{ s }}</span>
            </div>
            <div class="grid grid-cols-2 gap-3 mt-4 text-sm">
              <div class="bg-white/50 rounded p-3"><span class="text-qianhui text-xs">材质</span><p class="mt-0.5">{{ detail.material || '—' }}</p></div>
              <div class="bg-white/50 rounded p-3"><span class="text-qianhui text-xs">尺寸</span><p class="mt-0.5">{{ detail.size || '—' }}</p></div>
            </div>
            <div class="mt-4">
              <span class="text-xs text-qianhui tracking-widest">作品介绍</span>
              <p class="text-sm leading-7 mt-2 text-moyan/85 whitespace-pre-line">{{ detail.description || '暂无介绍' }}</p>
            </div>
            <div v-if="detail.concepts.length" class="mt-5 border-t border-black/5 pt-4">
              <span class="text-xs text-qianhui tracking-widest">相关意象</span>
              <div class="flex flex-wrap gap-2 mt-2">
                <button v-for="c in detail.concepts" :key="c.id"
                  class="tag !text-sm !px-3 !py-1 hover:scale-105 transition-transform cursor-pointer"
                  :style="{ color: c.theme_color, borderColor: c.theme_color + '66', background: c.theme_color + '0F' }"
                  @click="$router.push(`/concept/${c.id}`)">{{ c.name }}</button>
              </div>
              <p v-for="c in detail.concepts" :key="'d' + c.id" class="text-xs text-qianhui leading-6 mt-2">· {{ c.relation_desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
    <BackToTop />
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getArtworkDetail, getArtworkList } from '../api'
import Pagination from '../components/Pagination.vue'
import SectionTitle from '../components/SectionTitle.vue'
import BackToTop from '../components/BackToTop.vue'

const route = useRoute()
const items = ref([])
const filters = ref({ dynasties: [], subjects: [] })
const dynasty = ref('')
const subject = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = 12
const total = ref(0)
const totalCount = ref(0)
const loading = ref(true)
const detail = ref(null)
const fullscreen = ref(false)

// 缩放/放大镜
const zoom = ref(1)
const pan = ref({ x: 0, y: 0 })
const lens = ref({ on: false, x: 0, y: 0, imgX: 0, imgY: 0 })
const zoomBox = ref(null)
let panning = false, panStart = { x: 0, y: 0 }, panOrigin = { x: 0, y: 0 }

function enterFullscreen() { fullscreen.value = true; zoom.value = 1; pan.value = { x: 0, y: 0 } }
function exitFullscreen() { fullscreen.value = false; lens.value.on = false }
function closeDetail() { detail.value = null; fullscreen.value = false }

function onWheel(e) { zoom.value = Math.min(6, Math.max(0.5, zoom.value + (e.deltaY < 0 ? 0.25 : -0.25))) }
function startPan(e) {
  if (lens.value.on) return
  panning = true; panStart = { x: e.clientX, y: e.clientY }; panOrigin = { ...pan.value }
}
function onPan(e) {
  if (lens.value.on) { updateLens(e); return }
  if (!panning) return
  pan.value = { x: panOrigin.x + (e.clientX - panStart.x), y: panOrigin.y + (e.clientY - panStart.y) }
}
function endPan() { panning = false }
function updateLens(e) {
  const rect = zoomBox.value.getBoundingClientRect()
  lens.value.x = e.clientX - rect.left
  lens.value.y = e.clientY - rect.top
  lens.value.imgX = lens.value.x - rect.width / 2 - pan.value.x
  lens.value.imgY = lens.value.y - rect.height / 2 - pan.value.y
}
function onKeyToggle(e) { if (fullscreen.value && (e.key === 'l' || e.key === 'L')) lens.value.on = true }
function onKeyRelease(e) { if (e.key === 'l' || e.key === 'L') lens.value.on = false }
function onEsc(e) {
  if (e.key === 'Escape') { if (fullscreen.value) exitFullscreen(); else if (detail.value) closeDetail() }
}

async function load() {
  loading.value = true
  try {
    const data = await getArtworkList({ dynasty: dynasty.value, subject: subject.value, keyword: keyword.value, page: page.value, page_size: pageSize })
    items.value = data.items
    total.value = data.total
    filters.value = data.filters
    totalCount.value = data.filters.dynasties.reduce((s, d) => s + d.count, 0)
  } finally { loading.value = false }
}

// 某朝代的作品数（用于唐/宋快捷按钮）
function dynastyCount(name) {
  const d = filters.value.dynasties.find((x) => x.name === name)
  return d ? d.count : 0
}
function toggleDynasty(name) {
  dynasty.value = dynasty.value === name ? '' : name
  page.value = 1
  load()
}

async function openDetail(id) { detail.value = await getArtworkDetail(id) }

onMounted(async () => {
  document.addEventListener('keydown', onEsc)
  document.addEventListener('keydown', onKeyToggle)
  document.addEventListener('keyup', onKeyRelease)
  await load()
  if (route.query.id) openDetail(Number(route.query.id))
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onEsc)
  document.removeEventListener('keydown', onKeyToggle)
  document.removeEventListener('keyup', onKeyRelease)
})
</script>
