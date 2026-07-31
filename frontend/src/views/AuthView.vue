<template>
  <div v-if="auth.user" class="max-w-md mx-auto px-4 py-20 text-center">
    <div class="card p-8">
      <div class="seal !w-16 !h-16 !text-xl mx-auto">{{ auth.user.username[0] }}</div>
      <h1 class="font-song text-2xl font-bold mt-4">已登录</h1>
      <p class="text-sm text-qianhui mt-2">{{ auth.user.username }}（{{ auth.user.role === 'admin' ? '管理员' : '用户' }}）</p>
      <button class="btn-outline mt-6" @click="auth.logout()">退出登录</button>
      <router-link to="/" class="btn-primary block mt-3">回到首页</router-link>
    </div>
  </div>
  <div v-else class="max-w-md mx-auto px-4 py-16">
    <div class="card p-8">
      <span class="seal !w-14 !h-14 !text-lg mx-auto block text-center">诗</span>
      <h1 class="font-song text-2xl font-bold text-center mt-4">{{ mode === 'login' ? '登录' : mode === 'register' ? '注册' : '找回密码' }}</h1>

      <form @submit.prevent="submit" class="mt-6 space-y-4">
        <input v-model="form.username" placeholder="用户名" required minlength="2"
          class="w-full px-4 py-2.5 rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing text-sm" />
        <input v-if="mode !== 'login'" v-model="form.email" placeholder="邮箱（选填）"
          class="w-full px-4 py-2.5 rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing text-sm" />
        <input v-if="mode !== 'reset'" v-model="form.password" type="password" placeholder="密码" required minlength="6"
          class="w-full px-4 py-2.5 rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing text-sm" />
        <!-- 验证码 -->
        <div v-if="mode !== 'reset'" class="flex items-center gap-3">
          <span class="bg-black/5 px-3 py-2 rounded text-sm font-mono tracking-wider select-none cursor-pointer"
            @click="refreshCaptcha" :title="'点击刷新'">{{ captcha.question }}</span>
          <input v-model="form.captcha_answer" placeholder="答案" required
            class="flex-1 px-3 py-2 rounded border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing text-sm" />
        </div>

        <p v-if="error" class="text-xs text-zhusha">{{ error }}</p>
        <p v-if="msg" class="text-xs text-zhuqing">{{ msg }}</p>

        <button type="submit" class="btn-primary w-full justify-center !py-2.5" :disabled="loading">
          {{ loading ? '处理中…' : mode === 'login' ? '登录' : mode === 'register' ? '注册' : '找回密码' }}
        </button>
      </form>

      <div class="flex justify-between mt-5 text-xs">
        <button class="text-shiqing hover:underline" @click="switchMode('register')">注册账号</button>
        <button class="text-shiqing hover:underline" @click="switchMode('login')">已有账号</button>
        <button class="text-shiqing hover:underline" @click="switchMode('reset')">忘记密码</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '../stores/auth'
import axios from 'axios'

const router = useRouter()
const mode = ref('login')
const form = ref({ username: '', email: '', password: '', captcha_id: '', captcha_answer: '' })
const captcha = ref({ id: '', question: '1 + 1 = ?' })
const error = ref('')
const msg = ref('')
const loading = ref(false)

async function refreshCaptcha() {
  const { data } = await axios.get('/api/auth/captcha')
  captcha.value = data.data
  form.value.captcha_id = data.data.id
  form.value.captcha_answer = ''
}
onMounted(refreshCaptcha)

function switchMode(m) {
  mode.value = m
  error.value = msg.value = ''
}

async function submit() {
  error.value = msg.value = ''
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(form.value.username, form.value.password, captcha.value.id, form.value.captcha_answer)
    } else if (mode.value === 'register') {
      await auth.register(form.value.username, form.value.password, form.value.email, captcha.value.id, form.value.captcha_answer)
    } else {
      const r = await auth.resetPassword(form.value.email)
      msg.value = `新密码：${r.new_password}。${r.note}`
      return
    }
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || e.message
  } finally {
    loading.value = false
  }
}
</script>
