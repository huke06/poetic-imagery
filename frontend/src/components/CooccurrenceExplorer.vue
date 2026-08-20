<!--
  共现知识图谱 · 全屏探索器（嵌套子图谱版）
  中心意象居中，共现意象环绕；支持子意象嵌套图谱展开、缩放平移、节点拖拽。
-->
<template>
  <Teleport to="body">
    <Transition name="fade">
    <div v-if="show" ref="rootRef" class="fixed inset-0 z-[100] flex flex-col cooc-root" @click.self="close">

      <!-- 顶栏 -->
      <div class="flex items-center justify-between px-6 py-4 text-xuanzhi shrink-0">
        <div class="flex items-center gap-3 min-w-0">
          <span class="seal shrink-0">共现</span>
          <div class="min-w-0">
            <h3 class="font-song text-xl font-bold truncate">「{{ data?.concept_name }}」共现图谱</h3>
            <p class="text-xs text-xuanzhi/55 mt-0.5 truncate">线粗 = NPMI 关联强度 · 线型 = 共现类型 · 悬停/点击节点查看详情 · 点空白处关闭</p>
          </div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <button
            v-if="graph && childNodeIds.length > 0"
            class="px-3 py-1.5 rounded-lg text-sm transition-all border"
            :class="expanded ? 'bg-white/20 text-white border-white/30 hover:bg-white/30' : 'bg-white/10 text-xuanzhi border-white/20 hover:bg-white/25'"
            :disabled="expandLoading"
            @click="toggleExpand">
            <span v-if="expandLoading">加载中…</span>
            <span v-else>{{ expanded ? '收拢子意象图谱' : '展开子意象图谱' }}</span>
          </button>
          <button class="w-10 h-10 rounded-full bg-white/10 hover:bg-white/25 text-xl transition-all shrink-0" @click="close" title="关闭 (Esc)">×</button>
        </div>
      </div>

      <!-- 主体：径向图谱 + 节点卡片 -->
      <div ref="canvasRef" class="flex-1 relative overflow-hidden min-h-0"
        @mousedown="onCanvasMouseDown"
        @mousemove="onCanvasMouseMove"
        @mouseup="onCanvasMouseUp"
        @mouseleave="onCanvasMouseLeave">
        <div class="cooc-scene"
        :class="{ 'scene-expanded': expanded }">
        <svg
          v-if="projectedGraph"
          ref="svgRef"
          :viewBox="`0 0 ${W} ${H}`"
          class="w-full h-full"
          preserveAspectRatio="xMidYMid meet"
          @wheel.prevent="onZoom"
          @click.self="clearSelection">
          <defs>
            <radialGradient :id="'coocGlow' + uid" cx="50%" cy="50%" r="50%">
              <stop offset="0%" :stop-color="themeColor" stop-opacity="0.22" />
              <stop offset="60%" :stop-color="themeColor" stop-opacity="0.06" />
              <stop offset="100%" :stop-color="themeColor" stop-opacity="0" />
            </radialGradient>
            <filter :id="'coocBlur' + uid" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="4" result="b" />
            </filter>
            <filter :id="'coocDepthBlur' + uid" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur :stdDeviation="3" />
            </filter>
          </defs>

          <!-- 可缩放/平移的变换组 -->
          <g :transform="`translate(${panX},${panY}) scale(${zoom})`">

            <!-- 背景光晕 + 同心圆 -->
            <circle :cx="W/2" :cy="H/2" :r="Math.min(W,H)/2" :fill="`url(#coocGlow${uid})`" pointer-events="none" />
            <g class="cooc-rings" stroke="#F5F1E8" fill="none" pointer-events="none">
              <circle :cx="W/2" :cy="H/2" r="150" stroke-opacity="0.05" />
              <circle :cx="W/2" :cy="H/2" r="250" stroke-opacity="0.07" />
            </g>
            <!-- 3D旋转控制环 -->
            <circle v-if="expanded" :cx="W/2" :cy="H/2" r="340" fill="none"
              :stroke="mouseInsideRing ? themeColor : '#F5F1E8'"
              :stroke-opacity="mouseInsideRing ? 0.55 : 0.25"
              stroke-width="2" stroke-dasharray="6 4"
              style="transition: stroke-opacity 0.3s, stroke 0.3s"
              class="cooc-control-ring" />

            <!-- 连线（使用投影坐标） -->
            <g class="cooc-edges" pointer-events="none">
              <g v-for="(e, eIdx) in projectedGraph.projectedEdges" :key="'e' + e.source + '_' + e.target + (e.isSubEdge ? '_sub' : '')"
                :class="[e.isSubEdge ? 'edge-draw-enter' : '', { 'edge-collapsing-sub': collapsing && e.isSubEdge }]"
                :style="e.isSubEdge && !collapsing
                  ? 'animation-delay:' + Math.min(0.6, eIdx * 0.03) + 's'
                  : ''">
                <line v-if="e.isContain"
                  :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
                  stroke="#9aa0aa" stroke-width="1" stroke-opacity="0.45" stroke-dasharray="3 5" />
                <line v-else
                  :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
                  :stroke="e.isSubEdge ? (e.strokeColor || themeColor) : themeColor"
                  :stroke-width="e.width" :stroke-opacity="e.opacity"
                  :stroke-dasharray="e.dash" stroke-linecap="round" />
              </g>
            </g>

            <!-- 中心根节点（投影坐标） -->
            <g :transform="`translate(${projectedGraph.projectedCenter.px},${projectedGraph.projectedCenter.py})`"
              :style="{ opacity: expanded ? (isRotating ? 0.92 : depthOpacity(projectedGraph.projectedCenter.pdepth)) : 1 }"
              class="cursor-pointer">
              <circle :r="74 * (expanded ? projectedGraph.projectedCenter.pscale : 1)" :fill="themeColor" opacity="0.12" class="cooc-pulse" />
              <circle :r="58 * (expanded ? projectedGraph.projectedCenter.pscale : 1)" :fill="themeColor" stroke="#F5F1E8" stroke-width="3"
                :filter="expanded ? `url(#coocBlur${uid})` : undefined" opacity="0.85" />
              <circle :r="58 * (expanded ? projectedGraph.projectedCenter.pscale : 1)" :fill="themeColor" stroke="#F5F1E8" stroke-width="3" />
              <circle :r="68 * (expanded ? projectedGraph.projectedCenter.pscale : 1)" fill="none" :stroke="themeColor" stroke-opacity="0.35" stroke-width="1.5" stroke-dasharray="3 4" class="cooc-spin" />
              <text text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8"
                :font-size="displayGraph.center.font * (expanded ? projectedGraph.projectedCenter.pscale : 1)"
                style="font-family:'Kaiti SC',KaiTi,serif;font-weight:700" pointer-events="none">{{ displayGraph.center.name }}</text>
            </g>

            <!-- 所有节点（投影后，按深度排序） -->
            <g v-for="(n, nIdx) in projectedGraph.projectedNodes" :key="n.id"
              :transform="`translate(${n.px},${n.py})`"
              :class="['cursor-pointer', 'node-group', { 'node-no-transition': draggingNodeId === n.id || isRotating }]"
              :style="{
                transition: isRotating ? 'none' : 'transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.3s ease',
                opacity: expanded ? (isRotating ? 0.92 : n.popacity) : undefined,
              }"
              @mousedown.stop="onNodeMouseDown($event, n)"
              @click="select(n)"
              @mouseenter="hovered = n.id"
              @mouseleave="hovered = null">
              <g :class="[
                n.isSubNode ? 'sub-node-enter' : '',
                n.isSubCenter ? 'sub-center-enter' : '',
                { 'node-collapsing': collapsing && (n.isSubNode || n.isSubCenter) }
              ]"
              :style="{
                'animation-delay': (n.isSubNode || n.isSubCenter) && !collapsing
                  ? Math.min(0.5, nIdx * 0.035) + 's'
                  : undefined,
              }">

              <!-- 子图谱中心节点 -->
              <template v-if="n.isSubCenter">
                <circle :r="(n.r + 10) * (expanded ? n.pscale : 1)" :fill="n.theme_color || '#8A6D3B'"
                  :opacity="expanded && !isRotating && n.pdepth < -150 ? 0.1 : 0.15"
                  :filter="expanded && !isRotating && n.pdepth < -150 ? `url(#coocDepthBlur${uid})` : undefined" />
                <circle :r="(n.r + 8) * (expanded ? n.pscale : 1)" :fill="n.theme_color || '#8A6D3B'" opacity="0.25" class="cooc-pulse" />
                <circle :r="n.r * (expanded ? n.pscale : 1)" :fill="n.theme_color || '#8A6D3B'"
                  stroke="#F5F1E8" :stroke-width="2.5 * (expanded ? n.pscale : 1)" stroke-dasharray="4 3"
                  :opacity="dim(n) ? 0.45 : 1" style="transition: opacity .2s" />
                <text text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8"
                  :font-size="n.font * (expanded ? n.pscale : 1)"
                  style="font-family:'Kaiti SC',KaiTi,serif" pointer-events="none">{{ n.name }}</text>
              </template>

              <!-- 桥接词节点 -->
              <template v-else-if="n.isBridge">
                <circle :r="14 * (expanded ? n.pscale : 1)" fill="#3a4050" stroke="#9aa0aa" :stroke-width="1.5 * (expanded ? n.pscale : 1)" stroke-dasharray="3 3" />
                <text text-anchor="middle" :y="26 * (expanded ? n.pscale : 1)" fill="#c3c8d2" :font-size="11 * (expanded ? n.pscale : 1)"
                  style="font-family:'Kaiti SC',KaiTi,serif">{{ n.name }}</text>
              </template>

              <!-- 普通共现节点 -->
              <template v-else-if="!n.isSubNode">
                <circle :r="(n.r + 6) * (expanded ? n.pscale : 1)" :fill="n.theme_color || '#8A6D3B'" opacity="0.18" class="cooc-pulse" />
                <circle :r="n.r * (expanded ? n.pscale : 1)" :fill="n.theme_color || '#8A6D3B'"
                  :stroke="selected === n.id || hovered === n.id ? '#F5F1E8' : 'rgba(245,241,232,0.55)'"
                  :stroke-width="(selected === n.id ? 3 : 1.6) * (expanded ? n.pscale : 1)"
                  :opacity="dim(n) ? 0.45 : 1" style="transition: opacity .2s" />
                <text text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8"
                  :font-size="n.font * (expanded ? n.pscale : 1)"
                  style="font-family:'Kaiti SC',KaiTi,serif" pointer-events="none">{{ n.name }}</text>
              </template>

              <!-- 子图谱子节点 -->
              <template v-else>
                <circle :r="(n.r + 4) * (expanded ? n.pscale : 1)" :fill="n.theme_color || '#8A6D3B'"
                  :opacity="expanded && !isRotating && n.pdepth < -150 ? 0.1 : 0.2"
                  :filter="expanded && !isRotating && n.pdepth < -150 ? `url(#coocDepthBlur${uid})` : undefined" />
                <circle :r="n.r * (expanded ? n.pscale : 1)" :fill="n.theme_color || '#8A6D3B'"
                  :stroke="selected === n.id || hovered === n.id ? '#F5F1E8' : 'rgba(245,241,232,0.55)'"
                  :stroke-width="(selected === n.id ? 2.5 : 1.2) * (expanded ? n.pscale : 1)"
                  :opacity="dim(n) ? 0.45 : 1" style="transition: opacity .2s" />
                <text text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8"
                  :font-size="n.font * (expanded ? n.pscale : 1)"
                  style="font-family:'Kaiti SC',KaiTi,serif" pointer-events="none">{{ n.name }}</text>
              </template>
              </g>
            </g>

          </g>
        </svg>
        </div>

        <!-- 悬浮/选中详情卡片 -->
        <div v-for="n in activeCards" :key="'card_' + n.id"
          class="absolute pointer-events-auto z-10 cooc-card-wrapper"
          :style="{ left: n.screenX + 'px', top: n.screenY + 'px', width: n.cardW + 'px' }">
          <div class="cooc-card" :style="{ ['--accent']: n.accentColor }">
            <div class="flex items-start justify-between gap-2">
              <b class="font-song text-sm" :style="{ color: n.accentColor }">{{ n.name }}</b>
              <span v-if="n.edge?.npmi != null" class="text-[10px] text-qianhui whitespace-nowrap">NPMI {{ n.edge.npmi.toFixed(2) }}</span>
            </div>
            <div class="flex items-center gap-1.5 mt-0.5 text-[10px] text-qianhui/80 flex-wrap">
              <span v-if="n.edge?.type">{{ typeLabel(n.edge.type) }}</span>
              <span v-if="n.edge?.same_poem" class="text-qianhui/60">· 共现 {{ n.edge.same_poem }} 篇</span>
              <span v-if="n.isBridge" class="text-zheshi">· 桥接词</span>
              <span v-if="n.isSubCenter" class="text-zheshi">· 已展开</span>
              <span v-if="n.isSubNode" class="text-zheshi">· 子意象</span>
            </div>
            <p v-if="n.edge?.verse" class="verse-text text-moyan/90 mt-1.5 leading-6 text-[12px]">「{{ n.edge.verse }}」</p>
            <p v-if="n.edge?.description" class="text-qianhui mt-1 text-[11px] leading-5">{{ n.edge.description }}</p>
            <p v-if="n.edge?.poet || n.edge?.dynasty" class="text-[10px] text-qianhui/70 mt-1">
              {{ [n.edge.dynasty, n.edge.poet].filter(Boolean).join(' · ') }}
              <span v-if="n.edge.poem_title">《{{ n.edge.poem_title }}》</span>
            </p>
            <button v-if="n.concept_id" class="mt-2 text-[11px] hover:underline pointer-events-auto font-semibold"
              :style="{ color: n.accentColor }"
              @click.stop="goConcept(n.concept_id)">探索该意象 →</button>
          </div>
        </div>

        <!-- 图例 -->
        <div v-if="graph" class="absolute left-5 bottom-5 bg-black/35 backdrop-blur rounded-lg px-4 py-3 text-xuanzhi/85 text-xs space-y-1.5 pointer-events-none">
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="4"/></svg> 粗 = NPMI 强</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="1.5"/></svg> 细 = NPMI 弱</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="2"/></svg> 实线 = 句内</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="2" stroke-dasharray="7 5"/></svg> 虚线 = 跨句</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#F5F1E8" stroke-width="2" stroke-dasharray="2 4"/></svg> 点线 = 全诗</div>
          <div class="flex items-center gap-2"><svg width="34" height="6"><line x1="0" y1="3" x2="34" y2="3" stroke="#9aa0aa" stroke-width="1.2" stroke-dasharray="3 5"/></svg> 灰线 = 桥接</div>
        </div>

        <!-- 缩放控制 -->
        <div v-if="graph" class="absolute right-5 top-2 bg-black/35 backdrop-blur rounded-lg px-2 py-1.5 flex items-center gap-1 text-xuanzhi/80 text-sm">
          <button class="w-7 h-7 rounded hover:bg-white/15 flex items-center justify-center" @click="zoomIn" title="放大">+</button>
          <span class="text-xs w-12 text-center">{{ Math.round(zoom * 100) }}%</span>
          <button class="w-7 h-7 rounded hover:bg-white/15 flex items-center justify-center" @click="zoomOut" title="缩小">−</button>
          <button class="w-7 h-7 rounded hover:bg-white/15 flex items-center justify-center" @click="resetView" title="重置视图">⌂</button>
        </div>

        <!-- 统计 -->
        <div v-if="graph" class="absolute right-5 bottom-5 bg-black/35 backdrop-blur rounded-lg px-4 py-2.5 text-xuanzhi/70 text-[11px] text-right leading-5 pointer-events-none">
          <div>共现意象 <b class="text-xuanzhi">{{ stats.total }}</b> 个</div>
          <div>句内 {{ stats.inner }} · 跨句 {{ stats.cross }} · 全诗 {{ stats.whole }}</div>
          <div v-if="expanded" class="text-xuanzhi/80 mt-1">已展开 {{ expandedCount }} 个子图谱</div>
        </div>

        <!-- 提示 -->
        <div class="absolute left-5 top-2 bg-black/35 backdrop-blur rounded-lg px-3 py-1.5 text-xuanzhi/60 text-[10px] pointer-events-none">
          滚轮缩放 · 拖拽节点移动 · 拖拽空白平移
        </div>
      </div>
    </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.cooc-root { background: radial-gradient(120% 90% at 50% 0%, #16263f 0%, #0e1726 58%, #0a101c 100%); }
.cooc-scene { }
.cooc-scene.scene-expanded { animation: sceneBreath 8s ease-in-out infinite; }
@keyframes sceneBreath {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.08); }
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.35s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.cooc-card {
  width: 224px; border-radius: 10px; padding: 10px 12px;
  font-size: 12px; line-height: 1.6;
  background: #F5F1E8; box-shadow: 0 0 0 2px var(--accent), 0 14px 36px rgba(0,0,0,0.4);
}
.cooc-card-wrapper { pointer-events: auto; }
.cooc-edges line { opacity: 1; }
.cooc-pulse { opacity: 0.14; }
.cooc-spin { }
.node-group { cursor: grab; will-change: transform; }
.node-group:active { cursor: grabbing; }
.node-group > g { transform-box: fill-box; transform-origin: center; }
.node-no-transition { transition: none !important; }

@keyframes nodePopIn {
  0% { opacity: 0; }
  40% { opacity: 0.8; }
  100% { opacity: 1; }
}

@keyframes subCenterMorph {
  0% { opacity: 0; }
  100% { opacity: 1; }
}

@keyframes nodeFadeOut {
  0% { opacity: 1; }
  100% { opacity: 0; }
}

@keyframes edgeDrawIn {
  0% { opacity: 0; }
  40% { opacity: 0.6; }
  100% { opacity: 1; }
}

@keyframes edgeFadeOut {
  0% { opacity: 1; }
  100% { opacity: 0; }
}

.sub-node-enter {
  animation: nodePopIn 0.55s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

.sub-center-enter {
  animation: subCenterMorph 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

.node-collapsing {
  animation: nodeFadeOut 0.38s ease-in forwards;
  pointer-events: none;
}

.edge-draw-enter {
  animation: edgeDrawIn 0.6s ease-out both;
}

.edge-collapsing-sub {
  animation: edgeFadeOut 0.38s ease-in forwards !important;
}

.cooc-control-ring {
  animation: controlRingPulse 4s ease-in-out infinite;
  transform-box: fill-box;
}

@keyframes controlRingPulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
</style>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getConceptCooccurrence, resolveConcept } from '../api'

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

const svgRef = ref(null)
const canvasRef = ref(null)

// ── 缩放/平移状态 ──
const zoom = ref(1)
const panX = ref(0)
const panY = ref(0)
let pannedDuringDrag = false
let panStart = null
let draggingNode = null   // { id, startX, startY, offsetX, offsetY }
const draggingNodeId = ref(null)
const nodeOverrides = ref({})  // { nodeId: { x, y } } 拖拽后的位置覆盖

// ── 子图谱展开状态 ──
const expanded = ref(false)
const expandLoading = ref(false)
const collapsing = ref(false)
const expansionData = ref({})
const MAX_NESTING_LEVEL = 2
const COLLAPSE_MS = 420

function typeLabel(t) { return t === '句内' ? '句内共现' : t === '跨句' ? '跨句共现' : '全诗共现' }
function dashOf(t) { return t === '句内' ? '' : t === '跨句' ? '7 5' : '2 5' }
function nodeRadius(name, samePoem) {
  const base = 20 + Math.min(12, samePoem ? Math.log2(samePoem + 1) * 2 : 5)
  return Math.max(20, Math.min(32, base))
}
function nodeFont(name) { return name.length > 2 ? 14 : name.length === 2 ? 17 : 20 }
function centerFont(name) { return name.length > 3 ? 26 : name.length === 3 ? 30 : 36 }

// ── 基础图谱（一级）──
const graph = computed(() => {
  const d = props.data
  if (!d || !d.edges?.length) return null
  const nodes = d.nodes || []
  const center = nodes.find((n) => n.center)
  const centerId = center?.id
  if (!centerId) return null
  const cx = W / 2, cy = H / 2
  const pos = { [centerId]: { x: cx, y: cy } }

  const containEdges = []
  const directEdges = []
  const bridgeEdges = []
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
    const dx = t.x - s.x, dy = t.y - s.y
    const len = Math.hypot(dx, dy) || 1
    const ux = dx / len, uy = dy / len
    const startR = (placed.find((p) => p.id === e.source)?.r || 0) + 4
    const endR = (placed.find((p) => p.id === e.target)?.r || 0) + 3
    geoEdges.push({
      ...e,
      x1: s.x + ux * startR, y1: s.y + uy * startR,
      x2: t.x - ux * endR, y2: t.y - uy * endR,
      isContain, isBridgeEdge: e.source !== centerId,
      width: 1 + ((e.npmi + 1) / 2) * 5,
      opacity: e.diaphaneity || 0.5,
      dash: dashOf(e.type),
    })
  }
  return { center: centerNode, nodes: placedNodes, edges: geoEdges }
})

// 一级子意象节点 ID 列表
const childNodeIds = computed(() => {
  if (!graph.value) return []
  return graph.value.nodes.filter((n) => !n.isCenter && !n.isBridge).map((n) => n.id)
})

// ── 拖拽位置查询 ──
function getDragPos(n) {
  const o = nodeOverrides.value[n.id]
  if (o) return { x: o.x, y: o.y }
  return { x: n.x, y: n.y }
}

// ── 斥力布局：对可变节点做排斥迭代，固定节点不动 ──
function applyRepulsion(nodes, opts = {}) {
  const {
    iterations = 12,
    minDist = 30,
    centerX = W / 2,
    centerY = H / 2,
    centerGravity = 0.02,
    damping = 0.85,
    boundPadding = 40,
  } = opts

  // 固定节点：isCenter、isSubCenter、isBridge 不动
  const fixedIds = new Set(
    nodes.filter((n) => n.isCenter || n.isSubCenter || n.isBridge)
      .map((n) => n.id)
  )
  const parentMap = {}
  for (const n of nodes) {
    if (n.parentId) parentMap[n.id] = n.parentId
  }

  const pos = {}
  const vel = {}
  for (const n of nodes) {
    pos[n.id] = { x: n.x, y: n.y }
    vel[n.id] = { x: 0, y: 0 }
  }

  for (let iter = 0; iter < iterations; iter++) {
    const forces = {}
    for (const n of nodes) forces[n.id] = { x: 0, y: 0 }

    // 斥力：所有节点对之间
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i]
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j]
        const dx = pos[a.id].x - pos[b.id].x
        const dy = pos[a.id].y - pos[b.id].y
        const dist = Math.hypot(dx, dy) || 0.01
        const rA = a.r || 10
        const rB = b.r || 10
        const desired = rA + rB + minDist
        if (dist < desired) {
          const strength = (desired - dist) / dist * 0.5
          const fx = dx * strength
          const fy = dy * strength
          forces[a.id].x += fx
          forces[a.id].y += fy
          forces[b.id].x -= fx
          forces[b.id].y -= fy
        }
      }
    }

    // 吸引力：子节点向父节点聚拢
    for (const n of nodes) {
      if (!n.parentId || fixedIds.has(n.id)) continue
      const pp = pos[parentMap[n.id]]
      if (!pp) continue
      const dx = pp.x - pos[n.id].x
      const dy = pp.y - pos[n.id].y
      const dist = Math.hypot(dx, dy) || 0.01
      const desired = 70
      if (dist > desired) {
        const strength = (dist - desired) / dist * centerGravity
        forces[n.id].x += dx * strength
        forces[n.id].y += dy * strength
      }
    }

    // 根节点对可变节点的轻微吸引，防止飘太远
    for (const n of nodes) {
      if (fixedIds.has(n.id)) continue
      const dx = centerX - pos[n.id].x
      const dy = centerY - pos[n.id].y
      const dist = Math.hypot(dx, dy) || 0.01
      if (dist > 400) {
        const strength = (dist - 400) / dist * 0.01
        forces[n.id].x += dx * strength
        forces[n.id].y += dy * strength
      }
    }

    // 应用力
    const tempDamping = damping * (1 - iter / iterations)
    for (const n of nodes) {
      if (fixedIds.has(n.id)) continue
      vel[n.id].x = (vel[n.id].x + forces[n.id].x) * tempDamping
      vel[n.id].y = (vel[n.id].y + forces[n.id].y) * tempDamping
      pos[n.id].x += vel[n.id].x
      pos[n.id].y += vel[n.id].y
      // 边界约束
      pos[n.id].x = Math.max(boundPadding, Math.min(W - boundPadding, pos[n.id].x))
      pos[n.id].y = Math.max(boundPadding, Math.min(H - boundPadding, pos[n.id].y))
    }
  }

  return nodes.map((n) => ({ ...n, x: pos[n.id].x, y: pos[n.id].y }))
}

