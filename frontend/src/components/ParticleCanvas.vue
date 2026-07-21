<template>
  <canvas ref="el" class="absolute inset-0 w-full h-full pointer-events-none" :style="{ opacity }"></canvas>
</template>

<script setup>
/**
 * 国风粒子画布
 * mode: moon(月辉·银尘上浮闪烁) / sunset(夕照·暖烬斜落) / willow(柳絮·摇曳飘落)
 *       petal(花瓣·旋转飘坠) / ink(淡墨·墨点缓升)
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  mode: { type: String, default: 'ink' },
  density: { type: Number, default: 1 },   // 密度系数
  opacity: { type: Number, default: 1 },
})

const el = ref(null)
let raf = 0
let particles = []
let ctx = null
let W = 0
let H = 0
let observer = null
let visible = true
let io = null

const PALETTES = {
  moon: { colors: ['#E8ECF5', '#C9D6EA', '#F5F1E8', '#A8BEDC'], glow: true },
  sunset: { colors: ['#E8A05C', '#D97E4A', '#F5C396', '#C96A3A'], glow: true },
  willow: { colors: ['#D9E8CF', '#B8D4A8', '#EAF2E0', '#9FC48F'], glow: false },
  petal: { colors: ['#E8C4C4', '#DCA8B0', '#F0D8D0', '#D49AA8'], glow: false },
  ink: { colors: ['#4A5A6A', '#3A4A5A', '#5A6B7A'], glow: false },
}

function spawn(initial = false) {
  const m = props.mode
  const p = {
    x: Math.random() * W,
    y: initial ? Math.random() * H : (m === 'moon' || m === 'ink' ? H + 10 : -10),
    r: 0, vx: 0, vy: 0, phase: Math.random() * Math.PI * 2,
    speed: 0.3 + Math.random() * 0.8,
    color: PALETTES[m].colors[(Math.random() * PALETTES[m].colors.length) | 0],
    rot: Math.random() * Math.PI * 2,
    rotSpeed: (Math.random() - 0.5) * 0.02,
  }
  if (m === 'moon') {
    p.r = 0.8 + Math.random() * 2.2
    p.vy = -(0.08 + Math.random() * 0.25)
    p.vx = (Math.random() - 0.5) * 0.12
  } else if (m === 'sunset') {
    p.r = 1 + Math.random() * 2.5
    p.vy = 0.15 + Math.random() * 0.4
    p.vx = -(0.05 + Math.random() * 0.2)
  } else if (m === 'willow' || m === 'petal') {
    p.r = 1.5 + Math.random() * 2.8
    p.vy = 0.25 + Math.random() * 0.5
    p.vx = (Math.random() - 0.5) * 0.2
  } else { // ink
    p.r = 1.5 + Math.random() * 4
    p.vy = -(0.06 + Math.random() * 0.18)
    p.vx = (Math.random() - 0.5) * 0.08
  }
  return p
}

function resize() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  const rect = el.value.getBoundingClientRect()
  W = rect.width
  H = rect.height
  el.value.width = W * dpr
  el.value.height = H * dpr
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  const count = Math.round(((W * H) / 16000) * props.density)
  particles = Array.from({ length: Math.min(count, 160) }, () => spawn(true))
}

function tick(t) {
  raf = requestAnimationFrame(tick)
  if (!visible) return
  ctx.clearRect(0, 0, W, H)
  const m = props.mode
  const palette = PALETTES[m]
  for (let i = 0; i < particles.length; i++) {
    const p = particles[i]
    p.phase += 0.02
    p.x += p.vx + Math.sin(p.phase) * (m === 'willow' || m === 'petal' ? 0.5 : 0.15)
    p.y += p.vy
    p.rot += p.rotSpeed
    // 出界回收
    if (p.y < -14 || p.y > H + 14 || p.x < -14 || p.x > W + 14) particles[i] = spawn()

    const twinkle = palette.glow ? 0.45 + 0.55 * Math.abs(Math.sin(p.phase * 1.5)) : 0.55 + 0.35 * Math.sin(p.phase)
    ctx.globalAlpha = Math.max(0.08, Math.min(1, twinkle))
    ctx.fillStyle = p.color
    if (m === 'petal' || m === 'willow') {
      // 椭圆花瓣/絮
      ctx.save()
      ctx.translate(p.x, p.y)
      ctx.rotate(p.rot + Math.sin(p.phase) * 0.4)
      ctx.beginPath()
      ctx.ellipse(0, 0, p.r, p.r * 0.55, 0, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()
    } else {
      // 圆点（月辉/夕烬带光晕）
      if (palette.glow) {
        ctx.shadowBlur = 8
        ctx.shadowColor = p.color
      }
      ctx.beginPath()
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
      ctx.fill()
      ctx.shadowBlur = 0
    }
  }
  ctx.globalAlpha = 1
}

onMounted(() => {
  ctx = el.value.getContext('2d')
  resize()
  observer = new ResizeObserver(resize)
  observer.observe(el.value)
  io = new IntersectionObserver(([e]) => { visible = e.isIntersecting })
  io.observe(el.value)
  document.addEventListener('visibilitychange', onVis)
  raf = requestAnimationFrame(tick)
})

function onVis() { visible = !document.hidden }

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  observer && observer.disconnect()
  io && io.disconnect()
  document.removeEventListener('visibilitychange', onVis)
})
</script>
