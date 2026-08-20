<template>
  <div v-if="poetry" class="max-w-6xl mx-auto px-4 pt-6 pb-14" :style="{ '--tc': themeColor }">
    <!-- 返回上一页 -->
    <button class="back-btn" @click="goBack">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="m12 19-7-7 7-7"/></svg>
      返回
    </button>

    <div class="grid grid-cols-1 lg:grid-cols-[11fr_13fr] gap-10 lg:gap-14 mt-8">
      <!-- ═══ 左：诗歌阅读区 ═══ -->
      <section class="flex flex-col">
        <header class="text-center">
          <h1 class="font-song text-4xl font-semibold text-moyan tracking-[0.12em]">{{ poetry.title }}</h1>
          <p class="mt-4 text-sm text-qianhui tracking-[0.2em]">
            {{ poetry.dynasty }} · {{ poetry.author }}
            <span v-if="poetry.writing_type" class="writing-tag ml-2">{{ poetry.writing_type }}</span>
          </p>
        </header>

        <!-- 极小朱砂印章：标题与诗句间的视觉停顿 -->
        <div class="title-seal" aria-hidden="true"></div>

        <!-- 诗句正文（意象词细下划线高亮，点击查看意象） -->
        <div class="my-12">
          <div class="verse-text text-2xl leading-[2.5] text-moyan/85 space-y-2 text-center">
            <p v-for="(line, li) in renderedLines" :key="li">
              <template v-for="(seg, si) in line" :key="si">
                <span v-if="seg.concept"
                  class="cursor-pointer border-b transition-all hover:opacity-70"
                  :style="{ color: seg.concept.theme_color, borderColor: seg.concept.theme_color }"
                  :title="`意象 · ${seg.concept.name}（点击查看）`"
                  @click="$router.push(`/concept/${seg.concept.id}`)">{{ seg.text }}</span>
                <span v-else>{{ seg.text }}</span>
              </template>
            </p>
          </div>
        </div>

        <!-- 本诗意象（意象印鉴） -->
        <div v-if="poetry.concepts.length" class="text-center mt-10">
          <span class="text-xs text-qianhui tracking-[0.3em]">本诗意象</span>
          <div class="flex flex-wrap justify-center gap-3 mt-3">
            <router-link v-for="c in poetry.concepts" :key="c.id" :to="`/concept/${c.id}`"
              class="concept-seal" :style="{ '--cs': c.theme_color }">
              {{ c.name }}
            </router-link>
          </div>
        </div>
      </section>

      <!-- ═══ 右：诗歌解读功能区 ═══ -->
      <aside class="interpret-card">
        <h2 class="font-song text-lg font-semibold text-moyan tracking-[0.22em]">诗歌解读</h2>

        <!-- Tab 切换（四等分，底部指示线滑动） -->
        <div class="relative border-b border-black/5 mt-4">
          <div class="grid grid-cols-4">
            <button v-for="t in tools" :key="t.key"
              class="poem-tab font-hei pb-2.5 text-sm tracking-wide text-center transition-colors"
              :class="{ active: activeTool === t.key }"
              @click="switchTool(t.key)">
              {{ t.label }}
            </button>
          </div>
          <span class="tab-indicator" :style="{ transform: `translateX(${activeIndex * 100}%)` }"></span>
        </div>

        <!-- 内容区（四工具共用同一阅读框架，切换淡入） -->
        <div class="pt-5 min-h-[280px]">
          <div v-if="toolLoading" class="py-10 text-center text-qianhui text-sm">加载中…</div>
          <Transition v-else name="tool" mode="out-in">
            <div :key="activeTool">
            <!-- 平仄标注 -->
            <div v-if="activeTool === 'tones' && toolData">
              <p class="text-[11px] text-qianhui/70 mb-5">{{ toolData.note || '' }}（<span class="tone-ping">平</span> / <span class="tone-ze">仄</span>）</p>
              <div class="space-y-4">
                <div v-for="(row, i) in toolData.items" :key="i" class="space-y-1.5">
                  <div class="font-song text-lg text-moyan/85 leading-relaxed">
                    <span v-for="(c, ci) in row.chars" :key="ci">{{ c.char }}</span>
                  </div>
                  <div class="text-[13px] tracking-[0.3em] leading-relaxed">
                    <span v-for="(c, ci) in row.chars" :key="ci" :class="c.tone === '平' ? 'tone-ping' : 'tone-ze'">{{ c.tone }}</span>
                  </div>
                </div>
              </div>
            </div>
            <!-- 自动笺注 -->
            <div v-else-if="activeTool === 'labelize' && toolData">
              <div v-if="toolData.items?.length" class="space-y-6">
                <div v-for="(n, i) in toolData.items" :key="i" class="note-item pl-4">
                  <p class="font-song text-[17px] text-moyan/85 whitespace-normal break-words">{{ n.clause }}</p>
                  <p class="font-song text-[13px] text-qianhui leading-[1.9] mt-2 whitespace-pre-wrap break-words">{{ plainText(n.note) }}</p>
                </div>
              </div>
              <p v-else class="text-sm text-qianhui py-8 text-center">{{ toolData.note || '暂无笺注数据' }}</p>
            </div>
            <!-- 诗歌翻译 -->
            <div v-else-if="activeTool === 'translate' && toolData">
              <div v-if="toolData.text" class="font-song text-[14px] leading-[1.9] whitespace-pre-wrap text-moyan/80">{{ plainText(toolData.text) }}</div>
              <p v-else class="text-sm text-qianhui py-8 text-center">{{ toolData.note || '暂无翻译' }}</p>
            </div>
            <!-- 诗歌赏析 -->
            <div v-else-if="activeTool === 'appreciation' && toolData">
              <div v-if="toolData.text" class="font-song text-[14px] leading-[1.9] whitespace-pre-wrap text-moyan/80">{{ plainText(toolData.text) }}</div>
              <p v-else class="text-sm text-qianhui py-8 text-center">{{ toolData.note || '暂无赏析' }}</p>
            </div>
            </div>
          </Transition>
        </div>
      </aside>
    </div>

    <BackToTop />
  </div>
  <div v-else class="py-32 text-center text-qianhui">加载中…</div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAppreciation, getLabelize, getPoetryDetail, getSimilar, getTones, getTranslate } from '../api'
