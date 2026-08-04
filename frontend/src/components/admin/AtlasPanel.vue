<template>
  <div>
    <!-- 顶部操作 -->
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs text-qianhui leading-6">上传画卷图片 → 在「标注工作台」拖动红色圆点到意象位置 → 点击圆点填写意象内容与跳转意象。</p>
      <button class="btn-primary !py-1.5 !text-xs" @click="createPainting">新建画卷</button>
    </div>

    <!-- 画卷列表 -->
    <div v-if="!items.length" class="card p-10 text-center text-sm text-qianhui">
      暂无画卷，点击右上「新建画卷」开始。
    </div>
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="p in items" :key="p.id" class="card overflow-hidden">
        <div class="h-36 bg-black/5 flex items-center justify-center overflow-hidden">
          <img v-if="p.image_url" :src="p.image_url" :alt="p.title" class="w-full h-full object-cover" />
          <span v-else class="text-xs text-qianhui">未上传图片</span>
        </div>
        <div class="p-3">
          <div class="flex items-center justify-between">
            <b class="font-song text-sm">《{{ p.title }}》</b>
            <span class="text-[11px] text-qianhui">{{ p.dots.length }} 个标注</span>
          </div>
          <p class="text-xs text-qianhui mt-0.5">{{ p.en || '—' }}</p>
          <div class="flex flex-wrap gap-1 mt-1.5">
            <span v-for="d in p.dots.slice(0, 6)" :key="d.id" class="tag border-zheshi/40 text-zheshi !text-[10px]">{{ d.label }}</span>
            <span v-if="p.dots.length > 6" class="text-[10px] text-qianhui">+{{ p.dots.length - 6 }}</span>
          </div>
          <div class="flex gap-1.5 mt-3">
            <button class="btn-primary !py-0.5 !px-3 !text-[11px]" @click="openWorkbench(p)">标注工作台</button>
            <button class="btn-outline !py-0.5 !px-2 !text-[11px] !border-zhusha/50 !text-zhusha hover:!bg-zhusha" @click="removePainting(p)">删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ 标注工作台 ═══ -->
    <Modal :show="wb !== null" :title="`标注工作台 · ${wb?.title || ''}`" width="max-w-5xl" @close="wb = null">
      <div v-if="wb" class="space-y-4">
        <!-- 元信息 -->
        <div class="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <label class="sm:col-span-2"><span class="text-xs text-qianhui">图画名称 *</span>
            <input v-model="wb.title" class="field" /></label>
          <label><span class="text-xs text-qianhui">英文名</span>
            <input v-model="wb.en" class="field" /></label>
          <label><span class="text-xs text-qianhui">排序（越小越靠前）</span>
            <input v-model.number="wb.sort_order" type="number" class="field" /></label>
        </div>

        <!-- 图片上传 -->
        <div class="flex items-center gap-3">
          <input type="file" accept="image/*" ref="wbFile" class="text-xs flex-1" />
          <button class="btn-outline !py-1 !px-3 !text-xs" :disabled="uploading" @click="uploadImage">
            {{ uploading ? '上传中…' : '上传画卷图片' }}
          </button>
        </div>

        <!-- 画布：图片 + 红点 -->
        <div v-if="wb.image_url" class="relative border border-shiqing/20 rounded overflow-hidden select-none"
          :style="{ cursor: adding ? 'crosshair' : 'default' }" ref="wbCanvas" @click="onCanvasClick">
          <img :src="wb.image_url" class="w-full block pointer-events-none" draggable="false" />
          <!-- 红点 -->
          <div v-for="(d, i) in wb.dots" :key="i"
            class="wb-dot" :class="{ 'wb-dot-active': editIdx === i }"
            :style="{ left: d.left_pct + '%', top: d.top_pct + '%' }"
            @mousedown.stop="startDrag(i, $event)" @click.stop>
            <span class="wb-dot-label">{{ d.label || '待标注' }}</span>
          </div>
          <p class="absolute bottom-2 left-1/2 -translate-x-1/2 text-[11px] bg-black/45 text-white/80 px-3 py-1 rounded pointer-events-none">
            点击空白处添加圆点 · 拖动圆点调整位置 · 点击圆点编辑内容
          </p>
        </div>
        <div v-else class="p-10 text-center text-sm text-qianhui border border-dashed border-shiqing/30 rounded">
          请先上传画卷图片，再进行圆点标注。
        </div>

        <!-- 圆点内容编辑 -->
        <div v-if="editIdx !== null && wb.dots[editIdx]" class="card p-4 border-l-4" style="border-left-color:#9B2C1F">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-semibold text-zheshi">编辑圆点「{{ wb.dots[editIdx].label || '待标注' }}」</span>
            <button class="text-xs text-zhusha hover:underline" @click="removeDot(editIdx)">删除此圆点</button>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <label><span class="text-xs text-qianhui">意象名称（圆点标签）*</span>
              <input v-model="wb.dots[editIdx].label" class="field" placeholder="如：月" /></label>
            <label><span class="text-xs text-qianhui">跳转意象（关联库内意象，可留空）</span>
              <select v-model.number="wb.dots[editIdx].concept_id" class="field">
                <option :value="null">（不关联）</option>
                <option v-for="c in concepts" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select></label>
            <label class="sm:col-span-2"><span class="text-xs text-qianhui">意象基本内容（诗句 / 短语）</span>
              <input v-model="wb.dots[editIdx].poem" class="field" placeholder="如：床前明月光 · 疑是地上霜" /></label>
            <label class="sm:col-span-2"><span class="text-xs text-qianhui">阐释说明</span>
              <textarea v-model="wb.dots[editIdx].desc" rows="2" class="field" placeholder="该意象在此画中的意境与内涵…"></textarea></label>
          </div>
          <div class="flex justify-end mt-3">
            <button class="btn-outline !py-1 !px-4 !text-xs" @click="editIdx = null">完成编辑</button>
          </div>
        </div>

        <!-- 保存 -->
        <div class="flex items-center justify-between pt-2 border-t border-black/5">
          <span v-if="saveMsg" class="text-xs text-zhuqing">{{ saveMsg }}</span>
          <div class="flex gap-3 ml-auto">
            <button class="btn-outline !text-xs" @click="wb = null">取消</button>
            <button class="btn-primary !text-xs" :disabled="!wb.title || saving" @click="saveWorkbench">
              {{ saving ? '保存中…' : '保存画卷与标注' }}
            </button>
          </div>
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import {
  adminAtlasList, adminCreateAtlas, adminDeleteAtlas, adminSaveAtlasDots,
  adminUpdateAtlas, adminUploadAtlasImage, getConceptList,
} from '../../api'
import Modal from './Modal.vue'

