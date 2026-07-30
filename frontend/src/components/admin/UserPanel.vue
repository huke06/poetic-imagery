<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <p class="text-sm text-qianhui">共 {{ users.length }} 个用户</p>
      <button class="btn-primary !py-1.5 !text-xs" @click="openEdit(null)">新建用户</button>
    </div>
    <div class="space-y-2">
      <div v-for="u in users" :key="u.id" class="card p-4 flex items-center gap-4">
        <span class="seal !w-9 !h-9 !text-xs">{{ u.username[0] }}</span>
        <div class="flex-1">
          <b>{{ u.username }}</b> <span class="text-xs text-qianhui ml-1">{{ u.email }}</span>
          <span class="tag ml-2 !text-[10px]" :class="u.role === 'admin' ? 'border-zheshi/40 text-zheshi' : 'border-shiqing/40 text-shiqing'">{{ u.role }}</span>
          <span v-if="!u.is_active" class="tag border-zhusha/40 text-zhusha !text-[10px] ml-1">已禁用</span>
        </div>
        <span class="text-xs text-qianhui">{{ u.create_time.slice(0, 10) }}</span>
        <button class="btn-outline !py-1 !px-3 !text-xs" @click="openEdit(u)">编辑</button>
        <button class="btn-outline !py-1 !px-3 !text-xs !border-zhusha/50 !text-zhusha hover:!bg-zhusha" @click="remove(u)">删除</button>
      </div>
    </div>
    <Modal :show="editing !== null" :title="form.id ? `编辑用户 · ${form.username}` : '新建用户'" @close="editing = null">
      <div class="grid grid-cols-2 gap-3">
        <label><span class="text-xs text-qianhui">用户名 *</span><input v-model="form.username" class="field" /></label>
        <label><span class="text-xs text-qianhui">邮箱</span><input v-model="form.email" class="field" /></label>
        <label><span class="text-xs text-qianhui">密码（留空=不改）</span><input v-model="form.password" type="password" class="field" /></label>
        <label><span class="text-xs text-qianhui">角色</span>
          <select v-model="form.role" class="field"><option>user</option><option>admin</option></select>
        </label>
        <label class="col-span-2 flex items-center gap-2 text-sm">
          <input type="checkbox" :checked="form.is_active" @change="form.is_active = $event.target.checked" /> 账号启用
        </label>
      </div>
      <div class="flex justify-end gap-3 mt-5">
        <button class="btn-outline !text-xs" @click="editing = null">取消</button>
        <button class="btn-primary !text-xs" :disabled="!form.username" @click="save">保存</button>
      </div>
    </Modal>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { getToken } from '../../api'
import axios from 'axios'
import Modal from './Modal.vue'

const users = ref([])
const editing = ref(null)
const form = ref({})

async function load() {
  const { data } = await axios.get('/api/admin/users', { headers: { 'X-Admin-Token': getToken() } })
  users.value = data.data
}

function openEdit(u) {
  form.value = u ? { ...u, password: '' } : { id: 0, username: '', email: '', password: '', role: 'user', is_active: true }
  editing.value = true
}

async function save() {
  const payload = { ...form.value, is_active: form.value.is_active }
  delete payload.id
  if (form.value.id) await axios.put(`/api/admin/users/${form.value.id}`, payload, { headers: { 'X-Admin-Token': getToken() } })
  else await axios.post('/api/admin/users', payload, { headers: { 'X-Admin-Token': getToken() } })
  editing.value = null
  await load()
}

async function remove(u) {
  if (!confirm(`删除用户 ${u.username}？`)) return
  await axios.delete(`/api/admin/users/${u.id}`, { headers: { 'X-Admin-Token': getToken() } })
  await load()
}

onMounted(load)
</script>
<style scoped>.field{@apply mt-1 w-full px-3 py-2 text-sm rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing;}</style>
