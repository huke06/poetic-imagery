<template>
  <div class="atlas-root">
    <!-- ═══ Gallery（翻页浏览） ═══ -->
    <section class="max-w-6xl mx-auto px-4 md:px-8 py-12">
      <div class="text-center mb-10">
        <div class="text-[11px] tracking-[0.3em] text-zheshi font-semibold mb-4">GALLERY · 画卷赏析</div>
        <h2 class="font-song text-4xl font-bold tracking-[0.06em] mb-3">诗意图鉴 · 画中诗境</h2>
        <p class="font-song text-sm text-qianhui tracking-[0.05em]">点击画中圆点 · 探寻意象之美</p>
      </div>

      <div v-if="loading" class="py-24 text-center text-qianhui">加载中…</div>
      <div v-else-if="!paintings.length" class="py-24 text-center text-qianhui">
        暂无画卷，请到管理后台「诗意图鉴」上传画卷并标注意象。
      </div>

      <article v-else-if="currentPainting">
        <div class="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-8 lg:gap-12">
          <!-- Left: meta -->
          <div class="flex lg:flex-col items-center lg:items-start gap-4 lg:gap-6">
            <div class="w-16 h-16 flex items-center justify-center bg-zheshi text-xuanzhi font-kai font-bold text-3xl rounded-sm shadow-md shrink-0">
              {{ cnNum(page) }}
            </div>
            <div>
              <h3 class="font-song font-bold text-2xl md:text-3xl tracking-[0.08em]">{{ currentPainting.title }}</h3>
              <p class="font-serif text-sm text-qianhui italic tracking-[0.05em] mt-1">{{ currentPainting.en }}</p>
            </div>
            <div class="hidden lg:flex justify-between items-center w-full mt-auto pt-6 border-t border-shiqing/10 text-[11px] tracking-[0.15em] text-qianhui">
              <span>NO. {{ String(page + 1).padStart(2, '0') }} · 卷{{ cnNum(page) }}</span>
              <strong class="text-zheshi text-lg font-semibold">
                {{ Object.keys(currentPainting.imageries).length }}
                <span class="text-[11px] font-normal tracking-[0.2em] text-qianhui">意象</span>
              </strong>
            </div>
          </div>

          <!-- Right: image frame -->
          <div>
            <div class="image-frame" @dblclick="fullscreenPi = page">
              <img :src="currentPainting.src" :alt="currentPainting.title" :key="page"
                class="w-full h-full object-cover block" />
              <div class="image-overlay"></div>
              <button v-for="dot in currentPainting.dots" :key="dot.label"
                class="dot" :style="{ left: dot.left, top: dot.top }"
                @click.stop="openModal(page, dot.label)">
                <span class="dot__pulse"></span><span class="dot__ring-outer"></span><span class="dot__core"></span><span class="dot__label">{{ dot.label }}</span>
              </button>
            </div>
            <div class="flex flex-wrap gap-2.5 pt-3">
              <span v-for="tag in Object.keys(currentPainting.imageries)" :key="tag" class="tag-pill">{{ tag }}</span>
            </div>
          </div>
        </div>

        <!-- 翻页控制 -->
        <div class="flex items-center justify-center gap-3 mt-10 flex-wrap">
          <button class="btn-outline !py-1.5 !px-4 !text-xs" :disabled="page === 0" @click="goPage(page - 1)">← 上一卷</button>
          <div class="flex items-center gap-2 text-sm text-qianhui">
            <span>第</span>
            <input type="number" min="1" :max="paintings.length" :value="page + 1" @change="onJumpInput"
              class="w-16 px-2 py-1.5 text-center rounded border border-zheshi/40 text-moyan focus:outline-none focus:border-zheshi" />
            <span>/ {{ paintings.length }} 卷</span>
          </div>
          <button class="btn-outline !py-1.5 !px-4 !text-xs" :disabled="paintings.length < 2" @click="randomScroll">随机一卷</button>
          <button class="btn-outline !py-1.5 !px-4 !text-xs" :disabled="page === paintings.length - 1" @click="goPage(page + 1)">下一卷 →</button>
        </div>
        <p class="text-center text-xs text-qianhui mt-3 tracking-widest">
          共 {{ paintings.length }} 卷 · {{ totalImagery }} 个意象 · 可用 ←/→ 键翻页
        </p>
      </article>
    </section>

    <!-- ═══ Imagery Detail Modal ═══ -->
    <Teleport to="body">
      <div v-if="modalOpen" class="fixed inset-0 z-[200] flex items-center justify-center p-6" @click.self="closeModal">
        <div class="absolute inset-0 bg-moyan/70 backdrop-blur-sm" @click="closeModal"></div>
        <div class="modal-card relative bg-xuanzhi w-full max-w-lg px-10 md:px-12 py-12 rounded-lg shadow-2xl max-h-[90vh] overflow-y-auto animate-modal-in">
          <button class="absolute top-5 right-5 w-9 h-9 flex items-center justify-center text-qianhui text-2xl rounded-full hover:bg-shiqing/5 hover:text-zheshi transition-colors"
            @click="closeModal" aria-label="关闭">×</button>
          <div class="inline-flex items-center justify-center w-[72px] h-[72px] bg-zheshi text-xuanzhi font-kai font-bold text-4xl rounded-sm mb-6">
            {{ modalData?.stamp || '象' }}
          </div>
          <div class="font-serif text-xs text-qianhui tracking-[0.15em] uppercase mb-2">出自 · {{ modalData?.paintingTitle }}</div>
          <h2 class="font-song font-bold text-4xl text-moyan tracking-[0.08em] mb-5 leading-tight">{{ modalData?.label }}</h2>
          <div class="w-10 h-px bg-zheshi mb-6"></div>
          <p class="font-song text-xl text-moyan tracking-[0.1em] leading-relaxed mb-5">{{ modalData?.poem }}</p>
          <p class="text-sm text-qianhui leading-7 p-4 bg-shiqing/5 border-l-2 border-zheshi rounded-sm mb-6">{{ modalData?.desc }}</p>
          <div v-if="modalData?.conceptId" class="mb-3">
            <router-link :to="`/concept/${modalData.conceptId}`"
              class="btn-primary !bg-zheshi hover:!bg-zheshi/90 !text-xs" @click="closeModal">
              查看「{{ modalData.label }}」完整意象 →
            </router-link>
          </div>
          <div class="flex justify-between pt-5 border-t border-shiqing/10 font-serif text-[11px] tracking-[0.2em] text-qianhui">
            <span>NO. {{ modalData?.idx || '—' }} · {{ modalData?.paintingTitle }}</span>
            <span>POETRY ATLAS · 2026</span>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ═══ Fullscreen Image Overlay ═══ -->
    <Teleport to="body">
      <div v-if="fullscreenPi !== null" class="fixed inset-0 z-[250] bg-black flex items-center justify-center p-4"
        @dblclick="fullscreenPi = null">
        <button class="fixed top-4 right-4 w-12 h-12 flex items-center justify-center rounded-full bg-white/20 hover:bg-white/35 text-white text-2xl transition-all z-[260]"
          @click="fullscreenPi = null">×</button>
        <span class="fixed bottom-4 left-1/2 -translate-x-1/2 text-white/30 text-xs z-[260] pointer-events-none">双击或 Esc 退出</span>
        <template v-for="(painting, pi) in paintings" :key="'fs-' + pi">
          <div v-if="fullscreenPi === pi" class="image-frame" style="width:95vw;height:85vh;box-shadow:none;background:transparent;">
            <img :src="painting.src" :alt="painting.title" class="w-full h-full object-cover block" />
            <button v-for="dot in painting.dots" :key="dot.label"
              class="dot" :style="{ left: dot.left, top: dot.top }" @click.stop="openModal(pi, dot.label)">
              <span class="dot__pulse"></span><span class="dot__ring-outer"></span><span class="dot__core"></span><span class="dot__label">{{ dot.label }}</span>
            </button>
          </div>
        </template>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { getAtlasPaintings, getConceptList } from '../api'

