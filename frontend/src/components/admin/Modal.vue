<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 bg-black/45 backdrop-blur-sm flex items-center justify-center p-4"
      @click.self="$emit('close')">
      <div class="bg-xuanzhi rounded-lg w-full shadow-2xl rise-in flex flex-col max-h-[92vh]" :class="width">
        <div class="flex items-center justify-between px-6 py-4 border-b border-black/8">
          <h3 class="font-song text-lg font-bold">{{ title }}</h3>
          <button class="text-qianhui hover:text-moyan text-xl leading-none" @click="$emit('close')">×</button>
        </div>
        <div class="p-6 overflow-y-auto">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({ show: Boolean, title: String, width: { type: String, default: 'max-w-2xl' } })
defineEmits(['close'])
</script>