// ── 3D 投影系统 ──
const FOCAL = 900          // 透视焦距
const camAngleX = ref(18)  // 摄像机俯仰角（度）
const camAngleY = ref(0)   // 摄像机水平旋转角（度）
const isRotating = ref(false)
let autoRotateRAF = null

// 鼠标位置驱动的旋转控制
const mouseNormX = ref(0)   // -1 ~ 1, 鼠标在控制圈内的归一化X
const mouseNormY = ref(0)   // -1 ~ 1, 鼠标在控制圈内的归一化Y
const mouseInsideRing = ref(false)

const CONTROL_RADIUS = 340

function startAutoRotate() {
  if (autoRotateRAF) return
  isRotating.value = true
  let last = performance.now()
  const tick = (now) => {
    const dt = (now - last) / 1000
    last = now
    if (!draggingNode && !panStart && expanded.value) {
      const speedBias = mouseInsideRing.value ? mouseNormX.value * 12 : 0
      camAngleY.value += dt * (8 + speedBias)
      if (mouseInsideRing.value) {
        const targetPitch = mouseNormY.value * 50
        camAngleX.value += (targetPitch - camAngleX.value) * 0.06
      }
      if (cachedNodes) {
        doProject()
      }
    }
    autoRotateRAF = requestAnimationFrame(tick)
  }
  autoRotateRAF = requestAnimationFrame(tick)
}
function stopAutoRotate() {
  if (autoRotateRAF) { cancelAnimationFrame(autoRotateRAF); autoRotateRAF = null }
  isRotating.value = false
}

