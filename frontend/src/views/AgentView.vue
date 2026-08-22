<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <!-- 顶部标题 -->
    <SectionTitle sub="意象问答 · 格律创诗">灵犀助手</SectionTitle>

    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 mt-6">
      <!-- 对话列表 -->
      <div class="agent-card p-4 h-[640px] flex flex-col">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-song font-semibold text-sm tracking-widest">对话记录</h3>
          <button class="btn-primary !py-1 !px-3 !text-xs" :disabled="!auth.loggedIn || busy" @click="newConv">
            + 新对话
          </button>
        </div>
        <div v-if="!auth.loggedIn" class="conv-empty">
          <span class="conv-empty__seal">灵</span>
          <p><router-link to="/auth" class="text-shiqing hover:underline">登录</router-link>&nbsp;后可以保存对话记录</p>
        </div>
        <div v-else-if="!convs.length" class="conv-empty">
          <span class="conv-empty__seal">灵</span>
          <p>暂无对话，点击“新对话”开始</p>
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
      <div class="lg:col-span-3 agent-card flex flex-col h-[640px]">
        <!-- Tab -->
        <div class="px-3 pt-3">
          <div class="flex bg-white/40 rounded-lg p-1 gap-1">
            <button v-for="m in modes" :key="m.key"
              class="flex-1 py-2.5 text-sm tracking-widest rounded-md transition-all duration-300"
              :class="mode === m.key ? 'tab-active' : 'tab-idle'"
              @click="mode = m.key">
              {{ m.label }}
            </button>
          </div>
        </div>

        <!-- 内容区 -->
        <div class="flex-1 relative overflow-hidden">
          <Transition name="fade" mode="out-in">
            <!-- 意象问答：消息气泡 -->
            <div v-if="mode === 'ask'" key="ask" ref="msgBox" class="absolute inset-0 overflow-y-auto p-5 space-y-5">
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

            <!-- 意象创诗：创作台 / 诗笺 -->
            <div v-else key="compose" class="absolute inset-0 overflow-y-auto p-6">
              <div v-if="composing" class="compose-stage py-16 text-center">
                <Transition name="fade" mode="out-in">
                  <span :key="composeStage" class="compose-stage__text">{{ composeStage }}<i class="compose-cursor"></i></span>
                </Transition>
              </div>
              <div v-else-if="composeResult" class="poem-paper poem-reveal">
                <div class="poem-paper__head">
                  <span class="seal !w-5 !h-5 !text-[9px]" style="background:#9B2C1F">成</span>
                  <span class="poem-paper__label">灵犀成诗</span>
                </div>
                <h4 class="poem-paper__title">《{{ composeResult.title }}》</h4>
                <p class="poem-paper__poem">{{ composeResult.poem }}</p>
                <p class="poem-paper__foot">
                  {{ composeResult.concepts.join(' · ') }}<template v-if="composeResult.theme.length"> ｜ {{ composeResult.theme.join(' · ') }}</template>
                </p>
              </div>
              <div v-else-if="composeError" class="py-16 text-center text-sm text-qianhui">{{ composeError }}</div>
              <div v-else class="compose-empty py-16">
                <img src="/lingxi-logo.png" alt="灵犀助手" class="w-24 h-24 object-contain" />
                <p class="text-sm text-qianhui mt-4">选意象、定情感、择诗体，灵犀为你成诗</p>
              </div>
            </div>
          </Transition>
        </div>

        <!-- 输入区 -->
        <div class="border-t border-black/5 p-4">
          <div v-if="mode === 'ask'" class="flex gap-3">
            <input v-model="question" @keyup.enter="sendAsk" placeholder="例如：同时写月和夕阳的诗词有哪些？"
              class="flex-1 px-4 py-2.5 text-sm rounded-full border border-shiqing/25 bg-white/80 focus:outline-none focus:border-shiqing" />
            <button class="btn-primary !rounded-full" :disabled="sending || !question.trim()" @click="sendAsk">发送</button>
          </div>
          <div v-else>
            <Transition name="compose" mode="out-in">
              <div v-if="!composeResult" key="controls" class="space-y-3">
            <!-- 意象检索区 -->
            <div>
              <div class="flex flex-wrap items-center gap-2">
                <label v-for="c in recommendedList" :key="c" class="concept-chip cursor-pointer" :class="selectedConcepts.includes(c) ? 'is-on' : ''">
                  <input type="checkbox" class="hidden" :value="c" v-model="selectedConcepts" />{{ c }}
                </label>
                <button type="button" class="btn-outline !py-1 !px-3 !text-xs" @click="showAllConcepts = !showAllConcepts">
                  {{ showAllConcepts ? '收起' : '⌕ 更多意象' }}
                </button>
              </div>
              <Transition name="fade">
                <div v-if="showAllConcepts" class="mt-2 p-3 rounded-lg border border-black/5 bg-white/50">
                  <input v-model="conceptSearch" placeholder="搜索意象…"
                    class="w-full px-3 py-1.5 text-sm rounded-full border border-zhuqing/25 bg-white/80 focus:outline-none focus:border-zhuqing mb-2" />
                  <div class="max-h-48 overflow-y-auto flex flex-wrap gap-1.5">
                    <label v-for="c in filteredConcepts" :key="c" class="concept-chip cursor-pointer" :class="selectedConcepts.includes(c) ? 'is-on' : ''">
                      <input type="checkbox" class="hidden" :value="c" v-model="selectedConcepts" />{{ c }}
                    </label>
                  </div>
                </div>
              </Transition>
            </div>

            <!-- 创作设置行：诗体 + 情感基调 -->
            <div class="flex flex-wrap items-center gap-2">
              <div class="flex items-center gap-1">
                <button v-for="s in styles" :key="s" type="button" class="style-pill" :class="style === s ? 'is-on' : ''" @click="style = s">{{ s }}</button>
              </div>
              <div class="relative">
                <button type="button" class="tone-trigger" :class="{ 'has-tone': selectedTones.length }" @click="toneOpen = !toneOpen">
                  <template v-if="selectedTones.length">
                    <span>{{ selectedTones.join(' · ') }}</span>
                    <span class="text-xs opacity-70" @click.stop="clearTones">清除</span>
                  </template>
                  <span v-else class="text-qianhui">选择情感基调</span>
                  <span class="text-[10px] text-qianhui">{{ toneOpen ? '▲' : '▼' }}</span>
                </button>
                <Transition name="fade">
                  <div v-if="toneOpen" class="tone-panel">
                    <div class="flex flex-wrap gap-1.5">
                      <button v-for="t in EMOTION_TONES" :key="t" type="button" class="tone-chip" :class="selectedTones.includes(t) ? 'is-on' : ''" @click="toggleTone(t)">{{ t }}</button>
                    </div>
                  </div>
                </Transition>
              </div>
            </div>

            <!-- 意境摘要 + 创诗按钮 -->
            <div class="flex items-center justify-between gap-3">
              <p class="text-xs text-zhuqing/55 leading-5">{{ composeSummary }}</p>
              <button class="compose-btn" :class="{ 'is-brewing': composing }" :disabled="composing || !selectedConcepts.length" @click="sendCompose">
                <span v-if="!composing"><i class="compose-btn__star">✦</i>创诗</span>
                <span v-else>酝酿诗意…</span>
              </button>
            </div>
              </div>
              <div v-else key="result" class="flex justify-center">
                <button class="btn-outline !py-1.5 !px-5 !text-xs" @click="resetCompose">重新创作</button>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'
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
const suggestions = ref([])
const convs = ref([])
const activeConv = ref(0)

