/**
 * 金叶集 — localStorage 持久化的个人意象探索记录
 *
 * 每浏览一个意象详情页，自动收录。左下角「金叶集」面板展示。
 * 存储: { id, name, themeColor, theme, exploredAt }
 */
import { computed, ref } from 'vue'

const STORAGE_KEY = 'sxz_explored_imageries'

// 情感标签 → 七大主题族
const THEME_KEYWORDS = {
  '思乡怀人': ['思乡', '怀人', '离别', '离愁', '相思'],
  '时光咏怀': ['时光流逝', '怀古', '落寞', '惜春'],
  '孤寂哲思': ['孤寂', '时空永恒', '哲理'],
  '豪迈壮烈': ['豪迈', '壮烈', '激昂', '慷慨'],
  '苍凉悲壮': ['苍凉', '悲壮', '边塞', '厌战'],
  '自然咏物': ['咏物', '山水', '田园', '闲适'],
  '爱情闺怨': ['爱情', '闺怨', '思念', '怨妇'],
}

const THEME_COLORS = {
  '思乡怀人': '#B5352C',
  '时光咏怀': '#6B5078',
  '孤寂哲思': '#3A5070',
  '豪迈壮烈': '#8B2518',
  '自然咏物': '#5A7050',
  '苍凉悲壮': '#7B6840',
  '爱情闺怨': '#A05058',
}

function classifyTheme(emotionTags) {
  if (!emotionTags || !emotionTags.length) return '自然咏物'
  let best = '自然咏物', bestScore = 0
  for (const [theme, keywords] of Object.entries(THEME_KEYWORDS)) {
    const score = emotionTags.filter((t) => keywords.includes(t)).length
    if (score > bestScore) { bestScore = score; best = theme }
  }
  return best
}

const explored = ref(load())
const newCount = ref(0) // 用于触发面板闪烁

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch { return [] }
}

function save() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(explored.value)) }
  catch { /* silently degrade */ }
}

// Achievement definitions
const ACHIEVEMENTS = [
  { id: 'first', name: '初探诗境', desc: '探索第 1 个意象', icon: '芽', req: 1 },
  { id: 'five', name: '诗路行者', desc: '探索 5 个意象', icon: '叶', req: 5 },
  { id: 'ten', name: '意象猎手', desc: '探索 10 个意象', icon: '枫', req: 10 },
  { id: 'twenty', name: '诗象大师', desc: '探索 20 个意象', icon: '冠', req: 20 },
]

export function useExploredImageries() {
  const exploredIds = computed(() => new Set(explored.value.map((e) => e.id)))
  const exploredList = computed(() => [...explored.value].reverse())
  const exploredThemes = computed(() => [...new Set(explored.value.map((e) => e.theme).filter(Boolean))])

  // Theme progress: { themeName: { explored: N, total: M } }
  const themeProgress = computed(() => {
    const themes = {}
    for (const e of explored.value) {
      if (!e.theme) continue
      if (!themes[e.theme]) themes[e.theme] = { explored: 0, total: 0, color: e.themeColor }
      themes[e.theme].explored++
    }
    // Note: total per theme requires knowing ALL concepts in that theme from the DB
    // For now just track explored count
    return themes
  })

  // Unlocked achievements
  const achievements = computed(() => {
    const count = explored.value.length
    return ACHIEVEMENTS.filter(a => count >= a.req)
  })

  function addExplored(concept) {
    const existing = explored.value.find((e) => e.id === concept.id)
    if (existing) {
      existing.exploredAt = fmtDate()
      save()
      return
    }
    const theme = classifyTheme(concept.emotion_tags)
    explored.value.push({
      id: concept.id,
      name: concept.name,
      themeColor: THEME_COLORS[theme] || concept.theme_color || '#B5352C',
      theme,
      poetryCount: concept.poetry_count || 0,
      exploredAt: fmtDate(),
    })
    newCount.value++
    save()
  }

  function removeExplored(id) {
    explored.value = explored.value.filter((e) => e.id !== id)
    save()
  }

  function clearExplored() {
    explored.value = []
    save()
  }

  function consumeNew() { newCount.value = 0 }

  return { exploredIds, exploredList, exploredThemes, newCount, themeProgress, achievements, addExplored, removeExplored, clearExplored, consumeNew }
}

function fmtDate() {
  const d = new Date()
  return `${d.getMonth() + 1}/${d.getDate()}`
}
