<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-[70] flex flex-col" style="background: rgba(20,26,38,0.95)">
      <!-- 顶栏 -->
      <div class="flex items-center justify-between px-6 py-4 text-xuanzhi">
        <div class="flex items-center gap-3">
          <span class="seal">共现</span>
          <div>
            <h3 class="font-song text-xl font-bold">「{{ data?.concept_name }}」共现图谱</h3>
            <p class="text-xs text-xuanzhi/60 mt-0.5">线条粗细=NPMI 关联强度 · 线型=共现类型 · 透明度=强度权重 · 悬停/点击节点查看卡片</p>
          </div>
        </div>
        <button class="w-10 h-10 rounded-full bg-white/10 hover:bg-white/25 text-xl transition-all" @click="close" title="关闭 (Esc)">×</button>
      </div>

      <!-- 主体：径向图谱 + 节点卡片 -->
      <div class="flex-1 relative overflow-hidden">
        <svg v-if="layout" :viewBox="`0 0 ${W} ${H}`" class="w-full h-full" preserveAspectRatio="xMidYMid meet">
          <!-- 连线 -->
          <g v-for="e in layout.edges" :key="'e' + e.target">
            <line :x1="layout.center.x" :y1="layout.center.y" :x2="e.x" :y2="e.y"
              :stroke="themeColor" :stroke-width="e.width" :stroke-opacity="e.opacity"
              :stroke-dasharray="e.dash" stroke-linecap="round" />
          </g>
          <!-- 中心节点 -->
          <g :transform="`translate(${layout.center.x},${layout.center.y})`">
            <circle r="46" :fill="themeColor" stroke="#F5F1E8" stroke-width="3" />
            <circle r="60" fill="none" :stroke="themeColor" stroke-opacity="0.35" stroke-width="1.5" stroke-dasharray="3 4" />
            <text text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8" font-size="26"
              style="font-family:'Kaiti SC',KaiTi,serif;font-weight:700">{{ data?.concept_name }}</text>
          </g>
          <!-- 共现节点 -->
          <g v-for="n in layout.nodes" :key="n.id" :transform="`translate(${n.x},${n.y})`" class="cursor-pointer"
            @click="select(n)" @mouseenter="hovered = n.id" @mouseleave="hovered = null">
            <circle :r="n.r" :fill="n.theme_color || '#8A6D3B'"
              :stroke="selected === n.id ? '#F5F1E8' : 'rgba(245,241,232,0.5)'" :stroke-width="selected === n.id ? 3 : 1.5" />
            <text text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8" :font-size="n.font"
              style="font-family:'Kaiti SC',KaiTi,serif">{{ n.name }}</text>
          </g>
          <!-- 节点卡片：仅悬停/选中的节点显示，避免遮挡 -->
          <foreignObject v-for="n in activeCards" :key="'fo' + n.id"
            :x="n.card.x" :y="n.card.y" width="230" height="150" style="overflow:visible" class="pointer-events-none">
            <div class="w-[220px] rounded-lg p-3 text-xs leading-6 shadow-xl ring-2 bg-xuanzhi"
              :style="{ ['--tw-ring-color']: themeColor }">
              <div class="flex items-center justify-between">
                <b class="font-song text-sm" :style="{ color: themeColor }">{{ n.name }}</b>
                <span class="text-[10px] text-qianhui">NPMI {{ n.edge.npmi.toFixed(2) }}</span>
              </div>
              <p v-if="n.edge.verse" class="verse-text text-moyan/90 mt-1">「{{ n.edge.verse }}」</p>
              <p v-if="n.edge.description" class="text-qianhui mt-1">{{ n.edge.description }}</p>
              <p v-if="!n.edge.verse && !n.edge.description" class="text-qianhui/70 mt-1">共现 {{ n.edge.same_poem }} 篇 · {{ typeLabel(n.edge.type) }}</p>
              <button v-if="n.concept_id" class="mt-1.5 text-[11px] hover:underline pointer-events-auto" :style="{ color: themeColor }"
                @click.stop="goConcept(n.concept_id)">探索该意象 →</button>
            </div>
          </foreignObject>
        </svg>

        <!-- 图例 -->
        <div class="absolute left-5 bottom-5 bg-white/10 backdrop-blur rounded-lg px-4 py-3 text-xuanzhi/80 text-xs space-y-1.5">
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="4"/></svg> 粗 = NPMI 强</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="1.5"/></svg> 细 = NPMI 弱</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="2"/></svg> 实线 = 句内</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="2" stroke-dasharray="6 4"/></svg> 虚线 = 跨句</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="2" stroke-dasharray="2 4"/></svg> 点线 = 全诗</div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  show: { type: Boolean, default: false },
  data: { type: Object, default: null },
  themeColor: { type: String, default: '#2B4C7E' },
})
const emit = defineEmits(['close'])

const router = useRouter()
const selected = ref(null)
const hovered = ref(null)
const W = 1280, H = 800

// 当前显示卡片的节点：选中优先，其次悬停
const activeCards = computed(() => {
  if (!layout.value) return []
  const ids = new Set([selected.value, hovered.value].filter(Boolean))
  return layout.value.nodes.filter((n) => ids.has(n.id))
})

function typeLabel(t) { return t === '句内' ? '句内共现' : t === '跨句' ? '跨句共现' : '全诗共现' }
function dashOf(t) { return t === '句内' ? '' : t === '跨句' ? '7 5' : '2 5' }

const layout = computed(() => {
  if (!props.data || !props.data.edges?.length) return null
  const edges = props.data.edges
  const cx = W / 2, cy = H / 2
  const R = 235
  const n = edges.length
  const nodes = []
  const edgeGeo = []
  edges.forEach((e, i) => {
    const ang = (i / n) * Math.PI * 2 - Math.PI / 2
    const jitter = (i % 2 ? 26 : -16)
    const r = R + jitter
    const x = cx + r * Math.cos(ang)
    const y = cy + r * Math.sin(ang)
    const width = 1 + ((e.npmi + 1) / 2) * 5
    // 卡片沿节点径向外推，水平居中于节点外侧
    const cardDist = 92
    const cardCx = x + cardDist * Math.cos(ang)
    const cardCy = y + cardDist * Math.sin(ang)
    nodes.push({
      id: e.target, name: e.name, x, y,
      r: 24 + Math.min(14, e.same_poem ? Math.log2(e.same_poem + 1) * 2 : 6),
      font: e.name.length > 2 ? 15 : 19,
      theme_color: nodeColor(e), concept_id: e.concept_id, edge: e,
      card: { x: cardCx - 110, y: cardCy - 40 },
    })
    edgeGeo.push({ target: e.target, x, y, width, opacity: e.diaphaneity, dash: dashOf(e.type) })
  })
  return { center: { x: cx, y: cy }, nodes, edges: edgeGeo }
})

function nodeColor(e) {
  const nd = props.data.nodes.find((n) => n.id === e.target)
  return nd?.theme_color || '#8A6D3B'
}

function select(n) { selected.value = selected.value === n.id ? null : n.id }
function goConcept(id) { emit('close'); router.push(`/concept/${id}`) }
function close() { emit('close') }

function onKey(e) { if (e.key === 'Escape' && props.show) close() }
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
watch(() => props.show, (v) => { if (!v) { selected.value = null; hovered.value = null } })
</script>
