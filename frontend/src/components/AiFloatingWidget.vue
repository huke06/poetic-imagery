<!-- AI 助手悬浮窗 — 右下角，支持随时调用 · 可沿右侧拖拽调整位置 · 多轮对话 -->
<template>
  <div class="ai-float-root" :style="{ bottom: bottom + 'px', right: right + 'px' }">
    <!-- Collapsed button -->
    <Transition name="swap">
      <button v-if="!open" class="ai-float-btn" @pointerdown="onPointerDown" @click="onBtnClick" title="诗象问答（可拖拽移动）">
        <img src="/lingxi-logo.png" alt="灵犀" class="w-8 h-8 object-contain rounded-full" />
      </button>
    </Transition>

    <!-- Expanded window -->
    <Transition name="slide">
      <div v-if="open" class="ai-float-card">
        <div class="ai-float-head" @pointerdown="onPointerDown" title="拖拽移动">
          <span class="font-kai text-sm font-bold text-moyan/80">诗象问答 · 灵犀</span>
          <button class="ai-float-close no-drag" @click="open = false">×</button>
        </div>

        <div class="ai-float-body" ref="bodyRef">
          <div v-if="!msgs.length && !loading" class="text-center text-qianhui/50 text-xs py-10 px-2">
            <p class="font-kai text-base mb-2">何以解诗？</p>
            <p>问意象、问诗句、问诗人，也可与我闲聊…</p>
            <div class="flex flex-col gap-1.5 mt-4 text-left">
              <button v-for="q in starterQuestions" :key="q" class="ai-suggest" @click="send(q)">{{ q }}</button>
            </div>
          </div>
          <div v-for="(m, i) in msgs" :key="i" class="mb-3">
            <div v-if="m.role === 'user'" class="flex justify-end">
              <span class="ai-bubble-user">{{ m.text }}</span>
            </div>
            <div v-else class="flex flex-col items-start" @click="onCiteClick($event, i)">
              <span class="ai-bubble-ai" v-html="renderText(m.text)"></span>
              <div v-if="m.refs && m.refs.length" class="flex flex-wrap gap-1 mt-1.5">
                <button v-for="r in m.refs" :key="r.key" :id="r.idx != null ? 'ai-cite-' + i + '-' + r.idx : null"
                  class="ai-ref" @click="goRef(r.to)">
                  <span v-if="r.idx != null" class="ai-ref-idx">[{{ r.idx }}]</span>{{ r.label }}
                </button>
              </div>
            </div>
          </div>
          <div v-if="loading" class="flex justify-start mb-3">
            <span class="ai-bubble-ai thinking-dots">
              <span class="dot-bounce" style="animation-delay:0s">●</span>
              <span class="dot-bounce" style="animation-delay:0.15s">●</span>
              <span class="dot-bounce" style="animation-delay:0.3s">●</span>
            </span>
          </div>
          <div v-if="suggestions.length && !loading" class="flex flex-wrap gap-1.5 mt-1">
            <button v-for="s in suggestions" :key="s" class="ai-suggest" @click="send(s)">{{ s }}</button>
          </div>
        </div>

        <div class="ai-float-foot">
          <input v-model="input" @keyup.enter="send()"
            placeholder="问意象、诗句，或聊聊诗词…" class="ai-input"
            :disabled="loading" />
          <button class="ai-send-btn" @click="send()" :disabled="loading || !input.trim()">→</button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { agentAsk } from '../api'
import { useFreeDrag } from '../composables/useFreeDrag'

const open = ref(false)
// 展开后可上下 + 左右自由移动；收起后吸附回右侧
const { right, bottom, onPointerDown, wasDragged, resetRight } = useFreeDrag('sxz_ai_float_pos', 20, 20)

const input = ref('')
const msgs = ref([])
const loading = ref(false)
const bodyRef = ref(null)
const history = ref([])        // 多轮对话历史（传给后端解析指代）
const suggestions = ref([])    // 后端返回的追问建议
const starterQuestions = [
  '“月”在古诗里有哪些含义？',
  '夕阳为什么总与离愁相伴？',
  '同时写月和夕阳的诗词有哪些？',
]

// 区分点击与拖拽：拖拽后不触发打开
function onBtnClick() {
  if (!wasDragged()) open.value = true
}

