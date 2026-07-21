import axios from 'axios'

const http = axios.create({ baseURL: '/', timeout: 30000 })

http.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) return Promise.reject(new Error(body.msg || '请求失败'))
      return body.data
    }
    return body
  },
  (err) => Promise.reject(err),
)

// ─────────── 意象 ───────────
export const getConceptList = (params = {}) => http.get('/api/concept/list', { params })
export const getConceptDetail = (id) => http.get(`/api/concept/${id}`)
export const getConceptPoetries = (id, params = {}) => http.get(`/api/concept/${id}/poetries`, { params })
export const getConceptArtworks = (id) => http.get(`/api/concept/${id}/artworks`)
export const getConceptRelations = (id) => http.get(`/api/concept/${id}/relations`)
export const shareCardUrl = (id) => `/api/concept/${id}/share-card`

// ─────────── 诗文 ───────────
export const getPoetryDetail = (id) => http.get(`/api/poetry/${id}`)
export const searchPoetry = (payload) => http.post('/api/poetry/search', payload)
export const getSimilar = (id) => http.get(`/api/poetry/${id}/similar`)
export const getTones = (id) => http.get(`/api/poetry/${id}/tones`)
export const getBookLinks = (id) => http.get(`/api/poetry/${id}/book-links`)
export const getLabelize = (id) => http.get(`/api/poetry/${id}/labelize`)

// ─────────── 艺术品 ───────────
export const getArtworkList = (params = {}) => http.get('/api/artwork/list', { params })
export const getArtworkDetail = (id) => http.get(`/api/artwork/${id}`)

// ─────────── 智能助手 ───────────
export const agentAsk = (question) => http.post('/api/agent/ask', { question })
export const agentCompose = (payload) => http.post('/api/agent/compose', payload)

// ─────────── 管理后台 ───────────
const TOKEN_KEY = 'sxz_admin_token'
export const getToken = () => localStorage.getItem(TOKEN_KEY) || ''
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)

const admin = axios.create({ baseURL: '/', timeout: 30000 })
admin.interceptors.request.use((cfg) => {
  cfg.headers['X-Admin-Token'] = getToken()
  return cfg
})
admin.interceptors.response.use(
  (resp) => {
    const body = resp.data
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) return Promise.reject(new Error(body.msg || '请求失败'))
      return body.data
    }
    return body
  },
  (err) => {
    if (err.response?.status === 401) throw new Error('管理令牌无效或已过期')
    throw new Error(err.response?.data?.detail || err.message)
  },
)

export const adminOverview = () => admin.get('/api/admin/overview')
export const getAdminConfig = () => admin.get('/api/admin/config')
export const putAdminConfig = (changes) => admin.put('/api/admin/config', { changes })
export const getPalette = (params) => admin.get('/api/admin/palette', { params })
export const recomputeStats = () => admin.post('/api/admin/stats/recompute')

export const adminCreateConcept = (payload) => admin.post('/api/admin/concept', payload)
export const adminUpdateConcept = (id, payload) => admin.put(`/api/admin/concept/${id}`, payload)
export const adminDeleteConcept = (id) => admin.delete(`/api/admin/concept/${id}`)

export const adminPoetryList = (params) => admin.get('/api/admin/poetry/list', { params })
export const adminCreatePoetry = (payload) => admin.post('/api/admin/poetry', payload)
export const adminUpdatePoetry = (id, payload) => admin.put(`/api/admin/poetry/${id}`, payload)
export const adminDeletePoetry = (id) => admin.delete(`/api/admin/poetry/${id}`)

export const adminArtworkList = (params) => admin.get('/api/admin/artwork/list', { params })
export const adminCreateArtwork = (payload) => admin.post('/api/admin/artwork', payload)
export const adminUpdateArtwork = (id, payload) => admin.put(`/api/admin/artwork/${id}`, payload)
export const adminDeleteArtwork = (id) => admin.delete(`/api/admin/artwork/${id}`)
export const adminUploadImage = (id, file) => {
  const fd = new FormData()
  fd.append('file', file)
  return admin.post(`/api/admin/artwork/${id}/image`, fd)
}
export const adminRegenSvg = (id, theme) => admin.post(`/api/admin/artwork/${id}/svg`, null, { params: { theme } })

export const adminCoupletList = (params) => admin.get('/api/admin/couplet/list', { params })
export const adminCreateCouplet = (payload) => admin.post('/api/admin/couplet', payload)
export const adminUpdateCouplet = (id, payload) => admin.put(`/api/admin/couplet/${id}`, payload)
export const adminDeleteCouplet = (id) => admin.delete(`/api/admin/couplet/${id}`)

export const adminCreateRelation = (payload) => admin.post('/api/admin/relation', payload)
export const adminDeleteRelation = (id) => admin.delete(`/api/admin/relation/${id}`)
export const getRelationSuggestions = () => admin.get('/api/admin/relation-suggestions')
