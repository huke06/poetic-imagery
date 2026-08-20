<!--
  金叶集 — 左下角悬浮探索记录面板
  宣纸底 + 金叶 + 脉络连线 · rAF 渲染无抖动
  v2：多字意象完整显示 + 主题族进度 + 分享意象地图
-->
<template>
  <div class="leaf-root" :style="{ bottom: bottom + 'px' }">
    <!-- Collapsed -->
    <Transition name="swap">
      <button v-if="!open" class="leaf-collapsed" :class="{ 'leaf-pulse': pulse }"
        @pointerdown="onPointerDown" @click="onBtnClick" title="金叶集（可拖拽移动）">
        <img src="/jinyeji-logo.png" alt="金叶集" class="w-10 h-10 object-contain" />
        <span v-if="list.length" class="leaf-badge">{{ list.length }}</span>
      </button>
    </Transition>

    <!-- Expanded -->
    <Transition name="panel">
      <div v-if="open" ref="cardEl" class="leaf-card">
        <div class="leaf-head" @pointerdown="onPointerDown" title="拖拽移动">
          <span class="font-kai text-sm font-bold tracking-wider text-moyan/80">
            金叶集 · 已探 <b class="text-zheshi">{{ list.length }}</b> 象
          </span>
          <div class="flex items-center gap-1">
            <button class="leaf-btn no-drag" @click.stop="zoomIn">+</button>
            <button class="leaf-btn no-drag" @click.stop="zoomOut">−</button>
            <button class="leaf-btn no-drag" @click.stop="open = false">─</button>
          </div>
        </div>

        <!-- Achievement badges -->
        <div v-if="achievements.length" class="flex gap-1.5 px-4 py-2 border-b border-black/5">
          <span v-for="a in achievements" :key="a.id"
            class="text-[10px] px-1.5 py-0.5 rounded border"
            :style="{ color: '#9B6820', borderColor: '#C8983844', background: '#FDF5E6' }"
            :title="a.desc">{{ a.icon }} {{ a.name }}</span>
        </div>

        <!-- 主题族进度 -->
        <div v-if="themeChips.length" class="flex flex-wrap gap-1 px-4 py-1.5 border-b border-black/5">
          <span v-for="t in themeChips" :key="t.name"
            class="text-[9px] px-1.5 py-0.5 rounded-full text-white leading-4"
            :style="{ background: t.color }">{{ t.name }} · {{ t.count }}</span>
        </div>

        <canvas ref="cvs"
          class="leaf-cvs"
          @mousedown="onDown" @mousemove="onMove" @mouseup="onUp" @mouseleave="onUp"
          @wheel.prevent="onWheel" @dblclick="onDbl"></canvas>

        <div v-if="hover" class="leaf-foot">
          <span class="font-kai text-sm font-bold" style="color:#9B6820">{{ hover.name }}</span>
          <span class="mx-1.5 text-qianhui/40">|</span>
          <span class="text-[10px] text-qianhui">{{ hover.theme }}</span>
          <span class="mx-1 text-qianhui/30">|</span>
          <span class="text-[10px] text-qianhui">{{ hover.poetryCount != null ? '收录' + hover.poetryCount + '首诗' : '' }}</span>
        </div>
        <div v-else class="leaf-foot text-qianhui/40 text-[10px]">
          滚轮缩放 · 拖拽平移 · 悬停叶面 · 双击前往
        </div>

        <div class="leaf-actions">
          <button class="leaf-share no-drag" @click.stop="shareMap">✦ 分享意象地图</button>
        </div>
      </div>
    </Transition>

    <!-- 分享预览弹窗 -->
    <Teleport to="body">
      <div v-if="shareOpen" class="fixed inset-0 z-[120] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
        @click.self="shareOpen = false">
        <div class="bg-xuanzhi rounded-lg max-w-2xl w-full max-h-[92vh] overflow-y-auto p-4">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-song font-bold text-lg">我的意象地图</h3>
            <button class="w-8 h-8 rounded-full hover:bg-black/5 text-xl" @click="shareOpen = false">×</button>
          </div>
          <div v-if="shareBusy" class="py-16 text-center text-qianhui text-sm">生成中…</div>
          <div v-else-if="!shareSvg" class="py-16 text-center text-qianhui text-sm">生成失败，请稍后再试。</div>
          <img v-else :src="shareUrl" class="w-full rounded shadow-card" alt="我的意象地图" />
          <div class="flex gap-2 mt-4 justify-center">
            <button class="btn-primary !py-1.5 !text-xs" @click="downloadPng">下载 PNG</button>
            <button class="btn-outline !py-1.5 !text-xs" @click="downloadSvg">下载 SVG</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { useExploredImageries } from '../composables/useExploredImageries'
