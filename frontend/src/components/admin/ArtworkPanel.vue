<template>
  <div>
    <div class="flex items-center gap-3 mb-3">
      <input v-model="keyword" @keyup.enter="page = 1; load()" placeholder="检索画名/作者…"
        class="w-56 px-3 py-2 text-sm rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing" />
      <button class="btn-outline !py-1.5 !text-xs" @click="page = 1; load()">检索</button>
      <div class="flex-1"></div>
      <button class="btn-primary !py-1.5 !text-xs" @click="openEdit(null)">录入古画</button>
    </div>
    <p class="text-xs text-qianhui mb-4 leading-6">
      图片接入三种方式：① 外链 URL（接入 artlib.cn 等图库）② 本地上传图片文件 ③ 自动生成国风水墨占位图。
      批量接入路径：注册 artlib.cn 获取 appkey/secret 后，可编写脚本将艺术品库元数据批量写入本表并回填 image_url。
    </p>

    <div class="grid grid-cols-2 lg:grid-cols-3 gap-4">
      <div v-for="a in items" :key="a.id" class="card overflow-hidden">
        <img :src="a.thumb_url" :alt="a.name" class="w-full h-32 object-cover bg-black/5" />
        <div class="p-3">
          <b class="font-song text-sm">《{{ a.name }}》</b>
          <p class="text-xs text-qianhui">{{ a.dynasty }} · {{ a.artist }}</p>
          <div class="flex flex-wrap gap-1 mt-1.5">
            <span v-for="r in a.rels" :key="r.concept_id" class="tag border-shiqing/30 text-shiqing !text-[10px]">{{ r.concept_name }}</span>
          </div>
          <div class="flex gap-1.5 mt-3">
            <button class="btn-outline !py-0.5 !px-2 !text-[11px]"
              :class="a.is_featured ? '!border-amber-500 !text-amber-600' : '!text-qianhui/50'"
              :title="a.is_featured ? '取消首页精选' : '设为首页精选（出现在首页滚动封面/艺术品精选）'"
              @click="toggleHomeFeature(a)">{{ a.is_featured ? '★ 精选' : '☆ 精选' }}</button>
            <button class="btn-outline !py-0.5 !px-2 !text-[11px]" @click="openEdit(a)">编辑</button>
            <button class="btn-outline !py-0.5 !px-2 !text-[11px]" @click="openImage(a)">图片</button>
            <button class="btn-outline !py-0.5 !px-2 !text-[11px] !border-zhusha/50 !text-zhusha hover:!bg-zhusha" @click="remove(a)">删除</button>
          </div>
        </div>
      </div>
    </div>
    <Pagination :page="page" :page-size="pageSize" :total="total" @change="(p) => { page = p; load() }" />

    <!-- 元数据编辑弹窗 -->
    <Modal :show="editing !== null" :title="form.id ? `编辑古画 · ${form.name}` : '录入古画'" width="max-w-3xl" @close="editing = null">
      <div class="grid grid-cols-3 gap-3">
        <label class="col-span-2"><span class="text-xs text-qianhui">名称 *</span><input v-model="form.name" class="field" /></label>
        <label><span class="text-xs text-qianhui">作者</span><input v-model="form.artist" class="field" /></label>
        <label><span class="text-xs text-qianhui">朝代</span><input v-model="form.dynasty" class="field" /></label>
        <label><span class="text-xs text-qianhui">材质</span><input v-model="form.material" class="field" /></label>
        <label><span class="text-xs text-qianhui">尺寸</span><input v-model="form.size" class="field" /></label>
        <label class="col-span-2"><span class="text-xs text-qianhui">主题（分号分隔）</span><input v-model="form.subject_names" class="field" /></label>
        <label><span class="text-xs text-qianhui">上游 workId（可选）</span><input v-model="form.source_work_id" class="field font-mono" /></label>
        <label class="col-span-3"><span class="text-xs text-qianhui">简介</span><textarea v-model="form.description" rows="3" class="field"></textarea></label>
        <label class="col-span-3"><span class="text-xs text-qianhui">外链图片 URL（方式①，保存后生效）</span><input v-model="form.image_url" class="field font-mono" placeholder="https://…" /></label>
        <div class="col-span-2">
          <span class="text-xs text-qianhui">关联意象</span>
          <div class="flex flex-wrap gap-2 mt-1">
            <label v-for="c in concepts" :key="c.id" class="tag cursor-pointer"
              :class="form.concept_ids.includes(c.id) ? '!bg-shiqing !text-white !border-shiqing' : 'border-shiqing/30 text-shiqing'">
              <input type="checkbox" class="hidden" :value="c.id" v-model="form.concept_ids" />{{ c.name }}
            </label>
          </div>
        </div>
        <label><span class="text-xs text-qianhui">关联阐释</span><input v-model="form.relation_desc" class="field" /></label>
      </div>
      <div class="flex justify-end gap-3 mt-6">
        <button class="btn-outline !text-xs" @click="editing = null">取消</button>
        <button class="btn-primary !text-xs" :disabled="!form.name" @click="save">保存</button>
      </div>
    </Modal>

    <!-- 图片接入弹窗 -->
    <Modal :show="imaging !== null" :title="`图片接入 · ${imaging?.name || ''}`" @close="imaging = null">
      <div v-if="imaging" class="space-y-5">
        <div class="flex justify-center"><img :src="imaging.thumb_url" class="max-h-52 rounded border border-black/10" /></div>
        <div class="card p-4">
          <h4 class="text-sm font-semibold">方式②：本地上传</h4>
          <div class="flex items-center gap-3 mt-2">
            <input type="file" accept="image/*" ref="fileInput" class="text-xs" />
            <button class="btn-primary !py-1 !px-3 !text-xs" :disabled="uploading" @click="doUpload">{{ uploading ? '上传中…' : '上传' }}</button>
          </div>
        </div>
        <div class="card p-4">
          <h4 class="text-sm font-semibold">方式③：重新生成水墨占位图</h4>
          <div class="flex items-center gap-2 mt-2">
            <select v-model="svgTheme" class="field !w-32">
              <option value="">自动判断</option><option>月</option><option>夕阳</option><option>青绿</option>
            </select>
            <button class="btn-outline !py-1 !px-3 !text-xs" @click="doRegen">重新生成</button>
          </div>
        </div>
        <p v-if="imageMsg" class="text-sm text-zhuqing">{{ imageMsg }}</p>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import {
  adminArtworkList, adminCreateArtwork, adminDeleteArtwork, adminRegenSvg,
  adminToggleArtworkHomeFeature, adminUpdateArtwork, adminUploadImage, getConceptList,
} from '../../api'
import Modal from './Modal.vue'
import Pagination from '../Pagination.vue'