function deg2rad(d) { return d * Math.PI / 180 }

// 3D → 2D 投影：旋转后透视投影
// 返回 { x, y, scale, depthZ }
function project3D(x, y, z, cx, cy) {
  // 以画布中心为原点的相对坐标
  let rx = x - cx
  let ry = y - cy
  let rz = z

  // rotateY（水平旋转）
  const ay = deg2rad(camAngleY.value)
  const cosY = Math.cos(ay), sinY = Math.sin(ay)
  let nx = rx * cosY + rz * sinY
  let nz = -rx * sinY + rz * cosY
  rx = nx; rz = nz

  // rotateX（俯仰旋转）
  const ax = deg2rad(camAngleX.value)
  const cosX = Math.cos(ax), sinX = Math.sin(ax)
  let ny_ = ry * cosX - rz * sinX
  nz = ry * sinX + rz * cosX
  ry = ny_; rz = nz

  // 透视投影
  const denom = FOCAL - rz
  const scale = denom > 1 ? FOCAL / denom : FOCAL
  const px = cx + rx * scale
  const py = cy + ry * scale

  return { x: px, y: py, scale, depthZ: rz }
}

function depthOpacity(depthZ) {
  const t = Math.max(0, Math.min(1, (-depthZ) / 200))
  return 1 - t * 0.4
}

