<template>
  <div>
    <div class="flex items-center gap-3 mb-4">
      <input v-model="keyword" @keyup.enter="page = 1; load()" placeholder="检索标题/作者/内容…"
        class="w-64 px-3 py-2 text-sm rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing" />
      <button class="btn-outline !py-1.5 !text-xs" @click="page = 1; load()">检索</button>
      <div class="flex-1"></div>
      <button class="btn-primary !py-1.5 !text-xs" @click="openEdit(null)">录入诗文</button>
    </div>

    <div class="space-y-2">
      <div v-for="p in items" :key="p.id" class="card p-4">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <b class="font-song">《{{ p.title }}》</b>
              <span class="text-xs text-qianhui">{{ p.dynasty }} · {{ p.author }} · {{ p.writing_type }}</span>
              <span v-for="r in p.rels" :key="r.rel_id" class="tag border-shiqing/30 text-shiqing !text-[10px]">{{ r.concept_name }}</span>
            </div>
            <p class="text-xs text-qianhui mt-1 line-clamp-1 verse-text">{{ p.content.replace(/\n/g, ' ') }}</p>
          </div>
          <div class="flex gap-2 shrink-0">
            <button class="btn-outline !py-1 !px-3 !text-xs" @click="openEdit(p)">编辑</button>
            <button class="btn-outline !py-1 !px-3 !text-xs !border-zhusha/50 !text-zhusha hover:!bg-zhusha" @click="remove(p)">删除</button>
          </div>
        </div>
      </div>
    </div>
    <Pagination :page="page" :page-size="pageSize" :total="total" @change="(p) => { page = p; load() }" />

    <!-- 编辑弹窗 -->
    <Modal :show="editing !== null" :title="form.id ? `编辑诗文 · ${form.title}` : '录入诗文'" width="max-w-3xl" @close="editing = null">
      <div class="grid grid-cols-4 gap-3">
        <label class="col-span-2"><span class="text-xs text-qianhui">标题 *</span><input v-model="form.title" class="field" /></label>
        <label><span class="text-xs text-qianhui">作者</span><input v-model="form.author" class="field" /></label>
        <label><span class="text-xs text-qianhui">朝代</span>
          <select v-model="form.dynasty" class="field"><option v-for="d in dynasties" :key="d">{{ d }}</option></select>
        </label>
        <label><span class="text-xs text-qianhui">体裁</span>
          <select v-model="form.writing_type" class="field"><option v-for="t in ['诗', '词', '曲', '文']" :key="t">{{ t }}</option></select>
        </label>
        <label class="col-span-3"><span class="text-xs text-qianhui">上游 writingId（可选，填入后平仄/笺注/出处自动走上游透传）</span>
          <input v-model="form.source_writing_id" class="field font-mono" /></label>
        <label class="col-span-4"><span class="text-xs text-qianhui">全文 *</span>
          <textarea v-model="form.content" rows="6" class="field verse-text"></textarea>
        </label>
      </div>

      <!-- 意象关联编辑 -->
      <div class="mt-5 border-t border-black/8 pt-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-semibold">意象关联标注</span>
          <button class="btn-outline !py-1 !px-3 !text-xs" @click="form.rels.push({ concept_id: concepts[0]?.id, clause: '', emotion: '', is_classic: 0, weight: 1 })">+ 添加关联</button>
        </div>
        <div v-for="(r, i) in form.rels" :key="i" class="grid grid-cols-12 gap-2 mb-2 items-center">
          <select v-model="r.concept_id" class="field col-span-2">
            <option v-for="c in concepts" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <input v-model="r.clause" placeholder="含象诗句（原文片段）" class="field col-span-5" />
          <select v-model="r.emotion" class="field col-span-2">
            <option value="">情感</option>
            <option v-for="e in emotionsOf(r.concept_id)" :key="e">{{ e }}</option>
          </select>
          <select v-model.number="r.weight" class="field col-span-1">
            <option :value="3">权重3</option><option :value="2">权重2</option><option :value="1">权重1</option>
          </select>
          <label class="col-span-1 flex items-center gap-1 text-xs text-qianhui">
            <input type="checkbox" :checked="!!r.is_classic" @change="r.is_classic = $event.target.checked ? 1 : 0" />名句
          </label>
          <button class="col-span-1 text-zhusha text-lg" @click="form.rels.splice(i, 1)">×</button>
        </div>
      </div>

      <div class="flex justify-end gap-3 mt-6">
        <button class="btn-outline !text-xs" @click="editing = null">取消</button>
        <button class="btn-primary !text-xs" :disabled="!form.title || !form.content" @click="save">保存</button>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import {
  adminCreatePoetry, adminDeletePoetry, adminPoetryList, adminUpdatePoetry, getConceptList,
} from '../../api'
import Modal from './Modal.vue'
import Pagination from '../Pagination.vue'

const dynasties = ['先秦', '汉', '魏晋', '唐', '五代', '宋', '元', '明', '清']
const items = ref([])
const concepts = ref([])
const keyword = ref('')
const page = ref(1)
const pageSize = 10
const total = ref(0)
const editing = ref(null)
const form = ref({})

const emotionsOf = (cid) => {
  const c = concepts.value.find((x) => x.id === cid)
  return c ? c.emotion_tags : []
}

async function load() {
  const data = await adminPoetryList({ keyword: keyword.value, page: page.value, page_size: pageSize })
  items.value = data.items
  total.value = data.total
}

function openEdit(p) {
  form.value = p
    ? { id: p.id, title: p.title, author: p.author, dynasty: p.dynasty, writing_type: p.writing_type, content: p.content, source_writing_id: p.source_writing_id, rels: p.rels.map((r) => ({ concept_id: r.concept_id, clause: r.clause, emotion: r.emotion, is_classic: r.is_classic, weight: r.weight })) }
    : { id: 0, title: '', author: '', dynasty: '唐', writing_type: '诗', content: '', source_writing_id: '', rels: [] }
  editing.value = true
}

async function save() {
  const payload = { ...form.value }
  delete payload.id
  payload.rels = payload.rels.filter((r) => r.clause.trim())
  if (form.value.id) await adminUpdatePoetry(form.value.id, payload)
  else await adminCreatePoetry(payload)
  editing.value = null
  await load()
}

async function remove(p) {
  if (!confirm(`确定删除《${p.title}》？其意象关联将一并删除。`)) return
  await adminDeletePoetry(p.id)
  await load()
}

onMounted(async () => {
  const data = await getConceptList()
  concepts.value = data.items
  await load()
})
</script>

<style scoped>
.field {
  @apply mt-1 w-full px-3 py-2 text-sm rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing;
}
</style>
