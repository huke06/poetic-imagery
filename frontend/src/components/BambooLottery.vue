<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="lottery fixed inset-0 z-[80] flex flex-col items-center justify-center gap-6 select-none"
        @click.self="close">

        <!-- 水墨场景层（竹签升起时微虚化聚焦） -->
        <div class="scene" :class="{ 'is-focused': isStickVisible }">
          <!-- 淡墨山影 -->
          <svg class="absolute bottom-0 left-0 w-full" preserveAspectRatio="none" viewBox="0 0 1200 260" style="height: 34%">
            <path d="M0 160 Q150 60 320 130 T640 110 Q760 40 900 120 T1200 90 L1200 260 L0 260 Z" fill="#2C3C50" opacity="0.08"/>
            <path d="M0 205 Q200 130 420 180 T840 160 Q1000 120 1200 175 L1200 260 L0 260 Z" fill="#2C3C50" opacity="0.12"/>
            <path d="M0 245 Q260 200 520 232 T1200 220 L1200 260 L0 260 Z" fill="#2C3C50" opacity="0.16"/>
          </svg>
          <!-- 雾气两团，缓慢漂移 -->
          <div class="mist mist--a"></div>
          <div class="mist mist--b"></div>
          <!-- 烛光暖晕，轻微晃动 -->
          <div class="candle"></div>
        </div>

        <p class="relative z-10 font-kai text-moyan/45 text-sm tracking-[0.5em]">— 竹筒寻象 · 诚心祈问 —</p>

        <!-- 竹筒与竹签 -->
        <div class="relative z-10 flex flex-col items-center" style="margin-top: 24px">
          <!-- 升起的竹签 -->
          <div v-if="isStickVisible" class="stick">
            <div class="stick__cap"></div>
            <div class="stick__body">
              <span class="stick__seal"></span>
              <div class="stick__name font-kai">
                <template v-if="showChars">
                  <span v-for="(ch, i) in chars" :key="i" class="ink-char"
                    :style="{ animationDelay: (i * 0.3) + 's' }">{{ ch }}</span>
                </template>
              </div>
            </div>
            <div class="stick__cap stick__cap--bottom"></div>
          </div>

          <!-- 竹筒 -->
          <div class="tube" :class="{ 'is-shaking': phase === 'shaking' }">
            <!-- 墨色粒子（仅摇签时） -->
            <template v-if="phase === 'shaking'">
              <span v-for="i in 3" :key="'ink' + i" class="ink-dot" :class="'ink-dot--' + i"></span>
            </template>
            <!-- 古铜筒口 -->
            <div class="tube__rim"></div>
            <!-- 筒身 -->
            <div class="tube__body">
              <span class="tube__node tube__node--a"></span>
              <span class="tube__node tube__node--b"></span>
              <!-- 篆意「象」字铭刻（系统有篆体时自动更古拙） -->
              <span class="tube__glyph font-kai">象</span>
              <!-- 筒内签条 -->
              <div class="tube__sticks">
                <span v-for="i in 9" :key="i"
                  :style="{ height: (12 + i * 2) + 'px', '--r': ((i - 5) * 1.5) + 'deg', animationDelay: (i * 0.03) + 's' }"></span>
              </div>
            </div>
            <!-- 古铜筒底 -->
            <div class="tube__foot"></div>
            <!-- 底座 -->
            <div class="tube__base"></div>
          </div>
        </div>

        <!-- 操作区 -->
        <div class="relative z-10 flex flex-col items-center gap-4" style="min-height: 96px; margin-top: 56px">
          <button v-if="phase === 'idle'" class="seal-btn font-kai" @click.stop="start">开始寻象</button>
          <span v-else-if="phase === 'shaking'" class="font-kai text-moyan/40 text-sm tracking-[0.4em] animate-pulse">祈问中…</span>
          <template v-else-if="phase === 'done'">
            <p class="font-kai text-moyan/55 text-sm tracking-[0.4em]">今日意象 · {{ result?.name }}</p>
            <div class="flex items-center gap-4">
              <button class="seal-btn font-kai" @click.stop="$emit('explore')">探索该意象</button>
              <button class="seal-btn--outline font-kai" @click.stop="again">再求一签</button>
            </div>
          </template>
        </div>

        <p class="relative z-10 font-kai text-moyan/25 text-xs tracking-[0.3em]">轻触空白处 · 合上签筒</p>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  open: Boolean,
  result: Object,          // 抽中的意象对象（父组件随机选好传入）
})
const emit = defineEmits(['close', 'explore', 'again'])

