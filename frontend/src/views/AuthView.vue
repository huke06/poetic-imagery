<template>
  <div v-if="auth.user" class="max-w-2xl mx-auto px-4 py-10 space-y-8">
    <!-- Profile card -->
    <div class="card p-8 text-center">
      <div class="seal !w-16 !h-16 !text-xl mx-auto">{{ auth.user.username[0] }}</div>
      <h1 class="font-song text-2xl font-bold mt-4">{{ auth.user.username }}</h1>
      <p class="text-sm text-qianhui mt-1">{{ auth.user.role === 'admin' ? '管理员' : '用户' }}</p>
      <div class="flex justify-center gap-3 mt-5">
        <router-link to="/" class="btn-primary !text-xs !py-1.5">回到首页</router-link>
        <button class="btn-outline !text-xs !py-1.5" @click="auth.logout()">退出登录</button>
      </div>
    </div>

    <!-- ═══ 诗旅手帖 ═══ -->
    <div class="card p-6">
      <h2 class="font-song text-lg font-bold flex items-center gap-2">
        <span>🍂</span> 诗旅手帖
      </h2>

      <!-- Stats + Leaf canvas -->
      <div v-if="exploredList.length" class="flex flex-wrap gap-6 mt-4 text-sm">
        <div class="bg-shiqing/5 rounded-lg px-4 py-3 text-center">
          <div class="text-2xl font-bold text-zheshi" style="font-family:'Cormorant Garamond',serif">{{ exploredList.length }}</div>
          <div class="text-[10px] text-qianhui mt-1">已探索意象</div>
        </div>
        <div class="bg-shiqing/5 rounded-lg px-4 py-3 text-center">
          <div class="text-2xl font-bold text-zheshi" style="font-family:'Cormorant Garamond',serif">{{ exploredThemes.length }}</div>
          <div class="text-[10px] text-qianhui mt-1">跨越主题族</div>
        </div>
      </div>

      <!-- Achievements -->
      <div v-if="achievements.length" class="mt-5">
        <h3 class="text-sm font-semibold tracking-widest text-moyan/70 mb-3">🏅 已获成就</h3>
        <div class="flex flex-wrap gap-2">
          <span v-for="a in achievements" :key="a.id"
            class="text-xs px-3 py-1.5 rounded-full border"
            :style="{ color: '#9B6820', borderColor: '#C8983855', background: '#FDF5E6' }">
            {{ a.icon }} {{ a.name }} — {{ a.desc }}
          </span>
        </div>
      </div>

      <!-- Theme progress -->
      <div v-if="Object.keys(themeProgress).length" class="mt-4">
        <h3 class="text-sm font-semibold tracking-widest text-moyan/70 mb-2">主题进度</h3>
        <div class="space-y-1.5">
          <div v-for="(info, theme) in themeProgress" :key="theme" class="flex items-center gap-2 text-xs">
            <span class="w-16 text-right text-qianhui truncate">{{ theme }}</span>
            <div class="flex-1 h-2 bg-black/5 rounded-full overflow-hidden">
              <div class="h-full rounded-full transition-all" :style="{ width: Math.min(100, info.explored * 25) + '%', background: info.color }"></div>
            </div>
            <span class="text-qianhui w-8">{{ info.explored }}</span>
          </div>
        </div>
      </div>

      <!-- Golden leaf canvas -->
      <div v-if="exploredList.length" class="mt-5 flex justify-center">
        <canvas ref="leafCvs" class="cursor-pointer" width="580" height="320"
          style="width:100%;max-width:580px;height:auto;aspect-ratio:580/320"
          @mousemove="onLeafMove" @click="onLeafClick" @dblclick="onLeafDbl"></canvas>
      </div>

      <!-- Explored tags -->
      <div v-if="exploredList.length" class="mt-4">
        <div class="flex flex-wrap gap-2">
          <span v-for="item in exploredList" :key="item.id"
            class="tag cursor-pointer hover:scale-105 transition-transform"
            :style="{ color: item.themeColor, borderColor: item.themeColor + '66', background: item.themeColor + '0F' }"
            @click="$router.push(`/concept/${item.id}`)">
            {{ item.name }}
            <span class="text-[10px] opacity-60 ml-1">{{ item.poetryCount || 0 }}首</span>
          </span>
        </div>
      </div>

      <!-- AI Report -->
      <div v-if="exploredList.length" class="mt-5 p-5 bg-shiqing/[0.04] rounded-md border-l-2 border-zheshi">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-semibold tracking-widest">AI 探索报告</span>
          <button
            class="text-xs text-zheshi border border-zheshi/40 rounded-full px-3 py-1 hover:bg-zheshi/5 transition-colors"
            :disabled="reportLoading"
            @click="genReport">
            {{ reportLoading ? '生成中…' : hasCachedReport ? '重新生成' : '生成报告' }}
          </button>
        </div>
        <p v-if="report" class="text-sm text-moyan/80 leading-7 whitespace-pre-line">{{ report }}</p>
        <p v-else class="text-xs text-qianhui">
          点击「生成报告」，AI 将分析你的 {{ exploredList.length }} 个已探索意象，生成约 200 字的个性化探索报告
        </p>
      </div>

      <!-- Actions -->
      <div v-if="exploredList.length" class="flex gap-3 mt-5">
        <button class="btn-primary !py-1.5 !px-4 !text-xs" @click="generateShareCard">
          生成分享卡片
        </button>
        <button class="btn-outline !py-1.5 !px-4 !text-xs" @click="clearExplored">
          清空记录
        </button>
      </div>

      <!-- Empty state -->
      <div v-if="!exploredList.length" class="text-center py-8 text-qianhui">
        <p class="font-kai text-base">尚未探索任何意象</p>
        <p class="text-xs mt-2">浏览意象详情页后，已探索的意象将自动收录</p>
        <router-link to="/concepts" class="btn-primary mt-4 !text-xs">去意象画廊探索 →</router-link>
      </div>
    </div>
  </div>
  <div v-else class="max-w-md mx-auto px-4 py-16">
    <div class="card p-8">
      <span class="seal !w-14 !h-14 !text-lg mx-auto block text-center">诗</span>
      <h1 class="font-song text-2xl font-bold text-center mt-4">{{ mode === 'login' ? '登录' : mode === 'register' ? '注册' : '找回密码' }}</h1>

      <form @submit.prevent="submit" class="mt-6 space-y-4">
        <input v-model="form.username" placeholder="用户名" required minlength="2"
          class="w-full px-4 py-2.5 rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing text-sm" />
        <input v-if="mode !== 'login'" v-model="form.email" placeholder="邮箱（选填）"
          class="w-full px-4 py-2.5 rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing text-sm" />
        <input v-if="mode !== 'reset'" v-model="form.password" type="password" placeholder="密码" required minlength="6"
          class="w-full px-4 py-2.5 rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing text-sm" />
        <!-- 验证码 -->
        <div v-if="mode !== 'reset'" class="flex items-center gap-3">
          <span class="bg-black/5 px-3 py-2 rounded text-sm font-mono tracking-wider select-none cursor-pointer"
            @click="refreshCaptcha" :title="'点击刷新'">{{ captcha.question }}</span>
          <input v-model="form.captcha_answer" placeholder="答案" required
            class="flex-1 px-3 py-2 rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing text-sm" />
        </div>

        <p v-if="error" class="text-xs text-zhusha">{{ error }}</p>
        <p v-if="msg" class="text-xs text-zhuqing">{{ msg }}</p>

        <button type="submit" class="btn-primary w-full justify-center !py-2.5" :disabled="loading">
          {{ loading ? '处理中…' : mode === 'login' ? '登录' : mode === 'register' ? '注册' : '找回密码' }}
        </button>
      </form>

      <div class="flex justify-between mt-5 text-xs">
        <button class="text-shiqing hover:underline" @click="switchMode('register')">注册账号</button>
        <button class="text-shiqing hover:underline" @click="switchMode('login')">已有账号</button>
        <button class="text-shiqing hover:underline" @click="switchMode('reset')">忘记密码</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../stores/auth'
