<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <SectionTitle sub="轻量 RAG · 对话记录持久化">灵犀助手</SectionTitle>
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 mt-6">
      <!-- 对话列表 -->
      <div class="card p-4 h-[640px] flex flex-col">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-song font-bold text-sm">对话记录</h3>
          <button class="btn-primary !py-1 !px-3 !text-xs" :disabled="!auth.loggedIn || busy" @click="newConv">
            + 新对话
          </button>
        </div>
        <div v-if="!auth.loggedIn" class="flex-1 flex items-center justify-center text-xs text-qianhui">
          <router-link to="/auth" class="text-shiqing hover:underline">登录</router-link>&nbsp;后可以保存对话记录
        </div>
        <div v-else-if="!convs.length" class="flex-1 flex items-center justify-center text-xs text-qianhui">
          暂无对话，点击“新对话”开始
        </div>
        <div v-else class="flex-1 overflow-y-auto space-y-1">
          <div v-for="c in convs" :key="c.id" class="flex items-center gap-2 px-2 py-1.5 rounded text-sm cursor-pointer transition-colors"
            :class="activeConv === c.id ? 'bg-shiqing/10 text-shiqing font-semibold' : 'hover:bg-black/5 text-moyan/80'"
            @click="selectConv(c.id)">
            <span class="flex-1 truncate text-xs">{{ c.title }}</span>
            <button class="text-zhusha hover:opacity-70 shrink-0 text-xs" @click.stop="delConv(c.id)">×</button>
          </div>
        </div>
      </div>

      <!-- 对话区 -->
      <div class="lg:col-span-3 card flex flex-col h-[640px]">
        <div class="flex border-b border-black/5">
          <button v-for="m in modes" :key="m.key"
            class="flex-1 py-3 text-sm tracking-widest transition-colors"
            :class="mode === m.key ? 'text-shiqing font-semibold border-b-2 border-shiqing bg-shiqing/5' : 'text-qianhui hover:text-shiqing'"
            @click="mode = m.key">
            {{ m.label }}
          </button>
        </div>
        <div ref="msgBox" class="flex-1 overflow-y-auto p-5 space-y-5">
          <div v-if="!msgs.length" class="h-full flex flex-col items-center justify-center text-qianhui gap-3">
            <img src="/lingxi-logo.png" alt="灵犀助手" class="w-14 h-14 object-contain" />
            <p class="text-sm">{{ auth.loggedIn ? '开始新的对话吧' : '登录后可保存对话' }}</p>
          </div>
          <div v-for="m in msgs" :key="m.id">
            <div class="flex" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
              <div class="max-w-[85%]">
                <div v-if="m.role === 'user'" class="bg-shiqing text-white px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm leading-7 shadow-card">
                  {{ m.text }}
                </div>
                <div v-else class="bg-white/80 px-5 py-4 rounded-2xl rounded-tl-sm shadow-card border border-black/5" @click="onCiteClick($event, m)">
                  <div class="text-sm leading-7 text-moyan/90 whitespace-pre-wrap" v-html="renderAnswer(m.text)"></div>
                  <div v-if="refCards(m).length" class="mt-4 pt-3 border-t border-black/5">
                    <div class="text-[10px] text-qianhui tracking-widest mb-1.5">参考出处</div>
                    <div v-for="c in refCards(m)" :key="c.key"
                      :id="c.idx != null ? 'cite-' + m.id + '-' + c.idx : null"
                      class="cite-card flex items-center gap-2 text-xs cursor-pointer rounded px-2 py-1.5 -mx-1 hover:bg-black/5 transition-colors"
                      @click="$router.push(c.to)">
                      <span v-if="c.idx != null" class="cite-badge shrink-0">[{{ c.idx }}]</span>
                      <span class="font-song truncate" :class="c.kind === 'concept' ? 'text-zhuqing' : c.kind === 'artwork' ? 'text-zheshi' : 'text-shiqing'">{{ c.label }}</span>
                      <span class="text-[10px] text-qianhui/70 truncate">{{ c.sub }}</span>
                      <span class="ml-auto shrink-0 text-[10px] text-qianhui/50">{{ c.kindLabel }}</span>
                    </div>
                  </div>
                  <p v-if="m.source" class="text-[10px] mt-2" :class="sourceClass(m.source)">{{ sourceLabel(m.source) }}</p>
                </div>
              </div>
            </div>
          </div>
          <div v-if="sending" class="flex"><div class="bg-white/80 px-5 py-3 rounded-2xl rounded-tl-sm shadow-card text-sm text-qianhui">思考中<span class="animate-pulse">&hellip;</span></div></div>
          <div v-if="suggestions.length && !sending" class="flex flex-wrap gap-2 justify-center pt-1">
            <button v-for="s in suggestions" :key="s"
              class="tag border-shiqing/30 text-shiqing hover:bg-shiqing hover:text-white transition-colors cursor-pointer !text-xs !py-1.5 !px-3 !rounded-full"
              @click="sendAsk(s)">{{ s }}</button>
          </div>
        </div>

        <div class="border-t border-black/5 p-4">
          <div v-if="mode === 'ask'" class="flex gap-3">
            <input v-model="question" @keyup.enter="sendAsk" placeholder="例如：同时写月和夕阳的诗词有哪些？"
              class="flex-1 px-4 py-2.5 text-sm rounded-full border border-shiqing/25 bg-white/80 focus:outline-none focus:border-shiqing" />
            <button class="btn-primary !rounded-full" :disabled="sending || !question.trim()" @click="sendAsk">发送</button>
          </div>
          <div v-else class="space-y-3">
            <div class="flex flex-wrap items-center gap-2 text-sm">
              <label v-for="c in conceptOptions" :key="c" class="tag cursor-pointer transition-all"
                :class="selectedConcepts.includes(c) ? '!bg-shiqing !text-white !border-shiqing' : 'border-shiqing/30 text-shiqing hover:bg-shiqing/5'">
                <input type="checkbox" class="hidden" :value="c" v-model="selectedConcepts" />{{ c }}
              </label>
              <select v-model="style" class="px-3 py-1 text-sm rounded-full border border-shiqing/25 bg-white/80 focus:outline-none">
                <option v-for="s in styles" :key="s">{{ s }}</option>
              </select>
            </div>
            <div class="flex gap-3">
              <input v-model="theme" placeholder="情感基调（可选）" class="flex-1 px-4 py-2.5 text-sm rounded-full border border-shiqing/25 bg-white/80 focus:outline-none focus:border-shiqing" />
              <button class="btn-primary !rounded-full" :disabled="sending || !selectedConcepts.length" @click="sendCompose">创诗</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { getConceptList } from '../api'