// ── 五阶段状态机：idle → shaking → rising → ink → done ──
const phase = ref('idle')
let timers = []
function later(fn, ms) { timers.push(setTimeout(fn, ms)) }
function clearTimers() { timers.forEach(clearTimeout); timers = [] }

const chars = computed(() => (props.result?.name || '').split(''))
const isStickVisible = computed(() => ['rising', 'ink', 'done'].includes(phase.value))
const showChars = computed(() => phase.value === 'ink' || phase.value === 'done')

const SHAKE_MS = 2600
const RISE_MS = 1600

function start() {
  clearTimers()
  phase.value = 'shaking'
  playKnocks()
  later(() => { phase.value = 'rising' }, SHAKE_MS)
  later(() => { phase.value = 'ink' }, SHAKE_MS + RISE_MS)
  later(() => { phase.value = 'done' }, SHAKE_MS + RISE_MS + 500 + chars.value.length * 300)
}
function again() {
  start()                 // 本地立即重播摇签
  emit('again')           // 父组件重新随机取意象，墨显阶段读取最新 result
}
function close() { emit('close') }

watch(() => props.open, (v) => {
  if (v) { phase.value = 'idle' } else { clearTimers(); suspendAudio() }
})

// ── 竹木轻碰音效（WebAudio 合成，由疏到密；失败静默降级） ──
let audioCtx = null, noiseBuf = null
function ensureAudio() {
  if (audioCtx) return audioCtx
  const AC = window.AudioContext || window.webkitAudioContext
  if (!AC) return null
  audioCtx = new AC()
  const len = Math.floor(audioCtx.sampleRate * 0.06)
  noiseBuf = audioCtx.createBuffer(1, len, audioCtx.sampleRate)
  const d = noiseBuf.getChannelData(0)
  for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len)
  return audioCtx
}
// 竹木「笃」声 = 低频短促共鸣 + 高频轻击噪声
function knock(at) {
  const osc = audioCtx.createOscillator()
  osc.type = 'sine'
  osc.frequency.value = 190 + Math.random() * 60
  const og = audioCtx.createGain()
  og.gain.setValueAtTime(0.22, at)
  og.gain.exponentialRampToValueAtTime(0.001, at + 0.09)
  osc.connect(og).connect(audioCtx.destination)
  osc.start(at)
  osc.stop(at + 0.1)

  const src = audioCtx.createBufferSource()
  src.buffer = noiseBuf
  const bp = audioCtx.createBiquadFilter()
  bp.type = 'bandpass'
  bp.frequency.value = 1200 + Math.random() * 400
  bp.Q.value = 2
  const g = audioCtx.createGain()
  g.gain.setValueAtTime(0.14, at)
  g.gain.exponentialRampToValueAtTime(0.001, at + 0.05)
  src.connect(bp).connect(g).connect(audioCtx.destination)
  src.start(at)
}
async function playKnocks() {
  try {
    const ctx = ensureAudio()
    if (!ctx) return
    await ctx.resume()                       // 等音频上下文就绪再调度，避免丢击
    const gaps = [380, 340, 310, 280, 250, 220, 190, 165, 140]   // 由疏到密，总长约2.3s
    let t = 150
    for (const gap of gaps) { knock(ctx.currentTime + t / 1000); t += gap }
  } catch { /* 无声不影响流程 */ }
}
function suspendAudio() { try { audioCtx?.suspend() } catch {} }