import axios from 'axios'
import { agentAsk } from '../api'
import QRCode from 'qrcode'
import { useExploredImageries } from '../composables/useExploredImageries'

const router = useRouter()
const mode = ref('login')
const form = ref({ username: '', email: '', password: '', captcha_id: '', captcha_answer: '' })
const captcha = ref({ id: '', question: '1 + 1 = ?' })
const error = ref('')
const msg = ref('')
const loading = ref(false)

// 诗旅手帖
const { exploredList, exploredThemes, themeProgress, achievements, clearExplored } = useExploredImageries()
const report = ref(loadCachedReport())
const reportLoading = ref(false)
const hasCachedReport = ref(!!loadCachedReport())
const leafCvs = ref(null)

// AI report cache
const REPORT_CACHE_KEY = 'sxz_ai_report'
function reportHash() { return exploredList.value.map(e => e.id).sort().join(',') }
function loadCachedReport() {
  try {
    const raw = localStorage.getItem(REPORT_CACHE_KEY)
    if (!raw) return ''
    const data = JSON.parse(raw)
    if (data.hash === reportHash()) return data.report || ''
  } catch { }
  return ''
}
function saveCachedReport(text) {
  try {
    localStorage.setItem(REPORT_CACHE_KEY, JSON.stringify({ hash: reportHash(), report: text }))
  } catch { }
}

