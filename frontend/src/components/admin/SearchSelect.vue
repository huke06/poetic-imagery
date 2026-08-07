<template>
  <div class="search-select relative" ref="rootEl">
    <input
      :value="focused ? query : (selectedOption?.label || '')"
      :placeholder="placeholder"
      class="field pr-8"
      autocomplete="off"
      ref="inputEl"
      @input="onInput"
      @focus="onFocus"
      @keydown="onKeydown"
    />
    <!-- 清除按钮 -->
    <button v-if="modelValue != null" type="button"
      class="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5 flex items-center justify-center rounded-full text-qianhui hover:text-zhusha hover:bg-zhusha/10 transition-colors"
      title="清除选择" @mousedown.prevent @click="select(null)">×</button>

    <!-- 下拉列表 -->
    <div v-if="open"
      class="absolute z-30 mt-1 left-0 right-0 max-h-60 overflow-y-auto bg-xuanzhi border border-shiqing/30 rounded-md shadow-xl">
      <div v-if="allowEmpty"
        class="ss-opt text-qianhui"
        :class="{ 'ss-opt-active': highlight === -1 }"
        @mousedown.prevent="select(null)" @mouseenter="highlight = -1">{{ emptyLabel }}</div>
      <div v-for="(o, i) in filtered" :key="o.value"
        class="ss-opt"
        :class="{ 'ss-opt-active': highlight === i, 'ss-opt-selected': o.value === modelValue }"
        @mousedown.prevent="select(o.value)" @mouseenter="highlight = i">
        {{ o.label }}
      </div>
      <div v-if="!filtered.length" class="px-3 py-2.5 text-xs text-qianhui text-center">无匹配意象</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  modelValue: { default: null },
  options: { type: Array, default: () => [] },   // [{ value, label }]
  placeholder: { type: String, default: '请搜索选择…' },
  allowEmpty: { type: Boolean, default: true },
  emptyLabel: { type: String, default: '（不关联）' },
})
const emit = defineEmits(['update:modelValue'])

const rootEl = ref(null)
const inputEl = ref(null)
const open = ref(false)
const focused = ref(false)
const query = ref('')
const highlight = ref(0)

const selectedOption = computed(() => props.options.find((o) => o.value === props.modelValue) || null)

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return props.options
  return props.options.filter((o) => o.label.toLowerCase().includes(q))
})

function onInput(e) {
  query.value = e.target.value
  open.value = true
  highlight.value = 0
}

function onFocus() {
  focused.value = true
  query.value = ''
  open.value = true
  highlight.value = 0
}

function closeDropdown() {
  open.value = false
  focused.value = false
  query.value = ''
}

function select(value) {
  emit('update:modelValue', value)
  closeDropdown()
  inputEl.value?.blur()
}

function onKeydown(e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    open.value = true
    highlight.value = Math.min(highlight.value + 1, filtered.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    const min = props.allowEmpty ? -1 : 0
    highlight.value = Math.max(highlight.value - 1, min)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (!open.value) { open.value = true; return }
    if (highlight.value === -1) select(null)
    else if (filtered.value[highlight.value]) select(filtered.value[highlight.value].value)
  } else if (e.key === 'Escape') {
    closeDropdown()
    inputEl.value?.blur()
  }
}

// 点击组件外部关闭下拉
function onDocMousedown(e) {
  if (rootEl.value && !rootEl.value.contains(e.target)) closeDropdown()
}
onMounted(() => document.addEventListener('mousedown', onDocMousedown))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocMousedown))
</script>

<style scoped>
.ss-opt {
  padding: 7px 12px; font-size: 13px; cursor: pointer; color: #2C2C2C;
  transition: background 0.12s;
}
.ss-opt-active { background: rgba(43, 76, 126, 0.1); }
.ss-opt-selected { color: #9B4423; font-weight: 600; }
</style>
