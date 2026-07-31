<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <p class="text-sm" :class="loadErr ? 'text-zhusha' : 'text-qianhui'">
        {{ loadErr || `共 ${list.length} 个意象` }}
      </p>
      <button class="btn-primary !py-1.5 !text-xs" @click="openEdit(null)">新建意象</button>
    </div>
    <div class="space-y-2">
      <div v-for="c in list" :key="c.id" class="card p-4 flex items-center gap-4">
        <span class="w-9 h-9 rounded-md shrink-0 border border-black/10" :style="{ background: c.theme_color }"></span>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <b class="font-song text-lg">{{ c.name }}</b>
            <span class="text-xs text-qianhui">{{ c.category_main }} · {{ c.category_sub }}</span>
            <span v-if="c.emotion_tags" class="text-xs text-qianhui">{{ Array.isArray(c.emotion_tags) ? c.emotion_tags.join(',') : c.emotion_tags }}</span>
          </div>
        </div>
        <button class="btn-outline !py-1 !px-3 !text-xs" @click="openEdit(c)">编辑</button>
        <button class="btn-outline !py-1 !px-3 !text-xs !border-zhusha/50 !text-zhusha hover:!bg-zhusha" @click="remove(c)">删除</button>
      </div>
    </div>

    <Modal :show="editing !== null" :title="form.id ? `编辑意象 · ${form.name}` : '新建意象'" @close="editing = null">
      <div class="grid grid-cols-2 gap-3">
        <label class="block"><span class="text-xs text-qianhui">名称 *</span>
          <input v-model="form.name" class="field" :disabled="!!form.id" /></label>
        <label class="block"><span class="text-xs text-qianhui">一级分类</span>
          <select v-model="form.category_main" class="field" @change="onMainCatChange">
            <option v-for="cat in mainCategories" :key="cat">{{ cat }}</option></select></label>
        <label class="block"><span class="text-xs text-qianhui">二级类目</span>
          <select v-model="form.category_sub" class="field" @change="suggestColor">
            <option v-for="sub in (subCategories[form.category_main]||[])" :key="sub">{{ sub }}</option></select></label>
        <label class="block col-span-2"><span class="text-xs text-qianhui">别称（逗号分隔）</span>
          <input v-model="form.aliases" class="field" /></label>
        <label class="block col-span-2"><span class="text-xs text-qianhui">本义</span>
          <textarea v-model="form.original_meaning" rows="2" class="field"></textarea></label>
        <label class="block col-span-2"><span class="text-xs text-qianhui">诗词引申义 *</span>
          <textarea v-model="form.poetic_meaning" rows="3" class="field"></textarea></label>
        <label class="block"><span class="text-xs text-qianhui">情感标签（逗号分隔）*</span>
          <input v-model="form.emotion_tags" class="field" /></label>
        <div class="grid grid-cols-2 gap-2">
          <label class="block"><span class="text-xs text-qianhui">起源朝代</span><input v-model="form.origin_dynasty" class="field" /></label>
          <label class="block"><span class="text-xs text-qianhui">鼎盛朝代</span><input v-model="form.peak_dynasty" class="field" /></label></div>
        <label class="block col-span-2"><span class="text-xs text-qianhui">演变描述</span>
          <textarea v-model="form.description" rows="4" class="field"></textarea></label>
        <!-- 配色 -->
        <div class="col-span-2">
          <div class="flex items-center gap-3"><span class="text-xs text-qianhui">主题色</span>
            <span class="w-8 h-8 rounded border border-black/10" :style="{background:form.theme_color}"></span>
            <code class="text-xs">{{ form.theme_color }}</code>
            <button class="btn-outline !py-1 !px-3 !text-xs" @click="suggestColor">推荐色</button></div>
          <div class="flex flex-wrap gap-1.5 mt-2">
            <button v-for="p in palette" :key="p.color" :title="p.color_name"
              class="w-7 h-7 rounded border-2 transition-transform hover:scale-110"
              :style="{background:p.color,borderColor:form.theme_color===p.color?'#2C2C2C':'transparent'}"
              @click="form.theme_color=p.color"></button></div>
        </div>
      </div>
      <div class="flex justify-end gap-3 mt-6">
        <button class="btn-outline !text-xs" @click="editing=null">取消</button>
        <button class="btn-primary !text-xs" :disabled="!form.name||!form.poetic_meaning" @click="save">保存</button>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { adminCreateConcept, adminDeleteConcept, adminUpdateConcept, getConceptList, getConceptDetail, getPalette } from '../../api'
