<template>
  <div class="space-y-6">
    <!-- 模板下载 -->
    <div class="card p-5">
      <h3 class="font-song font-bold">第一步：下载模板</h3>
      <p class="text-xs text-qianhui mt-1 leading-6">
        三种模板按需组合：JSON 功能最全；CSV 适合 Excel 整理。<b class="text-moyan">可同时选择多个文件一起上传</b>——
        例如「意象本体表 + 诗文关联表」同传，一次建成完整意象；后续再传 JSON 补充对仗/古画/关联。<br />
        <b class="text-moyan">模板文件就在项目目录 <code class="bg-black/5 px-1 rounded">templates/</code> 下</b>（含填写说明.txt），也可点下方按钮直接下载：
      </p>
      <div class="flex flex-wrap gap-3 mt-3">
        <a v-for="t in templates" :key="t.format" :href="`/api/admin/import/template?format=${t.format}`" :download="t.file"
          class="btn-outline !py-1.5 !px-4 !text-xs">{{ t.label }}</a>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-3 mt-4 text-xs text-qianhui leading-6">
        <div class="bg-white/50 rounded p-3">
          <b class="text-moyan">JSON 富格式</b>（全量内容）<br />单意象或 {`{"concepts":[...]}`} 批量；
          含本体+诗文+对仗+古画+关联五段；也可只写其中几段，作为已有意象的「补充包」
        </div>
        <div class="bg-white/50 rounded p-3">
          <b class="text-moyan">CSV · 意象本体表</b>（骨架信息）<br />一行一个意象：名称/分类/别称/情感标签/本义/引申义/演变史。
          已存在的意象会自动<strong>补全空缺字段</strong>
        </div>
        <div class="bg-white/50 rounded p-3">
          <b class="text-moyan">CSV · 诗文关联表</b>（诗句数据）<br />一行一条「诗文-意象」关联；诗文按 标题+作者 自动去重复用；
          全文换行写 <code class="bg-black/5 px-1 rounded">\n</code>；情感标签空格分隔
        </div>
      </div>
    </div>

    <!-- 上传 -->
    <div class="card p-5">
      <h3 class="font-song font-bold">第二步：上传文件（可多选）</h3>
      <div class="mt-3 border-2 border-dashed border-shiqing/30 rounded-lg p-8 text-center transition-colors"
        :class="{ 'border-shiqing bg-shiqing/5': dragging }"
        @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="onDrop">
        <input ref="fileInput" type="file" accept=".json,.csv" multiple class="hidden" @change="onPick" />
        <p class="text-sm text-qianhui">拖拽 .json / .csv 文件到此处（可多选），或</p>
        <button class="btn-primary !py-1.5 !text-xs mt-3" @click="fileInput?.click()">选择文件</button>
        <div v-if="files.length" class="mt-4 flex flex-wrap justify-center gap-2">
          <span v-for="(f, i) in files" :key="i" class="tag border-shiqing/40 text-shiqing !text-xs">
            {{ f.name }}（{{ (f.size / 1024).toFixed(1) }}KB）
            <button class="ml-1 text-zhusha" @click="files.splice(i, 1); resetResult()">×</button>
          </span>
        </div>
      </div>
      <div class="flex gap-3 mt-4">
        <button class="btn-outline !text-xs" :disabled="!files.length || busy" @click="check">校验预览</button>
        <button class="btn-primary !text-xs" :disabled="!files.length || busy || (checked && hasErrors)" @click="doImport">
          {{ busy ? '处理中…' : '执行导入' }}
        </button>
        <span v-if="checked && hasErrors" class="text-xs text-zhusha self-center">存在校验错误，请修正后重新上传</span>
      </div>
    </div>

    <!-- 结果 -->
    <div v-if="result" class="card p-5">
      <h3 class="font-song font-bold">{{ imported ? '导入结果' : '校验预览' }}</h3>
      <div class="flex flex-wrap gap-4 mt-3 text-sm">
        <span class="tag border-shiqing/40 text-shiqing">{{ (result.preview.formats || []).join(' + ') }}</span>
        <span>文件 {{ result.preview.files }} 个</span>
        <span>意象 <b>{{ result.preview.concept_count }}</b> 个：{{ (result.preview.concepts || []).join('、') }}</span>
        <span>诗文 {{ result.preview.poetry_rows }} 首</span>
        <span>关联 {{ result.preview.rel_rows }} 条</span>
        <span v-if="result.preview.couplet_rows">对仗 {{ result.preview.couplet_rows }} 组</span>
        <span v-if="result.preview.artwork_rows">古画 {{ result.preview.artwork_rows }} 幅</span>
      </div>
      <div v-if="result.errors?.length" class="mt-4">
        <p class="text-sm font-semibold text-zhusha">错误（{{ result.errors.length }}）</p>
        <ul class="text-xs text-zhusha/90 mt-1 space-y-1 max-h-40 overflow-y-auto">
          <li v-for="(e, i) in result.errors" :key="i">· {{ e }}</li>
        </ul>
      </div>
      <div v-if="result.warnings?.length" class="mt-4">
        <p class="text-sm font-semibold text-zheshi">提示（{{ result.warnings.length }}）</p>
        <ul class="text-xs text-qianhui mt-1 space-y-1 max-h-32 overflow-y-auto">
          <li v-for="(w, i) in result.warnings" :key="i">· {{ w }}</li>
        </ul>
      </div>
      <div v-if="imported && result.reports?.length" class="mt-4 space-y-1.5">
        <div v-for="(r, i) in result.reports" :key="i" class="text-xs bg-zhuqing/10 border border-zhuqing/25 rounded px-3 py-2">
          <b class="text-zhuqing">{{ r.concept_created ? '新建' : '补充' }}「{{ r.concept }}」</b>
          ：诗文 新增{{ r.poetry_new }}/复用{{ r.poetry_reused }}，关联 {{ r.rel_new }} 条（跳过重复 {{ r.rel_skipped }}），
          对仗 {{ r.couplet_new }}，古画 新增{{ r.artwork_new }}/复用{{ r.artwork_reused }}，意象关联 {{ r.relation_new }}
        </div>
        <p class="text-sm text-zhuqing mt-2">导入完成 ✔ 前台页面、图表、问答已自动生效</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { getToken } from '../../api'

