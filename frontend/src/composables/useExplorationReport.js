/**
 * AI 探索报告 — 共享生成逻辑
 * 金叶集「分享意象地图」卡片 与 个人中心「诗旅手帖」共用。
 * localStorage 缓存，键 sxz_ai_report，按已探索意象 id 集合做 hash 校验。
 */
import { ref } from 'vue'
import { agentAsk } from '../api'

const CACHE_KEY = 'sxz_ai_report'

function hashOf(exploredList) {
  return (exploredList || []).map((e) => e.id).sort().join(',')
}

function loadCached(exploredList) {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return ''
    const data = JSON.parse(raw)
    return data.hash === hashOf(exploredList) ? data.report || '' : ''
  } catch {
    return ''
  }
}

function saveCached(exploredList, text) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ hash: hashOf(exploredList), report: text }))
  } catch { /* silently degrade */ }
}

function stripMd(text) {
  return (text || '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/###?\s?/g, '')
    .replace(/__/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function fallbackText(exploredList, exploredThemes) {
  return `你已探索了 ${exploredList.length} 个意象，跨越了 ${exploredThemes.length} 个文化主题族。这些意象承载着千年的诗情画意，每一次探索都是与古人的一次心灵对话。`
}

export function useExplorationReport() {
  const report = ref('')
  const loading = ref(false)
  const hasCached = ref(false)

  // 从缓存初始化（供展示层立即渲染已有报告）
  function hydrate(exploredList) {
    const cached = loadCached(exploredList)
    report.value = cached
    hasCached.value = !!cached
    return cached
  }

  // 确保拿到报告：有缓存直接返回，否则调 LLM 生成；失败时回退固定文案，保证永不空白
  async function generate(exploredList, exploredThemes = []) {
    const list = exploredList || []
    if (!list.length) return ''

    const cached = loadCached(list)
    if (cached) {
      report.value = cached
      hasCached.value = true
      return cached
    }

    loading.value = true
    try {
      const names = list.map((e) => e.name).join('、')
      const themes = (exploredThemes || []).join('、')
      const prompt =
        `我已探索了${list.length}个古典诗词意象：${names}。` +
        `它们跨越了${(exploredThemes || []).length}个文化主题族：${themes}。` +
        `请基于此生成一段约200字的个性化意象探索报告，分析我的兴趣偏好与意象探索路径。` +
        `要求：纯文本，不使用任何 Markdown 格式（不加粗、不写标题），语言典雅有文采。`
      const resp = await agentAsk(prompt)
      // 仅当 LLM 真正生成（source === 'llm'）才采用，否则视为未生成走回退
      const text = resp && resp.source === 'llm' ? stripMd(resp.answer) : ''
      const final = text || fallbackText(list, exploredThemes || [])
      report.value = final
      if (text) saveCached(list, final)
      hasCached.value = !!text
      return final
    } catch {
      const final = fallbackText(list, exploredThemes || [])
      report.value = final
      hasCached.value = false
      return final
    } finally {
      loading.value = false
    }
  }

  return { report, loading, hasCached, generate, hydrate }
}