/* ─────────── 中文卷号 ─────────── */
const cnNums = ['壹', '贰', '叁', '肆', '伍', '陆', '柒', '捌', '玖', '拾']
function cnNum(i) { return cnNums[i] || String(i + 1) }

/* ─────────── 内置兜底画卷（后台无数据时使用） ─────────── */
const FALLBACK_PAINTINGS = [
  { title: '山居春晓图', en: 'Spring Dawn in the Mountain Residence', src: '/shanju-chunxiao.png',
    imageries: {
      '竹': { poem: '竹影婆娑 · 清节凌云', desc: '竹以节立 · 虚心劲直 · 文人风骨之象' },
      '拱桥': { poem: '小桥流水 · 通幽达远', desc: '桥接彼岸 · 行旅往来 · 桃源之径' },
      '樱花': { poem: '樱云如霞 · 春意盎然', desc: '樱以繁盛 · 灿若云霞 · 春日之象征' },
      '溪流': { poem: '溪声潺潺 · 洗尽尘心', desc: '水之流逝 · 澹泊明志 · 智者所乐' },
      '古楼': { poem: '楼阁隐现 · 古意悠然', desc: '楼以观远 · 栖身立心 · 山居之寄' },
      '远山': { poem: '远山如黛 · 层峦叠嶂', desc: '山以镇定 · 雄浑苍莽 · 永恒之姿' },
      '晨雾': { poem: '雾霭缭绕 · 如梦似幻', desc: '雾以藏真 · 虚实相生 · 诗家秘境' },
    },
    dots: [
      { left: '12%', top: '50%', label: '竹' }, { left: '42%', top: '65%', label: '拱桥' },
      { left: '80%', top: '35%', label: '樱花' }, { left: '52%', top: '85%', label: '溪流' },
      { left: '72%', top: '45%', label: '古楼' }, { left: '25%', top: '30%', label: '远山' },
      { left: '40%', top: '52%', label: '晨雾' },
    ] },
  { title: '夕阳山色图', en: 'Sunset Glow over Mountain Pavilion', src: '/xiyang-shanse.png',
    imageries: {
      '落日': { poem: '夕阳西下 · 霞光万丈', desc: '日以归返 · 光华灿烂 · 壮美之绝唱' },
      '远山': { poem: '群山暮色 · 苍茫壮阔', desc: '山以静观 · 暮色沉沉 · 宇宙之恒久' },
      '楼阁': { poem: '楼阁临湖 · 飞檐凌空', desc: '阁以观远 · 高处不胜寒 · 仙境之境' },
      '湖水': { poem: '湖平如镜 · 倒影成画', desc: '水以载舟 · 静照万物 · 心之明镜' },
      '飞鸟': { poem: '归鸟入林 · 倦翼知还', desc: '鸟以归巢 · 林泉之思 · 吾土吾乡' },
      '烟岚': { poem: '烟岚浮动 · 山水氤氲', desc: '岚以蕴气 · 蒸腾为云 · 天地之和' },
    },
    dots: [
      { left: '79%', top: '16%', label: '落日' }, { left: '50%', top: '25%', label: '远山' },
      { left: '42%', top: '50%', label: '楼阁' }, { left: '50%', top: '82%', label: '湖水' },
      { left: '15%', top: '15%', label: '飞鸟' }, { left: '55%', top: '42%', label: '烟岚' },
    ] },
  { title: '长缨破阵图', en: 'The Spear-Maiden Breaking the Ranks', src: '/changying-pozhen.png',
    imageries: {
      '女将': { poem: '巾帼英姿 · 飒爽临阵', desc: '女以执戈 · 不让须眉 · 英武之极致' },
      '长枪': { poem: '长缨在手 · 锐不可当', desc: '枪以破阵 · 一往无前 · 武勇之魂' },
      '战旗': { poem: '旗帜猎猎 · 士气如虹', desc: '旗以聚心 · 风中招展 · 军魂之象' },
      '黑云': { poem: '乌云压城 · 战意凛然', desc: '云以凝重 · 压顶而来 · 苍穹之怒' },
      '战甲': { poem: '铁甲寒光 · 护身御敌', desc: '甲以卫身 · 寒铁凝霜 · 将士之铠' },
      '红袍': { poem: '红袍似火 · 英勇无畏', desc: '袍以染血 · 烈焰为魂 · 英烈之色' },
      '士卒': { poem: '兵卒云集 · 气吞山河', desc: '卒以成阵 · 万众一心 · 国之基石' },
    },
    dots: [
      { left: '26%', top: '45%', label: '女将' }, { left: '43%', top: '52%', label: '长枪' },
      { left: '85%', top: '40%', label: '战旗' }, { left: '45%', top: '8%', label: '黑云' },
      { left: '30%', top: '30%', label: '战甲' }, { left: '25%', top: '60%', label: '红袍' },
      { left: '50%', top: '70%', label: '士卒' },
    ] },
  { title: '钟馗斩鬼图', en: 'Zhong Kui Subduing the Demons', src: '/zhongkui-zhangui.png',
    imageries: {
      '钟馗': { poem: '判官威仪 · 正气凛然', desc: '馗以驱邪 · 终南进士 · 万鬼之魁' },
      '鬼': { poem: '魑魅魍魉 · 无所遁形', desc: '鬼以匿形 · 邪不胜正 · 阴阳之理' },
      '道袍': { poem: '道袍飘逸 · 仙风道骨', desc: '袍以载道 · 飘然出尘 · 仙真之服' },
      '魔影': { poem: '魔影幢幢 · 邪不胜正', desc: '影以匿踪 · 终见天日 · 善恶有报' },
    },
    dots: [
      { left: '40%', top: '40%', label: '钟馗' }, { left: '72%', top: '72%', label: '鬼' },
      { left: '48%', top: '50%', label: '道袍' }, { left: '25%', top: '68%', label: '魔影' },
    ] },
]

