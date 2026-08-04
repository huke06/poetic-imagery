<template>
  <svg :viewBox="`0 0 ${width} ${height}`" :style="{ width: '100%', height }" role="img">
    <text v-for="w in placed" :key="w.text"
      :x="w.x" :y="w.y"
      :font-size="w.size"
      :fill="w.color"
      :opacity="w.opacity"
      :transform="`rotate(${w.rotate} ${w.x} ${w.y})`"
      text-anchor="middle" dominant-baseline="middle"
      :style="{ fontFamily: 'Kaiti SC, KaiTi, serif', fontWeight: w.size > midSize ? 700 : 400 }">
      {{ w.text }}
    </text>
    <text v-if="!placed.length" :x="width / 2" :y="height / 2" text-anchor="middle"
      font-size="13" fill="#9A9A9A">暂无数据</text>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

/**
 * 云朵状词云：阿基米德螺线布局 + 离屏 canvas 包围盒碰撞检测。
 * props.words: [{ text, value, color? }]
 */
const props = defineProps({
  words: { type: Array, default: () => [] },
  width: { type: Number, default: 520 },
  height: { type: Number, default: 260 },
  palette: { type: Array, default: () => ['#2B4C7E', '#9B4423', '#5B7C5F', '#8A6D3B', '#6E4A7E', '#3A7A7C'] },
})

let measureCtx = null
function measure(text, size) {
  if (!measureCtx) {
    const c = document.createElement('canvas')
    measureCtx = c.getContext('2d')
  }
  measureCtx.font = `${size}px "Kaiti SC", KaiTi, serif`
  const w = measureCtx.measureText(text).width
  return { w: w + 6, h: size * 1.25 }
}

const midSize = computed(() => 20)

const placed = computed(() => {
  const words = props.words.filter((w) => w.text && w.value > 0)
  if (!words.length) return []
  const max = Math.max(...words.map((w) => w.value))
  const min = Math.min(...words.map((w) => w.value))
  const range = max - min || 1
  // 按权重降序放置，大词居中
  const sorted = [...words].sort((a, b) => b.value - a.value)
  const cx = props.width / 2, cy = props.height / 2
  const boxes = []
  const out = []

  sorted.forEach((w, i) => {
    const t = (w.value - min) / range
    const size = Math.round(14 + t * 30)
    const { w: bw, h: bh } = measure(w.text, size)
    // 阿基米德螺线寻找空位
    let angle = 0, radius = 0, x = cx, y = cy, ok = false
    for (let step = 0; step < 900; step++) {
      x = cx + radius * Math.cos(angle)
      y = cy + radius * Math.sin(angle) * 0.72 // 压扁成云朵椭圆
      const box = { l: x - bw / 2, r: x + bw / 2, t: y - bh / 2, b: y + bh / 2 }
      const inside = box.l > 2 && box.r < props.width - 2 && box.t > 2 && box.b < props.height - 2
      const collide = boxes.some((b) => !(box.l > b.r || box.r < b.l || box.t > b.b || box.b < b.t))
      if (inside && !collide) { boxes.push(box); ok = true; break }
      angle += 0.35
      radius += 0.55
    }
    if (!ok) return
    out.push({
      text: w.text, x: Math.round(x), y: Math.round(y), size,
      color: w.color || props.palette[i % props.palette.length],
      opacity: 0.55 + t * 0.45,
      rotate: (i % 5 === 3 ? -8 : i % 7 === 4 ? 6 : 0),
    })
  })
  return out
})
</script>
