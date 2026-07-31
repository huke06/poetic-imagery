import { reactive } from 'vue'
import axios from 'axios'

const TOKEN_KEY = 'sxz_jwt'

export const auth = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: null,
  loading: false,

  get loggedIn() { return !!this.token && !!this.user },

  async init() {
    if (!this.token) return
    try {
      const { data } = await axios.get('/api/auth/me', { headers: { Authorization: `Bearer ${this.token}` } })
      this.user = data.data
    } catch { this.logout() }
  },

  async login(username, password, captchaId, captchaAnswer) {
    const { data } = await axios.post('/api/auth/login', { username, password, captcha_id: captchaId || '', captcha_answer: captchaAnswer || '' })
    this.token = data.data.token
    this.user = data.data.user
    localStorage.setItem(TOKEN_KEY, this.token)
  },

  async register(username, password, email, captchaId, captchaAnswer) {
    const { data } = await axios.post('/api/auth/register', { username, password, email: email || '', captcha_id: captchaId || '', captcha_answer: captchaAnswer || '' })
    this.token = data.data.token
    this.user = data.data.user
    localStorage.setItem(TOKEN_KEY, this.token)
  },

  async resetPassword(email) {
    const { data } = await axios.post('/api/auth/reset-password', { email })
    return data.data
  },

  logout() {
    this.token = ''
    this.user = null
    localStorage.removeItem(TOKEN_KEY)
  },
})