import { useSideDrag } from '../composables/useSideDrag'
import { downloadDataUrl, downloadText, svgDataUrl, svgToPngDataUrl } from '../utils/share'

const { exploredList: list, newCount, achievements, themeProgress, consumeNew } = useExploredImageries()
const router = useRouter()

const open = ref(false)
const cardEl = ref(null)
// 动态测量面板真实高度，收紧上限避免顶部溢出（否则拖到上半部分后展开无法移动）
const { bottom, onPointerDown, wasDragged, reclamp } = useSideDrag(
  'sxz_leaf_float_pos', 20,
  () => (window.innerHeight || 800) - (open.value ? (cardEl.value?.offsetHeight || 560) : 70) - 8)
watch(open, async () => { await nextTick(); reclamp() })

const pulse = ref(false)
const cvs = ref(null)
const hover = ref(null)

const dpr = Math.min(window.devicePixelRatio || 1, 2)
const VW = 310, VH = 330

// 主题族进度 chips
const themeChips = computed(() => Object.entries(themeProgress.value)
  .map(([name, v]) => ({ name, color: v.color || '#B5352C', count: v.explored }))
  .sort((a, b) => b.count - a.count))

// 分享
const shareOpen = ref(false)
const shareBusy = ref(false)
const shareSvg = ref('')
const shareUrl = computed(() => (shareSvg.value ? svgDataUrl(shareSvg.value) : ''))

async function shareMap() {
  shareOpen.value = true
  shareBusy.value = true
  shareSvg.value = ''
  try {
    const explored = list.value.map((e) => ({
      name: e.name, theme: e.theme, themeColor: e.themeColor, poetryCount: e.poetryCount,
    }))
    const resp = await axios.post('/api/concept/exploration-card', { explored, theme_count: themeChips.value.length })
    shareSvg.value = typeof resp.data === 'string' ? resp.data : ''
  } catch { shareSvg.value = '' }
  finally { shareBusy.value = false }
}
function downloadPng() {
  if (!shareSvg.value) return
  svgToPngDataUrl(shareSvg.value, 720).then((u) => downloadDataUrl(u, '我的意象地图.png'))
}
function downloadSvg() {
  if (shareSvg.value) downloadText(shareSvg.value, '我的意象地图.svg')
}

// View state
let zoom = 1, tx = 0, ty = 0
let dragging = false, dsx = 0, dsy = 0, otx = 0, oty = 0
let dirty = true
let leaves = []
let timer = null
let rid = 0

/* ─────────── Elegant pointed leaf ─────────── */
function leafPath(ctx, s) {
  ctx.beginPath()
  ctx.moveTo(0, -s * 0.62)  // tip
  ctx.bezierCurveTo(s * 0.42, -s * 0.32, s * 0.38, s * 0.12, 0, s * 0.18)  // right
  ctx.bezierCurveTo(-s * 0.38, s * 0.12, -s * 0.42, -s * 0.32, 0, -s * 0.62) // left
  ctx.closePath()
}

