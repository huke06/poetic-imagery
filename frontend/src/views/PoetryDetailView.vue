<template>
  <div v-if="poetry" class="max-w-3xl mx-auto px-4 py-12">
    <!-- 古籍式正文 -->
    <div class="text-center rise-in">
      <h1 class="font-song text-4xl font-bold text-moyan tracking-widest">{{ poetry.title }}</h1>
      <p class="mt-4 text-qianhui tracking-[0.3em] text-sm">{{ poetry.dynasty }} · {{ poetry.author }} <span class="tag border-shiqing/30 text-shiqing ml-2">{{ poetry.writing_type }}</span></p>
      <div class="ink-divider my-10"></div>

      <!-- 正文（意象词高亮） -->
      <div class="verse-text text-2xl leading-[2.6] text-moyan/90 space-y-1">
        <p v-for="(line, li) in renderedLines" :key="li">
          <template v-for="(seg, si) in line" :key="si">
            <span v-if="seg.concept"
              class="cursor-pointer border-b-2 transition-all hover:opacity-70 px-0.5 rounded-sm"
              :style="{ color: seg.concept.theme_color, borderColor: seg.concept.theme_color, background: seg.concept.theme_color + '12' }"
              :title="`意象 · ${seg.concept.name}（点击查看）`"
              @click="$router.push(`/concept/${seg.concept.id}`)">{{ seg.text }}</span>
            <span v-else>{{ seg.text }}</span>
          </template>
        </p>
      </div>

      <div v-if="poetry.concepts.length" class="flex items-center justify-center gap-2 mt-10 text-sm">
        <span class="text-qianhui text-xs tracking-widest">本诗意象</span>
        <router-link v-for="c in poetry.concepts" :key="c.id" :to="`/concept/${c.id}`"
          class="tag !px-3 !py-1 hover:scale-105 transition-transform"
          :style="{ color: c.theme_color, borderColor: c.theme_color + '66', background: c.theme_color + '0F' }">
          {{ c.name }}
        </router-link>
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="card mt-14">
      <div class="flex border-b border-black/5 overflow-x-auto">
        <button v-for="t in tools" :key="t.key"
          class="flex-1 min-w-[100px] py-3.5 text-sm tracking-widest transition-colors whitespace-nowrap"
          :class="activeTool === t.key ? 'text-shiqing font-semibold border-b-2 border-shiqing bg-shiqing/5' : 'text-qianhui hover:text-shiqing'"
          @click="switchTool(t.key)">
          {{ t.label }}
        </button>
      </div>
      <div class="p-6 min-h-[180px]">
        <div v-if="toolLoading" class="py-10 text-center text-qianhui text-sm">加载中…</div>
        <template v-else>
          <!-- 平仄标注 -->
          <div v-if="activeTool === 'tones' && toolData">
            <p class="text-xs text-qianhui mb-4">{{ toolData.note || '' }}（<span class="text-shiqing">平</span> / <span class="text-zheshi">仄</span>）</p>
            <div class="space-y-3">
              <div v-for="(row, i) in toolData.items" :key="i" class="flex flex-wrap items-baseline gap-x-3">
                <span class="verse-text text-lg">
                  <span v-for="(c, ci) in row.chars" :key="ci"
                    :class="c.tone === '平' ? 'text-shiqing' : 'text-zheshi'">{{ c.char }}</span>
                </span>
                <span class="text-xs text-qianhui tracking-[0.2em]">{{ row.tone_string }}</span>
              </div>
            </div>
          </div>
          <!-- 自动笺注 -->
          <div v-else-if="activeTool === 'labelize' && toolData">
            <div v-if="toolData.items?.length" class="space-y-4">
              <div v-for="(n, i) in toolData.items" :key="i" class="border-l-2 border-shiqing/40 pl-4">
                <p class="verse-text text-lg text-shiqing">{{ n.clause }}</p>
                <p class="text-sm text-qianhui leading-7 mt-1">{{ n.note }} <span class="tag border-zhuqing/40 text-zhuqing ml-1">{{ n.emotion }}</span></p>
              </div>
            </div>
            <p v-else class="text-sm text-qianhui py-8 text-center">{{ toolData.note || '暂无笺注数据' }}</p>
          </div>
          <!-- 古籍出处 -->
          <div v-else-if="activeTool === 'booklinks' && toolData">
            <p v-if="!toolData.items?.length" class="text-sm text-qianhui py-8 text-center">{{ toolData.note || '暂无出处数据' }}</p>
            <pre v-else class="text-sm whitespace-pre-wrap">{{ JSON.stringify(toolData.items, null, 2) }}</pre>
          </div>
          <!-- 相似作品 -->
          <div v-else-if="activeTool === 'similar' && toolData">
            <p class="text-xs text-qianhui mb-4">与 «{{ toolData.key }}» 句意/字面相近的作品（{{ toolData.source === 'local' ? '本地计算' : '上游接口' }}）</p>
            <div v-if="toolData.items?.length" class="space-y-3">
              <div v-for="(s, i) in toolData.items" :key="i"
                class="flex items-center justify-between gap-4 p-3 rounded-md bg-white/60 border border-black/5 hover:border-shiqing/30 cursor-pointer transition-all"
                @click="s.poetry && $router.push(`/poetry/${s.poetry.id}`)">
                <div>
                  <p class="verse-text text-lg">{{ s.clause }}</p>
                  <p class="text-xs text-qianhui mt-1" v-if="s.poetry">{{ s.poetry.dynasty }} · {{ s.poetry.author }} 《{{ s.poetry.title }}》</p>
                </div>
                <span class="text-xs text-qianhui shrink-0">相似度 {{ Math.round(s.score * 100) }}%</span>
              </div>
            </div>
            <p v-else class="text-sm text-qianhui py-8 text-center">未找到相似作品</p>
          </div>
        </template>
      </div>
    </div>

    <div class="text-center mt-10">
      <button class="btn-outline !text-xs" @click="goBack">返回上一页</button>
    </div>
  </div>
  <div v-else class="py-32 text-center text-qianhui">加载中…</div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getBookLinks, getLabelize, getPoetryDetail, getSimilar, getTones } from '../api'