// ── 展开后合并的显示图谱 ──
const displayGraph = computed(() => {
  if (!graph.value) return null
  if (!expanded.value || Object.keys(expansionData.value).length === 0) {
    const nodes = graph.value.nodes.map((n) => ({ ...n, z: 0 }))
    return { center: { ...graph.value.center, z: 0 }, nodes, edges: graph.value.edges }
  }

  const base = graph.value
  const allNodes = base.nodes.map((n) => ({ ...n, z: 0 }))
  const allEdges = [...base.edges]

  // 已出现节点名称集合（先收录基础图谱所有节点，后续展开时去重）
  const seenNames = new Set(base.nodes.map((n) => n.name))

  for (const [childId, info] of Object.entries(expansionData.value)) {
    const childNode = base.nodes.find((n) => n.id === childId)
    if (!childNode) continue
    const subData = info.data
    if (!subData?.nodes?.length) continue

    const subCenter = subData.nodes.find((n) => n.center)
    if (!subCenter) continue

    // 子图谱中心节点（替换原节点显示，往后退入 3D 空间）
    const subCenterNode = {
      id: childId,
      name: childNode.name,
      x: childNode.x,
      y: childNode.y,
      z: -120,
      r: Math.max(14, nodeRadius(childNode.name, 0) * 0.85),
      font: Math.max(11, nodeFont(childNode.name) * 0.8),
      isCenter: false,
      isBridge: false,
      isSubCenter: true,
      concept_id: childNode.concept_id,
      theme_color: childNode.theme_color,
    }

    const nodeIdx = allNodes.findIndex((n) => n.id === childId)
    if (nodeIdx >= 0) {
      allNodes[nodeIdx] = subCenterNode
    }

    // 去重：过滤掉名称已出现的子节点
    const rawSubChildren = subData.nodes.filter((n) => !n.center)
    const subChildNodes = rawSubChildren.filter((sn) => {
      if (seenNames.has(sn.name)) return false
      return true
    })

    // 动态子图谱半径（球面）
    const subCount = subChildNodes.length
    const subRadius = Math.max(70, Math.min(130, 50 + subCount * 8))

    const subNodesWithPos = []
    subChildNodes.forEach((sn, i) => {
      // 球面分布（斐波那契球面算法）
      const n = subCount
      const phi = Math.acos(1 - 2 * (i + 0.5) / n)       // 极角 0~π
      const theta = Math.PI * (1 + Math.sqrt(5)) * (i + 0.5) // 方位角
      // 球面坐标 → 笛卡尔坐标，穹顶朝前（z 方向）
      const r = subRadius
      const sx = r * Math.sin(phi) * Math.cos(theta)
      const sy = r * Math.sin(phi) * Math.sin(theta)
      const sz = -r * Math.cos(phi) - 120   // 球心在 z=-120，穹顶朝前

      const x = childNode.x + sx
      const y = childNode.y + sy
      const r2 = Math.max(8, Math.min(16, nodeRadius(sn.name, 0) * 0.55))
      subNodesWithPos.push({
        id: `sub_${childId}_${sn.id}`,
        name: sn.name,
        x, y, z: sz, r: r2,
        font: Math.max(9, nodeFont(sn.name) * 0.7),
        isCenter: false,
        isBridge: false,
        isSubNode: true,
        parentId: childId,
        originalId: sn.id,
        concept_id: sn.concept_id,
        theme_color: sn.theme_color || childNode.theme_color,
      })
      seenNames.add(sn.name)
    })

    allNodes.push(...subNodesWithPos)

    // 被过滤掉的子节点名称集合（用于跳过对应边）
    const filteredNames = new Set(rawSubChildren.filter((sn) => seenNames.has(sn.name) && !subNodesWithPos.find((p) => p.name === sn.name)).map((sn) => sn.name))
    const filteredSourceIds = new Set(rawSubChildren.filter((sn) => filteredNames.has(sn.name)).map((sn) => sn.id))

    // 添加子图谱边（跳过涉及已过滤节点的边）
    for (const subEdge of subData.edges) {
      const isContain = subEdge.relation_type === '包含'
      const srcIsSubCenter = subEdge.source === subCenter.id
      const tgtIsSubCenter = subEdge.target === subCenter.id

      if (!srcIsSubCenter && filteredSourceIds.has(subEdge.source)) continue
      if (!tgtIsSubCenter && filteredSourceIds.has(subEdge.target)) continue

      const resolvedSrcId = srcIsSubCenter
        ? childId
        : `sub_${childId}_${subEdge.source}`
      const resolvedTgtId = tgtIsSubCenter
        ? childId
        : `sub_${childId}_${subEdge.target}`

      const subEdgeNode = subNodesWithPos.find((n) => n.id === `sub_${childId}_${subEdge.target}`)
      const strokeColor = subEdgeNode?.theme_color || childNode.theme_color || themeColor

      allEdges.push({
        ...subEdge,
        source: subEdge.source,
        target: subEdge.target,
        resolvedSrcId,
        resolvedTgtId,
        x1: 0, y1: 0, x2: 0, y2: 0,
        isContain,
        isSubEdge: true,
        strokeColor,
        width: 1 + ((subEdge.npmi + 1) / 2) * 4,
        opacity: subEdge.diaphaneity || 0.5,
        dash: dashOf(subEdge.type),
      })
    }
  }

  // ── 斥力迭代：对可变节点（子节点）做排斥+聚拢 ──
  const repulsedNodes = applyRepulsion(allNodes, {
    iterations: 15,
    minDist: 28,
    centerGravity: 0.03,
    damping: 0.82,
  })

  // 重新计算所有边的坐标（斥力后节点位置变了）—— 3D 投影在 projectedGraph 中处理
  const edgeNodesMap = {}
  for (const n of repulsedNodes) edgeNodesMap[n.id] = n

  const expandedChildIds = new Set(Object.keys(expansionData.value))

  const repulsedEdges = allEdges.map((e) => {
    let srcNode, tgtNode
    if (e.isSubEdge) {
      srcNode = edgeNodesMap[e.resolvedSrcId]
      tgtNode = edgeNodesMap[e.resolvedTgtId]
    } else {
      srcNode = edgeNodesMap[e.source]
      tgtNode = edgeNodesMap[e.target]
      if (!srcNode && expandedChildIds.has(e.source)) {
        srcNode = edgeNodesMap[e.source]
      }
      if (!tgtNode && expandedChildIds.has(e.target)) {
        tgtNode = edgeNodesMap[e.target]
      }
    }
    if (!srcNode || !tgtNode) return e
    return { ...e }  // 坐标在 projectedGraph 中投影后计算
  })

  // 应用拖拽位置覆盖
  const finalNodes = repulsedNodes

  return { center: { ...base.center, z: 0 }, nodes: finalNodes, edges: repulsedEdges }
})

