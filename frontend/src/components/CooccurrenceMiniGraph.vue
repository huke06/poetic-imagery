<!--
  共现知识图谱 · 缩略卡（美工优化版）
  与全屏探索器同源的径向布局：中心意象 + 环绕共现词，底部实时显示悬停节点详情。
-->
<template>
  <div class="cooc-mini" :style="{ '--accent': themeColor }">
    <svg v-if="graph" :viewBox="`0 0 ${W} ${H}`" class="w-full" preserveAspectRatio="xMidYMid meet">
      <defs>
        <radialGradient :id="'miniGlow' + uid" cx="50%" cy="50%" r="50%">
          <stop offset="0%" :stop-color="themeColor" stop-opacity="0.16" />
          <stop offset="100%" :stop-color="themeColor" stop-opacity="0" />
        </radialGradient>
      </defs>
      <rect :width="W" :height="H" rx="10" fill="#101a2b" />
      <rect :width="W" :height="H" rx="10" fill="url(#miniGlow)" />
      <g fill="none" stroke="#F5F1E8">
        <circle :cx="W/2" :cy="H/2" r="86" stroke-opacity="0.06" />
        <circle :cx="W/2" :cy="H/2" r="150" stroke-opacity="0.08" />
      </g>

      <g>
        <line v-for="e in graph.edges" :key="'e' + e.target"
          :x1="e.x1" :y1="e.y1" :x2="e.x2" :y2="e.y2"
          :stroke="e.isContain ? '#9aa0aa' : themeColor"
          :stroke-width="e.isContain ? 1 : e.width" :stroke-opacity="e.isContain ? 0.5 : e.opacity"
          :stroke-dasharray="e.dash" stroke-linecap="round" />
      </g>

      <g :transform="`translate(${W/2},${H/2})`">
        <circle r="34" :fill="themeColor" stroke="#F5F1E8" stroke-width="2" />
        <text text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8" :font-size="graph.centerFont"
          style="font-family:'Kaiti SC',KaiTi,serif;font-weight:700" pointer-events="none">{{ graph.centerName }}</text>
      </g>

      <g v-for="n in graph.nodes" :key="n.id" :transform="`translate(${n.x},${n.y})`" class="cursor-pointer"
        @click="clickNode(n)" @mouseenter="hover = n.id" @mouseleave="hover = null">
        <circle :r="n.r + 4" :fill="n.color" opacity="0.15" />
        <circle :r="n.r" :fill="n.color"
          :stroke="active(n) ? '#F5F1E8' : 'rgba(245,241,232,0.5)'"
          :stroke-width="active(n) ? 2.5 : 1.2" />
        <text text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8" :font-size="n.font"
          style="font-family:'Kaiti SC',KaiTi,serif" pointer-events="none">{{ n.name }}</text>
      </g>
    </svg>

    <!-- 底部详情条 -->
    <div class="cooc-mini__foot">
      <template v-if="hoverNode">
        <b class="font-song" :style="{ color: themeColor }">{{ hoverNode.name }}</b>
        <span v-if="hoverNode.edge?.npmi != null" class="text-qianhui/80">NPMI {{ hoverNode.edge.npmi.toFixed(2) }}</span>
        <span v-if="hoverNode.edge?.type" class="text-qianhui/70">{{ typeLabel(hoverNode.edge.type) }}</span>
        <span v-if="hoverNode.edge?.verse" class="verse-text text-moyan/80 truncate flex-1">「{{ hoverNode.edge.verse }}」</span>
      </template>
      <template v-else>
        <span class="text-qianhui/60">悬停节点查看共现详情 · 点击进入对应意象</span>
      </template>
    </div>
  </div>
</template>

<style scoped>
.cooc-mini { border-radius: 10px; overflow: hidden; }
.cooc-mini__foot {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  min-height: 34px; padding: 6px 10px; font-size: 11px;
  background: rgba(245,241,232,0.9); border: 1px solid rgba(0,0,0,0.05);
  border-top: none; border-radius: 0 0 10px 10px;
}
</style>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  data: { type: Object, default: null },
  themeColor: { type: String, default: '#2B4C7E' },
})
const router = useRouter()
const hover = ref(null)
const W = 560, H = 300
const uid = Math.floor(Math.random() * 1e6)

function typeLabel(t) { return t === '句内' ? '句内共现' : t === '跨句' ? '跨句共现' : '全诗共现' }
function dashOf(t) { return t === '句内' ? '' : t === '跨句' ? '7 5' : '2 5' }

const graph = computed(() => {
  const d = props.data
  if (!d || !d.edges?.length) return null
  const center = d.nodes?.find((n) => n.center)
  const centerId = center?.id
  if (!centerId) return null
  const cx = W / 2, cy = H / 2
  const R = 118
  const edges = d.edges
  const n = edges.length
  const nodes = []
  const geoEdges = []
  edges.forEach((e, i) => {
    const a = (i / n) * Math.PI * 2 - Math.PI / 2
    const x = cx + R * Math.cos(a)
    const y = cy + R * Math.sin(a)
    const meta = d.nodes.find((nd) => nd.id === e.target)
    const name = meta?.name || e.name || e.target
    const color = meta?.theme_color || '#8A6D3B'
    const r = e.relation_type === '包含' ? 9 : Math.max(13, Math.min(19, 15 + (e.same_poem ? Math.log2(e.same_poem + 1) : 2)))
    const isContain = e.relation_type === '包含'
    const dx = x - cx, dy = y - cy
    const len = Math.hypot(dx, dy) || 1
    const startR = 36
    const endR = r + 3
    nodes.push({
      id: e.target, name, x, y, r,
      color, concept_id: e.concept_id || meta?.concept_id,
      font: name.length > 2 ? 11 : name.length === 2 ? 13 : 15,
      edge: e, isContain,
    })
    geoEdges.push({
      target: e.target, isContain,
      x1: cx + (dx / len) * startR, y1: cy + (dy / len) * startR,
      x2: x - (dx / len) * endR, y2: y - (dy / len) * endR,
      width: 1 + ((e.npmi + 1) / 2) * 3.5,
      opacity: e.diaphaneity || 0.5,
      dash: dashOf(e.type),
    })
  })
  const centerName = center.name
  return {
    centerName, centerFont: centerName.length > 3 ? 20 : centerName.length === 3 ? 22 : 26,
    nodes, edges: geoEdges,
  }
})

const hoverNode = computed(() => {
  if (!graph.value || !hover.value) return null
  return graph.value.nodes.find((n) => n.id === hover.value)
})

function active(n) { return hover.value === n.id }

function clickNode(n) {
  if (n.isContain || !n.concept_id) return
  router.push('/concept/' + n.concept_id)
}
</script>
