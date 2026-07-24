<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <SectionTitle sub="轻量 RAG · 回答全部锚定本地意象知识库">智能助手</SectionTitle>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
      <!-- 左侧对话区 -->
      <div class="lg:col-span-2 card flex flex-col h-[640px]">
        <!-- 模式切换 -->
        <div class="flex border-b border-black/5">
          <button v-for="m in modes" :key="m.key"
            class="flex-1 py-3 text-sm tracking-widest transition-colors"
            :class="mode === m.key ? 'text-shiqing font-semibold border-b-2 border-shiqing bg-shiqing/5' : 'text-qianhui hover:text-shiqing'"
            @click="mode = m.key">
            {{ m.label }}
          </button>
        </div>

        <!-- 消息列表 -->
        <div ref="msgBox" class="flex-1 overflow-y-auto p-5 space-y-5">
          <div v-if="!messages.length" class="h-full flex flex-col items-center justify-center text-qianhui gap-3">
            <span class="seal !w-14 !h-14 !text-lg">问</span>
            <p class="text-sm">问意象、问诗句、问渊源，或让 AI 以意象创诗</p>
          </div>
          <div v-for="(m, i) in messages" :key="i" class="flex" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
            <div class="max-w-[85%] rise-in">
              <!-- 用户消息 -->
              <div v-if="m.role === 'user'" class="bg-shiqing text-white px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm leading-7 shadow-card">
                {{ m.text }}
              </div>
              <!-- AI 消息 -->
              <div v-else class="bg-white/80 px-5 py-4 rounded-2xl rounded-tl-sm shadow-card border border-black/5">
                <div v-if="m.source === 'llm' || m.source === 'llm_free'" class="text-sm leading-7 text-moyan/90 markdown-body" v-html="md(m.text)"></div>
                <p v-else class="text-sm leading-7 whitespace-pre-wrap text-moyan/90">{{ m.text }}</p>
                <!-- 创诗结果 -->
                <div v-if="m.compose" class="mt-4 bg-xuanzhi rounded-md p-4 border border-shiqing/15">
                  <div class="flex items-center justify-between">
                    <h4 class="font-song font-bold text-shiqing">《{{ m.compose.title }}》 <span class="text-xs font-normal text-qianhui">{{ m.compose.style }}</span></h4>
                    <button class="text-xs text-shiqing hover:underline" @click="copyPoem(m.compose)">复制</button>
                  </div>
                  <p class="verse-text text-lg leading-9 mt-2 whitespace-pre-wrap">{{ m.compose.poem }}</p>
                  <div v-if="m.compose.tones?.length" class="mt-3 text-xs text-qianhui">
                    <span class="tracking-widest">平仄</span>
                    <p v-for="(t, ti) in m.compose.tones" :key="ti" class="mt-0.5">{{ t.clause }} <span class="text-shiqing/70 ml-2">{{ t.tone_string }}</span></p>
                  </div>
                  <p v-if="m.compose.note" class="text-[11px] text-qianhui/80 mt-2">{{ m.compose.note }}</p>
                </div>
                <!-- 引用 -->
                <div v-if="m.refs" class="mt-4 pt-3 border-t border-black/5 space-y-2">
                  <div v-if="m.refs.poetries?.length" class="flex flex-wrap gap-1.5">
                    <button v-for="p in dedupePoetries(m.refs.poetries)" :key="p.poetry_id"
                      class="tag border-shiqing/30 text-shiqing hover:bg-shiqing hover:text-white transition-colors cursor-pointer"
                      @click="$router.push(`/poetry/${p.poetry_id}`)">
                      《{{ p.title }}》
                    </button>
                  </div>
                  <div v-if="m.refs.artworks?.length" class="flex gap-2">
                    <img v-for="a in m.refs.artworks" :key="a.id" :src="a.thumb_url" :alt="a.name"
                      class="w-16 h-16 object-cover rounded border border-black/10 cursor-pointer hover:scale-105 transition-transform"
                      :title="`《${a.name}》${a.dynasty}·${a.artist}`"
                      @click="$router.push(`/artworks?id=${a.id}`)" />
                  </div>
                  <div v-if="m.refs.concepts?.length" class="flex gap-1.5">
                    <router-link v-for="c in m.refs.concepts" :key="c.id" :to="`/concept/${c.id}`"
                      class="tag border-zhuqing/40 text-zhuqing hover:bg-zhuqing hover:text-white transition-colors">
                      意象 · {{ c.name }}
                    </router-link>
                  </div>
                </div>
                <p v-if="m.source" class="text-[10px] text-qianhui/70 mt-2">{{ m.source === 'llm' ? '由大模型生成（基于本地知识库检索）' : '由本地意象知识库生成' }}</p>
              </div>
            </div>
          </div>
          <div v-if="sending" class="flex">
            <div class="bg-white/80 px-5 py-3 rounded-2xl rounded-tl-sm shadow-card text-sm text-qianhui">
              思考中<span class="animate-pulse">…</span>
            </div>
          </div>
        </div>

        <!-- 输入区 -->
        <div class="border-t border-black/5 p-4">
          <!-- 问答模式 -->
          <div v-if="mode === 'ask'" class="flex gap-3">
            <input v-model="question" @keyup.enter="sendAsk" placeholder="例如：月亮在古诗里有什么含义？"
              class="flex-1 px-4 py-2.5 text-sm rounded-full border border-shiqing/25 bg-white/80
                     focus:outline-none focus:border-shiqing focus:ring-2 focus:ring-shiqing/10" />
            <button class="btn-primary !rounded-full" :disabled="sending || !question.trim()" @click="sendAsk">发送</button>
          </div>
          <!-- 创诗模式 -->
          <div v-else class="space-y-3">
            <div class="flex flex-wrap items-center gap-2 text-sm">
              <span class="text-qianhui text-xs tracking-widest mr-1">意象</span>
              <label v-for="c in conceptOptions" :key="c"
                class="tag cursor-pointer transition-all select-none"
                :class="selectedConcepts.includes(c) ? '!bg-shiqing !text-white !border-shiqing' : 'border-shiqing/30 text-shiqing hover:bg-shiqing/5'">
                <input type="checkbox" class="hidden" :value="c" v-model="selectedConcepts" />{{ c }}
              </label>
              <span class="text-qianhui text-xs tracking-widest ml-3 mr-1">体裁</span>
              <select v-model="style" class="px-3 py-1 text-sm rounded-full border border-shiqing/25 bg-white/80 focus:outline-none">
                <option v-for="s in styles" :key="s">{{ s }}</option>
              </select>
            </div>
            <div class="flex gap-3">
              <input v-model="theme" placeholder="情感基调（可选）：如 思乡 / 怀古"
                class="flex-1 px-4 py-2.5 text-sm rounded-full border border-shiqing/25 bg-white/80 focus:outline-none focus:border-shiqing" />
              <button class="btn-primary !rounded-full" :disabled="sending || !selectedConcepts.length" @click="sendCompose">创诗</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧快捷提问 -->
      <div class="space-y-4">
        <div class="card p-5">
          <h3 class="text-sm text-qianhui tracking-widest mb-3">高频问题</h3>
          <div class="space-y-2">
            <button v-for="q in quickQuestions" :key="q"
              class="w-full text-left text-sm px-4 py-2.5 rounded-md bg-white/70 border border-black/5
                     hover:border-shiqing/40 hover:text-shiqing transition-all leading-6"
              @click="askQuick(q)">
              {{ q }}
            </button>
          </div>
        </div>
        <div class="card p-5 text-xs text-qianhui leading-6">
          <h3 class="text-sm text-moyan tracking-widest mb-2">关于智能助手</h3>
          <p>问答基于本地意象知识库检索生成，所有引用诗句与古画均可溯源；配置大模型 API 后可获得更自然的表达。</p>
          <p class="mt-2">当前知识库收录意象：<router-link to="/concept/1" class="text-shiqing hover:underline">月</router-link>、<router-link to="/concept/2" class="text-shiqing hover:underline">夕阳</router-link>。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, nextTick, ref } from 'vue'