import BackToTop from '../components/BackToTop.vue'

const route = useRoute()
const router = useRouter()
const poetryId = Number(route.params.id)
const poetry = ref(null)
const renderedLines = ref([])

// 页面主题色：取第一个关联意象的系统主题色（无意象回退石青）
const themeColor = computed(() => poetry.value?.concepts?.[0]?.theme_color || '#2B4C7E')

const tools = [
  { key: 'tones', label: '平仄标注' },
  { key: 'labelize', label: '自动笺注' },
  { key: 'translate', label: '诗歌翻译' },
  { key: 'appreciation', label: '诗歌赏析' },
]
const activeTool = ref('')
const activeIndex = computed(() => tools.findIndex((t) => t.key === activeTool.value))
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
    const fn = { tones: getTones, labelize: getLabelize, translate: getTranslate, appreciation: getAppreciation, similar: getSimilar }[key]
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

/** 去除 Markdown 语法，输出纯文本（翻译/赏析/笺注统一纯文本展示） */
function plainText(t) {
  if (!t) return ''
  return String(t)
    .replace(/```[\s\S]*?```/g, (m) => m.replace(/```/g, ''))
    .replace(/^#{1,6}\s*/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+[.、)]\s+/gm, '')
    .replace(/^\s*>\s?/gm, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
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

<style scoped>
/* 体裁小签：主题色低饱和细边宋体，不抢标题 */
.writing-tag {
  display: inline-block;
  font-family: 'Noto Serif SC', 'Songti SC', STSong, SimSun, serif;
  font-size: 11px; letter-spacing: 0.2em;
  padding: 2px 8px; border: 1px solid; border-radius: 2px;
  color: color-mix(in srgb, var(--tc) 74%, #2C2C2C);
  border-color: color-mix(in srgb, var(--tc) 30%, transparent);
  background: color-mix(in srgb, var(--tc) 6%, transparent);
}

/* 极小朱砂印章：标题与诗句间的视觉停顿 */
.title-seal {
  width: 10px; height: 10px;
  background: #9B2C1F;
  border-radius: 2px;
  margin: 30px auto;
  opacity: 0.55;
  box-shadow: inset 0 0 0 1px rgba(245, 241, 232, 0.55);
}

/* 本诗意象印鉴：圆形淡色边框 + 主题色文字（各意象注入 --cs） */
.concept-seal {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 2.5rem; height: 2.5rem; padding: 0 0.65rem;
  border: 1px solid color-mix(in srgb, var(--cs) 42%, transparent);
  border-radius: 9999px;
  color: color-mix(in srgb, var(--cs) 80%, #2C2C2C);
  background: color-mix(in srgb, var(--cs) 6%, transparent);
  font-family: 'Noto Serif SC', 'Songti SC', STSong, SimSun, serif;
  font-size: 15px; letter-spacing: 0.08em;
  transition: opacity 0.2s, transform 0.2s, border-color 0.2s;
}
.concept-seal:hover {
  opacity: 0.75;
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--cs) 60%, transparent);
}

/* 解读容器：宣纸米白 + 浅暖灰边 + 极轻阴影 + 右下角淡墨远山 */
.interpret-card {
  position: relative;
  overflow: hidden;
  background: #FAF7F0;
  border: 1px solid #E7E0D2;
  border-radius: 8px;
  box-shadow: 0 1px 5px rgba(44, 44, 44, 0.04);
  padding: 1.5rem;
}
.interpret-card::after {
  content: '';
  position: absolute;
  right: -12px; bottom: -10px;
  width: 210px; height: 128px;
  background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 210 128'%3E%3Cpath d='M0 96 L46 44 L88 82 L136 24 L210 96 Z' fill='none' stroke='%232C2C2C' stroke-width='1.5' opacity='0.5'/%3E%3Cpath d='M0 114 L58 62 L104 100 L156 52 L210 106' fill='none' stroke='%232C2C2C' stroke-width='1' opacity='0.32'/%3E%3C/svg%3E") no-repeat right bottom / contain;
  opacity: 0.05;
  pointer-events: none;
}

/* 解读 Tab：四等分章节式（选中 = 主题色文字；底部指示线另设） */
.poem-tab { color: #6B6B6B; }
.poem-tab:hover { color: #2C2C2C; }
.poem-tab.active { color: color-mix(in srgb, var(--tc) 78%, #2C2C2C); }

/* 底部滑动指示线：随 activeIndex 平移，25% 宽 */
.tab-indicator {
  position: absolute;
  bottom: -1px; left: 0;
  width: 25%; height: 2px;
  background: color-mix(in srgb, var(--tc) 70%, transparent);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 工具内容切换：淡入 + 轻微位移 */
.tool-enter-active,
.tool-leave-active {
  transition: opacity 0.28s cubic-bezier(0.4, 0, 0.2, 1), transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
}
.tool-enter-from { opacity: 0; transform: translateY(8px); }
.tool-leave-to { opacity: 0; transform: translateY(-4px); }

/* 平仄：主题色 vs 墨灰（低饱和，弃红蓝强对比） */
.tone-ping { color: color-mix(in srgb, var(--tc) 82%, #2C2C2C); }
.tone-ze { color: #8A8578; }

/* 笺注条目：主题色细左边线 */
.note-item { border-left: 1px solid color-mix(in srgb, var(--tc) 35%, transparent); }
</style>
