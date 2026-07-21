<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <p class="text-sm text-qianhui leading-6">
        修改即时生效，保存在后端 <code class="text-xs bg-black/5 px-1 rounded">runtime_config.json</code>；
        留空表示回落环境变量 <code class="text-xs bg-black/5 px-1 rounded">.env</code> 中的值。
      </p>
      <button class="btn-primary !py-1.5 !text-xs shrink-0" :disabled="saving" @click="save">
        {{ saving ? '保存中…' : '保存配置' }}
      </button>
    </div>
    <div v-if="msg" class="text-sm px-4 py-2 rounded bg-zhuqing/10 text-zhuqing border border-zhuqing/30">{{ msg }}</div>
    <div class="space-y-4">
      <div v-for="item in items" :key="item.key" class="card p-4">
        <div class="flex items-center gap-2">
          <label class="font-semibold text-sm">{{ item.label }}</label>
          <code class="text-xs text-qianhui">{{ item.key }}</code>
          <span v-if="item.is_set" class="tag border-zhuqing/40 text-zhuqing">已配置</span>
          <span v-else class="tag border-black/20 text-qianhui">未配置</span>
          <span class="text-[10px] text-qianhui/70 ml-auto">来源：{{ item.source === 'runtime' ? '运行时配置' : '环境变量' }}</span>
        </div>
        <input v-model="form[item.key]" :type="item.secret ? 'password' : 'text'"
          :placeholder="item.secret && item.value ? `当前：${item.value}` : item.hint"
          class="mt-2 w-full px-3 py-2 text-sm rounded border border-shiqing/25 bg-white/70
                 focus:outline-none focus:border-shiqing font-mono" />
        <p class="text-xs text-qianhui mt-1.5">{{ item.hint }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getAdminConfig, putAdminConfig } from '../../api'

const items = ref([])
const form = ref({})
const saving = ref(false)
const msg = ref('')

onMounted(async () => {
  items.value = await getAdminConfig()
  for (const it of items.value) form.value[it.key] = ''
})

async function save() {
  saving.value = true
  msg.value = ''
  try {
    // 只提交非空字段（空 = 不修改/清除覆盖）
    const changes = {}
    for (const [k, v] of Object.entries(form.value)) {
      if (v && !(v.startsWith('••••'))) changes[k] = v
    }
    await putAdminConfig(changes)
    msg.value = '配置已保存并即时生效'
    items.value = await getAdminConfig()
    form.value = {}
    for (const it of items.value) form.value[it.key] = ''
  } catch (e) {
    msg.value = '保存失败：' + e.message
  } finally {
    saving.value = false
  }
}
</script>
