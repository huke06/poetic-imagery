<template>
  <span
    class="rounded-[2px] font-song tracking-wider border leading-none"
    :class="lg ? 'text-xs px-2.5 py-1' : 'text-[9px] px-2 py-[2px]'"
    :style="{ color: tagInk(tag), borderColor: emotionColor(tag) + '38', background: emotionColor(tag) + '0D' }">
    {{ tag }}
  </span>
</template>

<script setup>
import { emotionColor } from '../utils/emotionColors'

defineProps({
  tag: { type: String, required: true },
  lg: { type: Boolean, default: false },
})

// 情感标签文字色：主体色向宣纸灰掺和，降低饱和（标签仅作辅助信息）
const tagInk = (t) => `color-mix(in srgb, ${emotionColor(t)} 62%, #7A7468)`
</script>