// ── 3D 投影后的图谱（展开时应用透视投影）──
// 关键优化：wrapper 对象只在结构变化时创建一次，旋转期间仅原地修改属性
// 使用 ref (非 shallowRef) 以确保嵌套属性变更能被 Vue 追踪，实现精准 DOM 更新
const projectedGraph = ref(null)
let cachedNodes = null
let cachedEdges = null
let cachedCenter = null
let cachedNodeIds = ''
let lastExpanded = false
let pgWrapper = null    // 稳定的 wrapper 对象引用，旋转期间永不替换
let pgNodesArr = null   // 稳定的 projectedNodes 数组引用
let pgEdgesArr = null   // 稳定的 projectedEdges 数组引用

const PROJ_CX = W / 2
const PROJ_CY = H / 2

function rebuildProjectionBase() {
  const dg = displayGraph.value
  if (!dg) {
    projectedGraph.value = null
    pgWrapper = null
    pgNodesArr = null
    pgEdgesArr = null
    cachedNodes = null
    cachedEdges = null
    cachedCenter = null
    cachedNodeIds = ''
    return
  }

  const newIds = dg.nodes.map(n => n.id).join(',')

  if (cachedNodes && newIds === cachedNodeIds) {
    for (const n of cachedNodes) {
      const drag = getDragPos(n)
      n._bx = drag.x
      n._by = drag.y
    }
    cachedCenter._bx = dg.center.x
    cachedCenter._by = dg.center.y
    doProject()
    return
  }

  cachedNodeIds = newIds
  const nodes = dg.nodes.map(n => {
    const drag = getDragPos(n)
    return { ...n, _bx: drag.x, _by: drag.y }
  })
  const edges = dg.edges.map(e => ({ ...e }))
  const center = { ...dg.center, _bx: dg.center.x, _by: dg.center.y }

  cachedNodes = nodes
  cachedEdges = edges
  cachedCenter = center

  // 创建稳定的 wrapper 对象，后续永不替换
  pgNodesArr = cachedNodes
  pgEdgesArr = cachedEdges
  pgWrapper = {
    projectedNodes: pgNodesArr,
    projectedEdges: pgEdgesArr,
    projectedCenter: cachedCenter,
  }
  projectedGraph.value = pgWrapper

  lastExpanded = expanded.value
  doProject()
}