import { auth } from '../stores/auth'
import SectionTitle from '../components/SectionTitle.vue'
import axios from 'axios'

const modes = [{ key: 'ask', label: '意象问答' }, { key: 'compose', label: '意象创诗' }]
const mode = ref('ask')
const msgs = ref([])
const sending = ref(false)
const busy = ref(false)
const msgBox = ref(null)
const question = ref('')
const conceptOptions = ref([])
const selectedConcepts = ref(['月'])
const styles = ['五言绝句', '七言绝句', '五言律诗', '七言律诗']
const style = ref('七言绝句')
const theme = ref('')
const suggestions = ref([])
const convs = ref([])
const activeConv = ref(0)

function authHeaders() {
  const t = auth.token
  return t ? { Authorization: `Bearer ${t}` } : {}
}

async function afterSend(data) {
  activeConv.value = data.conversation_id
  await loadConvs()
  if (data.message) {
    msgs.value.push({ id: Date.now(), role: 'ai', text: data.message.text, source: data.message.source, references: data.message.references })
  }
  suggestions.value = data.suggestions || []
  await scrollBottom()
}

async function loadConvs() {
  if (!auth.loggedIn) return
  try {
    const { data } = await axios.get('/api/chat/conversations', { headers: authHeaders() })
    convs.value = data.data
  } catch { convs.value = [] }
}

async function selectConv(id) {
  activeConv.value = id
  msgs.value = []
  try {
    const { data } = await axios.get(`/api/chat/conversations/${id}/messages`, { headers: authHeaders() })
    msgs.value = data.data.map(m => ({ ...m, references: m.references || {} }))
  } catch { msgs.value = [] }
  await scrollBottom()
}

async function newConv() {
  busy.value = true
  try {
    const { data } = await axios.post('/api/chat/conversations', null, { headers: authHeaders(), params: { source: mode.value } })
    activeConv.value = data.data.id
    msgs.value = []
    await loadConvs()
  } finally { busy.value = false }
}

async function delConv(id) {
  if (!confirm('删除此对话？')) return
  await axios.delete(`/api/chat/conversations/${id}`, { headers: authHeaders() })
  if (activeConv.value === id) { activeConv.value = 0; msgs.value = [] }
  await loadConvs()
}

async function sendToServer(payload) {
  if (!auth.loggedIn || !activeConv.value) {
    try { await newConv() } catch { /* 未登录时不建会话，用旧接口兜底 */ }
  }
  const convId = activeConv.value
  if (auth.loggedIn && convId) {
    const { data } = await axios.post('/api/chat/send', { conversation_id: convId, ...payload }, { headers: authHeaders() })
    return data.data
  }
  // 未登录兜底：直接用旧 agent 接口（不存历史）
  if (payload.mode === 'compose') {
    const { data: d } = await axios.post('/api/agent/compose', { concepts: payload.concepts, style: payload.style, theme: payload.theme || '' })
    const poem = d.data
    return { conversation_id: 0, title: '', message: { id: 0, role: 'ai', source: poem.source, text: `为您创作一首${poem.style}：\n\n**《${poem.title}》**\n\n${poem.poem}\n\n平仄：\n${(poem.tones||[]).map(t => '· '+t.clause+' '+t.tone_string).join('\n')}`, references: {} } }
  }
  const { data: d } = await axios.post('/api/agent/ask', { question: payload.question })
  return { conversation_id: 0, title: '', message: { id: 0, role: 'ai', text: d.data.answer, source: d.data.source, references: d.data.references || {} } }
}

