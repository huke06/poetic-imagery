<!--
  共现知识图谱 · 缩略卡（自适应布局版）
  采用与 CooccurrenceExplorer 相同的分层径向布局，支持自适应缩放填满容器。
-->
<template>
  <div class="cooc-mini" :style="{ '--accent': themeColor }" ref="containerRef">
    <svg
      v-if="graph"
      ref="svgRef"
      :viewBox="`0 0 ${viewW} ${viewH}`"
      class="w-full h-full"
      preserveAspectRatio="none"
      @wheel.prevent="onWheel"
    >
      <defs>
        <radialGradient :id="'miniGlow' + uid" cx="50%" cy="50%" r="50%">
          <stop offset="0%" :stop-color="themeColor" stop-opacity="0.16" />
          <stop offset="100%" :stop-color="themeColor" stop-opacity="0" />
        </radialGradient>
      </defs>
      <rect :width="viewW" :height="viewH" rx="10" fill="#101a2b" />
      <rect :width="viewW" :height="viewH" rx="10" fill="url(#miniGlow)" />

      <!-- 自适应变换组：根据节点边界框自动缩放和居中 -->
      <g :transform="fitTransform">
        <!-- 连线 -->
        <g>
          <path v-for="e in graph.edges" :key="'e' + e.target"
            :d="e.pathD"
            fill="none"
            :stroke="e.isContain ? '#9aa0aa' : themeColor"
            :stroke-width="e.isContain ? 1 : e.width"
            :stroke-opacity="e.isContain ? 0.5 : e.opacity"
            :stroke-dasharray="e.dash" stroke-linecap="round" />
        </g>

        <!-- 中心节点 -->
        <g :transform="`translate(${graph.centerX},${graph.centerY})`">
          <circle :r="graph.centerR" :fill="themeColor" stroke="#F5F1E8" stroke-width="2" />
          <text text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8" :font-size="graph.centerFont"
            style="font-family:'Kaiti SC',KaiTi,serif;font-weight:700" pointer-events="none">{{ graph.centerName }}</text>
        </g>

        <!-- 所有节点 -->
        <g v-for="n in graph.nodes" :key="n.id" :transform="`translate(${n.x},${n.y})`" class="cursor-pointer"
          @click="clickNode(n)" @mouseenter="hover = n.id" @mouseleave="hover = null">
          <circle :r="n.r + 3" :fill="n.color" opacity="0.15" />
          <circle :r="n.r" :fill="n.color"
            :stroke="active(n) ? '#F5F1E8' : 'rgba(245,241,232,0.5)'"
            :stroke-width="active(n) ? 2.5 : 1.2" />
          <text text-anchor="middle" dominant-baseline="middle" fill="#F5F1E8" :font-size="n.font"
            style="font-family:'Kaiti SC',KaiTi,serif" pointer-events="none">{{ n.name }}</text>
        </g>
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
.cooc-mini { border-radius: 10px; overflow: hidden; display: flex; flex-direction: column; height: 100%; }
.cooc-mini svg { flex: 1; min-height: 0; display: block; }
.cooc-mini__foot {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  min-height: 34px; padding: 6px 10px; font-size: 11px;
  background: rgba(245,241,232,0.9); border: 1px solid rgba(0,0,0,0.05);
  border-top: none; border-radius: 0 0 10px 10px;
}
</style>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  data: { type: Object, default: null },
  themeColor: { type: String, default: '#2B4C7E' },
})
const router = useRouter()
const hover = ref(null)
const containerRef = ref(null)
const svgRef = ref(null)

// 动态画布尺寸（根据容器实际大小自适应）
const viewW = ref(560)
const viewH = ref(300)
const uid = Math.floor(Math.random() * 1e6)

// 自适应缩放状态
const customZoom = ref(1)  // 用户通过滚轮调整的额外缩放
const MIN_CUSTOM_ZOOM = 0.5
const MAX_CUSTOM_ZOOM = 3

function typeLabel(t) { return t === '句内' ? '句内共现' : t === '跨句' ? '跨句共现' : '全诗共现' }
function dashOf(t) { return t === '句内' ? '' : t === '跨句' ? '7 5' : '2 5' }
function nodeRadius(name, samePoem) {
  const base = 11 + Math.min(7, samePoem ? Math.log2(samePoem + 1) * 1.2 : 2.5)
  return Math.max(11, Math.min(19, base))
}
function nodeFont(name) { return name.length > 2 ? 9 : name.length === 2 ? 10 : 12 }
function centerFont(name) { return name.length > 3 ? 16 : name.length === 3 ? 18 : 22 }