function doProject() {
  if (!cachedNodes) return
  const cx = PROJ_CX, cy = PROJ_CY

  if (!expanded.value) {
    for (const n of cachedNodes) {
      n.px = n._bx
      n.py = n._by
      n.pscale = 1
      n.pdepth = 0
      n.popacity = 1
    }
    cachedCenter.px = cachedCenter._bx
    cachedCenter.py = cachedCenter._by
    cachedCenter.pscale = 1
    cachedCenter.pdepth = 0
    cachedCenter.popacity = 1

    for (const e of cachedEdges) {
      let srcNode, tgtNode
      if (e.isSubEdge) {
        srcNode = cachedNodes.find(n => n.id === e.resolvedSrcId)
        tgtNode = cachedNodes.find(n => n.id === e.resolvedTgtId)
      } else {
        srcNode = cachedNodes.find(n => n.id === (e.source || e.resolvedSrcId))
        tgtNode = cachedNodes.find(n => n.id === (e.target || e.resolvedTgtId))
      }
      if (!srcNode || !tgtNode) {
        e.x1 = 0; e.y1 = 0; e.x2 = 0; e.y2 = 0
        continue
      }
      const srcR = srcNode.r || 10
      const tgtR = tgtNode.r || 10
      const dx = tgtNode.px - srcNode.px
      const dy = tgtNode.py - srcNode.py
      const len = Math.hypot(dx, dy) || 1
      const ux = dx / len, uy = dy / len
      e.x1 = srcNode.px + ux * (srcR + 3)
      e.y1 = srcNode.py + uy * (srcR + 3)
      e.x2 = tgtNode.px - ux * (tgtR + 3)
      e.y2 = tgtNode.py - uy * (tgtR + 3)
    }

    projectedGraph.value = {
      projectedNodes: pgNodesArr,
      projectedEdges: pgEdgesArr,
      projectedCenter: cachedCenter,
    }
    return
  }

  for (const n of cachedNodes) {
    const p = project3D(n._bx, n._by, n.z || 0, cx, cy)
    n.px = p.x; n.py = p.y; n.pscale = p.scale; n.pdepth = p.depthZ
    n.popacity = depthOpacity(p.depthZ)
  }
  const p = project3D(cachedCenter._bx, cachedCenter._by, cachedCenter.z || 0, cx, cy)
  cachedCenter.px = p.x; cachedCenter.py = p.y
  cachedCenter.pscale = p.scale; cachedCenter.pdepth = p.depthZ

  const nodeMap = {}
  for (const n of cachedNodes) nodeMap[n.id] = n
  nodeMap['__center__'] = cachedCenter

  for (const e of cachedEdges) {
    let srcNode, tgtNode
    if (e.isSubEdge) {
      srcNode = nodeMap[e.resolvedSrcId]
      tgtNode = nodeMap[e.resolvedTgtId]
    } else {
      srcNode = nodeMap[e.source] || nodeMap[e.resolvedSrcId]
      tgtNode = nodeMap[e.target] || nodeMap[e.resolvedTgtId]
    }
    if (!srcNode || !tgtNode) {
      e.x1 = 0; e.y1 = 0; e.x2 = 0; e.y2 = 0
      continue
    }
    const srcR = (srcNode.r || 10) * srcNode.pscale
    const tgtR = (tgtNode.r || 10) * tgtNode.pscale
    const dx = tgtNode.px - srcNode.px
    const dy = tgtNode.py - srcNode.py
    const len = Math.hypot(dx, dy) || 1
    const ux = dx / len, uy = dy / len
    e.x1 = srcNode.px + ux * (srcR + 3)
    e.y1 = srcNode.py + uy * (srcR + 3)
    e.x2 = tgtNode.px - ux * (tgtR + 3)
    e.y2 = tgtNode.py - uy * (tgtR + 3)
  }

  cachedNodes.sort((a, b) => {
    const da = Math.round(a.pdepth / 40) * 40
    const db = Math.round(b.pdepth / 40) * 40
    if (da !== db) return da - db
    return String(a.id).localeCompare(String(b.id))
  })
  projectedGraph.value = {
    projectedNodes: pgNodesArr,
    projectedEdges: pgEdgesArr,
    projectedCenter: cachedCenter,
  }
}