/* ─────────── State ─────────── */
const paintings = ref([])
const page = ref(0)
const loading = ref(true)
const fullscreenPi = ref(null)

const currentPainting = computed(() => paintings.value[page.value] || null)
const totalImagery = computed(() => paintings.value.reduce((s, p) => s + Object.keys(p.imageries).length, 0))

function goPage(i) {
  if (i < 0 || i >= paintings.value.length) return
  page.value = i
  fullscreenPi.value = null
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// 页码输入跳转（可扩展到几十卷）
function onJumpInput(e) {
  const v = parseInt(e.target.value, 10)
  if (!Number.isNaN(v)) {
    goPage(Math.min(paintings.value.length, Math.max(1, v)) - 1)
  }
  e.target.value = page.value + 1
}

// 随机跳转一卷（避开当前卷）
function randomScroll() {
  const n = paintings.value.length
  if (n < 2) return
  let i = page.value
  while (i === page.value) i = Math.floor(Math.random() * n)
  goPage(i)
}

/* ─────────── Modal ─────────── */
const modalOpen = ref(false)
const modalData = ref(null)
const conceptMap = ref({})  // name → concept（用于兜底画卷未存 conceptId 时匹配）

function openModal(pi, label) {
  const painting = paintings.value[pi]
  const data = painting.imageries[label]
  if (!data) return
  const idx = Object.keys(painting.imageries).indexOf(label) + 1
  const conceptId = data.conceptId ?? conceptMap.value[label]?.id ?? null
  modalData.value = {
    stamp: label.charAt(0), paintingTitle: painting.title, label,
    poem: data.poem, desc: data.desc, idx: String(idx).padStart(2, '0'), conceptId,
  }
  modalOpen.value = true
  document.body.style.overflow = 'hidden'
}

function closeModal() {
  modalOpen.value = false
  document.body.style.overflow = ''
}

function onKeydown(e) {
  if (e.key === 'Escape') {
    if (fullscreenPi.value !== null) { fullscreenPi.value = null; return }
    if (modalOpen.value) closeModal()
    return
  }
  if (modalOpen.value || fullscreenPi.value !== null) return
  // 焦点在输入框时不触发翻页
  const tag = e.target?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
  if (e.key === 'ArrowLeft') goPage(page.value - 1)
  if (e.key === 'ArrowRight') goPage(page.value + 1)
}

/* ─────────── Lifecycle ─────────── */
onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  // 意象映射（兜底匹配）
  try {
    const data = await getConceptList({ page_size: 500 })
    for (const c of data.items) {
      conceptMap.value[c.name] = c
      for (const a of (c.aliases || [])) if (a && !conceptMap.value[a]) conceptMap.value[a] = c
    }
  } catch { /* silent */ }
  // 加载画卷：优先后台数据，缺省回落内置
  try {
    const d = await getAtlasPaintings()
    paintings.value = d.paintings?.length ? d.paintings : FALLBACK_PAINTINGS
  } catch {
    paintings.value = FALLBACK_PAINTINGS
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.atlas-root { --accent: #9B4423; --accent-deep: #6E2D18; font-family: inherit; color: #2C2C2C; }

.image-frame {
  position: relative; width: 100%; height: 560px; overflow: hidden; background: #F2EAD6;
  border-radius: 2px; box-shadow: 0 1px 3px rgba(26,20,16,0.06), 0 8px 24px rgba(26,20,16,0.08);
}
.image-overlay { position: absolute; inset: 0; background: linear-gradient(180deg, rgba(0,0,0,0) 60%, rgba(26,20,16,0.3) 100%); pointer-events: none; }

.dot { position: absolute; z-index: 5; transform: translate(-50%, -50%); cursor: pointer; -webkit-tap-highlight-color: transparent; background: none; border: none; padding: 0; font: inherit; color: inherit; }
.dot__ring-outer { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 24px; height: 24px; border-radius: 50%; border: 1.5px solid var(--accent); background: rgba(250,245,235,0.15); backdrop-filter: blur(2px); opacity: 0.75; transition: all 0.3s; }
.dot__core { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 8px; height: 8px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 2px rgba(250,245,235,0.6); transition: all 0.3s; }
.dot__pulse { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 36px; height: 36px; border-radius: 50%; border: 1px solid var(--accent); opacity: 0; animation: dot-pulse 2.4s ease-out infinite; }
.dot__label { position: absolute; left: 50%; top: 50%; transform: translate(-50%, calc(-50% - 26px)); background: #1A1410; color: #FAF5EB; font-family: 'Noto Serif SC','Kaiti SC',serif; font-size: 12px; font-weight: 500; padding: 5px 10px; border-radius: 2px; white-space: nowrap; letter-spacing: 0.05em; opacity: 0; pointer-events: none; transition: opacity 0.25s, transform 0.25s; box-shadow: 0 4px 12px rgba(26,20,16,0.25); }
.dot__label::after { content: ''; position: absolute; left: 50%; top: 100%; transform: translateX(-50%); border: 4px solid transparent; border-top-color: #1A1410; }
.dot:hover .dot__ring-outer { width: 32px; height: 32px; opacity: 1; background: rgba(155,68,35,0.12); }
.dot:hover .dot__core { width: 10px; height: 10px; box-shadow: 0 0 0 3px rgba(250,245,235,0.8); }
.dot:hover .dot__label { opacity: 1; transform: translate(-50%, calc(-50% - 32px)); }
.dot:focus-visible { outline: none; }
.dot:focus-visible .dot__ring-outer { outline: 2px solid var(--accent); outline-offset: 4px; }
@keyframes dot-pulse { 0% { opacity: 0.6; transform: translate(-50%, -50%) scale(0.6); } 100% { opacity: 0; transform: translate(-50%, -50%) scale(1.4); } }

.tag-pill { font-family: 'Noto Serif SC','Kaiti SC',serif; font-size: 13px; padding: 5px 12px; border: 1px solid #E0D8C8; border-radius: 99px; color: #2A2520; background: #FAF5EB; transition: all 0.2s; cursor: default; }
.tag-pill:hover { border-color: var(--accent); color: var(--accent); background: rgba(155,68,35,0.04); }

@keyframes modal-in { from { opacity: 0; transform: translateY(20px) scale(0.96); } to { opacity: 1; transform: translateY(0) scale(1); } }
.animate-modal-in { animation: modal-in 0.35s cubic-bezier(0.16, 1, 0.3, 1); }

@media (max-width: 768px) { .image-frame { height: 340px; } .dot__label { display: none; } }
@media (max-width: 1024px) { .image-frame { height: 480px; } }
</style>
