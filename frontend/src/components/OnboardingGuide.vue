<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-[80] bg-moyan/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-xuanzhi rounded-xl max-w-2xl w-full shadow-2xl rise-in overflow-hidden">
        <!-- 头图 -->
        <div class="relative px-8 pt-8 pb-5 text-center" style="background: linear-gradient(180deg, #16283F, #2B4C7E)">
          <div class="seal mx-auto !w-14 !h-14 !text-lg">入门</div>
          <h3 class="font-song text-2xl font-bold text-xuanzhi mt-4 tracking-widest">欢迎使用「诗象万千」</h3>
          <p class="text-xuanzhi/70 text-sm mt-2">游心万象，一眼千年 —— 一分钟了解四大功能</p>
        </div>

        <div class="px-8 py-6">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div v-for="(f, i) in features" :key="f.title" class="flex gap-3 p-3 rounded-lg bg-white/50 border border-black/5 rise-in"
              :style="{ animationDelay: i * 0.08 + 's' }">
              <span class="w-9 h-9 shrink-0 rounded-md flex items-center justify-center text-xuanzhi font-kai" :style="{ background: f.color }">{{ f.icon }}</span>
              <div>
                <b class="font-song text-sm" :style="{ color: f.color }">{{ f.title }}</b>
                <p class="text-xs text-qianhui leading-5 mt-0.5">{{ f.desc }}</p>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-between mt-6">
            <label class="flex items-center gap-2 text-xs text-qianhui cursor-pointer select-none">
              <input type="checkbox" v-model="dontShow" class="accent-shiqing" /> 不再提示
            </label>
            <div class="flex gap-3">
              <button class="btn-outline !py-1.5 !px-4 !text-xs" @click="dismiss">稍后再看</button>
              <button class="btn-primary !py-1.5 !px-5 !text-xs" @click="start">开始探索</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const show = ref(false)
const dontShow = ref(true)
const KEY = 'sxz_onboarded'

const features = [
  { icon: '象', color: '#2B4C7E', title: '意象画廊', desc: '浏览精选意象，进入卡片查看情感分布、朝代演变、名句与用法谱系。' },
  { icon: '鉴', color: '#5B7C5F', title: '诗意图鉴', desc: '按主题族类纵览全部意象，构建你的诗词知识图谱。' },
  { icon: '艺', color: '#9B4423', title: '艺术展厅', desc: '诗画互证，按朝代检索古画与器物，放大镜细赏。' },
  { icon: '问', color: '#6E4A7E', title: '灵犀助手', desc: 'AI 意象问答与格律创诗，一问一答皆有据可依。' },
]

onMounted(() => {
  try {
    if (!localStorage.getItem(KEY)) show.value = true
  } catch { show.value = false }
})

function persist() {
  try { if (dontShow.value) localStorage.setItem(KEY, '1') } catch { /* ignore */ }
}
function dismiss() { persist(); show.value = false }
function start() { persist(); show.value = false; router.push('/concepts') }
</script>
