<template>
  <button
    class="backtop-btn"
    :class="{ 'backtop-show': show, 'backtop-hide': !show }"
    @click="toTop"
    aria-label="返回顶部" title="返回顶部"
  >
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="m5 12 7-7 7 7"/></svg>
  </button>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  threshold: { type: Number, default: 500 },
})

const show = ref(false)

function onScroll() {
  show.value = window.scrollY > props.threshold
}
function toTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.backtop-btn {
  position: fixed; right: 28px; bottom: 96px; z-index: 85;
  width: 44px; height: 44px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: #9B4423; color: #F5F1E8; border: none; cursor: pointer;
  box-shadow: 0 4px 16px rgba(155,68,35,0.35);
  transition: opacity .3s, transform .3s, background .2s;
}
.backtop-btn:hover { background: #B0512C; transform: translateY(-2px); }
.backtop-show { opacity: 1; pointer-events: auto; }
.backtop-hide { opacity: 0; pointer-events: none; }
</style>
