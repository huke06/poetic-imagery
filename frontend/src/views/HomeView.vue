<template>
  <div>
    <!-- 首屏：夜航山水意境 -->
    <section class="relative overflow-hidden min-h-[78vh] flex items-center">
      <!-- 层叠夜空 -->
      <div class="absolute inset-0" style="background: linear-gradient(180deg, #16283F 0%, #2B4C7E 46%, #7A89A0 78%, #F5F1E8 100%)"></div>
      <!-- 明月 -->
      <div class="absolute right-[12%] top-[14%] w-28 h-28 sm:w-36 sm:h-36 rounded-full moon-breathe"
        style="background: radial-gradient(circle at 38% 34%, #FDF9E7 0%, #F2E8C9 58%, #E3D5A8 100%);
               box-shadow: 0 0 60px 26px rgba(245, 236, 200, 0.35), 0 0 140px 60px rgba(245, 236, 200, 0.16)"></div>
      <!-- 淡墨群山 -->
      <svg class="absolute bottom-0 left-0 w-full pointer-events-none" preserveAspectRatio="none" viewBox="0 0 1200 260" style="height: 42%">
        <path d="M0 160 Q150 60 320 130 T640 110 Q760 40 900 120 T1200 90 L1200 260 L0 260 Z" fill="#1D3450" opacity="0.55"/>
        <path d="M0 205 Q200 130 420 180 T840 160 Q1000 120 1200 175 L1200 260 L0 260 Z" fill="#16283F" opacity="0.8"/>
        <path d="M0 245 Q260 200 520 232 T1200 220 L1200 260 L0 260 Z" fill="#0F1E33"/>
      </svg>
      <!-- 月辉粒子 -->
      <ParticleCanvas mode="moon" :density="1.2" />

      <div class="relative max-w-6xl mx-auto px-4 py-24 w-full">
        <div class="flex items-center justify-between">
          <div class="rise-in max-w-2xl">
            <h1 class="font-song text-7xl sm:text-8xl font-bold tracking-[0.42em] text-xuanzhi drop-shadow-lg">诗象志</h1>
            <div class="mt-7 flex items-center gap-4">
              <span class="h-px w-14 bg-xuanzhi/50"></span>
              <p class="font-kai text-xl sm:text-2xl tracking-[0.3em] text-xuanzhi/90">一字藏万象，一诗见千年</p>
            </div>
            <p class="mt-6 text-sm text-xuanzhi/70 max-w-xl leading-7">
              以古典诗词意象为切口，集意象知识图谱、诗画联动、演变可视化与智能问答于一体，
              直观呈现一个词语在千年诗词中的情感承载与演变轨迹。
            </p>
            <div class="mt-10 flex items-center gap-5">
              <router-link to="/concepts" class="btn-primary !bg-xuanzhi !text-shiqing hover:!bg-white shadow-lg">意象漫游</router-link>
              <router-link to="/artworks" class="btn-outline !border-xuanzhi/70 !text-xuanzhi hover:!bg-xuanzhi hover:!text-shiqing">古画寻诗</router-link>
            </div>
          </div>
          <!-- 竖排题句 -->
          <div class="hidden md:flex flex-col items-center gap-6 select-none rise-in" style="animation-delay:.3s">
            <span class="vertical-verse text-xuanzhi/85">明月出天山</span>
            <span class="w-px h-10 bg-xuanzhi/30"></span>
            <span class="vertical-verse text-xuanzhi/85">苍茫云海间</span>
            <span class="seal mt-2">诗象</span>
          </div>
        </div>
      </div>
      <!-- 底部渐隐入宣纸 -->
      <div class="absolute bottom-0 left-0 w-full h-16" style="background: linear-gradient(180deg, transparent, #F5F1E8)"></div>
    </section>

    <div class="ink-divider max-w-4xl mx-auto"></div>

    <!-- 意象精选 -->
    <section class="max-w-6xl mx-auto px-4 py-16">
      <SectionTitle sub="点击卡片进入意象详情">意象精选</SectionTitle>
      <div v-if="loading" class="py-16 text-center text-qianhui">加载中…</div>
        <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-6 mt-8">
        <ConceptCard v-for="c in concepts" :key="c.id" :concept="c" class="rise-in" />
      </div>
    </section>

    <!-- 项目简介 -->
    <section class="bg-white/40 border-y border-shiqing/10">
      <div class="max-w-6xl mx-auto px-4 py-16">
        <SectionTitle>三大核心价值</SectionTitle>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          <div v-for="(f, i) in features" :key="f.title" class="card card-hover p-6 rise-in" :style="{ animationDelay: i * 0.1 + 's' }">
            <div class="w-11 h-11 rounded-md flex items-center justify-center text-xl text-xuanzhi font-kai" :style="{ background: f.color }">{{ f.icon }}</div>
            <h3 class="font-song text-lg font-semibold mt-4">{{ f.title }}</h3>
            <p class="text-sm text-qianhui leading-7 mt-2">{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 智能助手入口 -->
    <section class="max-w-6xl mx-auto px-4 py-16 text-center">
      <p class="font-kai text-2xl text-moyan/80">「月」在古诗里有哪些含义？</p>
      <p class="font-kai text-2xl text-moyan/80 mt-2">「夕阳」为何总与离愁相伴？</p>
      <router-link to="/agent" class="btn-primary mt-8">向智能助手提问</router-link>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getConceptList } from '../api'
import ConceptCard from '../components/ConceptCard.vue'
import ParticleCanvas from '../components/ParticleCanvas.vue'
import SectionTitle from '../components/SectionTitle.vue'

const concepts = ref([])
const loading = ref(true)

const features = [
  { icon: '变', color: '#2B4C7E', title: '意象演变', desc: '朝代时间轴 × 频次折线 × 情感环形图，用数据讲清一个意象的兴衰流变与情感变迁。' },
  { icon: '画', color: '#9B4423', title: '诗画互证', desc: '每个意象匹配对应古画，见意象知画意，观古画品诗情，打通诗文库与艺术品库。' },
  { icon: '问', color: '#5B7C5F', title: '智能问答', desc: '基于自建意象知识库的轻量 RAG 问答与格律创诗，回答全部锚定本地权威数据。' },
]

onMounted(async () => {
  try {
    const data = await getConceptList()
    concepts.value = data.items
  } finally {
    loading.value = false
  }
})
</script>