// 轻量富文本：加粗 / 换行 / 列表，其余转义防止注入
function renderText(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(new RegExp(String.fromCharCode(10), 'g'), '<br>')
    .replace(/^[-·•]\s?(.+)$/gm, '· $1')
    .replace(/\[(\d+)\]/g, '<sup class="cite-link" data-cite="$1">[$1]</sup>')
}

async function send(q) {
  const question = (q || input.value || '').trim()
  if (!question || loading.value) return
  msgs.value.push({ role: 'user', text: question })
  input.value = ''
  loading.value = true
  suggestions.value = []
  history.value.push({ role: 'user', content: question })
  await nextTick()
  if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  try {
    const resp = await agentAsk(question, history.value.slice(-8))
    msgs.value.push({ role: 'ai', text: resp.answer || '暂无回答', refs: buildRefs(resp.references) })
    history.value.push({ role: 'ai', content: resp.answer || '' })
    suggestions.value = (resp.suggestions || []).slice(0, 3)
  } catch {
    msgs.value.push({ role: 'ai', text: '抱歉，暂时无法回答。请稍后再试。' })
  } finally {
    loading.value = false
    await nextTick()
    if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  }
}

watch(open, async (v) => {
  if (!v) resetRight()
  if (v) await nextTick()
  if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
})

const router = useRouter()
function buildRefs(references) {
  if (!references) return []
  const out = []
  const cits = references.citations
  if (Array.isArray(cits) && cits.length) {
    for (const r of cits) {
      if (r.type === 'poetry') out.push({ idx: r.idx, kind: 'poetry', label: '《' + (r.title || '') + '》', to: '/poetry/' + r.poetry_id, key: 'c' + r.idx })
      else if (r.type === 'concept') out.push({ idx: r.idx, kind: 'concept', label: r.name, to: '/concept/' + r.concept_id, key: 'c' + r.idx })
      else if (r.type === 'artwork') out.push({ idx: r.idx, kind: 'artwork', label: '《' + (r.name || '') + '》', to: '/artworks?id=' + r.artwork_id, key: 'c' + r.idx })
    }
    return out.slice(0, 8)
  }
  const push = (kind, label, to) => out.push({ idx: null, kind, label, to, key: kind + to + label })
  for (const p of references.poetries || []) push('poetry', '《' + (p.title || '') + '》', '/poetry/' + p.poetry_id)
  for (const c of references.concepts || []) push('concept', c.name, '/concept/' + c.id)
  for (const a of references.artworks || []) push('artwork', '《' + (a.name || '') + '》', '/artworks?id=' + a.id)
  return out.slice(0, 6)
}

function onCiteClick(e, msgIdx) {
  const sup = e.target && e.target.closest ? e.target.closest('.cite-link') : null
  if (!sup) return
  const n = sup.getAttribute('data-cite')
  const el = document.getElementById('ai-cite-' + msgIdx + '-' + n)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    el.classList.add('ai-ref-flash')
    setTimeout(() => el.classList.remove('ai-ref-flash'), 1800)
  }
}
function goRef(to) { router.push(to) }

// 供首页「向灵犀助手提问」等入口触发：window 派发 sxz-ask 事件后自动打开并提问
function onAskEvent(e) {
  const q = e.detail?.question || e.detail
  if (!q) return
  open.value = true
  if (q !== input.value) input.value = ''
  send(q)
}
onMounted(() => window.addEventListener('sxz-ask', onAskEvent))
onBeforeUnmount(() => window.removeEventListener('sxz-ask', onAskEvent))
</script>

<style scoped>
.ai-float-root { position: fixed; z-index: 81; }

.ai-float-btn {
  width: 48px; height: 48px; border-radius: 50%;
  background: transparent; border: none; cursor: grab;
  box-shadow: 0 4px 18px rgba(80,55,20,0.18);
  display: flex; align-items: center; justify-content: center;
  transition: box-shadow 0.3s;
  user-select: none; touch-action: none;
}
.ai-float-btn:active { cursor: grabbing; }
.ai-float-btn:hover { box-shadow: 0 6px 24px rgba(80,55,20,0.25); }