// ═══ 意象创诗 ═══
const EMOTION_TONES = [
  '喜悦', '欢愉', '赞美', '旷达', '豪迈', '闲适',
  '思乡', '怀人', '思念', '离愁', '惜别', '闺怨',
  '惆怅', '忧愁', '孤寂', '感伤', '悲凉', '悲壮',
  '怀古', '感时', '惜时', '身世感怀',
  '宁静', '清冷',
]
const recommendedConcepts = ['月', '柳', '花', '风', '云', '山', '水', '雁']
const selectedTones = ref([])          // 已选情感基调
const toneOpen = ref(false)            // 情感面板开合
const showAllConcepts = ref(false)     // 更多意象展开
const conceptSearch = ref('')          // 意象搜索词
const composeResult = ref(null)        // { title, poem, concepts, theme }
const composeError = ref('')
const composeStage = ref('')           // 创作阶段文案
const composing = ref(false)           // 酝酿中

const recommendedList = computed(() => recommendedConcepts.filter(c => conceptOptions.value.includes(c)))
const filteredConcepts = computed(() => {
  const kw = conceptSearch.value.trim()
  if (!kw) return conceptOptions.value
  return conceptOptions.value.filter(c => c.includes(kw))
})
const composeSummary = computed(() => {
  if (!selectedConcepts.value.length) return '请先选择意象'
  const concepts = selectedConcepts.value.join('、')
  if (selectedTones.value.length) return `以${concepts}为意象，营造${selectedTones.value.join('、')}的诗境`
  return `以${concepts}为意象，依${style.value}成诗`
})

