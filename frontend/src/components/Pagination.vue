<template>
  <div v-if="total > pageSize" class="flex items-center justify-center gap-4 py-6 text-sm">
    <button class="btn-outline !px-4 !py-1.5 disabled:opacity-40 disabled:pointer-events-none"
      :disabled="page <= 1" @click="$emit('change', page - 1)">上一页</button>
    <span class="text-qianhui tracking-wider">{{ page }} / {{ pages }}</span>
    <button class="btn-outline !px-4 !py-1.5 disabled:opacity-40 disabled:pointer-events-none"
      :disabled="page >= pages" @click="$emit('change', page + 1)">下一页</button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ page: { type: Number, default: 1 }, pageSize: { type: Number, default: 10 }, total: { type: Number, default: 0 } })
defineEmits(['change'])
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
</script>