const route = useRoute()
const router = useRouter()
const poetryId = Number(route.params.id)
const poetry = ref(null)
const renderedLines = ref([])

const tools = [
  { key: 'tones', label: '平仄标注' },
  { key: 'labelize', label: '自动笺注' },
  { key: 'booklinks', label: '古籍出处' },
  { key: 'similar', label: '相似作品' },
]
const activeTool = ref('')
const toolData = ref(null)
const toolLoading = ref(false)
const loaded = {}

/** 将正文按行拆分，并把意象句读替换为高亮段 */
function buildLines(p) {
  // 收集（片段, concept），按在全文中的位置排序
  const marks = []
  for (const c of p.concepts) {
    for (const clause of c.clauses) {
      const core = clause.replace(/[，。！？；、：\s]+$/, '')
      const idx = core ? p.content.indexOf(core) : -1
      if (idx >= 0) marks.push({ start: idx, end: idx + core.length, concept: c })
    }
  }
  marks.sort((a, b) => a.start - b.start)
  // 行级渲染：content 按 \n 分行，逐行切分高亮段
  renderedLines.value = p.content.split('\n').map((line) => {
    const segments = []
    let cursor = 0
    // 计算行在全文中的偏移需另行处理——简化：在行内匹配
    const lineMarks = []
    for (const c of p.concepts) {
      for (const clause of c.clauses) {
        const core = clause.replace(/[，。！？；、：\s]+$/, '')
        let idx = line.indexOf(core)
        while (idx >= 0) {
          lineMarks.push({ start: idx, end: idx + core.length, concept: c })
          idx = line.indexOf(core, idx + core.length)
        }
      }
    }
    lineMarks.sort((a, b) => a.start - b.start)
    for (const m of lineMarks) {
      if (m.start < cursor) continue // 跳过重叠
      if (m.start > cursor) segments.push({ text: line.slice(cursor, m.start) })
      segments.push({ text: line.slice(m.start, m.end), concept: m.concept })
      cursor = m.end
    }
    if (cursor < line.length) segments.push({ text: line.slice(cursor) })
    return segments
  })
}

async function switchTool(key) {
  activeTool.value = key
  if (loaded[key]) {
    toolData.value = loaded[key]
    return
  }
  toolLoading.value = true
  toolData.value = null
  try {
    const fn = { tones: getTones, labelize: getLabelize, booklinks: getBookLinks, similar: getSimilar }[key]
    const data = await fn(poetryId)
    loaded[key] = data
    toolData.value = data
  } catch {
    toolData.value = { items: [], note: '加载失败' }
  } finally {
    toolLoading.value = false
  }
}

/** 返回上一页；若无站内历史（直接打开/分享链接进入）则回首页 */
function goBack() {
  if (window.history.state?.back) router.back()
  else router.push('/')
}

onMounted(async () => {
  try {
    if (!Number.isFinite(poetryId)) throw new Error('invalid id')
    poetry.value = await getPoetryDetail(poetryId)
    buildLines(poetry.value)
    switchTool('tones')
  } catch {
    router.replace({ name: 'not-found' })
  }
})
</script>