import Modal from './Modal.vue'

const mainCategories = ['自然类','社会生活类','人类自身类','人造物类','虚拟类']
const subCategories = {
  '自然类':['天文气象','山水地理','文化地标','植物','动物','自然景观'],
  '社会生活类':['战争军事','仕途游宦','农耕渔猎','交通迁徙','节日民俗'],
  '人类自身类':['身体器官','情感心理','人格精神'],
  '人造物类':['建筑空间','生活器物','服饰装饰','交通工具','城市与文化空间'],
  '虚拟类':['神仙仙境','神话传说','鬼怪灵异','宗教','概念'],
}
const list = ref([])
const editing = ref(null)
const form = ref({})
const palette = ref([])
const loadErr = ref('')

async function load() {
  loadErr.value = ''
  try {
    const data = await getConceptList()
    list.value = data?.items || []
  } catch (e) {
    loadErr.value = '加载失败: ' + (e.response?.data?.detail || e.message)
    list.value = []
  }
}

async function openEdit(c) {
  if (c) {
    // 取详情获得完整字段
    try {
      const detail = await getConceptDetail(c.id)
      form.value = {
        ...detail,
        emotion_tags: Array.isArray(detail.emotion_tags) ? detail.emotion_tags.join(',') : (detail.emotion_tags||''),
        aliases: Array.isArray(detail.aliases) ? detail.aliases.join(',') : (detail.aliases||''),
        category_main: detail.category_main || '自然类',
        category_sub: detail.category_sub || '',
      }
    } catch {
      form.value = { id: c.id, name: c.name, category_main: c.category_main||'自然类', category_sub: c.category_sub||'', aliases: '', original_meaning: '', poetic_meaning: '', emotion_tags: Array.isArray(c.emotion_tags)?c.emotion_tags.join(','):(c.emotion_tags||''), origin_dynasty: '', peak_dynasty: '', description: '', theme_color: c.theme_color||'' }
    }
  } else {
    form.value = { id: 0, name: '', category_main: '自然类', category_sub: '天文气象', aliases: '', original_meaning: '', poetic_meaning: '', emotion_tags: '', origin_dynasty: '', peak_dynasty: '', description: '', theme_color: '' }
  }
  editing.value = true
  suggestColor()
}

function onMainCatChange() {
  form.value.category_sub = (subCategories[form.value.category_main]||[])[0]||''
  suggestColor()
}

async function suggestColor() {
  try {
    const data = await getPalette({ name: form.value.name||'x', category: form.value.category_main||'' })
    palette.value = data.family_colors || []
    if (!form.value.theme_color && data.suggested) form.value.theme_color = data.suggested.color
  } catch { palette.value = [] }
}

async function save() {
  const payload = { ...form.value }
  delete payload.id
  if (form.value.id) await adminUpdateConcept(form.value.id, payload)
  else await adminCreateConcept(payload)
  editing.value = null
  await load()
}

async function remove(c) {
  if (!confirm('确定删除「'+c.name+'」？关联/对仗/统计级联删除，诗文本体保留。')) return
  await adminDeleteConcept(c.id)
  await load()
}

onMounted(load)
</script>

<style scoped>
.field { @apply mt-1 w-full px-3 py-2 text-sm rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing; }
</style>
