<template>
  <router-link :to="`/concept/${concept.id}`"
    class="concept-card block relative overflow-hidden rounded-[3px] border bg-xuanzhi aspect-[3/4] group"
    :style="{ '--tc': concept.theme_color || '#2B4C7E' }">

    <!-- 视觉主体：标注精选艺术品（无精选则为淡墨山水册页） -->
    <div class="art-area absolute inset-x-0 top-0 h-[44%] overflow-hidden">
      <img v-if="concept.artwork_image" :src="concept.artwork_image" :alt="concept.name"
        class="art-img w-full h-full object-cover" loading="lazy" decoding="async" />
      <div v-else class="w-full h-full bg-[#EFE8D8]"></div>
    </div>

    <!-- 四角古典纹样（鎏金 L 角饰） -->
    <span class="corner corner--tl"></span>
    <span class="corner corner--tr"></span>
    <span class="corner corner--bl"></span>
    <span class="corner corner--br"></span>

    <!-- 宣纸信息层：文字浮于册页之上（细墨线 + 双线版框） -->
    <div class="glass absolute inset-x-3.5 top-[35%] bottom-3.5 rounded-[3px] border border-moyan/15
      flex flex-col items-center justify-center gap-2 text-center px-5 py-5">
      <!-- ① 意象名称（全卡视觉核心，古籍题名感） -->
      <h3 class="font-kai text-4xl tracking-[0.15em] text-moyan leading-none mb-1">{{ concept.name }}</h3>
      <!-- ② 意象分类（辅助信息：细边框小签，随意象主题色） -->
      <CategoryTag :main="concept.category_main" :sub="concept.category_sub" :theme-color="concept.theme_color" />
      <!-- ③ 代表名句（单行完整显示，字号随长度自适应收缩；mt-5 形成批注区断点） -->
      <p ref="verseEl"
        class="verse w-full max-w-full whitespace-nowrap overflow-hidden font-song text-[13px] font-medium text-moyan/80 tracking-[0.08em] leading-relaxed mt-5">
        {{ concept.classic_clause || '——' }}
      </p>
      <!-- ④ 情感标签（低饱和辅助信息，小而淡） -->
      <div class="flex flex-wrap justify-center gap-2.5 mt-4">
        <EmotionTag v-for="tag in concept.emotion_tags.slice(0, 3)" :key="tag" :tag="tag" />
      </div>
    </div>
  </router-link>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import CategoryTag from './CategoryTag.vue'
import EmotionTag from './EmotionTag.vue'

const props = defineProps({ concept: { type: Object, required: true } })

// 代表诗句单行自适应：基准 13px，超出信息层宽度时逐步收缩，下限 10.5px
const verseEl = ref(null)
let verseRO = null

function fitVerse() {
  const el = verseEl.value
  if (!el) return
  el.style.fontSize = ''                 // 复位为基准字号（13px）
  let s = 13
  while (s > 10.5 && el.scrollWidth > el.clientWidth) {
    s -= 0.5
    el.style.fontSize = s + 'px'
  }
}

onMounted(() => {
  nextTick(fitVerse)
  // 卡片跨断点变宽/变窄时重算
  verseRO = new ResizeObserver(() => fitVerse())
  if (verseEl.value) verseRO.observe(verseEl.value)
})
// 换一批/翻页后意象更换，重新测量
watch(() => props.concept.id, () => nextTick(fitVerse))
onBeforeUnmount(() => verseRO && verseRO.disconnect())
</script>

<style scoped>
/* 整卡：宣纸底，主题色淡边（--tc 由 concept.theme_color 注入，与详情页同色系），hover 轻微浮起 */
.concept-card {
  border-color: color-mix(in srgb, var(--tc) 26%, rgba(44, 44, 44, 0.12));
  box-shadow: 0 2px 12px rgba(44, 44, 44, 0.06);
  transition: transform 0.35s ease, box-shadow 0.35s ease, border-color 0.35s ease;
}
.concept-card:hover {
  transform: translateY(-4px);
  border-color: color-mix(in srgb, var(--tc) 58%, transparent);
  box-shadow: 0 14px 32px color-mix(in srgb, var(--tc) 22%, rgba(44, 44, 44, 0.10));
}