function applyRepulsion(nodes, opts = {}) {
  const {
    iterations = 20,
    minDist = 24,
    damping = 0.82,
    bounds = { minX: 0, maxX: viewW.value, minY: 0, maxY: viewH.value, padding: 15 },
  } = opts

  const pos = {}
  const vel = {}
  for (const n of nodes) {
    pos[n.id] = { x: n.x, y: n.y }
    vel[n.id] = { x: 0, y: 0 }
  }

  const minD2 = minDist * minDist
  const padding = bounds.padding

  for (let iter = 0; iter < iterations; iter++) {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j]
        if (a.isCenter || a.isBridge) continue
        if (b.isCenter || b.isBridge) continue

        const dx = pos[a.id].x - pos[b.id].x
        const dy = pos[a.id].y - pos[b.id].y
        const d2 = dx * dx + dy * dy
        if (d2 < minD2 && d2 > 0.001) {
          const d = Math.sqrt(d2)
          const force = (minDist - d) / d * 0.5
          const fx = dx * force
          const fy = dy * force
          vel[a.id].x += fx
          vel[a.id].y += fy
          vel[b.id].x -= fx
          vel[b.id].y -= fy
        }
      }
    }

    for (const n of nodes) {
      if (n.isCenter || n.isBridge) continue

      vel[n.id].x *= damping
      vel[n.id].y *= damping

      pos[n.id].x += vel[n.id].x
      pos[n.id].y += vel[n.id].y

      if (pos[n.id].x < bounds.minX + padding) {
        pos[n.id].x = bounds.minX + padding
        vel[n.id].x *= -0.5
      }
      if (pos[n.id].x > bounds.maxX - padding) {
        pos[n.id].x = bounds.maxX - padding
        vel[n.id].x *= -0.5
      }
      if (pos[n.id].y < bounds.minY + padding) {
        pos[n.id].y = bounds.minY + padding
        vel[n.id].y *= -0.5
      }
      if (pos[n.id].y > bounds.maxY - padding) {
        pos[n.id].y = bounds.maxY - padding
        vel[n.id].y *= -0.5
      }
    }
  }

  return nodes.map((n) => ({
    ...n,
    x: pos[n.id].x,
    y: pos[n.id].y,
  }))
}

