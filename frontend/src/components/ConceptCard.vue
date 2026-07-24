<template>
  <router-link :to="`/concept/${concept.id}`"
    class="card card-hover block overflow-hidden group"
    :style="{ borderTop: `3px solid ${concept.theme_color}` }">
    <div class="p-5">
      <div class="flex items-start justify-between">
        <div>
          <h3 class="font-song text-3xl font-bold" :style="{ color: concept.theme_color }">{{ concept.name }}</h3>
          <span class="text-xs text-qianhui">{{ concept.category_main }} · {{ concept.category_sub }}</span>
        </div>
        <img v-if="concept.artwork_thumb" :src="concept.artwork_thumb" :alt="concept.name"
          class="w-14 h-14 object-cover rounded-md border border-black/10 opacity-90 group-hover:opacity-100 transition-opacity" loading="lazy" />
      </div>
      <p class="verse-text text-lg text-moyan/85 mt-4 leading-relaxed min-h-[3.5rem]">
        {{ concept.classic_clause || '——' }}
      </p>
      <div class="flex items-center justify-between mt-4">
        <div class="flex flex-wrap gap-1.5">
          <span v-for="tag in concept.emotion_tags" :key="tag" class="tag"
            :style="{ color: concept.theme_color, borderColor: concept.theme_color + '55', background: concept.theme_color + '0D' }">
            {{ tag }}
          </span>
        </div>
        <span class="text-xs text-qianhui whitespace-nowrap ml-2">{{ concept.poetry_count }} 首</span>
      </div>
    </div>
  </router-link>
</template>

<script setup>
defineProps({ concept: { type: Object, required: true } })
</script>