const items = ref([])
const concepts = ref([])
const wb = ref(null)          // 工作台当前画卷（含 dots）
const wbFile = ref(null)
const wbCanvas = ref(null)
const editIdx = ref(null)     // 正在编辑的圆点下标
const uploading = ref(false)
const saving = ref(false)
const saveMsg = ref('')

// 拖拽状态
let dragIdx = -1
let dragMoved = false
let dragStart = { x: 0, y: 0 }

async function load() {
  items.value = await adminAtlasList()
}

async function createPainting() {
  const r = await adminCreateAtlas({ title: '新画卷', en: '', image_url: '', sort_order: items.value.length })
  await load()
  const p = items.value.find((x) => x.id === r.id)
  if (p) openWorkbench(p)
}

function openWorkbench(p) {
  wb.value = JSON.parse(JSON.stringify(p))
  editIdx.value = null
  saveMsg.value = ''
}

async function removePainting(p) {
  if (!confirm(`确定删除画卷《${p.title}》及其全部标注？`)) return
  await adminDeleteAtlas(p.id)
  await load()
}

async function uploadImage() {
  const file = wbFile.value?.files?.[0]
  if (!file) { saveMsg.value = '请先选择图片文件'; return }
  uploading.value = true
  try {
    const d = await adminUploadAtlasImage(wb.value.id, file)
    wb.value.image_url = d.image_url
    saveMsg.value = '图片已上传'
  } catch (e) {
    saveMsg.value = '上传失败：' + e.message
  } finally {
    uploading.value = false
  }
}

