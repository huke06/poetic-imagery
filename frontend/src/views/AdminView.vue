<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <!-- 登录门 -->
    <div v-if="!authed" class="max-w-sm mx-auto mt-20 card p-8 text-center">
      <span class="seal !w-14 !h-14 !text-lg mx-auto">管</span>
      <h1 class="font-song text-2xl font-bold mt-4">管理后台</h1>
      <p class="text-xs text-qianhui mt-2">请输入管理令牌（默认 shixiangzhi-admin，可在环境变量中修改）</p>
      <input v-model="tokenInput" type="password" @keyup.enter="login" placeholder="管理令牌"
        class="mt-5 w-full px-4 py-2.5 text-sm rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing text-center" />
      <p v-if="loginErr" class="text-xs text-zhusha mt-2">{{ loginErr }}</p>
      <button class="btn-primary w-full justify-center mt-4" @click="login">进入</button>
    </div>

    <template v-else>
      <div class="flex items-center justify-between">
        <SectionTitle sub="数据配置 · 系统变量 · 内容管理">管理后台</SectionTitle>
        <button class="btn-outline !py-1 !px-3 !text-xs" @click="logout">退出登录</button>
      </div>

      <!-- 选项卡 -->
      <div class="flex border-b border-black/8 mt-6 overflow-x-auto">
        <button v-for="t in tabs" :key="t.key"
          class="px-5 py-3 text-sm tracking-widest whitespace-nowrap transition-colors"
          :class="tab === t.key ? 'text-shiqing font-semibold border-b-2 border-shiqing bg-shiqing/5' : 'text-qianhui hover:text-shiqing'"
          @click="tab = t.key">
          {{ t.label }}
        </button>
      </div>

      <div class="py-6">
        <!-- 数据总览 -->
        <div v-if="tab === 'dashboard'">
          <div v-if="overview" class="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div v-for="s in statCards" :key="s.label" class="card p-5 text-center">
              <div class="text-3xl font-song font-bold" :style="{ color: s.color }">{{ s.value }}</div>
              <div class="text-xs text-qianhui mt-1">{{ s.label }}</div>
            </div>
          </div>
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
            <div class="card p-5">
              <h3 class="font-song font-bold mb-3">已收录意象</h3>
              <div class="flex flex-wrap gap-2">
                <span v-for="c in overview?.concept_list || []" :key="c.id" class="tag !text-sm !px-3 !py-1"
                  :style="{ color: c.theme_color, borderColor: c.theme_color + '66', background: c.theme_color + '0F' }">
                  {{ c.name }}（{{ c.category }}）
                </span>
              </div>
              <p class="text-xs text-qianhui mt-3 leading-6">扩充方式：①「意象管理」页手动新建；② 命令行增量导入 <code class="bg-black/5 px-1 rounded">scripts/add_concept.py</code>（支持 JSON 批量）</p>
            </div>
            <div class="card p-5">
              <h3 class="font-song font-bold mb-3">系统状态</h3>
              <div class="space-y-2 text-sm">
                <div class="flex justify-between"><span class="text-qianhui">大模型</span>
                  <span :class="overview?.llm_configured ? 'text-zhuqing' : 'text-zheshi'">{{ overview?.llm_configured ? '已配置（LLM 生成）' : '未配置（本地知识库生成）' }}</span>
                </div>
                <div class="flex justify-between"><span class="text-qianhui">数据库</span><span>SQLite 单文件</span></div>
              </div>
              <button class="btn-outline !py-1.5 !text-xs mt-4" :disabled="recomputing" @click="doRecompute">
                {{ recomputing ? '重算中…' : '重算朝代统计' }}
              </button>
              <span v-if="recomputeMsg" class="text-xs text-zhuqing ml-2">{{ recomputeMsg }}</span>
            </div>
          </div>
        </div>

        <ConfigPanel v-else-if="tab === 'config'" />
        <ImportPanel v-else-if="tab === 'import'" />
        <ConceptPanel v-else-if="tab === 'concept'" />
        <PoetryPanel v-else-if="tab === 'poetry'" />
        <ArtworkPanel v-else-if="tab === 'artwork'" />
        <RelationPanel v-else-if="tab === 'relation'" />
        <CoupletPanel v-else-if="tab === 'couplet'" />
        <UserPanel v-else-if="tab === 'users'" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import {
  adminOverview, getToken, recomputeStats, setToken as saveToken,
} from '../api'
import SectionTitle from '../components/SectionTitle.vue'
import ArtworkPanel from '../components/admin/ArtworkPanel.vue'
import ConceptPanel from '../components/admin/ConceptPanel.vue'
import ConfigPanel from '../components/admin/ConfigPanel.vue'
import CoupletPanel from '../components/admin/CoupletPanel.vue'
import ImportPanel from '../components/admin/ImportPanel.vue'
import UserPanel from '../components/admin/UserPanel.vue'
import PoetryPanel from '../components/admin/PoetryPanel.vue'
import RelationPanel from '../components/admin/RelationPanel.vue'

const tabs = [
  { key: 'dashboard', label: '数据总览' },
  { key: 'import', label: '批量导入' },
  { key: 'config', label: '系统配置' },
  { key: 'concept', label: '意象管理' },
  { key: 'poetry', label: '诗文管理' },
  { key: 'artwork', label: '古画管理' },
  { key: 'relation', label: '关联管理' },
  { key: 'couplet', label: '对仗管理' },
  { key: 'users', label: '用户管理' },
]
const tab = ref('dashboard')
const route = useRoute()
const authed = ref(false)
const tokenInput = ref('')
const loginErr = ref('')
const overview = ref(null)
const recomputing = ref(false)
const recomputeMsg = ref('')

const statCards = computed(() => overview.value ? [
  { label: '意象', value: overview.value.concepts, color: '#2B4C7E' },
  { label: '诗文', value: overview.value.poetries, color: '#9B4423' },
  { label: '古画', value: overview.value.artworks, color: '#5B7C5F' },
  { label: '意象关联', value: overview.value.concept_poetry_rels, color: '#6E4A7E' },
] : [])

async function login() {
  saveToken(tokenInput.value)
  try {
    overview.value = await adminOverview()
    authed.value = true
    loginErr.value = ''
  } catch (e) {
    loginErr.value = e.message
    saveToken('')
  }
}

function logout() {
  saveToken('')
  authed.value = false
}

async function doRecompute() {
  recomputing.value = true
  try {
    const d = await recomputeStats()
    recomputeMsg.value = d?.msg || '已重算'
  } finally {
    recomputing.value = false
  }
}

onMounted(async () => {
  if (route.query.tab && tabs.some((t) => t.key === route.query.tab)) tab.value = route.query.tab
  if (getToken()) {
    try {
      overview.value = await adminOverview()
      authed.value = true
    } catch { saveToken('') }
  }
})
</script>