// Canvas leaf rendering
let leafItems = []
const leafDpr = 2

function renderLeafCanvas() {
  const cvs = leafCvs.value; if (!cvs) return
  const ctx = cvs.getContext('2d')
  const W = 580, H = 320
  cvs.width = W * leafDpr; cvs.height = H * leafDpr
  cvs.style.width = '100%'
  ctx.scale(leafDpr, leafDpr)

  // Paper bg
  ctx.fillStyle = '#F5F1E8'; ctx.fillRect(0, 0, W, H)

  const items = exploredList.value
  if (!items.length) return

  // Layout leaves in a flowing horizontal arrangement
  const n = items.length
  leafItems = items.map((item, i) => {
    const x = 50 + (i / Math.max(n - 1, 1)) * (W - 100) + (Math.random() - 0.5) * 30
    const y = H / 2 + Math.sin(i * 1.2) * 40 + (Math.random() - 0.5) * 30
    return {
      id: item.id, name: item.name, theme: item.theme || '',
      poetryCount: item.poetryCount || 0,
      x: Math.max(40, Math.min(W - 40, x)),
      y: Math.max(50, Math.min(H - 50, y)),
      rot: (Math.random() - 0.5) * 0.35,
    }
  })

  // Exploration order lines
  ctx.strokeStyle = 'rgba(170,130,55,0.3)'; ctx.lineWidth = 1
  for (let i = 0; i < leafItems.length - 1; i++) {
    ctx.beginPath(); ctx.moveTo(leafItems[i].x, leafItems[i].y); ctx.lineTo(leafItems[i + 1].x, leafItems[i + 1].y); ctx.stroke()
  }

  // Same theme dashed
  ctx.strokeStyle = 'rgba(150,110,40,0.16)'; ctx.lineWidth = 0.6; ctx.setLineDash([3, 5])
  for (let i = 0; i < leafItems.length; i++) {
    for (let j = i + 1; j < leafItems.length; j++) {
      if (leafItems[i].theme === leafItems[j].theme) {
        ctx.beginPath(); ctx.moveTo(leafItems[i].x, leafItems[i].y); ctx.lineTo(leafItems[j].x, leafItems[j].y); ctx.stroke()
      }
    }
  }
  ctx.setLineDash([])

  // Draw leaves
  for (const lf of leafItems) {
    drawLeafAt(ctx, lf.x, lf.y, 22, lf.rot)
    // Character
    ctx.fillStyle = '#FDF9F2'; ctx.font = 'bold 15px "Kaiti SC","STKaiti","KaiTi",serif'
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
    ctx.shadowColor = 'rgba(70,32,3,0.15)'; ctx.shadowBlur = 1
    ctx.fillText(lf.name.charAt(0), lf.x, lf.y - 2)
    ctx.shadowBlur = 0
  }
}