const graph = computed(() => {
  const d = props.data
  if (!d || !d.edges?.length) return null
  const nodes = d.nodes || []
  const center = nodes.find((n) => n.center)
  const centerId = center?.id
  if (!centerId) return null

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

  const bridgeIds = containEdges.map((e) => e.target)
  const bridgeIdSet = new Set(bridgeIds)

  const bridgeChildrenMap = {}
  for (const bid of bridgeIds) bridgeChildrenMap[bid] = []
  for (const e of bridgeEdges) {
    if (bridgeIdSet.has(e.source)) {
      bridgeChildrenMap[e.source].push(e.target)
    }
  }

  const directTargets = directEdges.map((e) => e.target)

  const cx = viewW.value / 2, cy = viewH.value / 2
  const padding = 25

  // 计算总节点数以动态调整半径
  const totalNodes = containEdges.length + bridgeEdges.length + directEdges.length + 1

  // 动态计算半径，预留边界空间
  const maxRadiusX = (viewW.value / 2) - padding - 22 - 16
  const maxRadiusY = (viewH.value / 2) - padding - 22 - 16

  // 根据节点数量调整半径
  const scaleFactor = Math.min(1, 35 / Math.max(totalNodes, 20))
  const BRIDGE_RX = Math.max(35, maxRadiusX * 0.55 * scaleFactor)
  const BRIDGE_RY = Math.max(28, maxRadiusY * 0.55 * scaleFactor)
  const LEAF_RX = Math.max(55, maxRadiusX * 0.88 * scaleFactor)
  const LEAF_RY = Math.max(42, maxRadiusY * 0.88 * scaleFactor)

  const allGroups = []
  for (const bid of bridgeIds) allGroups.push({ id: bid, type: 'bridge', children: bridgeChildrenMap[bid] || [] })
  if (directTargets.length > 0) allGroups.push({ id: '__direct__', type: 'direct', children: directTargets })

  const pos = { [centerId]: { x: cx, y: cy } }

  const totalGroups = allGroups.length
  allGroups.forEach((g, gi) => {
    const angle = (gi / totalGroups) * Math.PI * 2 - Math.PI / 2
    const cosA = Math.cos(angle)
    const sinA = Math.sin(angle)

    if (g.type === 'bridge') {
      const bx = cx + BRIDGE_RX * cosA
      const by = cy + BRIDGE_RY * sinA
      pos[g.id] = { x: bx, y: by }

      const children = g.children
      if (children.length > 0) {
        const spreadAngle = Math.min(Math.PI * 1.0, children.length * 0.28)
        const startAngle = angle - spreadAngle / 2
        const angleStep = children.length > 1 ? spreadAngle / (children.length - 1) : 0

        children.forEach((cid, ci) => {
          const ca = children.length === 1 ? angle : startAngle + ci * angleStep
          pos[cid] = {
            x: cx + LEAF_RX * Math.cos(ca),
            y: cy + LEAF_RY * Math.sin(ca),
          }
        })
      }
    } else {
      const children = g.children
      if (children.length > 0) {
        const spreadAngle = Math.min(Math.PI * 1.0, children.length * 0.28)
        const startAngle = angle - spreadAngle / 2
        const angleStep = children.length > 1 ? spreadAngle / (children.length - 1) : 0

        children.forEach((cid, ci) => {
          const ca = children.length === 1 ? angle : startAngle + ci * angleStep
          pos[cid] = {
            x: cx + LEAF_RX * Math.cos(ca),
            y: cy + LEAF_RY * Math.sin(ca),
          }
        })
      }
    }
  })

  const bridgeChildrenEdges = []
  const childEdgeSet = new Set()
  for (const e of bridgeEdges) {
    const srcIsBridge = bridgeIdSet.has(e.source)
    const tgtIsBridge = bridgeIdSet.has(e.target)
    if (srcIsBridge || tgtIsBridge) {
      bridgeChildrenEdges.push({
        ...e,
        bridgeSrc: srcIsBridge ? e.source : e.target,
        childId: srcIsBridge ? e.target : e.source,
      })
      childEdgeSet.add(srcIsBridge ? e.target : e.source)
    }
  }

  const nodeList = []
  const includedIds = new Set([centerId])
  for (const id of Object.keys(pos)) {
    if (id === centerId) continue
    const meta = nodes.find((nd) => nd.id === id)
    const edge = d.edges.find((e) =>
      (e.source === centerId && e.target === id) ||
      (bridgeIdSet.has(e.source) && e.target === id)
    )
    if (!edge && !meta) continue

    const name = meta?.name || edge?.name || id
    const color = meta?.theme_color || '#8A6D3B'
    const isBridge = bridgeIdSet.has(id)
    const r = isBridge
      ? Math.max(11, Math.min(16, 12 + (edge?.same_poem ? Math.log2(edge.same_poem + 1) : 1.5)))
      : Math.max(9, Math.min(14, 10 + (edge?.same_poem ? Math.log2(edge.same_poem + 1) : 1.2)))

    nodeList.push({
      id, name, x: pos[id].x, y: pos[id].y, r,
      color, concept_id: edge?.concept_id || meta?.concept_id,
      font: nodeFont(name),
      isCenter: false,
      isBridge,
    })
    includedIds.add(id)
  }

  const repulsedNodes = applyRepulsion(nodeList, {
    iterations: 25,
    minDist: 16,
    damping: 0.82,
    bounds: { minX: 0, maxX: viewW.value, minY: 0, maxY: viewH.value, padding: 22 },
  })

  const finalNodes = repulsedNodes.map((n) => ({ ...n }))
  const nodeMap = {}
  for (const n of finalNodes) nodeMap[n.id] = n

  const geoEdges = []
  const centerNode = { x: cx, y: cy, r: 22 }

  for (const e of d.edges) {
    const isContain = e.relation_type === '包含'
    const srcId = e.source
    const tgtId = e.target

    let srcNode, tgtNode
    if (srcId === centerId) {
      srcNode = centerNode
      tgtNode = nodeMap[tgtId]
    } else {
      srcNode = nodeMap[srcId]
      tgtNode = nodeMap[tgtId]
    }

    if (!srcNode || !tgtNode) continue

    const srcR = srcNode.r || 10
    const tgtR = tgtNode.r || 10
    const dx = tgtNode.x - srcNode.x
    const dy = tgtNode.y - srcNode.y
    const len = Math.hypot(dx, dy) || 1
    const ux = dx / len, uy = dy / len
    const x1 = srcNode.x + ux * (srcR + 2)
    const y1 = srcNode.y + uy * (srcR + 2)
    const x2 = tgtNode.x - ux * (tgtR + 2)
    const y2 = tgtNode.y - uy * (tgtR + 2)

    const isCurveEdge = (srcId === centerId || tgtId === centerId) && !isContain

    let pathD
    if (isCurveEdge) {
      const nx = -uy, ny = ux
      const curveAmt = Math.min(25, len * 0.25)
      const mx = (x1 + x2) / 2 + nx * curveAmt
      const my = (y1 + y2) / 2 + ny * curveAmt
      pathD = `M${x1},${y1} Q${mx},${my} ${x2},${y2}`
    } else {
      pathD = `M${x1},${y1} L${x2},${y2}`
    }

    geoEdges.push({
      ...e,
      pathD,
      opacity: isContain ? 0.55 : 0.85,
      width: isContain ? 1 : 1.8,
      dash: dashOf(e.relation_type),
      isContain,
    })
  }

  const containCount = containEdges.length
  const directCount = directEdges.length
  const bridgeCount = bridgeChildrenEdges.length

  return {
    centerX: cx,
    centerY: cy,
    centerR: 22,
    centerName: center.name,
    centerFont: centerFont(center.name),
    nodes: finalNodes,
    edges: geoEdges,
    stats: {
      contain: containCount,
      direct: directCount,
      bridge: bridgeCount,
      total: containCount + directCount + bridgeCount,
    },
  }
})