const templates = [
  { format: 'json', label: 'JSON 模板', file: 'concept_template.json' },
  { format: 'csv_concepts', label: 'CSV · 意象本体表', file: 'concepts_template.csv' },
  { format: 'csv_poetries', label: 'CSV · 诗文关联表', file: 'poetries_template.csv' },
]

const files = ref([])
const fileInput = ref(null)
const dragging = ref(false)
const busy = ref(false)
const checked = ref(false)
const hasErrors = ref(false)
const imported = ref(false)
const result = ref(null)

function onPick(e) {
  files.value = [...files.value, ...Array.from(e.target.files || [])]
  e.target.value = ''
  resetResult()
}

function onDrop(e) {
  dragging.value = false
  const dropped = Array.from(e.dataTransfer.files || []).filter((f) => /\.(json|csv)$/i.test(f.name))
  if (dropped.length) {
    files.value = [...files.value, ...dropped]
    resetResult()
  }
}

function resetResult() {
  result.value = null
  checked.value = false
  hasErrors.value = false
  imported.value = false
}

async function send(dryRun) {
  const fd = new FormData()
  files.value.forEach((f) => fd.append('files', f))
  const resp = await axios.post(`/api/admin/import?dry_run=${dryRun}`, fd, {
    headers: { 'X-Admin-Token': getToken() },
  })
  return resp.data
}

async function check() {
  busy.value = true
  try {
    const body = await send(true)
    result.value = body.data
    hasErrors.value = body.code !== 0
    checked.value = true
  } catch (e) {
    result.value = { preview: {}, errors: [e.response?.data?.detail || e.message], warnings: [] }
    hasErrors.value = true
    checked.value = true
  } finally {
    busy.value = false
  }
}

async function doImport() {
  busy.value = true
  try {
    const body = await send(false)
    result.value = body.data
    hasErrors.value = body.code !== 0
    imported.value = body.code === 0
  } catch (e) {
    result.value = { preview: {}, errors: [e.response?.data?.detail || e.message], warnings: [] }
    hasErrors.value = true
  } finally {
    busy.value = false
  }
}
</script>