function drawLeafAt(ctx, x, y, s, rot) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(rot)
  ctx.beginPath()
  ctx.moveTo(0, -s * 0.62)
  ctx.bezierCurveTo(s * 0.42, -s * 0.32, s * 0.38, s * 0.12, 0, s * 0.18)
  ctx.bezierCurveTo(-s * 0.38, s * 0.12, -s * 0.42, -s * 0.32, 0, -s * 0.62)
  ctx.closePath()
  const g = ctx.createLinearGradient(0, -s * 0.62, 0, s * 0.18)
  g.addColorStop(0, '#F4DC80'); g.addColorStop(0.25, '#DEB445'); g.addColorStop(0.6, '#C59328')
  g.addColorStop(0.85, '#A07015'); g.addColorStop(1, '#7B5208')
  ctx.fillStyle = g; ctx.fill()
  ctx.strokeStyle = 'rgba(110,68,10,0.2)'; ctx.lineWidth = 0.4; ctx.stroke()
  // Stem
  ctx.beginPath(); ctx.moveTo(0, s * 0.17); ctx.lineTo(0, s * 0.5)
  ctx.strokeStyle = 'rgba(90,48,4,0.3)'; ctx.lineWidth = 0.5; ctx.stroke()
  ctx.restore()
}

function hitLeaf(e) {
  const r = leafCvs.value?.getBoundingClientRect(); if (!r) return null
  const sx = (e.clientX - r.left) * (580 / r.width)
  const sy = (e.clientY - r.top) * (320 / r.height)
  for (const lf of leafItems) {
    if (Math.hypot(sx - lf.x, sy - lf.y) < 26) return lf
  }
  return null
}

function onLeafMove(e) {
  const lf = hitLeaf(e)
  if (leafCvs.value) leafCvs.value.style.cursor = lf ? 'pointer' : 'default'
}
function onLeafClick(e) {
  const lf = hitLeaf(e)
  if (lf) router.push(`/concept/${lf.id}`)
}
function onLeafDbl(e) {
  const lf = hitLeaf(e)
  if (lf) router.push(`/concept/${lf.id}`)
}

watch(exploredList, () => nextTick(renderLeafCanvas), { deep: true })

