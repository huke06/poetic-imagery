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
export const explorationCardUrl = '/api/concept/exploration-card'
export const resolveConcept = (q) => http.get('/api/concept/resolve', { params: { q } })
export const getConceptUsageSpectrum = (id) => http.get(`/api/concept/${id}/usage-spectrum`)
export const getConceptCooccurrence = (id, params = {}) => http.get(`/api/concept/${id}/cooccurrence`, { params })
export const getUsageSummary = (id, refresh = false) => http.get(`/api/concept/${id}/usage-summary`, { params: { refresh } })
export const getConceptPanorama = () => http.get('/api/concept/panorama')
export const recommendSimilar = (q) => http.get('/api/concept/recommend-similar', { params: { q } })

// ─────────── 诗文 ───────────
export const getPoetryDetail = (id) => http.get(`/api/poetry/${id}`)
export const searchPoetry = (payload) => http.post('/api/poetry/search', payload)
export const getSimilar = (id) => http.get(`/api/poetry/${id}/similar`)
export const getTones = (id) => http.get(`/api/poetry/${id}/tones`)
export const getTranslate = (id) => http.get(`/api/poetry/${id}/translate`)
export const getAppreciation = (id) => http.get(`/api/poetry/${id}/appreciation`)
export const getLabelize = (id) => http.get(`/api/poetry/${id}/labelize`)

// ─────────── 艺术品 ───────────
export const getArtworkList = (params = {}) => http.get('/api/artwork/list', { params })
export const getArtworkDetail = (id) => http.get(`/api/artwork/${id}`)

// ─────────── 诗意图鉴 ───────────
export const getAtlasPaintings = () => http.get('/api/atlas/paintings')
export const adminAtlasList = () => admin.get('/api/atlas/admin/list')
export const adminCreateAtlas = (payload) => admin.post('/api/atlas/admin', payload)
export const adminUpdateAtlas = (id, payload) => admin.put(`/api/atlas/admin/${id}`, payload)
export const adminDeleteAtlas = (id) => admin.delete(`/api/atlas/admin/${id}`)
export const adminUploadAtlasImage = (id, file) => {
  const fd = new FormData()
  fd.append('file', file)
  return admin.post(`/api/atlas/admin/${id}/image`, fd)
}
export const adminSaveAtlasDots = (id, dots) => admin.put(`/api/atlas/admin/${id}/dots`, { dots })

// ─────────── 智能助手 ───────────
export const agentAsk = (question, history = []) => http.post('/api/agent/ask', { question, history })
export const agentCompose = (payload) => http.post('/api/agent/compose', payload)

// ─────────── 管理后台 ───────────
const TOKEN_KEY = 'sxz_admin_token'
export const getToken = () => localStorage.getItem(TOKEN_KEY) || ''
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)

const admin = axios.create({ baseURL: '/', timeout: 300000 })  // 批量导入可能较慢，放宽至 5 分钟
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
export const adminVectorIndexStatus = () => admin.get('/api/admin/vector-index/status')
export const adminVectorIndexRebuild = () => admin.post('/api/admin/vector-index/rebuild')
export const adminVectorIndexRefresh = () => admin.post('/api/admin/vector-index/refresh')
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
export const adminToggleArtworkHomeFeature = (id, featured) => admin.post(`/api/admin/artwork/${id}/home-feature`, null, { params: { featured } })
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
