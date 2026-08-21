<template>
  <div class="flex items-center gap-3 select-none">
    <span class="h-px w-8 bg-gradient-to-r from-transparent to-current opacity-30"></span>
    <h2 class="section-title" :style="{ color: color || undefined }">
      <slot />
    </h2>
    <span class="h-px flex-1 bg-gradient-to-r from-current to-transparent opacity-20"></span>
    <span v-if="sub" class="section-sub text-xs text-qianhui tracking-wider">{{ sub }}</span>
  </div>
</template>

<script setup>
defineProps({ sub: String, color: String })
</script>