function toggleTone(t) {
  const i = selectedTones.value.indexOf(t)
  if (i >= 0) selectedTones.value.splice(i, 1)
  else selectedTones.value.push(t)
}
function clearTones() { selectedTones.value = [] }
function resetCompose() {
  composeResult.value = null
  toneOpen.value = false
  showAllConcepts.value = false
}

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
  composeResult.value = null
  composeStage.value = ''
  composeError.value = ''
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
    composeResult.value = null
    composeStage.value = ''
    composeError.value = ''
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
    const result = data.data
    if (payload.mode === 'compose' && result.message) {
      result.poem = { ...extractPoem(result.message.text), note: '' }
    }
    return result
  }
  // 未登录兜底：直接用旧 agent 接口（不存历史）
  if (payload.mode === 'compose') {
    const { data: d } = await axios.post('/api/agent/compose', { concepts: payload.concepts, style: payload.style, theme: payload.theme || '' })
    const poem = d.data
    return {
      conversation_id: 0, title: '',
      message: { id: 0, role: 'ai', source: poem.source, text: `为您创作一首${poem.style}：\n\n**《${poem.title}》**\n\n${poem.poem}\n\n平仄：\n${(poem.tones || []).map(t => '· ' + t.clause + ' ' + t.tone_string).join('\n')}`, references: {} },
      poem: { title: poem.title, poem: poem.poem, note: poem.note || '' }
    }
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
  if (!selectedConcepts.value.length || composing.value) return
  const themeStr = selectedTones.value.join('、')
  const desc = `“${selectedConcepts.value.join('、')}”${style.value}${themeStr ? '（' + themeStr + '）' : ''}`
  msgs.value.push({ id: Date.now(), role: 'user', text: desc })
  composing.value = true
  composeResult.value = null
  composeError.value = ''
  const stages = ['正在取意', '正在择韵', '正在构境', '正在成篇']
  let stageIdx = 0
  composeStage.value = stages[0]
  const timer = setInterval(() => {
    stageIdx += 1
    if (stageIdx < stages.length) composeStage.value = stages[stageIdx]
  }, 800)
  try {
    const result = await sendToServer({ mode: 'compose', concepts: selectedConcepts.value, style: style.value, theme: themeStr })
    await afterSend(result)
    if (result.poem) {
      composeResult.value = {
        title: result.poem.title,
        poem: result.poem.poem,
        concepts: [...selectedConcepts.value],
        theme: [...selectedTones.value]
      }
      composeStage.value = '诗成'
      await new Promise(r => setTimeout(r, 700))
    }
  } catch {
    composeError.value = '创诗失败，请稍后再试。'
  } finally {
    clearInterval(timer)
    composing.value = false
    composeStage.value = ''
  }
}

