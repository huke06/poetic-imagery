<template>
  <div>
    <div class="flex items-center gap-3 mb-4">
      <select v-model.number="filterConcept" @change="load" class="px-3 py-2 text-sm rounded border border-shiqing/25 bg-white/70">
        <option :value="0">全部意象</option>
        <option v-for="c in concepts" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <div class="flex-1"></div>
      <button class="btn-primary !py-1.5 !text-xs" @click="openEdit(null)">新建对仗</button>
    </div>
    <div class="space-y-2">
      <div v-for="cp in items" :key="cp.id" class="card p-4 flex items-center gap-4">
        <span class="tag border-zhuqing/40 text-zhuqing shrink-0">{{ cp.concept_name }}</span>
        <div class="shrink-0 font-kai">
          <span class="text-shiqing">{{ cp.word_a }}</span>
          <span class="text-qianhui text-xs mx-1">对</span>
          <span class="text-zheshi">{{ cp.word_b }}</span>
        </div>
        <div class="flex-1 min-w-0">
          <p class="verse-text text-sm truncate">{{ cp.verse }}</p>
          <p class="text-xs text-qianhui">{{ cp.source }}</p>
        </div>
        <button class="btn-outline !py-1 !px-3 !text-xs" @click="openEdit(cp)">编辑</button>
        <button class="btn-outline !py-1 !px-3 !text-xs !border-zhusha/50 !text-zhusha hover:!bg-zhusha" @click="remove(cp)">删除</button>
      </div>
    </div>

    <Modal :show="editing !== null" :title="form.id ? '编辑对仗' : '新建对仗'" @close="editing = null">
      <div class="grid grid-cols-2 gap-3">
        <label><span class="text-xs text-qianhui">所属意象</span>
          <select v-model.number="form.concept_id" class="field">
            <option v-for="c in concepts" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </label>
        <div class="grid grid-cols-2 gap-2">
          <label><span class="text-xs text-qianhui">对仗词甲</span><input v-model="form.word_a" class="field" /></label>
          <label><span class="text-xs text-qianhui">对仗词乙</span><input v-model="form.word_b" class="field" /></label>
        </div>
        <label class="col-span-2"><span class="text-xs text-qianhui">例句</span><input v-model="form.verse" class="field" /></label>
        <label class="col-span-2"><span class="text-xs text-qianhui">出处</span><input v-model="form.source" class="field" /></label>
      </div>
      <div class="flex justify-end gap-3 mt-5">
        <button class="btn-outline !text-xs" @click="editing = null">取消</button>
        <button class="btn-primary !text-xs" :disabled="!form.word_a || !form.word_b || !form.verse" @click="save">保存</button>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import {
  adminCoupletList, adminCreateCouplet, adminDeleteCouplet, adminUpdateCouplet, getConceptList,
} from '../../api'
import Modal from './Modal.vue'

const concepts = ref([])
const items = ref([])
const filterConcept = ref(0)
const editing = ref(null)
const form = ref({})

async function load() {
  items.value = await adminCoupletList({ concept_id: filterConcept.value || undefined })
}

function openEdit(cp) {
  form.value = cp
    ? { id: cp.id, concept_id: cp.concept_id, word_a: cp.word_a, word_b: cp.word_b, verse: cp.verse, source: cp.source }
    : { id: 0, concept_id: concepts.value[0]?.id, word_a: '', word_b: '', verse: '', source: '' }
  editing.value = true
}

async function save() {
  const payload = { ...form.value }
  delete payload.id
  if (form.value.id) await adminUpdateCouplet(form.value.id, payload)
  else await adminCreateCouplet(payload)
  editing.value = null
  await load()
}

async function remove(cp) {
  if (!confirm(`删除对仗「${cp.word_a}/${cp.word_b}」？`)) return
  await adminDeleteCouplet(cp.id)
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