.ai-float-card {
  position: absolute; bottom: 56px; right: 0;
  width: 340px; height: 440px;
  background: rgba(245,241,232,0.96); backdrop-filter: blur(14px);
  border: 1px solid rgba(160,135,100,0.2); border-radius: 12px;
  box-shadow: 0 10px 40px rgba(80,55,20,0.15);
  display: flex; flex-direction: column; overflow: hidden;
}
.ai-float-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; border-bottom: 1px solid rgba(160,135,100,0.12);
  flex-shrink: 0;
  cursor: grab; user-select: none; touch-action: none;
}
.ai-float-head:active { cursor: grabbing; }
.ai-float-close {
  font-size: 18px; color: #9A8B70; cursor: pointer;
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
  border-radius: 50%; border: none; background: none;
}
.ai-float-close:hover { background: rgba(0,0,0,0.05); color: #6B5B40; }
.ai-float-body {
  flex: 1; overflow-y: auto; padding: 12px 14px;
  display: flex; flex-direction: column; gap: 2px;
}
.ai-bubble-user {
  background: #2B4C7E; color: #F5F1E8; font-size: 12px;
  padding: 6px 12px; border-radius: 12px 12px 2px 12px; max-width: 80%;
  word-break: break-word; line-height: 1.6;
}
.ai-bubble-ai {
  background: rgba(43,76,126,0.08); color: #2C2C2C; font-size: 12px;
  padding: 6px 12px; border-radius: 12px 12px 12px 2px; max-width: 88%;
  word-break: break-word; line-height: 1.7; white-space: normal;
}
.ai-bubble-ai :deep(b) { color: #2B4C7E; }
.ai-suggest {
  display: block; width: 100%; text-align: left;
  font-size: 11px; padding: 6px 10px; color: #2B4C7E;
  border: 1px solid rgba(43,76,126,0.22); border-radius: 8px;
  background: rgba(43,76,126,0.04); cursor: pointer; transition: all 0.15s;
}
.ai-suggest:hover { background: rgba(43,76,126,0.1); border-color: #2B4C7E; }
.ai-ref {
  font-size: 11px; padding: 2px 8px; color: #2B4C7E;
  border: 1px solid rgba(43,76,126,0.25); border-radius: 6px;
  background: rgba(43,76,126,0.05); cursor: pointer; transition: all 0.15s;
}
.ai-ref:hover { background: rgba(43,76,126,0.12); border-color: #2B4C7E; }
.ai-ref-idx { color: #2B4C7E; font-weight: 700; margin-right: 2px; }
.ai-ref-flash { background: rgba(43,76,126,0.14) !important; box-shadow: 0 0 0 2px rgba(43,76,126,0.35); }
.cite-link { color: #2B4C7E; font-weight: 700; cursor: pointer; font-size: 0.75em; vertical-align: super; line-height: 0; padding: 0 1px; }
.cite-link:hover { text-decoration: underline; }
.thinking-dots {
  display: flex; align-items: center; gap: 3px;
  padding: 10px 16px;
}
.dot-bounce {
  font-size: 8px; color: #2B4C7E;
  animation: bounce 0.6s ease-in-out infinite;
}
@keyframes bounce {
  0%, 100% { opacity: 0.2; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-4px); }
}
.ai-float-foot {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px; border-top: 1px solid rgba(160,135,100,0.12); flex-shrink: 0;
}
.ai-input {
  flex: 1; padding: 6px 10px; font-size: 12px;
  border: 1px solid rgba(160,135,100,0.2); border-radius: 8px;
  background: rgba(255,255,255,0.6); outline: none;
  font-family: inherit;
}
.ai-input:focus { border-color: #2B4C7E; }
.ai-send-btn {
  width: 30px; height: 30px; border-radius: 50%; border: none;
  background: #2B4C7E; color: #F5F1E8; font-size: 16px; cursor: pointer;
  flex-shrink: 0; display: flex; align-items: center; justify-content: center;
}
.ai-send-btn:disabled { opacity: 0.4; cursor: default; }

.swap-enter-active,.swap-leave-active { transition: all 0.2s; }
.swap-enter-from,.swap-leave-to { opacity: 0; transform: scale(0.7); }
.slide-enter-active { transition: all 0.25s cubic-bezier(0.16,1,0.3,1); }
.slide-leave-active { transition: all 0.2s; }
.slide-enter-from { opacity: 0; transform: translateY(12px) scale(0.94); }
.slide-leave-to { opacity: 0; transform: translateY(8px) scale(0.96); }
</style>