import { agentAsk, agentCompose, getConceptList } from '../api'
import SectionTitle from '../components/SectionTitle.vue'

const modes = [
  { key: 'ask', label: '意象问答' },
  { key: 'compose', label: '意象创诗' },
]
const mode = ref('ask')
const messages = ref([])
const sending = ref(false)
const msgBox = ref(null)

const question = ref('')
const conceptOptions = ref([])
const selectedConcepts = ref(['月'])
const styles = ['五言绝句', '七言绝句', '五言律诗', '七言律诗']
const style = ref('七言绝句')
const theme = ref('')

onMounted(async () => {
  const data = await getConceptList()
  conceptOptions.value = data.items.map((c) => c.name)
})

const quickQuestions = [
  '月亮在古诗里有什么含义？',
  '表达思乡之情的月亮名句有哪些？',
  '夕阳为什么总让人感到落寞？',
  '夕阳在怀古诗里扮演什么角色？',
  '哪些作品同时写到了月和夕阳？',
]

async function scrollBottom() {
  await nextTick()
  if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
}

/** 简单 Markdown → HTML */
function md(text) {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code class="bg-black/5 px-1 rounded text-xs">$1</code>')
    .replace(/^### (.+$)/gm, '<h4 class="font-semibold mt-2 mb-1">$1</h4>')
    .replace(/^## (.+$)/gm, '<h3 class="font-bold mt-3 mb-1">$1</h3>')
    .replace(/^- (.+$)/gm, '<li class="ml-4 list-disc">$1</li>')
    .replace(/\n\n/g, '</p><p>')
  return '<p>' + html + '</p>'
}

/** 引用诗篇按 poetry_id 去重（同一首诗的多条句读只显示一个入口） */
function dedupePoetries(list) {
  const seen = new Set()
  return (list || []).filter((p) => {
    if (seen.has(p.poetry_id)) return false
    seen.add(p.poetry_id)
    return true
  })
}

async function sendAsk() {
  const q = question.value.trim()
  if (!q || sending.value) return
  messages.value.push({ role: 'user', text: q })
  question.value = ''
  sending.value = true
  await scrollBottom()
  try {
    const data = await agentAsk(q)
    messages.value.push({ role: 'ai', text: data.answer, refs: data.references, source: data.source })
  } catch {
    messages.value.push({ role: 'ai', text: '服务暂时不可用，请稍后再试。' })
  } finally {
    sending.value = false
    await scrollBottom()
  }
}

function askQuick(q) {
  mode.value = 'ask'
  question.value = q
  sendAsk()
}

async function sendCompose() {
  if (!selectedConcepts.value.length || sending.value) return
  const desc = `以「${selectedConcepts.value.join('、')}」作${style.value}${theme.value ? '（' + theme.value + '）' : ''}`
  messages.value.push({ role: 'user', text: desc })
  sending.value = true
  await scrollBottom()
  try {
    const data = await agentCompose({ concepts: selectedConcepts.value, style: style.value, theme: theme.value })
    if (data.poem) {
      messages.value.push({ role: 'ai', text: '为您拟作一首：', compose: data, source: data.source })
    } else {
      messages.value.push({ role: 'ai', text: data.note || '暂未能生成。' })
    }
  } catch {
    messages.value.push({ role: 'ai', text: '创诗失败，请稍后再试。' })
  } finally {
    sending.value = false
    await scrollBottom()
  }
}

async function copyPoem(c) {
  try {
    await navigator.clipboard.writeText(`《${c.title}》\n${c.poem}`)
  } catch { /* 剪贴板不可用时静默 */ }
}
</script>
