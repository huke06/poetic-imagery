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
      const { data } = await axios.get('/api/auth/me', { headers: { Authorization: 'Bearer ' + this.token } })
      this.user = data.data
    } catch { this.logout() }
  },

  async login(username, password) {
    const { data } = await axios.post('/api/auth/login', { username, password })
    this.token = data.data.token
    this.user = data.data.user
    localStorage.setItem(TOKEN_KEY, this.token)
  },

  async register(username, password, email) {
    const { data } = await axios.post('/api/auth/register', { username, password, email: email || '' })
    this.token = data.data.token
    this.user = data.data.user
    localStorage.setItem(TOKEN_KEY, this.token)
  },

  async changePassword(oldPassword, newPassword) {
    const { data } = await axios.post('/api/auth/change-password',
      { old_password: oldPassword, new_password: newPassword },
      { headers: { Authorization: 'Bearer ' + this.token } })
    return data
  },

  logout() {
    this.token = ''
    this.user = null
    localStorage.removeItem(TOKEN_KEY)
  },
})
