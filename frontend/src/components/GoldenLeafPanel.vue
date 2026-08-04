<!--
  金叶集 — 左下角悬浮探索记录面板
  宣纸底 + 金叶 + 脉络连线 · rAF 渲染无抖动
-->
<template>
  <div class="leaf-root" :style="{ bottom: bottom + 'px' }">
    <!-- Collapsed -->
    <Transition name="swap">
      <button v-if="!open" class="leaf-collapsed" :class="{ 'leaf-pulse': pulse }"
        @pointerdown="onPointerDown" @click="onBtnClick" title="金叶集（可拖拽移动）">
        <svg width="42" height="46" viewBox="0 0 44 52">
          <path d="M22 3 C9 3 1 13 1 25 C1 30 3 35 8 39 L22 52 L36 39 C41 35 43 30 43 25 C43 13 35 3 22 3Z"
            fill="#C89838" stroke="#8B6910" stroke-width="0.9"/>
          <line x1="22" y1="15" x2="22" y2="33" stroke="#8B6910" stroke-width="0.7"/>
        </svg>
        <span v-if="list.length" class="leaf-badge">{{ list.length }}</span>
      </button>
    </Transition>

    <!-- Expanded -->
    <Transition name="panel">
      <div v-if="open" class="leaf-card">
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
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useExploredImageries } from '../composables/useExploredImageries'
import { useSideDrag } from '../composables/useSideDrag'

const { exploredList: list, newCount, achievements, themeProgress, consumeNew } = useExploredImageries()
const router = useRouter()

const open = ref(false)
// 展开面板高约 460，收紧上限避免顶部溢出
const { bottom, onPointerDown, wasDragged, reclamp } = useSideDrag(
  'sxz_leaf_float_pos', 20, () => (window.innerHeight || 800) - (open.value ? 480 : 70))
watch(open, reclamp)

const pulse = ref(false)
const cvs = ref(null)
const hover = ref(null)

const dpr = Math.min(window.devicePixelRatio || 1, 2)
const VW = 310, VH = 330

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

function drawChar(ctx, x, y, ch) {
  ctx.fillStyle = '#FDF9F2'
  ctx.font = `bold 16px "Kaiti SC","STKaiti","KaiTi","Noto Serif SC",serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.shadowColor = 'rgba(70,32,3,0.18)'
  ctx.shadowBlur = 1.2
  ctx.fillText(ch, x, y - 2)
  ctx.shadowBlur = 0
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

  // Layout
  const cx = VW / 2, cy = VH / 2
  leaves = items.map((item, i) => {
    const a = i * 1.7 + (i > 5 ? 0.45 : 0)
    const r = Math.min(26 + i * 17 + (i > 6 ? (i - 6) * 10 : 0), 115)
    return {
      id: item.id, name: item.name, theme: item.theme || '—',
      poetryCount: item.poetryCount, at: item.exploredAt,
      x: Math.max(44, Math.min(VW - 44, cx + Math.cos(a) * r + (Math.random() - 0.5) * 8)),
      y: Math.max(50, Math.min(VH - 36, cy + Math.sin(a) * r * 0.62 + (Math.random() - 0.5) * 5)),
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

  // Leaves (size 24)
  for (const lf of leaves) {
    drawLeaf(ctx, lf.x, lf.y, 24, lf.rot)
    drawChar(ctx, lf.x, lf.y, lf.name.charAt(0))
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
    if (Math.hypot(sx - lf.x, sy - lf.y) < 24 * 1.25) return lf
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
  if (lf) { open.value = false; router.push(`/concept/${lf.id}`) }
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
  background: rgba(245,241,232,0.88); backdrop-filter: blur(10px);
  border: 1px solid rgba(180,150,100,0.3); border-radius: 14px;
  box-shadow: 0 2px 16px rgba(100,70,20,0.1); cursor: grab; transition: box-shadow .3s, background .3s;
  user-select: none; touch-action: none;
}
.leaf-collapsed:active { cursor: grabbing; }
.leaf-collapsed:hover { background: rgba(245,241,232,0.97); box-shadow: 0 6px 24px rgba(100,70,20,0.18); }
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
  padding: 8px 16px 10px; text-align: center;
  border-top: 1px solid rgba(160,135,100,0.1);
  min-height: 32px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.swap-enter-active,.swap-leave-active{transition:all .2s}
.swap-enter-from,.swap-leave-to{opacity:0;transform:scale(.75)}
.panel-enter-active{transition:all .25s cubic-bezier(.16,1,.3,1)}
.panel-leave-active{transition:all .2s}
.panel-enter-from{opacity:0;transform:translateY(14px) scale(.94)}
.panel-leave-to{opacity:0;transform:translateY(8px) scale(.96)}
</style>