/* 意象名称：墨色不变，题名下缀主题色短装饰线（hover 时延展） */
.concept-card h3 {
  padding-bottom: 7px;
  background-image: linear-gradient(
    color-mix(in srgb, var(--tc) 60%, transparent),
    color-mix(in srgb, var(--tc) 60%, transparent));
  background-repeat: no-repeat;
  background-position: bottom center;
  background-size: 1.2em 2px;
  transition: background-size 0.35s ease;
}
.concept-card:hover h3 { background-size: 2em 2px; }

/* 艺术品区：下缘渐变融入宣纸（有无画作统一处理，渐隐带放缓） */
.art-area {
  -webkit-mask-image: linear-gradient(180deg, #000 45%, transparent 97%);
  mask-image: linear-gradient(180deg, #000 45%, transparent 97%);
}
.art-img { transition: transform 0.6s ease, filter 0.6s ease; }
.concept-card:hover .art-img { transform: scale(1.04); filter: saturate(1.1); }

/* 宣纸信息层：主题色薄纱叠宣纸纵向渐变（顶透底实，艺术渗入文字区）+ 细墨线双线版框 */
.glass {
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--tc) 10%, transparent), color-mix(in srgb, var(--tc) 5%, transparent)),
    linear-gradient(180deg, rgba(245, 241, 232, 0.80), rgba(245, 241, 232, 0.93));
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  /* 外细线 + 内双线框，仿古籍版框 */
  box-shadow:
    inset 0 0 0 3px rgba(245, 241, 232, 0.9),
    inset 0 0 0 4px rgba(44, 44, 44, 0.14),
    0 6px 20px rgba(44, 44, 44, 0.08);
  transition: backdrop-filter 0.35s ease, background 0.35s ease;
}
.concept-card:hover .glass {
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--tc) 10%, transparent), color-mix(in srgb, var(--tc) 5%, transparent)),
    linear-gradient(180deg, rgba(245, 241, 232, 0.88), rgba(245, 241, 232, 0.96));
  backdrop-filter: blur(7px);
  -webkit-backdrop-filter: blur(7px);
}

/* 四角鎏金 L 形角饰（hover 时向主题色偏移） */
.corner { position: absolute; width: 14px; height: 14px; pointer-events: none; transition: border-color 0.35s ease; }
.corner--tl { top: 6px; left: 6px; border-top: 2px solid rgba(176, 141, 74, 0.4); border-left: 2px solid rgba(176, 141, 74, 0.4); }
.corner--tr { top: 6px; right: 6px; border-top: 2px solid rgba(176, 141, 74, 0.4); border-right: 2px solid rgba(176, 141, 74, 0.4); }
.corner--bl { bottom: 6px; left: 6px; border-bottom: 2px solid rgba(176, 141, 74, 0.4); border-left: 2px solid rgba(176, 141, 74, 0.4); }
.corner--br { bottom: 6px; right: 6px; border-bottom: 2px solid rgba(176, 141, 74, 0.4); border-right: 2px solid rgba(176, 141, 74, 0.4); }
.concept-card:hover .corner--tl { border-top-color: color-mix(in srgb, var(--tc) 50%, rgba(176, 141, 74, 0.4)); border-left-color: color-mix(in srgb, var(--tc) 50%, rgba(176, 141, 74, 0.4)); }
.concept-card:hover .corner--tr { border-top-color: color-mix(in srgb, var(--tc) 50%, rgba(176, 141, 74, 0.4)); border-right-color: color-mix(in srgb, var(--tc) 50%, rgba(176, 141, 74, 0.4)); }
.concept-card:hover .corner--bl { border-bottom-color: color-mix(in srgb, var(--tc) 50%, rgba(176, 141, 74, 0.4)); border-left-color: color-mix(in srgb, var(--tc) 50%, rgba(176, 141, 74, 0.4)); }
.concept-card:hover .corner--br { border-bottom-color: color-mix(in srgb, var(--tc) 50%, rgba(176, 141, 74, 0.4)); border-right-color: color-mix(in srgb, var(--tc) 50%, rgba(176, 141, 74, 0.4)); }
</style>