const items = ref([])
const concepts = ref([])
const keyword = ref('')
const page = ref(1)
const pageSize = 12
const total = ref(0)
const editing = ref(null)
const form = ref({})
const imaging = ref(null)
const fileInput = ref(null)
const uploading = ref(false)
const svgTheme = ref('')
const imageMsg = ref('')

async function load() {
  const data = await adminArtworkList({ keyword: keyword.value, page: page.value, page_size: pageSize })
  items.value = data.items
  total.value = data.total
}

function openEdit(a) {
  form.value = a
    ? { id: a.id, name: a.name, artist: a.artist, dynasty: a.dynasty, material: a.material, size: a.size, subject_names: a.subject_names, description: a.description, image_url: a.image_url?.startsWith('/static') ? '' : a.image_url, source_work_id: a.source_work_id, concept_ids: a.rels.map((r) => r.concept_id), relation_desc: a.rels[0]?.relation_desc || '' }
    : { id: 0, name: '', artist: '', dynasty: '宋', material: '', size: '', subject_names: '中国绘画;山水', description: '', image_url: '', source_work_id: '', concept_ids: [], relation_desc: '' }
  editing.value = true
}

function openImage(a) {
  imaging.value = a
  imageMsg.value = ''
  svgTheme.value = ''
}

async function save() {
  const payload = { ...form.value }
  delete payload.id
  if (form.value.id) await adminUpdateArtwork(form.value.id, payload)
  else await adminCreateArtwork(payload)
  editing.value = null
  await load()
}

async function remove(a) {
  if (!confirm(`确定删除《${a.name}》？`)) return
  await adminDeleteArtwork(a.id)
  await load()
}

async function toggleHomeFeature(a) {
  const newVal = !a.is_featured
  try {
    await adminToggleArtworkHomeFeature(a.id, newVal)
    a.is_featured = newVal
  } catch (e) {
    alert('设置精选失败：' + e.message)
  }
}

async function doUpload() {
  const file = fileInput.value?.files?.[0]
  if (!file) { imageMsg.value = '请先选择图片文件'; return }
  uploading.value = true
  try {
    const data = await adminUploadImage(imaging.value.id, file)
    imageMsg.value = '上传成功：' + data.image_url
    await load()
    imaging.value = items.value.find((x) => x.id === imaging.value.id)
  } catch (e) {
    imageMsg.value = '上传失败：' + e.message
  } finally {
    uploading.value = false
  }
}

async function doRegen() {
  const data = await adminRegenSvg(imaging.value.id, svgTheme.value)
  imageMsg.value = `已按「${data.theme}」主题重新生成`
  await load()
  imaging.value = items.value.find((x) => x.id === imaging.value.id)
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
