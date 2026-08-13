<!--
  共现知识图谱 · 全屏探索器（美工优化版）
  中心意象居中，共现意象环绕；桥接词走内环。径向布局 + 卡片悬浮 + 动画连线。
-->
<template>
  <Teleport to="body">
    <Transition name="fade">
    <div v-if="show" class="fixed inset-0 z-[100] flex flex-col cooc-root" @click.self="close">

      <!-- 顶栏 -->
      <div class="flex items-center justify-between px-6 py-4 text-xuanzhi shrink-0">
        <div class="flex items-center gap-3 min-w-0">
          <span class="seal shrink-0">共现</span>
          <div class="min-w-0">
            <h3 class="font-song text-xl font-bold truncate">「{{ data?.concept_name }}」共现图谱</h3>
            <p class="text-xs text-xuanzhi/55 mt-0.5 truncate">线粗 = NPMI 关联强度 · 线型 = 共现类型 · 悬停/点击节点查看详情 · 点空白处关闭</p>
          </div>
        </div>
        <button class="w-10 h-10 rounded-full bg-white/10 hover:bg-white/25 text-xl transition-all shrink-0" @click="close" title="关闭 (Esc)">×</button>
      </div>

      <!-- 主体：径向图谱 + 节点卡片 -->
      <div class="flex-1 relative overflow-hidden min-h-0">
        <svg v-if="graph" :viewBox="`0 0 ${W} ${H}`" class="w-full h-full" preserveAspectRatio="xMidYMid meet" @click.self="clearSelection">
          <defs>
            <radialGradient :id="'coocGlow' + uid" cx="50%" cy="50%" r="50%">
              <stop offset="0%" :stop-color="themeColor" stop-opacity="0.22" />
              <stop offset="60%" :stop-color="themeColor" stop-opacity="0.06" />
              <stop offset="100%" :stop-color="themeColor" stop-opacity="0" />
            </radialGradient>
            <filter :id="'coocBlur' + uid" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="4" result="b" />
            </filter>
          </defs>

          <!-- 背景光晕 + 同心圆（不拦截点击，点击空白处可取消选中） -->
          <circle :cx="W/2" :cy="H/2" :r="Math.min(W,H)/2" :fill="`url(#coocGlow${uid})`" pointer-events="none" />
          <g class="cooc-rings" stroke="#F5F1E8" fill="none" pointer-events="none">
            <circle :cx="W/2" :cy="H/2" r="150" stroke-opacity="0.05" />
            <circle :cx="W/2" :cy="H/2" r="250" stroke-opacity="0.07" />
            <circle :cx="W/2" :cy="H/2" r="340" stroke-opacity="0.04" stroke-dasharray="2 6" />
          </g>

          <!-- 连线（先画，置于节点之下） -->
          <g class="cooc-edges" pointer-events="none">
            <g v-for="e in graph.edges" :key="'e' + e.target + e.source">
              <!-- 桥接词：中心 → 桥接词，用灰色细虚线 -->
              <line v-if="e.isContain"
                :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
                stroke="#9aa0aa" stroke-width="1" stroke-opacity="0.45" stroke-dasharray="3 5" />
              <!-- 普通共现边 -->
              <line v-else
                :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
                :stroke="themeColor" :stroke-width="e.width" :stroke-opacity="e.opacity"
                :stroke-dasharray="e.dash" stroke-linecap="round" />
            </g>
          </g>

          <!-- 中心节点 -->
          <g :transform="`translate(${graph.center.x},${graph.center.y})`" class="cursor-pointer">
            <circle r="74" :fill="themeColor" opacity="0.12" class="cooc-pulse" />
            <circle r="58" :fill="themeColor" stroke="#F5F1E8" stroke-width="3"
              :filter="`url(#coocBlur${uid})`" opacity="0.85" />
            <circle r="58" :fill="themeColor" stroke="#F5F1E8" stroke-width="3" />
            <circle r="68" fill="none" :stroke="themeColor" stroke-opacity="0.35" stroke-width="1.5" stroke-dasharray="3 4" class="cooc-spin" />
            <text text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8" :font-size="graph.center.font"
              style="font-family:'Kaiti SC',KaiTi,serif;font-weight:700" pointer-events="none">{{ graph.center.name }}</text>
          </g>

          <!-- 桥接词 + 共现节点 -->
          <g v-for="n in graph.nodes" :key="n.id" :transform="`translate(${n.x},${n.y})`" class="cursor-pointer"
            @click="select(n)" @mouseenter="hovered = n.id" @mouseleave="hovered = null">
            <circle v-if="n.isBridge" r="14" fill="#3a4050" stroke="#9aa0aa" stroke-width="1.5" stroke-dasharray="3 3" />
            <template v-else>
              <circle :r="n.r + 6" :fill="n.theme_color || '#8A6D3B'" opacity="0.18" class="cooc-pulse" />
              <circle :r="n.r" :fill="n.theme_color || '#8A6D3B'"
                :stroke="selected === n.id || hovered === n.id ? '#F5F1E8' : 'rgba(245,241,232,0.55)'"
                :stroke-width="selected === n.id ? 3 : 1.6"
                :opacity="dim(n) ? 0.45 : 1" style="transition: opacity .2s" />
            </template>
            <text v-if="n.isBridge" text-anchor="middle" y="26" fill="#c3c8d2" font-size="11"
              style="font-family:'Kaiti SC',KaiTi,serif">{{ n.name }}</text>
            <text v-else text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8" :font-size="n.font"
              style="font-family:'Kaiti SC',KaiTi,serif" pointer-events="none">{{ n.name }}</text>
          </g>

          <!-- 节点卡片：仅悬停/选中的节点显示 -->
          <foreignObject v-for="n in activeCards" :key="'fo' + n.id"
            :x="n.card.x" :y="n.card.y" :width="n.card.w" :height="n.card.h" style="overflow:visible" class="pointer-events-none">
            <div class="cooc-card" :style="{ ['--accent']: themeColor }">
              <div class="flex items-start justify-between gap-2">
                <b class="font-song text-sm" :style="{ color: themeColor }">{{ n.name }}</b>
                <span v-if="n.edge?.npmi != null" class="text-[10px] text-qianhui whitespace-nowrap">NPMI {{ n.edge.npmi.toFixed(2) }}</span>
              </div>
              <div class="flex items-center gap-1.5 mt-0.5 text-[10px] text-qianhui/80">
                <span v-if="n.edge?.type">{{ typeLabel(n.edge.type) }}</span>
                <span v-if="n.edge?.same_poem" class="text-qianhui/60">· 共现 {{ n.edge.same_poem }} 篇</span>
                <span v-if="n.isBridge" class="text-zheshi">· 桥接词</span>
              </div>
              <p v-if="n.edge?.verse" class="verse-text text-moyan/90 mt-1.5 leading-6 text-[12px]">「{{ n.edge.verse }}」</p>
              <p v-if="n.edge?.description" class="text-qianhui mt-1 text-[11px] leading-5">{{ n.edge.description }}</p>
              <p v-if="n.edge?.poet || n.edge?.dynasty" class="text-[10px] text-qianhui/70 mt-1">
                {{ [n.edge.dynasty, n.edge.poet].filter(Boolean).join(' · ') }}
                <span v-if="n.edge.poem_title">《{{ n.edge.poem_title }}》</span>
              </p>
              <button v-if="n.concept_id" class="mt-2 text-[11px] hover:underline pointer-events-auto font-semibold" :style="{ color: themeColor }"
                @click.stop="goConcept(n.concept_id)">探索该意象 →</button>
            </div>
          </foreignObject>
        </svg>

        <!-- 图例 -->
        <div v-if="graph" class="absolute left-5 bottom-5 bg-black/35 backdrop-blur rounded-lg px-4 py-3 text-xuanzhi/85 text-xs space-y-1.5">
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="4"/></svg> 粗 = NPMI 强</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="1.5"/></svg> 细 = NPMI 弱</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="2"/></svg> 实线 = 句内</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="2" stroke-dasharray="7 5"/></svg> 虚线 = 跨句</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="2" stroke-dasharray="2 4"/></svg> 点线 = 全诗</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#9aa0aa" stroke-width="1.2" stroke-dasharray="3 5"/></svg> 灰线 = 桥接</div>
        </div>

        <!-- 统计 -->
        <div v-if="graph" class="absolute right-5 bottom-5 bg-black/35 backdrop-blur rounded-lg px-4 py-2.5 text-xuanzhi/70 text-[11px] text-right leading-5">
          <div>共现意象 <b class="text-xuanzhi">{{ stats.total }}</b> 个</div>
          <div>句内 {{ stats.inner }} · 跨句 {{ stats.cross }} · 全诗 {{ stats.whole }}</div>
        </div>
      </div>
    </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.cooc-root { background: radial-gradient(120% 90% at 50% 0%, #16263f 0%, #0e1726 58%, #0a101c 100%); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.35s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.cooc-card {
  width: 224px; border-radius: 10px; padding: 10px 12px;
  font-size: 12px; line-height: 1.6; box-shadow: 0 12px 32px rgba(0,0,0,0.35);
  background: #F5F1E8; box-shadow: 0 0 0 2px var(--accent), 0 14px 36px rgba(0,0,0,0.4);
}
.cooc-edges line { opacity: 1; }
.cooc-pulse { opacity: 0.14; }
.cooc-spin { }
</style>

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
const uid = Math.floor(Math.random() * 1e6)

function typeLabel(t) { return t === '句内' ? '句内共现' : t === '跨句' ? '跨句共现' : '全诗共现' }
function dashOf(t) { return t === '句内' ? '' : t === '跨句' ? '7 5' : '2 5' }
function nodeRadius(name, samePoem) {
  const base = 20 + Math.min(12, samePoem ? Math.log2(samePoem + 1) * 2 : 5)
  return Math.max(20, Math.min(32, base))
}
function nodeFont(name) { return name.length > 2 ? 14 : name.length === 2 ? 17 : 20 }
function centerFont(name) { return name.length > 3 ? 26 : name.length === 3 ? 30 : 36 }

const graph = computed(() => {
  const d = props.data
  if (!d || !d.edges?.length) return null
  const nodes = d.nodes || []
  const center = nodes.find((n) => n.center)
  const centerId = center?.id
  if (!centerId) return null
  const cx = W / 2, cy = H / 2
  const pos = { [centerId]: { x: cx, y: cy } }

  const containEdges = []   // 中心 → 桥接词
  const directEdges = []    // 中心 → 直接共现
  const bridgeEdges = []    // 桥接词 → 共现词
  for (const e of d.edges) {
    if (e.source === centerId) {
      if (e.relation_type === '包含') containEdges.push(e)
      else directEdges.push(e)
    } else {
      bridgeEdges.push(e)
    }
  }

  const angleFor = (i, n, off = 0) => (n <= 1 ? 0 : (i / n) * Math.PI * 2) - Math.PI / 2 + off

  const bridgeIds = containEdges.map((e) => e.target)
  bridgeIds.forEach((bid, i) => {
    if (pos[bid]) return
    const a = angleFor(i, bridgeIds.length)
    pos[bid] = { x: cx + 148 * Math.cos(a), y: cy + 148 * Math.sin(a) }
  })
  directEdges.forEach((e, i) => {
    if (pos[e.target]) return
    const a = angleFor(i, directEdges.length)
    pos[e.target] = { x: cx + 252 * Math.cos(a), y: cy + 252 * Math.sin(a) }
  })
  const bt = bridgeEdges.map((e) => e.target)
  bt.forEach((t, i) => {
    if (pos[t]) return
    const a = angleFor(i, bt.length, 0.35)
    pos[t] = { x: cx + 286 * Math.cos(a), y: cy + 286 * Math.sin(a) }
  })

  const nodeMap = {}
  for (const n of nodes) nodeMap[n.id] = n

  const placed = []
  for (const [id, p] of Object.entries(pos)) {
    const meta = nodeMap[id]
    if (!meta) continue
    const isCenter = id === centerId
    const isBridge = bridgeIds.includes(id)
    placed.push({
      id, name: meta.name, x: p.x, y: p.y,
      concept_id: meta.concept_id, theme_color: meta.theme_color,
      isCenter, isBridge,
      r: isCenter ? 58 : isBridge ? 14 : nodeRadius(meta.name, 0),
      font: isCenter ? centerFont(meta.name) : nodeFont(meta.name),
    })
  }
  const centerNode = placed.find((p) => p.isCenter)

  // 为每个共现节点计算半径（依据其 same_poem）
  const samePoemByTarget = {}
  for (const e of d.edges) {
    if (!samePoemByTarget[e.target] || e.same_poem > samePoemByTarget[e.target]) {
      samePoemByTarget[e.target] = e.same_poem
    }
  }
  const placedNodes = placed.map((p) => p.isCenter ? p : ({
    ...p, r: p.isBridge ? 14 : nodeRadius(p.name, samePoemByTarget[p.id] || 0),
  }))

  const geoEdges = []
  for (const e of d.edges) {
    const s = pos[e.source], t = pos[e.target]
    if (!s || !t) continue
    const isContain = e.relation_type === '包含'
    const isBridgeEdge = e.source !== centerId
    // 从节点边缘起止，避免压在圆心之下
    const dx = t.x - s.x, dy = t.y - s.y
    const len = Math.hypot(dx, dy) || 1
    const ux = dx / len, uy = dy / len
    const startR = (placed.find((p) => p.id === e.source)?.r || 0) + 4
    const endR = (placed.find((p) => p.id === e.target)?.r || 0) + 3
    geoEdges.push({
      ...e,
      x1: s.x + ux * startR, y1: s.y + uy * startR,
      x2: t.x - ux * endR, y2: t.y - uy * endR,
      isContain, isBridgeEdge,
      width: 1 + ((e.npmi + 1) / 2) * 5,
      opacity: e.diaphaneity || 0.5,
      dash: dashOf(e.type),
    })
  }
  return { center: centerNode, nodes: placedNodes, edges: geoEdges }
})

const stats = computed(() => {
  if (!props.data?.edges?.length) return { total: 0, inner: 0, cross: 0, whole: 0 }
  const nonContain = props.data.edges.filter((e) => e.relation_type !== '包含')
  return {
    total: nonContain.length,
    inner: nonContain.filter((e) => e.type === '句内').length,
    cross: nonContain.filter((e) => e.type === '跨句').length,
    whole: nonContain.filter((e) => e.type === '全诗').length,
  }
})

// 当前显示卡片的节点：选中优先，其次悬停
const activeCards = computed(() => {
  if (!graph.value) return []
  const ids = new Set([selected.value, hovered.value].filter(Boolean))
  return graph.value.nodes.filter((n) => ids.has(n.id) && !n.isCenter).map((n) => {
    const edge = edgeForNode(n.id)
    const cardW = 224, cardH = 176
    let x = n.x + n.r + 14
    if (x + cardW > W - 12) x = n.x - n.r - 14 - cardW
    x = Math.max(12, Math.min(W - cardW - 12, x))
    let y = n.y - cardH / 2
    y = Math.max(12, Math.min(H - cardH - 12, y))
    return { ...n, edge, card: { x, y, w: cardW + 8, h: cardH + 8 } }
  })
})

function edgeForNode(id) {
  if (!props.data?.edges) return null
  const list = props.data.edges
  return list.find((e) => e.target === id && e.relation_type === '共现')
    || list.find((e) => e.target === id)
}

function dim(n) {
  const active = activeCards.value.find((a) => a.id === n.id)
  const hasSelection = !!selected.value
  if (!hasSelection) return false
  return selected.value !== n.id && !isConnectedToSelected(n)
}
function isConnectedToSelected(n) {
  if (!props.data?.edges) return false
  return props.data.edges.some((e) => (e.target === n.id && e.source === selected.value) || (e.source === n.id && e.target === selected.value))
}

function select(n) {
  // 单击：显示详情卡片（再次点击同一节点或点击空白处则取消）
  selected.value = selected.value === n.id ? null : n.id
}
function clearSelection() { selected.value = null; hovered.value = null }
function goConcept(id) { emit('close'); router.push('/concept/' + id) }
function close() { emit('close') }

function onKey(e) { if (e.key === 'Escape' && props.show) close() }
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
watch(() => props.show, (v) => { if (!v) { selected.value = null; hovered.value = null } })
</script>