function drawLeaf(ctx, x, y, s, rot) {
  ctx.save()
  ctx.translate(x, y)
  ctx.rotate(rot)

  leafPath(ctx, s)

  // Warm gold gradient
  const g = ctx.createLinearGradient(0, -s * 0.62, 0, s * 0.18)
  g.addColorStop(0, '#F4DC80')
  g.addColorStop(0.25, '#DEB445')
  g.addColorStop(0.6, '#C59328')
  g.addColorStop(0.85, '#A07015')
  g.addColorStop(1, '#7B5208')
  ctx.fillStyle = g
  ctx.fill()

  // Edge
  ctx.strokeStyle = 'rgba(110,68,10,0.22)'
  ctx.lineWidth = 0.45
  ctx.stroke()

  // Center vein
  ctx.beginPath()
  ctx.moveTo(0, -s * 0.58)
  ctx.lineTo(0, s * 0.16)
  ctx.strokeStyle = 'rgba(120,72,10,0.12)'
  ctx.lineWidth = 0.25
  ctx.stroke()

  // Side veins
  for (let i = -3; i <= 3; i++) {
    if (i === 0) continue
    ctx.beginPath()
    ctx.moveTo(0, s * 0.02 - Math.abs(i) * s * 0.06)
    ctx.quadraticCurveTo(i * s * 0.06, -s * 0.05 - Math.abs(i) * s * 0.04,
      i * s * 0.14, -s * 0.25 - Math.abs(i) * s * 0.07)
    ctx.strokeStyle = 'rgba(120,72,10,0.08)'
    ctx.lineWidth = 0.18
    ctx.stroke()
  }

  // Stem
  ctx.beginPath()
  ctx.moveTo(0, s * 0.17)
  ctx.lineTo(0, s * 0.55)
  ctx.strokeStyle = 'rgba(90,48,4,0.32)'
  ctx.lineWidth = 0.55
  ctx.stroke()

  ctx.restore()
}

function drawName(ctx, x, y, name) {
  const n = name.length
  const size = n <= 1 ? 16 : n === 2 ? 13 : 10
  ctx.font = 'bold ' + size + 'px "Kaiti SC","STKaiti","KaiTi","Noto Serif SC",serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.lineJoin = 'round'
  // 先描一圈浅色光晕，再用深棕填充，保证在金色叶片上清晰可读
  ctx.lineWidth = 3
  ctx.strokeStyle = 'rgba(253,249,242,0.85)'
  ctx.strokeText(name, x, y - 2)
  ctx.fillStyle = '#3A2506'
  ctx.fillText(name, x, y - 2)
}