watch(displayGraph, () => {
  rebuildProjectionBase()
  if (props.show && expanded.value && !autoRotateRAF) {
    startAutoRotate()
  }
}, { immediate: true })

watch(expanded, (v) => {
  if (v) startAutoRotate()
  else stopAutoRotate()
})

watch(expanded, (v) => {
  if (v !== lastExpanded) {
    rebuildProjectionBase()
  }
})

watch(nodeOverrides, () => {
  if (cachedNodes) {
    rebuildProjectionBase()
  }
})

const expandedCount = computed(() => Object.keys(expansionData.value).length)

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

// ── SVG → 屏幕坐标转换 ──
function svgToScreen(svgX, svgY) {
  const svg = svgRef.value
  const canvas = canvasRef.value
  if (!svg || !canvas) return { x: svgX, y: svgY }
  const rect = canvas.getBoundingClientRect()
  const scaleX = rect.width / W
  const scaleY = rect.height / H
  // 考虑 preserveAspectRatio (xMidYMid meet)
  const scale = Math.min(scaleX, scaleY)
  const offsetX = (rect.width - W * scale) / 2
  const offsetY = (rect.height - H * scale) / 2
  // 应用 zoom/pan 逆变换
  const adjustedX = (svgX - panX.value) / zoom.value
  const adjustedY = (svgY - panY.value) / zoom.value
  return {
    x: offsetX + adjustedX * scale,
    y: offsetY + adjustedY * scale,
  }
}

function clientToSvg(clientX, clientY) {
  const canvas = canvasRef.value
  if (!canvas) return { x: 0, y: 0 }
  const rect = canvas.getBoundingClientRect()
  const scaleX = rect.width / W
  const scaleY = rect.height / H
  const scale = Math.min(scaleX, scaleY)
  const offsetX = (rect.width - W * scale) / 2
  const offsetY = (rect.height - H * scale) / 2
  const svgX = (clientX - rect.left - offsetX) / scale
  const svgY = (clientY - rect.top - offsetY) / scale
  return { x: svgX, y: svgY }
}

// ── 卡片位置计算 ──
const activeCards = computed(() => {
  if (!projectedGraph.value) return []
  const ids = new Set([selected.value, hovered.value].filter(Boolean))
  const result = []
  const cardW = 224, cardH = 176

  for (const n of projectedGraph.value.projectedNodes) {
    if (!ids.has(n.id) || n.isCenter) continue

    const edge = edgeForNode(n)
    const accentColor = n.theme_color || themeColor

    // 使用投影坐标
    const useX = n.px !== undefined ? n.px : n.x
    const useY = n.py !== undefined ? n.py : n.y
    const pos = svgToScreen(useX, useY)
    const useScale = n.pscale !== undefined ? n.pscale : 1
    const r = (n.r || 20) * useScale

    // 粗略估计节点屏幕大小
    const svg = svgRef.value
    const canvas = canvasRef.value
    const scale = canvas ? Math.min(canvas.clientWidth / W, canvas.clientHeight / H) : 1
    const screenR = r * zoom.value * scale

    let screenX = pos.x + screenR + 14
    if (screenX + cardW > (canvas?.clientWidth || W)) screenX = pos.x - screenR - 14 - cardW
    screenX = Math.max(8, Math.min((canvas?.clientWidth || W) - cardW - 8, screenX))
    let screenY = pos.y - cardH / 2
    screenY = Math.max(8, Math.min((canvas?.clientHeight || H) - cardH - 8, screenY))

    result.push({
      ...n,
      edge,
      screenX,
      screenY,
      cardW,
      accentColor,
    })
  }
  return result
})

function edgeForNode(node) {
  if (!node) return null
  const id = node.id || node
  if (!id) return null

  // 先查根层边
  if (props.data?.edges) {
    const list = props.data.edges
    const found = list.find((e) => e.target === id && e.relation_type === '共现')
      || list.find((e) => e.target === id)
    if (found) return found
  }

  // 子节点：通过 parentId 定位父图谱，用 originalId 查找目标边
  if (node.parentId && node.originalId) {
    const subInfo = expansionData.value[node.parentId]
    if (subInfo?.data?.edges) {
      const found = subInfo.data.edges.find((e) => e.target === node.originalId && e.relation_type === '共现')
        || subInfo.data.edges.find((e) => e.target === node.originalId)
      if (found) return found
    }
  }

  // 遍历所有子图谱（兜底）
  for (const [, info] of Object.entries(expansionData.value)) {
    if (!info.data?.edges) continue
    const lookupId = node.originalId || id
    const found = info.data.edges.find((e) => e.target === lookupId && e.relation_type === '共现')
      || info.data.edges.find((e) => e.target === lookupId)
    if (found) return found
  }
  return null
}

function dim(n) {
  if (!selected.value) return false
  return selected.value !== n.id && !isConnectedToSelected(n)
}
function isConnectedToSelected(n) {
  if (!props.data?.edges) return false
  return props.data.edges.some((e) => (e.target === n.id && e.source === selected.value) || (e.source === n.id && e.target === selected.value))
}

