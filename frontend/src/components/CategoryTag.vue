<template>
  <span
    class="cat-tag inline-block rounded-[2px] font-song border whitespace-nowrap"
    :class="lg ? 'text-sm px-3 py-1.5 tracking-[0.18em]' : 'text-[10px] px-2 py-[3px] tracking-[0.2em]'"
    :style="{ '--tc': themeColor || '#2B4C7E' }">
    {{ main }}<template v-if="sub"> · {{ sub }}</template>
  </span>
</template>

<script setup>
defineProps({
  main: { type: String, default: '' },
  sub: { type: String, default: '' },
  themeColor: { type: String, default: '#2B4C7E' },
  lg: { type: Boolean, default: false },
})
</script>

<style scoped>
/* 意象分类小签：主题色浅色版（掺墨保可读，极淡主题底）——与卡片封面同款 */
.cat-tag {
  color: color-mix(in srgb, var(--tc) 74%, #2C2C2C);
  border-color: color-mix(in srgb, var(--tc) 30%, transparent);
  background: color-mix(in srgb, var(--tc) 6%, transparent);
}
</style>