function stripMd(text) {
  return text.replace(/\*\*(.+?)\*\*/g, '$1').replace(/###?\s?/g, '').replace(/__/g, '').replace(/\n{3,}/g, '\n\n')
}

async function genReport() {
  if (!exploredList.value.length) return
  reportLoading.value = true
  try {
    const names = exploredList.value.map(e => e.name).join('、')
    const themes = exploredThemes.value.join('、')
    const prompt = `我已探索了${exploredList.value.length}个古典诗词意象：${names}。它们跨越了${exploredThemes.value.length}个文化主题族：${themes}。请基于此生成一段约200字的个性化意象探索报告。要求：纯文本，不使用任何Markdown格式（不要加粗、标题等）。语言典雅有文采，分析我的兴趣偏好和意象探索路径。例如："你已探索了X个意象，跨越了X个文化主题族。你似乎对XX族特别感兴趣——你探索了XX，它们恰好是XX场景中最经典的意象……"`
    const resp = await agentAsk(prompt)
    report.value = stripMd(resp.answer)
    saveCachedReport(report.value)
    hasCachedReport.value = true
  } catch {
    report.value = `你已探索了 ${exploredList.value.length} 个意象，跨越了 ${exploredThemes.value.length} 个文化主题族。这些意象承载着千年的诗情画意，每一次探索都是与古人的一次心灵对话。`
  } finally {
    reportLoading.value = false
  }
}

async function generateShareCard() {
  const items = exploredList.value
  const count = items.length
  const themes = exploredThemes.value.length
  const names = items.map(e => e.name).slice(0, 8).join(' · ') + (count > 8 ? ` …等${count}个` : '')
  const reportText = (report.value || '').replace(/\*\*/g, '').replace(/#/g, '')
  const reportLines = Math.max(1, Math.ceil(reportText.length / 38))
  const cardH = Math.max(480, 260 + reportLines * 22)

  const qrSvg = await QRCode.toString(window.location.origin + '/', {
    type: 'svg', width: 64, margin: 1,
    color: { dark: '#2C2C2C', light: '#F5F1E8' },
  })

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="720" height="${cardH}" viewBox="0 0 720 ${cardH}">
  <rect width="720" height="${cardH}" fill="#F5F1E8"/>
  <rect x="12" y="12" width="696" height="${cardH - 24}" fill="none" stroke="#B5352C" stroke-width="2" opacity="0.4"/>
  <rect x="18" y="18" width="684" height="${cardH - 36}" fill="none" stroke="#B5352C" stroke-width="0.75" opacity="0.25"/>
  <text x="360" y="64" font-size="34" fill="#B5352C" text-anchor="middle" font-family="'Kaiti SC','STKaiti','KaiTi',serif">诗旅手帖</text>
  <text x="360" y="110" font-size="18" fill="#2C2C2C" text-anchor="middle" font-family="'PingFang SC','Microsoft YaHei',sans-serif">
    已探索 <tspan fill="#B5352C" font-weight="bold">${count}</tspan> 个意象 · 跨越 <tspan fill="#B5352C" font-weight="bold">${themes}</tspan> 个主题族
  </text>
  <line x1="160" y1="128" x2="560" y2="128" stroke="#B5352C" stroke-width="1" opacity="0.4"/>
  <text x="56" y="168" font-size="14" fill="#6B6B6B" font-family="'PingFang SC','Microsoft YaHei',sans-serif">${escapeXml(names)}</text>
  <text x="56" y="205" font-size="13" fill="#4A4A4A" font-family="'PingFang SC','Microsoft YaHei',sans-serif" font-weight="bold">AI 探索报告</text>
  <foreignObject x="56" y="220" width="560" height="${cardH - 280}">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-family:'PingFang SC','Microsoft YaHei',sans-serif;font-size:13px;color:#2C2C2C;line-height:1.75;width:560px;word-wrap:break-word;">
      ${escapeXml(reportText)}
    </div>
  </foreignObject>
  <text x="56" y="${cardH - 40}" font-size="12" fill="#9A9A9A" font-family="'PingFang SC','Microsoft YaHei',sans-serif">诗象志 · 一字藏万象，一诗见千年</text>
  <rect x="620" y="${cardH - 70}" width="44" height="44" rx="4" fill="#9B2C1F" opacity="0.9"/>
  <text x="642" y="${cardH - 40}" font-size="20" fill="#F5F1E8" text-anchor="middle" font-family="'Kaiti SC','STKaiti','KaiTi',serif">诗象</text>
  <g transform="translate(56, ${cardH - 130}) scale(0.9)">${qrSvg}</g>
  <text x="88" y="${cardH - 52}" font-size="8" fill="#9A9A9A" text-anchor="middle" font-family="'PingFang SC','Microsoft YaHei',sans-serif">扫码访问</text>
</svg>`

  const blob = new Blob([svg], { type: 'image/svg+xml' })
  window.open(URL.createObjectURL(blob), '_blank')
}

function escapeXml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

async function refreshCaptcha() {
  const { data } = await axios.get('/api/auth/captcha')
  captcha.value = data.data
  form.value.captcha_id = data.data.id
  form.value.captcha_answer = ''
}
onMounted(() => { refreshCaptcha(); if (auth.user) renderLeafCanvas() })

function switchMode(m) {
  mode.value = m
  error.value = msg.value = ''
}

async function submit() {
  error.value = msg.value = ''
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(form.value.username, form.value.password, captcha.value.id, form.value.captcha_answer)
    } else if (mode.value === 'register') {
      await auth.register(form.value.username, form.value.password, form.value.email, captcha.value.id, form.value.captcha_answer)
    } else {
      const r = await auth.resetPassword(form.value.email)
      msg.value = `新密码：${r.new_password}。${r.note}`
      return
    }
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}
</script>