// 计算事件相对画布的百分比坐标
function pctFromEvent(e) {
  const rect = wbCanvas.value.getBoundingClientRect()
  const x = ((e.clientX - rect.left) / rect.width) * 100
  const y = ((e.clientY - rect.top) / rect.height) * 100
  return { x: Math.min(99, Math.max(1, x)), y: Math.min(99, Math.max(1, y)) }
}

// 点击空白处添加圆点
function onCanvasClick(e) {
  if (dragIdx >= 0) return
  const { x, y } = pctFromEvent(e)
  wb.value.dots.push({ left_pct: x, top_pct: y, label: '', poem: '', desc: '', concept_id: null })
  editIdx.value = wb.value.dots.length - 1
}

// 圆点拖拽
function startDrag(i, e) {
  dragIdx = i
  dragMoved = false
  dragStart = { x: e.clientX, y: e.clientY }
  window.addEventListener('mousemove', onDragMove)
  window.addEventListener('mouseup', onDragUp)
}
function onDragMove(e) {
  if (dragIdx < 0) return
  if (Math.abs(e.clientX - dragStart.x) > 4 || Math.abs(e.clientY - dragStart.y) > 4) dragMoved = true
  if (!dragMoved) return
  const { x, y } = pctFromEvent(e)
  const d = wb.value.dots[dragIdx]
  d.left_pct = x
  d.top_pct = y
}
function onDragUp() {
  const i = dragIdx
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragUp)
  dragIdx = -1
  if (!dragMoved) editIdx.value = i   // 未移动 → 视为点击，打开编辑
}

function removeDot(i) {
  wb.value.dots.splice(i, 1)
  editIdx.value = null
}

async function saveWorkbench() {
  saving.value = true
  saveMsg.value = ''
  try {
    await adminUpdateAtlas(wb.value.id, {
      title: wb.value.title, en: wb.value.en, image_url: '', sort_order: wb.value.sort_order,
    })
    const dots = wb.value.dots.map((d) => ({
      left_pct: d.left_pct, top_pct: d.top_pct, label: d.label,
      poem: d.poem, desc: d.desc, concept_id: d.concept_id || null,
    }))
    await adminSaveAtlasDots(wb.value.id, dots)
    saveMsg.value = '已保存 ✔'
    await load()
    wb.value = null
  } catch (e) {
    saveMsg.value = '保存失败：' + e.message
  } finally {
    saving.value = false
  }
}

onBeforeUnmount(() => {
  window.removeEventListener('mousemove', onDragMove)
  window.removeEventListener('mouseup', onDragUp)
})

onMounted(async () => {
  const data = await getConceptList({ page_size: 500 })
  concepts.value = data.items
  await load()
})
</script>

<style scoped>
.field {
  @apply mt-1 w-full px-3 py-2 text-sm rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing;
}
/* 红色标注圆点 */
.wb-dot {
  position: absolute; width: 22px; height: 22px; margin-left: -11px; margin-top: -11px;
  border-radius: 50%; background: #C0392B; border: 2px solid #F5F1E8;
  box-shadow: 0 0 0 2px rgba(192,57,43,0.35), 0 2px 6px rgba(0,0,0,0.3);
  cursor: grab; z-index: 5; transition: transform 0.15s;
}
.wb-dot:active { cursor: grabbing; }
.wb-dot:hover { transform: scale(1.15); }
.wb-dot-active { outline: 3px solid rgba(192,57,43,0.4); outline-offset: 2px; }
.wb-dot-label {
  position: absolute; left: 50%; top: -26px; transform: translateX(-50%);
  background: #1A1410; color: #FAF5EB; font-size: 11px; padding: 2px 7px;
  border-radius: 3px; white-space: nowrap; pointer-events: none;
}
</style>
