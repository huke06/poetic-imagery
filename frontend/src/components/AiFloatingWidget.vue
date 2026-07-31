<!-- AI 助手悬浮窗 — 右下角，支持随时调用 -->
<template>
  <div class="ai-float-root">
    <!-- Collapsed button -->
    <Transition name="swap">
      <button v-if="!open" class="ai-float-btn" @click="open = true" title="诗象问答">
        <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
          <circle cx="16" cy="14" r="8" stroke="#F5F1E8" stroke-width="2"/>
          <path d="M10 24 C10 20 22 20 22 24" stroke="#F5F1E8" stroke-width="2" stroke-linecap="round"/>
          <circle cx="12" cy="12" r="1.5" fill="#F5F1E8"/>
          <circle cx="20" cy="12" r="1.5" fill="#F5F1E8"/>
        </svg>
      </button>
    </Transition>

    <!-- Expanded window -->
    <Transition name="slide">
      <div v-if="open" class="ai-float-card">
        <div class="ai-float-head">
          <span class="font-kai text-sm font-bold text-moyan/80">诗象问答</span>
          <button class="ai-float-close" @click="open = false">×</button>
        </div>

        <div class="ai-float-body" ref="bodyRef">
          <div v-if="!msgs.length" class="text-center text-qianhui/50 text-xs py-16">
            <p class="font-kai text-base mb-2">何以解诗？</p>
            <p>问意象、问诗句、问诗人…</p>
          </div>
          <div v-for="(m, i) in msgs" :key="i" class="mb-3">
            <div v-if="m.role === 'user'" class="flex justify-end">
              <span class="ai-bubble-user">{{ m.text }}</span>
            </div>
            <div v-else class="flex justify-start">
              <span class="ai-bubble-ai" v-text="m.text"></span>
            </div>
          </div>
          <div v-if="loading" class="flex justify-start mb-3">
            <span class="ai-bubble-ai thinking-dots">
              <span class="dot-bounce" style="animation-delay:0s">●</span>
              <span class="dot-bounce" style="animation-delay:0.15s">●</span>
              <span class="dot-bounce" style="animation-delay:0.3s">●</span>
            </span>
          </div>
        </div>

        <div class="ai-float-foot">
          <input v-model="input" @keyup.enter="send"
            placeholder="问意象、诗句…" class="ai-input"
            :disabled="loading" />
          <button class="ai-send-btn" @click="send" :disabled="loading || !input.trim()">→</button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import { agentAsk } from '../api'

const open = ref(false)
const input = ref('')
const msgs = ref([])
const loading = ref(false)
const bodyRef = ref(null)

async function send() {
  const q = input.value.trim()
  if (!q || loading.value) return
  msgs.value.push({ role: 'user', text: q })
  input.value = ''
  loading.value = true
  await nextTick()
  if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  try {
    const resp = await agentAsk(q)
    msgs.value.push({ role: 'ai', text: resp.answer.replace(/\*\*/g, '').replace(/###?\s?/g, '') })
  } catch {
    msgs.value.push({ role: 'ai', text: '抱歉，暂时无法回答。请稍后再试。' })
  } finally {
    loading.value = false
    await nextTick()
    if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  }
}

watch(open, async (v) => {
  if (v) await nextTick()
  if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
})
</script>

<style scoped>
.ai-float-root { position: fixed; right: 20px; bottom: 20px; z-index: 81; }

.ai-float-btn {
  width: 48px; height: 48px; border-radius: 50%;
  background: #2B4C7E; border: none; cursor: pointer;
  box-shadow: 0 4px 18px rgba(43,76,126,0.35);
  display: flex; align-items: center; justify-content: center;
  transition: all 0.3s;
}
.ai-float-btn:hover { transform: scale(1.08); box-shadow: 0 6px 24px rgba(43,76,126,0.5); }

.ai-float-card {
  position: absolute; bottom: 56px; right: 0;
  width: 340px; height: 420px;
  background: rgba(245,241,232,0.96); backdrop-filter: blur(14px);
  border: 1px solid rgba(160,135,100,0.2); border-radius: 12px;
  box-shadow: 0 10px 40px rgba(80,55,20,0.15);
  display: flex; flex-direction: column; overflow: hidden;
}
.ai-float-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; border-bottom: 1px solid rgba(160,135,100,0.12);
  flex-shrink: 0;
}
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
  padding: 6px 12px; border-radius: 12px 12px 12px 2px; max-width: 85%;
  word-break: break-word; line-height: 1.6; white-space: pre-line;
}
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