async function sendAsk(q) {
  const text = (typeof q === 'string' ? q : question.value).trim()
  if (!text || sending.value) return
  msgs.value.push({ id: Date.now(), role: 'user', text })
  question.value = ''
  sending.value = true
  suggestions.value = []
  await scrollBottom()
  try { await afterSend(await sendToServer({ mode: 'ask', question: text })) }
  catch { msgs.value.push({ id: Date.now(), role: 'ai', text: '服务暂不可用，请稍后再试。' }) }
  finally { sending.value = false; await scrollBottom() }
}

async function sendCompose() {
  if (!selectedConcepts.value.length || sending.value) return
  const desc = `“${selectedConcepts.value.join('、')}”${style.value}${theme.value ? '（' + theme.value + '）' : ''}`
  msgs.value.push({ id: Date.now(), role: 'user', text: desc })
  sending.value = true
  await scrollBottom()
  try { await afterSend(await sendToServer({ mode: 'compose', concepts: selectedConcepts.value, style: style.value, theme: theme.value })) }
  catch { msgs.value.push({ id: Date.now(), role: 'ai', text: '创诗失败，请稍后再试。' }) }
  finally { sending.value = false; await scrollBottom() }
}

async function scrollBottom() {
  await nextTick()
  if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
}

function sourceClass(s) { return s === 'llm' ? 'text-zhuqing' : s === 'llm_free' ? 'text-zheshi' : 'text-qianhui' }
function sourceLabel(s) {
  if (s === 'llm') return '✦ DeepSeek 基于本地意象知识库作答'
  if (s === 'llm_free') return '✦ DeepSeek 自由回答（未锚定意象库）'
  return '由本地知识库生成'
}
function renderAnswer(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
    .replace(/\[(\d+)\]/g, '<sup class="cite-link" data-cite="$1">[$1]</sup>')
}

function refCards(m) {
  const refs = m.references || {}
  const cards = []
  const cits = refs.citations
  if (Array.isArray(cits) && cits.length) {
    for (const r of cits) {
      if (r.type === 'poetry') cards.push({ idx: r.idx, kind: 'poetry', kindLabel: '诗文', label: '《' + (r.title || '') + '》', sub: [r.dynasty, r.author].filter(Boolean).join(' · '), to: '/poetry/' + r.poetry_id })
      else if (r.type === 'concept') cards.push({ idx: r.idx, kind: 'concept', kindLabel: '意象', label: r.name, sub: '意象', to: '/concept/' + r.concept_id })
      else if (r.type === 'artwork') cards.push({ idx: r.idx, kind: 'artwork', kindLabel: '古画', label: '《' + (r.name || '') + '》', sub: [r.dynasty, r.artist].filter(Boolean).join(' · '), to: '/artworks?id=' + r.artwork_id })
    }
    return cards.map((c, i) => ({ ...c, key: 'c' + c.idx + '-' + i }))
  }
  for (const p of refs.poetries || []) cards.push({ idx: null, kind: 'poetry', kindLabel: '诗文', label: '《' + (p.title || '') + '》', sub: [p.dynasty, p.author].filter(Boolean).join(' · '), to: '/poetry/' + p.poetry_id })
  for (const c of refs.concepts || []) cards.push({ idx: null, kind: 'concept', kindLabel: '意象', label: c.name, sub: '意象', to: '/concept/' + c.id })
  for (const a of refs.artworks || []) cards.push({ idx: null, kind: 'artwork', kindLabel: '古画', label: '《' + (a.name || '') + '》', sub: [a.dynasty, a.artist].filter(Boolean).join(' · '), to: '/artworks?id=' + a.id })
  return cards.map((c, i) => ({ ...c, key: 'f' + i + '-' + c.to + '-' + c.label }))
}

function onCiteClick(e, m) {
  const sup = e.target && e.target.closest ? e.target.closest('.cite-link') : null
  if (!sup) return
  const n = sup.getAttribute('data-cite')
  const el = document.getElementById('cite-' + m.id + '-' + n)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    el.classList.add('cite-flash')
    setTimeout(() => el.classList.remove('cite-flash'), 1800)
  }
}

onMounted(async () => {
  const data = await getConceptList()
  conceptOptions.value = data.items.map(c => c.name)
  await auth.init()
  await loadConvs()
  if (auth.loggedIn && convs.value.length) selectConv(convs.value[0].id)
})
</script>

<style scoped>
.cite-link {
  color: #2B4C7E; font-weight: 700; cursor: pointer;
  font-size: 0.75em; vertical-align: super; line-height: 0;
  padding: 0 1px;
}
.cite-link:hover { text-decoration: underline; }
.cite-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 20px; height: 20px; padding: 0 4px;
  border-radius: 5px; font-size: 10px; font-weight: 700;
  background: rgba(43,76,126,0.1); color: #2B4C7E;
}
.cite-card { transition: background 0.15s, box-shadow 0.15s; }
.cite-flash {
  background: rgba(43,76,126,0.1) !important;
  box-shadow: 0 0 0 2px rgba(43,76,126,0.35);
  border-radius: 6px;
}
</style>