function select(n) {
  selected.value = selected.value === n.id ? null : n.id
}
function clearSelection() {
  if (pannedDuringDrag) { pannedDuringDrag = false; return }
  selected.value = null; hovered.value = null
}
function goConcept(id) { emit('close'); router.push('/concept/' + id) }
function close() { emit('close') }

// ── 缩放/平移/拖拽 ──
function onZoom(e) {
  const delta = e.deltaY > 0 ? 0.9 : 1.1
  const newZoom = Math.max(0.3, Math.min(5, zoom.value * delta))
  const mouseSvg = clientToSvg(e.clientX, e.clientY)
  panX.value = mouseSvg.x - (mouseSvg.x - panX.value) * (newZoom / zoom.value)
  panY.value = mouseSvg.y - (mouseSvg.y - panY.value) * (newZoom / zoom.value)
  zoom.value = newZoom
}

function zoomIn() { zoom.value = Math.min(5, zoom.value * 1.2) }
function zoomOut() { zoom.value = Math.max(0.3, zoom.value / 1.2) }
function resetView() { zoom.value = 1; panX.value = 0; panY.value = 0 }

function onCanvasMouseDown(e) {
  if (e.button !== 0) return
  draggingNode = null
  pannedDuringDrag = false
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const pos = clientToSvg(e.clientX, e.clientY)
  const dx = pos.x - PROJ_CX
  const dy = pos.y - PROJ_CY
  const dist = Math.hypot(dx, dy)
  const insideRing = expanded.value && dist <= CONTROL_RADIUS
  if (insideRing) {
    isRotating.value = true
  }
  panStart = {
    x: e.clientX, y: e.clientY,
    panX: panX.value, panY: panY.value,
    camX: camAngleX.value, camY: camAngleY.value,
    canvasLeft: rect.left, canvasTop: rect.top,
    canvasW: rect.width, canvasH: rect.height,
    insideRing,
  }
}

function onCanvasMouseMove(e) {
  const canvas = canvasRef.value
  if (!canvas) return
  const pos = clientToSvg(e.clientX, e.clientY)
  const dx = pos.x - PROJ_CX
  const dy = pos.y - PROJ_CY
  const dist = Math.hypot(dx, dy)

  if (expanded.value && dist <= CONTROL_RADIUS) {
    mouseInsideRing.value = true
    mouseNormX.value = Math.max(-1, Math.min(1, dx / CONTROL_RADIUS))
    mouseNormY.value = Math.max(-1, Math.min(1, dy / CONTROL_RADIUS))
  } else {
    mouseInsideRing.value = false
  }

  if (!panStart) return

  if (draggingNode) {
    nodeOverrides.value[draggingNode.id] = { x: pos.x, y: pos.y }
    if (cachedNodes) {
      const n = cachedNodes.find(n => n.id === draggingNode.id)
      if (n) {
        n._bx = pos.x
        n._by = pos.y
        doProject()
      }
    }
  } else if (panStart.insideRing) {
    const ddx = e.clientX - panStart.x
    const ddy = e.clientY - panStart.y
    if (Math.abs(ddx) > 2 || Math.abs(ddy) > 2) pannedDuringDrag = true
    camAngleY.value = panStart.camY + ddx * 0.3
    camAngleX.value = Math.max(-60, Math.min(80, panStart.camX + ddy * 0.2))
    if (cachedNodes) doProject()
  } else {
    const scale = Math.min(panStart.canvasW / W, panStart.canvasH / H)
    const newPanX = panStart.panX + (e.clientX - panStart.x) / scale
    const newPanY = panStart.panY + (e.clientY - panStart.y) / scale
    if (Math.abs(newPanX - panX.value) > 0.5 || Math.abs(newPanY - panY.value) > 0.5) {
      pannedDuringDrag = true
    }
    panX.value = newPanX
    panY.value = newPanY
  }
}

function onCanvasMouseUp() {
  panStart = null
  draggingNode = null
  draggingNodeId.value = null
  if (!autoRotateRAF) {
    isRotating.value = false
  }
}

function onCanvasMouseLeave() {
  mouseInsideRing.value = false
  panStart = null
  draggingNode = null
  draggingNodeId.value = null
  if (!autoRotateRAF) {
    isRotating.value = false
  }
}

function onNodeMouseDown(e, n) {
  e.stopPropagation()
  draggingNode = { id: n.id }
  draggingNodeId.value = n.id
  panStart = null
}

// ── 子图谱展开逻辑 ──
async function toggleExpand() {
  if (expanded.value) {
    // 收拢：先播放收拢动画，再清除数据
    collapsing.value = true
    await new Promise((r) => setTimeout(r, COLLAPSE_MS))
    expanded.value = false
    expansionData.value = {}
    nodeOverrides.value = {}
    collapsing.value = false
  } else {
    expandLoading.value = true
    try {
      await expandAllChildren()
      expanded.value = true
    } catch (err) {
      console.error('展开子图谱失败:', err)
    } finally {
      expandLoading.value = false
    }
  }
}

async function expandAllChildren() {
  if (!graph.value) return
  const children = graph.value.nodes.filter((n) => !n.isCenter && !n.isBridge)
  const results = {}

  const CONCURRENCY = 5
  const chunks = []
  for (let i = 0; i < children.length; i += CONCURRENCY) {
    chunks.push(children.slice(i, i + CONCURRENCY))
  }

  for (const chunk of chunks) {
    await Promise.all(chunk.map(async (node) => {
      try {
        let conceptId = node.concept_id
        if (!conceptId) {
          const resolved = await resolveConcept(node.name)
          if (resolved?.found) conceptId = resolved.concept_id
        }
        if (conceptId) {
          const cooc = await getConceptCooccurrence(conceptId)
          if (cooc?.nodes?.length > 1) {
            results[node.id] = { conceptId, data: cooc }
          }
        }
      } catch (e) {
      }
    }))
  }

  expansionData.value = results
}

// ── 重置状态 ──
function resetState() {
  selected.value = null
  hovered.value = null
  expanded.value = false
  collapsing.value = false
  draggingNodeId.value = null
  camAngleX.value = 18
  camAngleY.value = 0
  mouseInsideRing.value = false
  mouseNormX.value = 0
  mouseNormY.value = 0
  expansionData.value = {}
  nodeOverrides.value = {}
  zoom.value = 1
  panX.value = 0
  panY.value = 0
}

function onKey(e) { if (e.key === 'Escape' && props.show) close() }
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  stopAutoRotate()
})

watch(() => props.show, (v) => {
  if (!v) {
    resetState()
    stopAutoRotate()
  }
})
</script>
