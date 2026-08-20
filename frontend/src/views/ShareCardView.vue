<!-- 分享卡片预览 + 下载页 -->
<template>
  <div class="max-w-3xl mx-auto px-4 py-10">
    <button class="back-btn" @click="goBack">← 返回意象详情</button>
    <h1 class="font-song text-2xl font-bold mt-6 text-center">意象分享卡片</h1>
    <p class="text-center text-xs text-qianhui mt-1">长按或右键可保存 · 也可一键下载 PNG / SVG</p>

    <div v-if="loading" class="py-20 text-center text-qianhui">生成中…</div>
    <div v-else-if="error" class="py-20 text-center text-qianhui">{{ error }}</div>

    <div v-else class="mt-8">
      <div class="card p-4 shadow-card">
        <img :src="previewUrl" alt="分享卡片" class="w-full rounded" />
      </div>
      <div class="flex flex-wrap items-center justify-center gap-3 mt-6">
        <button class="btn-primary" :disabled="pngBusy" @click="downloadPng">
          {{ pngBusy ? '生成中…' : '下载图片 (PNG)' }}
        </button>
        <button class="btn-outline" @click="downloadSvg">下载矢量 (SVG)</button>
        <button class="btn-outline" @click="copyLink">复制分享链接</button>
      </div>
      <p class="text-center text-xs text-qianhui/60 mt-4">
        PNG 图片适合发朋友圈 / 保存相册；SVG 可无损放大。字体以系统楷体/宋体呈现。
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { downloadDataUrl, downloadText, svgDataUrl, svgToPngDataUrl } from '../utils/share'

const route = useRoute()
const router = useRouter()
const svg = ref('')
const loading = ref(true)
const error = ref('')
const pngBusy = ref(false)
const conceptId = Number(route.params.id)

const previewUrl = computed(() => (svg.value ? svgDataUrl(svg.value) : ''))

function goBack() {
  if (window.history.state?.back) router.back()
  else router.push('/concept/' + conceptId)
}

async function downloadPng() {
  if (!svg.value || pngBusy.value) return
  pngBusy.value = true
  try {
    const dataUrl = await svgToPngDataUrl(svg.value, 720)
    downloadDataUrl(dataUrl, '诗象万千-意象卡片.png')
  } finally { pngBusy.value = false }
}

function downloadSvg() {
  if (svg.value) downloadText(svg.value, '诗象万千-意象卡片.svg')
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(window.location.origin + '/concept/' + conceptId)
  } catch { /* ignore */ }
}

onMounted(async () => {
  try {
    const resp = await axios.get('/api/concept/' + conceptId + '/share-card')
    svg.value = typeof resp.data === 'string' ? resp.data : ''
    if (!svg.value) error.value = '未能生成分享卡片'
  } catch {
    error.value = '分享卡片生成失败，请稍后再试。'
  } finally {
    loading.value = false
  }
})
</script>
