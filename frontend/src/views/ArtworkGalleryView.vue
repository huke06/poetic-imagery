<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <SectionTitle sub="古代艺术品图文库 · 诗画互证">古画展厅</SectionTitle>

    <!-- 筛选栏 -->
    <div class="flex flex-wrap items-center gap-3 mt-6 text-sm">
      <select v-model="dynasty" @change="page = 1; load()"
        class="px-4 py-2 rounded-full border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing">
        <option value="">全部朝代</option>
        <option v-for="d in filters.dynasties" :key="d" :value="d">{{ d }}</option>
      </select>
      <select v-model="subject" @change="page = 1; load()"
        class="px-4 py-2 rounded-full border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing">
        <option value="">全部主题</option>
        <option v-for="s in filters.subjects" :key="s" :value="s">{{ s }}</option>
      </select>
      <div class="flex-1"></div>
      <input v-model="keyword" @keyup.enter="page = 1; load()" placeholder="检索画名 / 作者…"
        class="w-52 px-4 py-2 rounded-full border border-shiqing/25 bg-white/70 focus:outline-none focus:border-shiqing" />
    </div>

    <!-- 瀑布网格 -->
    <div v-if="loading" class="py-20 text-center text-qianhui">加载中…</div>
    <div v-else-if="!items.length" class="py-20 text-center text-qianhui">未找到匹配的古画</div>
    <div v-else class="columns-1 sm:columns-2 lg:columns-3 gap-6 mt-8 [&>div]:mb-6">
      <div v-for="(a, i) in items" :key="a.id"
        class="card card-hover overflow-hidden cursor-pointer break-inside-avoid rise-in"
        :style="{ animationDelay: (i % 6) * 0.06 + 's' }"
        @click="openDetail(a.id)">
        <img :src="a.thumb_url || a.image_url" :alt="a.name" class="w-full object-cover" loading="lazy" />
        <div class="p-4">
          <h3 class="font-song font-semibold">《{{ a.name }}》</h3>
          <p class="text-xs text-qianhui mt-1">{{ a.dynasty }} · {{ a.artist }}</p>
        </div>
      </div>
    </div>
    <Pagination :page="page" :page-size="pageSize" :total="total" @change="(p) => { page = p; load() }" />

    <!-- 详情弹窗 -->
    <Teleport to="body">
      <div v-if="detail" class="fixed inset-0 z-50 bg-black/55 backdrop-blur-sm flex items-center justify-center p-4"
        @click.self="detail = null">
        <div class="bg-xuanzhi rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto shadow-2xl rise-in">
          <img :src="detail.image_url" :alt="detail.name" class="w-full max-h-[52vh] object-cover bg-black/5" />
          <div class="p-6">
            <div class="flex items-start justify-between">
              <div>
                <h3 class="font-song text-2xl font-bold">《{{ detail.name }}》</h3>
                <p class="text-sm text-qianhui mt-1">{{ detail.dynasty }} · {{ detail.artist }}</p>
              </div>
              <div class="flex gap-1.5">
                <span v-for="s in detail.subject_names" :key="s" class="tag border-shiqing/30 text-shiqing">{{ s }}</span>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3 mt-4 text-sm">
              <div class="bg-white/50 rounded p-3"><span class="text-qianhui text-xs">材质</span><p class="mt-0.5">{{ detail.material || '—' }}</p></div>
              <div class="bg-white/50 rounded p-3"><span class="text-qianhui text-xs">尺寸</span><p class="mt-0.5">{{ detail.size || '—' }}</p></div>
            </div>
            <p class="text-sm leading-7 mt-4 text-moyan/85">{{ detail.description }}</p>
            <div v-if="detail.concepts.length" class="mt-5 border-t border-black/5 pt-4">
              <span class="text-xs text-qianhui tracking-widest">相关意象</span>
              <div class="flex flex-wrap gap-2 mt-2">
                <button v-for="c in detail.concepts" :key="c.id"
                  class="tag !text-sm !px-3 !py-1 hover:scale-105 transition-transform cursor-pointer"
                  :style="{ color: c.theme_color, borderColor: c.theme_color + '66', background: c.theme_color + '0F' }"
                  @click="$router.push(`/concept/${c.id}`)">
                  {{ c.name }}
                </button>
              </div>
              <p v-for="c in detail.concepts" :key="'d' + c.id" class="text-xs text-qianhui leading-6 mt-2">· {{ c.relation_desc }}</p>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getArtworkDetail, getArtworkList } from '../api'
import Pagination from '../components/Pagination.vue'
import SectionTitle from '../components/SectionTitle.vue'

const route = useRoute()
const items = ref([])
const filters = ref({ dynasties: [], subjects: [] })
const dynasty = ref('')
const subject = ref('')
const keyword = ref('')
const page = ref(1)
const pageSize = 12
const total = ref(0)
const loading = ref(true)
const detail = ref(null)

async function load() {
  loading.value = true
  try {
    const data = await getArtworkList({ dynasty: dynasty.value, subject: subject.value, keyword: keyword.value, page: page.value, page_size: pageSize })
    items.value = data.items
    total.value = data.total
    filters.value = data.filters
  } finally {
    loading.value = false
  }
}

async function openDetail(id) {
  detail.value = await getArtworkDetail(id)
}

onMounted(async () => {
  await load()
  if (route.query.id) openDetail(Number(route.query.id))
})
</script>
