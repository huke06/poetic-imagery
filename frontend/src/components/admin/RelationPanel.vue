<template>
  <div class="space-y-8">
    <!-- 自动推导建议 -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-song text-lg font-bold">数据推导的关联建议</h3>
        <button class="btn-outline !py-1 !px-3 !text-xs" @click="loadSuggestions">重新推导</button>
      </div>
      <p class="text-xs text-qianhui mb-3 leading-6">
        依据库中真实数据推导：共现 = 两意象关联到同一首诗；情感同源 = 情感标签存在交集。点击「采纳」即写入人工关联。
      </p>
      <div class="space-y-2">
        <div v-for="s in suggestions" :key="`${s.from_id}-${s.to_id}`" class="card p-4 flex items-center gap-4">
          <div class="flex items-center gap-2 shrink-0">
            <b class="font-song">{{ s.from_name }}</b>
            <span class="text-qianhui">↔</span>
            <b class="font-song">{{ s.to_name }}</b>
          </div>
          <div class="flex-1 text-xs text-qianhui leading-5">
            <span v-if="s.shared_poetries.length">共现作品：{{ s.shared_poetries.map(t => `《${t}》`).join('') }}</span>
            <span v-if="s.shared_emotions.length" class="ml-2">共同情感：{{ s.shared_emotions.join('、') }}</span>
          </div>
          <span v-if="s.exists" class="tag border-zhuqing/40 text-zhuqing">已建立</span>
          <button v-else class="btn-primary !py-1 !px-3 !text-xs" @click="adopt(s)">采纳</button>
        </div>
        <p v-if="!suggestions.length" class="text-sm text-qianhui py-4 text-center">暂无可推导的关联（意象间无共现作品与共同情感）</p>
      </div>
    </div>

    <!-- 人工关联管理 -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-song text-lg font-bold">人工共现关联</h3>
        <button class="btn-primary !py-1.5 !text-xs" @click="openCreate">新建共现关联</button>
      </div>
      <p class="text-xs text-qianhui mb-3 leading-6">
        关联类型已聚焦「共现」分析。批量导入请使用「数据导入」页的 <b class="text-moyan">共现分析 CSV 模板</b>
        （字段：name / to / cooccurrence_type / NPMI / diaphaneity / verse / description）。
      </p>
      <div class="space-y-2">
        <div v-for="r in manualEdges" :key="r.id" class="card p-4 flex items-center gap-4">
          <b class="font-song shrink-0">{{ r.from_name }} → {{ r.to_name }}</b>
          <span class="tag border-shiqing/30 text-shiqing shrink-0">{{ r.relation_type }}</span>
          <p class="flex-1 text-xs text-qianhui leading-5 line-clamp-2">{{ r.description }}</p>
          <button class="btn-outline !py-1 !px-3 !text-xs !border-zhusha/50 !text-zhusha hover:!bg-zhusha" @click="remove(r)">删除</button>
        </div>
      </div>
    </div>

    <!-- 新建弹窗 -->
    <Modal :show="creating" title="新建共现关联" @close="creating = false">
      <div class="grid grid-cols-2 gap-3">
        <label><span class="text-xs text-qianhui">源意象</span>
          <select v-model.number="form.from_concept_id" class="field">
            <option v-for="c in concepts" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </label>
        <label><span class="text-xs text-qianhui">共现意象</span>
          <select v-model.number="form.to_concept_id" class="field">
            <option v-for="c in concepts" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </label>
        <label><span class="text-xs text-qianhui">共现类型</span>
          <select v-model="form.cooccurrence_type" class="field">
            <option v-for="t in ['', '句内', '跨句', '全诗']" :key="t" :value="t">{{ t || '（未分型）' }}</option>
          </select>
        </label>
        <label><span class="text-xs text-qianhui">NPMI（-1~1）</span>
          <input v-model.number="form.npmi" type="number" step="0.01" min="-1" max="1" class="field" />
        </label>
        <label class="col-span-2"><span class="text-xs text-qianhui">共现例句</span>
          <input v-model="form.verse" class="field" />
        </label>
        <label class="col-span-2"><span class="text-xs text-qianhui">阐释说明</span>
          <textarea v-model="form.description" rows="3" class="field"></textarea>
        </label>
      </div>
      <div class="flex justify-end gap-3 mt-5">
        <button class="btn-outline !text-xs" @click="creating = false">取消</button>
        <button class="btn-primary !text-xs" :disabled="form.from_concept_id === form.to_concept_id" @click="create">保存</button>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import {
  adminCreateRelation, adminDeleteRelation, getConceptList, getConceptRelations, getRelationSuggestions,
} from '../../api'
import Modal from './Modal.vue'

const concepts = ref([])
const suggestions = ref([])
const manualEdges = ref([])
const creating = ref(false)
const form = ref({})

async function loadSuggestions() {
  suggestions.value = await getRelationSuggestions()
}

async function loadManual() {
  // 汇总每个意象的人工关联边（按 from-to-type 去重）
  const seen = new Set()
  manualEdges.value = []
  for (const c of concepts.value) {
    const data = await getConceptRelations(c.id)
    for (const e of data.edges) {
      if (e.auto) continue
      const key = `${e.from_id}-${e.to_id}-${e.relation_type}`
      if (seen.has(key)) continue
      seen.add(key)
      manualEdges.value.push({ ...e })
    }
  }
}

async function adopt(s) {
  const desc = [
    s.shared_poetries.length ? `共现作品：${s.shared_poetries.map((t) => `《${t}》`).join('')}` : '',
    s.shared_emotions.length ? `共同情感：${s.shared_emotions.join('、')}` : '',
  ].filter(Boolean).join('；')
  await adminCreateRelation({
    from_concept_id: s.from_id, to_concept_id: s.to_id,
    relation_type: '共现', description: desc,
  })
  await Promise.all([loadSuggestions(), loadManual()])
}

function openCreate() {
  form.value = { from_concept_id: concepts.value[0]?.id, to_concept_id: concepts.value[1]?.id,
    cooccurrence_type: '', npmi: 0, verse: '', description: '' }
  creating.value = true
}

async function create() {
  await adminCreateRelation({ ...form.value, relation_type: '共现' })
  creating.value = false
  await Promise.all([loadSuggestions(), loadManual()])
}

async function remove(r) {
  if (!confirm(`删除关联「${r.from_name} → ${r.to_name}」？`)) return
  await adminDeleteRelation(r.id)
  await Promise.all([loadSuggestions(), loadManual()])
}

onMounted(async () => {
  const data = await getConceptList()
  concepts.value = data.items
  await Promise.all([loadSuggestions(), loadManual()])
})
</script>

<style scoped>
.field {
  @apply mt-1 w-full px-3 py-2 text-sm rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing;
}
</style>