function extractPoem(text) {
  if (!text) return { title: '', poem: '' }
  const titleMatch = text.match(/\*\*《(.+?)》\*\*/)
  const title = titleMatch ? titleMatch[1].trim() : ''
  let body = text.replace(/\*\*《.+?》\*\*/, '')
  body = body.replace(/^为您创作一首[^\n]*：?\s*/, '')
  body = body.replace(/平仄[\s\S]*$/, '')
  const lines = body.split('\n').map(s => s.trim()).filter(Boolean)
  return { title, poem: lines.join('\n') }
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
/* ═══ 引用标注（原样保留） ═══ */
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

/* ═══ 古典文房卡片 ═══ */
.agent-card {
  background: rgba(252, 249, 242, 0.72);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(44, 44, 44, 0.04);
  border-radius: 14px;
  box-shadow: 0 2px 14px rgba(44, 44, 44, 0.05);
}

/* ═══ Tab ═══ */
.tab-active {
  color: #2B4C7E;
  font-weight: 600;
  background: rgba(43, 76, 126, 0.07);
  box-shadow: inset 0 -1px 0 rgba(43, 76, 126, 0.45);
}
.tab-idle { color: #6B6B6B; }
.tab-idle:hover { color: #2B4C7E; }

/* ═══ 对话记录空状态 ═══ */
.conv-empty {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: 12px;
  text-align: center; color: #6B6B6B; font-size: 12px;
  position: relative; overflow: hidden;
  background:
    radial-gradient(circle at 20% 18%, rgba(43, 76, 126, 0.05), transparent 55%),
    radial-gradient(circle at 82% 78%, rgba(155, 68, 35, 0.05), transparent 55%);
}
.conv-empty__seal {
  display: inline-flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; border-radius: 6px;
  background: #9B2C1F; color: #F5F1E8;
  font-family: "Kaiti SC", STKaiti, KaiTi, serif; font-size: 16px;
  opacity: 0.35; writing-mode: vertical-lr;
  box-shadow: inset 0 0 0 1.5px rgba(245, 241, 232, 0.55);
}

/* ═══ 意象创诗 ═══ */
/* 意象胶囊（竹青体系） */
.concept-chip {
  display: inline-flex; align-items: center;
  padding: 3px 12px; border-radius: 999px;
  border: 1px solid rgba(91, 124, 95, 0.28);
  color: rgba(44, 44, 44, 0.72);
  background: rgba(255, 255, 255, 0.6);
  font-size: 13px; line-height: 1.6;
  transition: all 0.15s ease; user-select: none;
}
.concept-chip:hover { border-color: rgba(91, 124, 95, 0.5); }
.concept-chip.is-on {
  background: #5B7C5F; border-color: #5B7C5F; color: #fff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18);
  transform: translateY(-1px);
}

/* 诗体 pill（石青体系） */
.style-pill {
  padding: 4px 14px; border-radius: 999px;
  border: 1px solid rgba(43, 76, 126, 0.25);
  color: #2B4C7E; background: rgba(255, 255, 255, 0.6);
  font-size: 13px; line-height: 1.6;
  transition: all 0.15s ease;
}
.style-pill:hover { border-color: rgba(43, 76, 126, 0.5); }
.style-pill.is-on { background: #2B4C7E; border-color: #2B4C7E; color: #fff; }

/* 情感基调（赭石体系） */
.tone-trigger {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 14px; border-radius: 999px;
  border: 1px solid rgba(155, 68, 35, 0.28);
  color: rgba(44, 44, 44, 0.72); background: rgba(255, 255, 255, 0.6);
  font-size: 13px; line-height: 1.6;
  transition: border-color 0.15s ease; cursor: pointer;
}
.tone-trigger:hover { border-color: rgba(155, 68, 35, 0.5); }
.tone-trigger.has-tone { color: #9B4423; }
.tone-panel {
  position: absolute; bottom: calc(100% + 8px); left: 0;
  padding: 12px; border-radius: 10px;
  border: 1px solid rgba(155, 68, 35, 0.15);
  background: rgba(255, 255, 255, 0.97);
  box-shadow: 0 6px 24px rgba(44, 44, 44, 0.08);
  width: max-content; max-width: 340px; z-index: 10;
}
.tone-chip {
  padding: 3px 11px; border-radius: 999px;
  border: 1px solid rgba(155, 68, 35, 0.25);
  color: #9B4423; background: rgba(255, 255, 255, 0.6);
  font-size: 12px; line-height: 1.6;
  transition: all 0.15s ease;
}
.tone-chip:hover { border-color: rgba(155, 68, 35, 0.5); }
.tone-chip.is-on {
  background: #9B4423; border-color: #9B4423; color: #fff;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18);
}

/* 创诗按钮（视觉焦点） */
.compose-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 10px 34px; border-radius: 999px;
  background: #2B4C7E; color: #fff;
  font-family: "Noto Serif SC", "Songti SC", serif; font-size: 15px;
  letter-spacing: 0.2em; border: none; cursor: pointer;
  transition: all 0.25s ease; white-space: nowrap;
}
.compose-btn:hover:not(:disabled) { background: #24406a; }
.compose-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.compose-btn.is-brewing { animation: compose-breathe 2s ease-in-out infinite; }
.compose-btn__star { font-style: normal; color: #E3C585; font-size: 13px; }
@keyframes compose-breathe { 0%, 100% { opacity: 1; } 50% { opacity: 0.72; } }

/* 创作过程阶段 */
.compose-stage { color: rgba(44, 44, 44, 0.6); }
.compose-stage__text { font-family: "Noto Serif SC", "Songti SC", serif; font-size: 15px; letter-spacing: 0.12em; }
.compose-cursor {
  display: inline-block; width: 2px; height: 1em;
  margin-left: 3px; vertical-align: -0.1em;
  background: currentColor;
  animation: cursor-blink 1s step-end infinite;
}
@keyframes cursor-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

/* 创诗空状态 */
.compose-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; }

/* 诗笺结果卡片 */
.poem-paper {
  position: relative; width: 100%; max-width: 480px; margin: 0 auto;
  background: #FBF7EE;
  border: 1px solid rgba(44, 44, 44, 0.05); border-radius: 8px;
  padding: 30px 36px;
  box-shadow: 0 6px 24px rgba(44, 44, 44, 0.06);
}
.poem-paper::before, .poem-paper::after {
  content: ''; position: absolute; width: 16px; height: 16px;
  border-style: solid; border-color: rgba(155, 44, 31, 0.25);
}
.poem-paper::before { top: 10px; left: 10px; border-width: 1px 0 0 1px; }
.poem-paper::after { bottom: 10px; right: 10px; border-width: 0 1px 1px 0; }
.poem-paper__head { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 16px; }
.poem-paper__label { font-size: 12px; letter-spacing: 0.35em; color: rgba(44, 44, 44, 0.5); font-family: "Noto Serif SC", "Songti SC", serif; }
.poem-paper__title {
  font-family: "Noto Serif SC", "Songti SC", serif;
  font-size: 18px; font-weight: 700; text-align: center;
  color: #2C2C2C; margin-bottom: 14px;
}
.poem-paper__poem {
  font-family: "Kaiti SC", STKaiti, KaiTi, "Noto Serif SC", serif;
  font-size: 18px; line-height: 2.2; text-align: center;
  color: rgba(44, 44, 44, 0.92); white-space: pre-line;
}
.poem-paper__foot {
  margin-top: 20px; padding-top: 14px;
  border-top: 1px solid rgba(44, 44, 44, 0.06);
  text-align: center; font-size: 12px; letter-spacing: 0.15em;
  color: rgba(107, 107, 107, 0.85);
}
@keyframes poem-reveal {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}
.poem-reveal { animation: poem-reveal 0.6s ease both; }

/* 创诗控件收起过渡 */
.compose-enter-active, .compose-leave-active { transition: opacity 0.28s ease, transform 0.28s ease; }
.compose-enter-from { opacity: 0; transform: translateY(10px); }
.compose-leave-to { opacity: 0; transform: translateY(-6px); }
</style>