// 计算所有节点的边界框
const bounds = computed(() => {
  if (!graph.value) return { minX: 0, minY: 0, maxX: viewW.value, maxY: viewH.value }
  const allX = [graph.value.centerX, ...graph.value.nodes.map(n => n.x)]
  const allY = [graph.value.centerY, ...graph.value.nodes.map(n => n.y)]
  const allR = [graph.value.centerR, ...graph.value.nodes.map(n => n.r)]

  let minX = Math.min(...allX)
  let minY = Math.min(...allY)
  let maxX = Math.max(...allX)
  let maxY = Math.max(...allY)
  const maxR = Math.max(...allR)

  // 扩展边界以包含节点半径
  minX -= maxR + 4
  minY -= maxR + 4
  maxX += maxR + 4
  maxY += maxR + 4

  return { minX, minY, maxX, maxY }
})

// 自适应变换：缩放并居中所有节点
const fitTransform = computed(() => {
  const b = bounds.value
  const graphW = b.maxX - b.minX
  const graphH = b.maxY - b.minY

  // 计算可用空间（SVG viewBox 尺寸）
  const availW = viewW.value
  const availH = viewH.value

  // 计算缩放比例，使所有节点适配画布
  const padding = 20
  const scaleX = (availW - padding * 2) / graphW
  const scaleY = (availH - padding * 2) / graphH
  const autoScale = Math.min(scaleX, scaleY, 1)  // 不放大，只缩小

  // 应用用户自定义缩放
  const finalScale = autoScale * customZoom.value

  // 计算居中偏移
  const graphCenterX = (b.minX + b.maxX) / 2
  const graphCenterY = (b.minY + b.maxY) / 2

  // 先平移到原点，再缩放，再平移到画布中心
  const tx = viewW.value / 2 - graphCenterX * finalScale
  const ty = viewH.value / 2 - graphCenterY * finalScale

  return `translate(${tx},${ty}) scale(${finalScale})`
})

// 监听容器尺寸变化
function updateContainerSize() {
  if (!containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  const footHeight = 40  // 底部详情条高度
  const svgH = rect.height - footHeight
  // 使用实际容器尺寸作为 viewBox
  viewW.value = Math.max(100, Math.round(rect.width))
  viewH.value = Math.max(80, Math.round(svgH))
}

let resizeObserver = null

onMounted(() => {
  nextTick(() => {
    updateContainerSize()
    resizeObserver = new ResizeObserver(updateContainerSize)
    if (containerRef.value) {
      resizeObserver.observe(containerRef.value)
    }
  })
})

onUnmounted(() => {
  if (resizeObserver) resizeObserver.disconnect()
})

watch(() => props.data, () => {
  customZoom.value = 1  // 数据变化时重置缩放
}, { deep: true })

function onWheel(e) {
  const delta = e.deltaY > 0 ? 0.9 : 1.1
  customZoom.value = Math.max(MIN_CUSTOM_ZOOM, Math.min(MAX_CUSTOM_ZOOM, customZoom.value * delta))
}

const hoverNode = computed(() => {
  if (!hover.value || !graph.value) return null
  const n = graph.value.nodes.find((n) => n.id === hover.value)
  if (!n) return null
  const edge = props.data?.edges?.find((e) =>
    (e.source === props.data?.nodes?.find((nd) => nd.center)?.id && e.target === n.id) ||
    e.source === n.id
  )
  return { node: n, edge }
})

function active(n) {
  return hover.value === n.id
}

function clickNode(n) {
  if (n.concept_id) {
    router.push(`/concept/${n.concept_id}`)
  }
}
</script>