/* ─────────── Render ─────────── */
function render() {
  const el = cvs.value; if (!el) return
  const ctx = el.getContext('2d')
  el.width = VW * dpr; el.height = VH * dpr
  el.style.width = VW + 'px'; el.style.height = VH + 'px'
  ctx.scale(dpr, dpr)

  // Paper
  ctx.fillStyle = '#F5F1E8'
  ctx.fillRect(0, 0, VW, VH)
  ctx.fillStyle = 'rgba(195,178,148,0.035)'
  for (let i = 0; i < 10; i++) ctx.fillRect(Math.random() * VW, Math.random() * VH, Math.random() * 35 + 10, 0.25)

  const items = list.value
  if (!items.length) {
    ctx.fillStyle = '#B0A590'
    ctx.font = '14px "Kaiti SC","STKaiti","KaiTi",serif'
    ctx.textAlign = 'center'
    ctx.fillText('未有落叶', VW / 2, VH / 2 - 10)
    ctx.fillText('探索意象来收集吧', VW / 2, VH / 2 + 16)
    leaves = []
    return
  }

  // Apply view
  ctx.save()
  ctx.translate(tx, ty)
  ctx.scale(zoom, zoom)

  // Layout：黄金角螺旋，意象再多也能均匀铺开、互不遮挡
  const cx = VW / 2, cy = VH / 2
  const golden = Math.PI * (3 - Math.sqrt(5))
  leaves = items.map((item, i) => {
    const a = i * golden
    const r = Math.min(28 + Math.sqrt(i) * 27, 130)
    const name = item.name || '?'
    return {
      id: item.id, name, theme: item.theme || '—',
      poetryCount: item.poetryCount, at: item.exploredAt,
      size: 24 + Math.max(0, name.length - 1) * 4,
      x: Math.max(46, Math.min(VW - 46, cx + Math.cos(a) * r + (Math.random() - 0.5) * 5)),
      y: Math.max(52, Math.min(VH - 38, cy + Math.sin(a) * r * 0.82 + (Math.random() - 0.5) * 4)),
      rot: (Math.random() - 0.5) * 0.4,
    }
  })

  // Solid: exploration order
  ctx.strokeStyle = 'rgba(170,130,55,0.35)'
  ctx.lineWidth = 1.2 / zoom
  for (let i = 0; i < leaves.length - 1; i++) {
    ctx.beginPath(); ctx.moveTo(leaves[i].x, leaves[i].y); ctx.lineTo(leaves[i + 1].x, leaves[i + 1].y); ctx.stroke()
  }

  // Dashed: same theme
  ctx.strokeStyle = 'rgba(150,110,40,0.2)'
  ctx.lineWidth = 0.7 / zoom
  ctx.setLineDash([3 / zoom, 6 / zoom])
  for (let i = 0; i < leaves.length; i++) {
    for (let j = i + 1; j < leaves.length; j++) {
      if (leaves[i].theme === leaves[j].theme) {
        ctx.beginPath(); ctx.moveTo(leaves[i].x, leaves[i].y); ctx.lineTo(leaves[j].x, leaves[j].y); ctx.stroke()
      }
    }
  }
  ctx.setLineDash([])

  // Leaves (自适应大小 + 完整意象名)
  for (const lf of leaves) {
    drawLeaf(ctx, lf.x, lf.y, lf.size, lf.rot)
    drawName(ctx, lf.x, lf.y, lf.name)
  }

  ctx.restore()
  dirty = false
}

/* ─────────── Hit test ─────────── */
function hit(se) {
  const r = cvs.value?.getBoundingClientRect(); if (!r) return null
  const sx = (se.clientX - r.left - tx) / zoom
  const sy = (se.clientY - r.top - ty) / zoom
  for (const lf of leaves) {
    if (Math.hypot(sx - lf.x, sy - lf.y) < Math.max(26, lf.size) * 1.3) return lf
  }
  return null
}

/* ─────────── Events ─────────── */
function onDown(e) { dragging = true; dsx = e.clientX; dsy = e.clientY; otx = tx; oty = ty }
function onMove(e) {
  if (dragging) { tx = otx + (e.clientX - dsx); ty = oty + (e.clientY - dsy); dirty = true }
  hover.value = hit(e) || null
  if (cvs.value) cvs.value.style.cursor = hover.value ? 'pointer' : dragging ? 'grabbing' : 'grab'
}
function onUp() { dragging = false }
function onWheel(e) {
  const r = cvs.value?.getBoundingClientRect(); if (!r) return
  const mx = e.clientX - r.left, my = e.clientY - r.top
  const ds = e.deltaY > 0 ? 0.9 : 1.1
  const ns = Math.max(0.45, Math.min(3, zoom * ds))
  tx = mx - (mx - tx) * (ns / zoom)
  ty = my - (my - ty) * (ns / zoom)
  zoom = ns
  dirty = true
}
function onDbl(e) {
  const lf = hit(e)
  if (lf) { open.value = false; router.push('/concept/' + lf.id) }
}
function zoomIn() { zoom = Math.min(3, zoom * 1.2); dirty = true }
function zoomOut() { zoom = Math.max(0.45, zoom / 1.2); dirty = true }

/* ─────────── Panel ─────────── */
function doOpen() { open.value = true; pulse.value = false; consumeNew(); tx = 0; ty = 0; zoom = 1; dirty = true }

// 区分点击与拖拽：拖拽后不触发打开
function onBtnClick() { if (!wasDragged()) doOpen() }