onBeforeUnmount(() => { clearTimers(); try { audioCtx?.close() } catch {} })
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.35s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* ── 整体：宣纸水墨空间 ── */
.lottery {
  background: radial-gradient(ellipse at 50% 30%, #FAF6EC 0%, #F5F1E8 55%, #EAE3D2 100%);
}

/* 场景层：镜头缓慢推进；竹签升起时微虚化聚焦 */
.scene {
  position: absolute; inset: 0; overflow: hidden; pointer-events: none;
  animation: scenePush 24s ease-out forwards;
  transition: filter 1s ease;
}
.scene.is-focused { filter: blur(2px) brightness(1.03); }
@keyframes scenePush { from { transform: scale(1); } to { transform: scale(1.04); } }

/* 雾气 */
.mist {
  position: absolute; border-radius: 9999px; filter: blur(48px);
  background: rgba(255, 255, 255, 0.55); pointer-events: none;
}
.mist--a { width: 46vw; height: 22vh; left: 6%; top: 20%; animation: mistDrift 34s ease-in-out infinite alternate; }
.mist--b { width: 40vw; height: 20vh; right: 4%; bottom: 24%; animation: mistDrift 42s ease-in-out infinite alternate-reverse; }
@keyframes mistDrift {
  from { transform: translateX(-3%) translateY(0); opacity: 0.5; }
  to   { transform: translateX(4%) translateY(-2%); opacity: 0.8; }
}

/* 烛光暖晕，轻微晃动 */
.candle {
  position: absolute; right: 18%; top: 30%; width: 220px; height: 220px; border-radius: 9999px;
  background: radial-gradient(circle, rgba(217, 169, 72, 0.20) 0%, transparent 70%);
  animation: candleFlicker 3.2s ease-in-out infinite;
  pointer-events: none;
}
@keyframes candleFlicker {
  0%, 100% { opacity: 0.55; transform: scale(1); }
  45% { opacity: 0.8; transform: scale(1.03); }
  70% { opacity: 0.65; transform: scale(0.99); }
}

/* ── 竹筒 ── */
.tube { position: relative; display: flex; flex-direction: column; align-items: center; width: 200px; }
.tube.is-shaking { animation: tubeShake 2.6s cubic-bezier(0.36, 0.07, 0.19, 0.97) 1 forwards; transform-origin: bottom center; }

/* 摇签：缓起 → 渐快渐强 → 衰减归定（单次运行） */
@keyframes tubeShake {
  0%   { transform: rotate(0deg); }
  6%   { transform: rotate(-2deg) translateY(-1px); }
  12%  { transform: rotate(2deg); }
  18%  { transform: rotate(-1deg); }
  26%  { transform: rotate(4deg) translateY(-2px); }
  34%  { transform: rotate(-4.5deg) translateY(-1px); }
  42%  { transform: rotate(5deg) translateY(-2px); }
  50%  { transform: rotate(-5deg); }
  57%  { transform: rotate(4.5deg) translateY(-2px); }
  64%  { transform: rotate(-3.5deg); }
  71%  { transform: rotate(2.5deg) translateY(-1px); }
  78%  { transform: rotate(-1.8deg); }
  85%  { transform: rotate(1deg); }
  92%  { transform: rotate(-0.5deg); }
  100% { transform: rotate(0deg); }
}

/* 古铜筒口 */
.tube__rim {
  width: 160px; height: 22px; z-index: 20;
  border-radius: 9999px 9999px 0 0;
  border: 2px solid rgba(122, 90, 40, 0.45); border-bottom: 0;
  background: linear-gradient(180deg, #A8894E, #8A6D3B);
  box-shadow: 0 -2px 6px rgba(60, 45, 20, 0.25);
}
/* 淡竹黄筒身 + 细竹纹 */
.tube__body {
  position: relative; z-index: 10; width: 160px; height: 160px; overflow: hidden;
  border-left: 2px solid rgba(122, 90, 40, 0.3); border-right: 2px solid rgba(122, 90, 40, 0.3);
  background:
    repeating-linear-gradient(90deg, transparent 0 7px, rgba(120, 95, 40, 0.07) 7px 8px),
    linear-gradient(180deg, #E3D3A0 0%, #D4C08A 30%, #C9B47C 58%, #BEAA6E 100%);
  box-shadow: inset 3px 0 12px rgba(90, 70, 30, 0.18), inset -3px 0 12px rgba(90, 70, 30, 0.18);
}
/* 竹节 */
.tube__node { position: absolute; left: 0; right: 0; background: rgba(140, 110, 55, 0.35); }
.tube__node--a { top: 40%; height: 3px; box-shadow: 0 1px 2px rgba(90, 70, 30, 0.25); }
.tube__node--b { top: 75%; height: 2px; }
/* 篆意「象」铭刻 */
.tube__glyph {
  position: absolute; left: 50%; top: 56%; transform: translate(-50%, -50%);
  width: 44px; height: 44px; border-radius: 9999px;
  border: 1.5px solid rgba(122, 90, 40, 0.5);
  display: flex; align-items: center; justify-content: center;
  color: rgba(110, 82, 35, 0.75); font-size: 24px;
  background: rgba(245, 238, 214, 0.35);
}
/* 筒内签条（仅露顶端，摇签时轻颤） */
.tube__sticks {
  position: absolute; left: 12px; right: 12px; bottom: 0; height: 80%;
  display: flex; justify-content: center; align-items: flex-end; gap: 8px;
}
.tube__sticks span {
  width: 12px; border-radius: 3px 3px 0 0; opacity: 0.55;
  background: linear-gradient(180deg, #E8D9AC, #CBB77E);
  transform: rotate(var(--r, 0deg));
}
.tube.is-shaking .tube__sticks span { animation: stickRattle 0.18s linear infinite; }
@keyframes stickRattle {
  0%, 100% { transform: rotate(var(--r, 0deg)) translateY(0); }
  50% { transform: rotate(calc(var(--r, 0deg) + 1.2deg)) translateY(-2px); }
}
/* 古铜筒底 + 底座 */
.tube__foot {
  width: 160px; height: 20px;
  border-radius: 0 0 9999px 9999px;
  border: 2px solid rgba(122, 90, 40, 0.45); border-top: 0;
  background: linear-gradient(180deg, #7A5C2E, #5F4620);
  box-shadow: 0 3px 8px rgba(60, 45, 20, 0.35);
}
.tube__base {
  width: 200px; height: 28px; margin-top: -4px;
  border-radius: 9999px; border: 1px solid rgba(122, 90, 40, 0.3);
  background: linear-gradient(180deg, #8A6D3B, #5F4620);
  box-shadow: 0 6px 20px rgba(60, 45, 20, 0.4), 0 0 30px rgba(138, 109, 59, 0.15);
}

/* 墨色粒子（克制，仅摇签时浮现） */
.ink-dot {
  position: absolute; width: 6px; height: 6px; border-radius: 9999px;
  background: rgba(44, 44, 44, 0.35); filter: blur(2px); z-index: 25;
  animation: inkFloat 2.4s ease-out forwards;
}
.ink-dot--1 { left: 30%; top: 20%; animation-delay: 0.2s; }
.ink-dot--2 { left: 62%; top: 26%; animation-delay: 0.9s; }
.ink-dot--3 { left: 46%; top: 14%; animation-delay: 1.5s; }
@keyframes inkFloat {
  0% { transform: translateY(0); opacity: 0; }
  20% { opacity: 0.5; }
  100% { transform: translateY(-90px) translateX(8px); opacity: 0; }
}

/* ── 竹签 ── */
.stick {
  position: absolute; bottom: 78%; left: 50%; margin-left: -15px; z-index: 30;
  display: flex; flex-direction: column; align-items: center;
  animation: riseStick 1.6s ease-out forwards;
}
@keyframes riseStick {
  0% { transform: translateY(30px); opacity: 0; }
  25% { opacity: 1; }
  100% { transform: translateY(-130px); opacity: 1; }
}
.stick__cap {
  width: 18px; height: 12px; border-radius: 3px 3px 0 0;
  background: linear-gradient(180deg, #B08D4A, #8A6D3B);
}
.stick__cap--bottom { border-radius: 0 0 3px 3px; background: linear-gradient(180deg, #8A6D3B, #B08D4A); }
.stick__body {
  width: 30px; min-height: 150px; position: relative;
  display: flex; align-items: center; justify-content: center;
  border-left: 1px solid rgba(122, 90, 40, 0.3); border-right: 1px solid rgba(122, 90, 40, 0.3);
  background:
    repeating-linear-gradient(0deg, transparent 0 9px, rgba(120, 95, 40, 0.06) 9px 10px),
    linear-gradient(180deg, #EFE3BC 0%, #E2D3A2 20%, #D6C48C 55%, #E2D3A2 85%, #EFE3BC 100%);
  box-shadow: 3px 0 10px rgba(60, 45, 20, 0.25);
}
/* 朱砂小印 */
.stick__seal {
  position: absolute; top: 8px; left: 50%; transform: translateX(-50%);
  width: 12px; height: 12px; border-radius: 2px;
  background: #9B2C1F; opacity: 0.85;
  box-shadow: inset 0 0 0 1px rgba(245, 241, 232, 0.35);
}
/* 意象名：竖排，逐字墨显 */
.stick__name {
  writing-mode: vertical-rl;
  font-size: 20px; letter-spacing: 0.35em; color: #3A2E18;
  padding-top: 18px;
}
.ink-char {
  opacity: 0; filter: blur(4px); color: #8A7A58;
  animation: inkBleed 0.9s ease-out forwards;
}
@keyframes inkBleed {
  0% { opacity: 0; filter: blur(4px); color: #A39370; }
  60% { opacity: 0.8; filter: blur(1px); }
  100% { opacity: 1; filter: blur(0); color: #3A2E18; }
}

/* ── 朱砂印章按钮 ── */
.seal-btn {
  padding: 0.7rem 2.4rem;
  border-radius: 6px;
  background: #9B2C1F; color: #F5F1E8;
  font-size: 1rem; letter-spacing: 0.3em;
  box-shadow: inset 0 0 0 1px rgba(245, 241, 232, 0.25), 0 6px 18px rgba(155, 44, 31, 0.28);
  transition: all 0.3s ease; cursor: pointer;
}
.seal-btn:hover {
  background: #7E2419; transform: translateY(-1px);
  box-shadow: inset 0 0 0 1px rgba(245, 241, 232, 0.3), 0 10px 24px rgba(155, 44, 31, 0.35);
}
/* 朱砂描边次按钮 */
.seal-btn--outline {
  padding: 0.7rem 1.8rem;
  border-radius: 6px;
  font-size: 0.95rem; letter-spacing: 0.3em;
  color: #9B2C1F;
  background: rgba(155, 44, 31, 0.06);
  border: 1.5px solid rgba(155, 44, 31, 0.55);
  transition: all 0.3s ease; cursor: pointer;
}
.seal-btn--outline:hover { background: #9B2C1F; color: #F5F1E8; }

/* ── 减少动态效果 ── */
@media (prefers-reduced-motion: reduce) {
  .scene, .mist, .candle, .tube.is-shaking, .tube.is-shaking .tube__sticks span,
  .stick, .ink-char, .ink-dot { animation: none !important; }
  .ink-char { opacity: 1; filter: none; color: #3A2E18; }
  .stick { transform: translateY(-130px); opacity: 1; }
}
</style>