watch(newCount, (v) => {
  if (v > 0 && !open.value) {
    pulse.value = true; open.value = true; consumeNew(); tx = 0; ty = 0; zoom = 1; dirty = true
    clearTimeout(timer)
    timer = setTimeout(() => { if (open.value) { open.value = false; pulse.value = false } }, 4000)
  }
  if (open.value) dirty = true
})
watch(list, () => { if (open.value) dirty = true }, { deep: true })

/* ─────────── rAF loop ─────────── */
function loop() {
  if (dirty) render()
  rid = requestAnimationFrame(loop)
}
onMounted(() => { rid = requestAnimationFrame(loop) })
onBeforeUnmount(() => cancelAnimationFrame(rid))
</script>

<style scoped>
.leaf-root { position: fixed; left: 20px; z-index: 80; }
.leaf-collapsed {
  position: relative; width: 52px; height: 52px;
  display: flex; align-items: center; justify-content: center;
  background: transparent; border: none; border-radius: 14px;
  box-shadow: 0 4px 18px rgba(80,55,20,0.18); cursor: grab; transition: box-shadow .3s;
  user-select: none; touch-action: none;
}
.leaf-collapsed:active { cursor: grabbing; }
.leaf-collapsed:hover { box-shadow: 0 6px 24px rgba(80,55,20,0.25); }
.leaf-pulse { animation: lp .5s ease-in-out 3; }
@keyframes lp { 0%,100%{box-shadow:0 2px 16px rgba(100,70,20,.1)} 50%{box-shadow:0 2px 28px rgba(200,152,56,.5)} }
.leaf-badge {
  position: absolute; top: -8px; right: -8px; min-width: 22px; height: 22px;
  display: flex; align-items: center; justify-content: center;
  background: #B5352C; color: #F5F1E8; font-size: 12px; font-weight: 700;
  font-family: 'Cormorant Garamond',serif; border-radius: 11px; padding: 0 6px;
  box-shadow: 0 2px 8px rgba(181,53,44,.35);
}
.leaf-card {
  width: 340px; background: rgba(245,241,232,0.95); backdrop-filter: blur(14px);
  border: 1px solid rgba(160,135,100,0.25); border-radius: 12px;
  box-shadow: 0 10px 40px rgba(80,55,20,0.13); overflow: hidden;
}
.leaf-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px 8px; border-bottom: 1px solid rgba(160,135,100,0.15);
  cursor: grab; user-select: none; touch-action: none;
}
.leaf-head:active { cursor: grabbing; }
.leaf-btn {
  font-size: 15px; color: #9A8B70; cursor: pointer; width: 26px; height: 26px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 4px; border: none; background: none; transition: all .15s;
}
.leaf-btn:hover { background: rgba(0,0,0,0.05); color: #6B5B40; }
.leaf-cvs { display: block; width: 310px; height: 330px; margin: 0 auto; cursor: grab; }
.leaf-foot {
  padding: 8px 16px 6px; text-align: center;
  border-top: 1px solid rgba(160,135,100,0.1);
  min-height: 32px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.leaf-actions { padding: 6px 16px 10px; text-align: center; border-top: 1px solid rgba(160,135,100,0.08); }
.leaf-share {
  font-size: 12px; color: #9B6820; cursor: pointer; padding: 5px 14px;
  border: 1px solid rgba(200,152,56,0.35); border-radius: 999px;
  background: rgba(200,152,56,0.06); transition: all .2s;
}
.leaf-share:hover { background: rgba(200,152,56,0.14); border-color: #C89838; }
.swap-enter-active,.swap-leave-active{transition:all .2s}
.swap-enter-from,.swap-leave-to{opacity:0;transform:scale(.75)}
.panel-enter-active{transition:all .25s cubic-bezier(.16,1,.3,1)}
.panel-leave-active{transition:all .2s}
.panel-enter-from{opacity:0;transform:translateY(14px) scale(.94)}
.panel-leave-to{opacity:0;transform:translateY(8px) scale(.96)}
</style>
