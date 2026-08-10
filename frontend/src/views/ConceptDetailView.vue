<template>
  <div v-if="detail" class="max-w-6xl mx-auto px-4 py-10 space-y-16">
    <!-- 返回上一页 -->
    <button class="back-btn" @click="goBack">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="m12 19-7-7 7-7"/></svg>
      返回
    </button>
    <!-- ═══ 1. 头部概览 ═══ -->
    <section class="relative rounded-xl overflow-hidden">
      <div class="absolute inset-0 -mx-4 -my-6 pointer-events-none"
        :style="{ background: `radial-gradient(ellipse 60% 55% at 18% 40%, ${detail.theme_color}14, transparent 70%)` }"></div>
      <div class="absolute inset-0 -mx-4 -my-6"><ParticleCanvas :mode="particleMode" :density="0.9" /></div>
      <div class="relative grid grid-cols-1 lg:grid-cols-5 gap-8 items-center py-4">
        <div class="lg:col-span-3 rise-in">
          <div class="flex items-end gap-4">
            <h1 class="font-song text-7xl font-bold concept-glow" :style="{ color: detail.theme_color, textShadow: `0 0 34px ${detail.theme_color}55` }">{{ detail.name }}</h1>
            <span class="tag mb-3" :style="{ color: detail.theme_color, borderColor: detail.theme_color + '55' }">{{ detail.category_main }} · {{ detail.category_sub }}</span>
          </div>
          <p class="mt-2 text-xs text-qianhui tracking-wider">别称：{{ detail.aliases.join('、') || '—' }}</p>
          <p class="mt-5 text-moyan/90 leading-8">{{ detail.original_meaning }}</p>
          <p class="mt-2 text-moyan/75 leading-8 text-sm">{{ detail.poetic_meaning }}</p>
          <div class="flex flex-wrap gap-2 mt-5">
            <span v-for="t in detail.emotion_tags" :key="t" class="tag !text-sm !px-3 !py-1"
              :style="{ color: detail.theme_color, borderColor: detail.theme_color + '66', background: detail.theme_color + '0F' }">{{ t }}</span>
          </div>
          <div class="flex gap-6 mt-6 text-sm text-qianhui">
            <span>起源 <b class="text-moyan">{{ detail.origin_dynasty }}</b></span>
            <span>鼎盛 <b class="text-moyan">{{ detail.peak_dynasty }}</b></span>
            <span>收录诗文 <b class="text-moyan">{{ detail.poetry_count }}</b> 首</span>
            <span>艺术作品 <b class="text-moyan">{{ detail.artwork_count }}</b> 件</span>
          </div>
        </div>
        <!-- 情感分布：环形饼图（色彩按一级情感标签，文字标注二级情感标签与占比） -->
        <div class="lg:col-span-2 card p-4 rise-in" style="animation-delay:.1s">
          <h3 class="text-sm text-qianhui text-center tracking-widest">情感分布占比</h3>
          <VChart :option="emotionOption" height="300px" />
        </div>
      </div>
    </section>

    <div class="ink-divider"></div>

    <!-- ═══ 2. 演变脉络 ═══ -->
    <section>
      <SectionTitle :color="detail.theme_color" sub="点击朝代可筛选下方名句">演变脉络</SectionTitle>
      <div class="card p-5 mt-6">
        <VChart :option="dynastyOption" height="300px" @click="onDynastyClick" ref="dynastyChart" />
        <p class="text-xs text-qianhui text-center mt-1">意象在各朝代的出现频次分布（先秦 · 秦汉 · 魏晋南北朝 · 隋唐 · 五代十国 · 宋 · 元 · 明 · 清）</p>
      </div>
      <p class="mt-5 text-sm leading-8 text-moyan/80 indent-8">{{ detail.description }}</p>
    </section>

    <!-- ═══ 3. 经典名句 ═══ -->
    <section>
      <SectionTitle :color="detail.theme_color" :sub="`共 ${poetryTotal} 条关联句读`">经典名句</SectionTitle>
      <!-- 朝代筛选：全部朝代（下拉）+ 唐 + 宋 -->
      <div class="flex flex-wrap items-center gap-2 mt-5 text-sm">
        <div class="relative">
          <select v-model="filterDynasty" @change="page = 1; loadPoetries()"
            class="appearance-none pl-3 pr-8 py-1.5 rounded-full border cursor-pointer transition-all focus:outline-none"
            :style="{ borderColor: detail.theme_color + '66', color: detail.theme_color, background: filterDynasty ? detail.theme_color + '14' : 'transparent' }">
            <option value="">全部朝代</option>
            <option v-for="d in dynastyList" :key="d" :value="d">{{ d }}</option>
          </select>
          <svg class="absolute right-2.5 top-1/2 -translate-y-1/2 w-3 h-3 pointer-events-none" :style="{ color: detail.theme_color }" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path d="m6 9 6 6 6-6"/></svg>
        </div>
        <button v-for="d in ['唐', '宋']" :key="d"
          class="px-4 py-1.5 rounded-full border transition-all"
          :class="filterDynasty === d ? 'text-white' : 'hover:bg-black/5'"
          :style="filterDynasty === d
            ? { background: detail.theme_color, borderColor: detail.theme_color }
            : { borderColor: detail.theme_color + '44', color: detail.theme_color }"
          @click="filterDynasty = filterDynasty === d ? '' : d; page = 1; loadPoetries()">
          {{ d }}
        </button>
        <span class="w-px h-6 bg-black/10 mx-1"></span>
        <!-- 一级情感标签筛选 -->
        <button v-for="e in ['' , ...detail.emotion_mains]" :key="'e' + e"
          class="px-3 py-1.5 rounded-full border transition-all"
          :class="filterEmotionMain === e ? 'text-white' : 'hover:bg-black/5'"
          :style="filterEmotionMain === e
            ? { background: emotionMainColor(e), borderColor: emotionMainColor(e) }
            : { borderColor: emotionMainColor(e) + '55', color: emotionMainColor(e) }"
          @click="filterEmotionMain = e; page = 1; loadPoetries()">
          {{ e || '全部情感' }}
        </button>
      </div>
      <!-- 列表 -->
      <div class="space-y-3 mt-5">
        <div v-for="(item, i) in poetryItems" :key="item.rel_id"
          class="card card-hover p-5 cursor-pointer rise-in" :style="{ animationDelay: i * 0.05 + 's' }"
          @click="$router.push(`/poetry/${item.poetry.id}`)">
          <div class="flex items-start justify-between gap-4">
            <p class="verse-text text-xl leading-relaxed" :style="{ color: detail.theme_color }">{{ item.clause }}</p>
            <span v-if="item.weight >= 2" class="shrink-0 text-xs font-bold tracking-wider" style="color:#c04040">✦ 经典</span>
          </div>
          <div class="flex items-center gap-3 mt-3 text-sm text-qianhui">
            <span>{{ item.poetry.dynasty }} · {{ item.poetry.author }} 《{{ item.poetry.title }}》</span>
            <span class="tag" :style="{ color: detail.theme_color, borderColor: detail.theme_color + '44' }">{{ item.emotion }}</span>
            <span v-if="item.emotion_main" class="tag !text-[10px]" :style="{ color: emotionMainColor(item.emotion_main), borderColor: emotionMainColor(item.emotion_main) + '55' }">{{ item.emotion_main }}</span>
          </div>
        </div>
        <p v-if="!poetryItems.length && !poetryTotal" class="text-sm text-qianhui/70 py-8 text-center">该筛选条件下暂无名句</p>
      </div>
      <Pagination :page="page" :page-size="pageSize" :total="poetryTotal" @change="(p) => { page = p; loadPoetries() }" />
    </section>

    <!-- ═══ 4. 对仗与共现关联 ═══ -->
    <section>
      <SectionTitle :color="detail.theme_color">对仗与共现关联</SectionTitle>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <!-- 对仗词组 -->
        <div class="card p-5">
          <h3 class="text-sm text-qianhui tracking-widest mb-4">高频对仗</h3>
          <div v-if="detail.couplets.length" class="space-y-4">
            <div v-for="c in detail.couplets" :key="c.verse" class="border-l-2 pl-4 py-1" :style="{ borderColor: detail.theme_color }">
              <div class="flex items-center gap-3 font-kai text-lg">
                <span :style="{ color: detail.theme_color }">{{ c.word_a }}</span>
                <span class="text-qianhui text-sm">对</span>
                <span class="text-zheshi">{{ c.word_b }}</span>
              </div>
              <p class="verse-text text-moyan/80 mt-1">{{ c.verse }}</p>
              <p class="text-xs text-qianhui mt-0.5">{{ c.source }}</p>
            </div>
          </div>
          <p v-else class="text-sm text-qianhui/70 py-8 text-center">对仗词组待补充（可在管理后台导入 CSV）</p>
        </div>
        <!-- 共现知识图谱（缩略） -->
        <div class="card p-5 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-sm text-qianhui tracking-widest">共现知识图谱</h3>
              <button v-if="cooc.edges?.length" class="btn-primary !py-1 !px-4 !text-xs transition-all duration-300 hover:scale-105 hover:shadow-lg" @click="showExplorer = true">
                探索 <span class="ml-0.5">⤢</span>
              </button>
            </div>
            <VChart v-if="coocOption" :option="coocOption" height="520px" @click="onCoocClick" />
            <p v-else class="text-sm text-qianhui/70 py-8 text-center">暂无共现分析数据</p>
          </div>
          <div v-if="cooc.edges?.length" class="flex gap-3 text-[10px] text-qianhui/70 border-t border-black/5 pt-2">
            <div class="flex items-center gap-1.5 bg-white/80 rounded px-2 py-1">
              <span class="inline-block w-8 h-0.5 rounded" style="background:#2B4C7E;height:3px"></span>
              <span>强</span>
              <span class="inline-block w-8 rounded" style="background:#2B4C7E;height:1px"></span>
              <span>弱</span>
              <span class="ml-1">NPMI</span>
            </div>
            <div class="flex items-center gap-1.5 bg-white/80 rounded px-2 py-1">
              <span class="inline-block w-5 border-t border-[#2B4C7E]" style="border-style:solid"></span>
              <span>句内</span>
              <span class="inline-block w-5 border-t border-[#2B4C7E]" style="border-style:dashed"></span>
              <span>跨句</span>
              <span class="inline-block w-5 border-t border-[#2B4C7E]" style="border-style:dotted"></span>
              <span>全诗</span>
            </div>
            <div class="flex items-center gap-1.5 bg-white/80 rounded px-2 py-1">
              <span class="inline-block w-6 border-t border-[#b0b0b0] opacity-40" style="border-style:dashed;border-width:1px"></span>
              <span class="text-qianhui/50">桥接</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ 4.5 诗画相映（置于用法谱系之前） ═══ -->
    <section v-if="artworks.length">
      <SectionTitle :color="detail.theme_color" sub="点击作品展开详情卡片">诗画相映</SectionTitle>
      <div class="flex gap-5 mt-6 overflow-x-auto pb-3">
        <div v-for="a in artworks" :key="a.rel_id"
          class="card card-hover shrink-0 w-72 cursor-pointer overflow-hidden"
          @click="openArtwork(a)">
          <img :src="a.artwork.thumb_url || a.artwork.image_url" :alt="a.artwork.name" class="w-full h-44 object-cover" loading="lazy" />
          <div class="p-4">
            <h4 class="font-song font-semibold truncate">《{{ a.artwork.name }}》</h4>
            <p class="text-xs text-qianhui mt-1 whitespace-nowrap">{{ a.artwork.dynasty || a.artwork.dynasty_main }} · {{ a.artwork.artist }}</p>
            <p class="text-xs text-qianhui leading-6 mt-2 line-clamp-2">{{ a.relation_desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ 5. 用法谱系（词云 + AI 总结） ═══ -->
    <section>
      <SectionTitle :color="detail.theme_color" sub="同一意象在不同诗人笔下的用法差异">用法谱系</SectionTitle>

      <!-- 两张云朵词云：情感功能 + 意象用法 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <div class="card p-5">
          <h3 class="text-sm text-qianhui tracking-widest mb-2">情感功能词云</h3>
          <WordCloud :words="emotionCloudWords" :height="240" />
        </div>
        <div class="card p-5">
          <h3 class="text-sm text-qianhui tracking-widest mb-2">意象用法画像</h3>
          <VChart :option="usageRadarOption" height="260px" />
        </div>
      </div>

      <!-- AI 用法谱系总结 -->
      <div class="card mt-6 overflow-hidden">
        <div class="flex items-center justify-between px-5 py-3 bg-shiqing/[0.03] border-b border-black/5">
          <span class="text-sm tracking-widest" :style="{ color: detail.theme_color }">✦ AI 用法谱系总结</span>
          <button class="text-xs text-zheshi hover:underline" :disabled="summarizeLoading" @click="loadUsageSummary(true)">
            {{ summarizeLoading ? '生成中…' : '重新生成' }}
          </button>
        </div>
        <div class="px-5 py-5">
          <p v-if="summarizeLoading" class="text-sm text-qianhui">AI 正在总结<span class="animate-pulse">…</span></p>
          <p v-else class="text-sm leading-8 text-moyan/90 indent-8">{{ usageSummary || '点击下方按钮生成用法谱系总结。' }}</p>
        </div>
      </div>

      <!-- 用法谱系明细表 -->
      <div v-if="spectrumLoading" class="py-8 text-center text-qianhui text-sm mt-4">加载中…</div>
      <div v-else-if="spectrum.length" class="card overflow-hidden mt-4">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-shiqing/10 text-left text-xs text-qianhui tracking-widest">
                <th class="p-3 pl-5 font-normal">情感功能</th>
                <th class="p-3 font-normal">代表诗人</th>
                <th class="p-3 font-normal">代表诗句</th>
                <th class="p-3 pr-5 font-normal">意象在诗中的角色</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in spectrum" :key="s.poet" class="border-b border-black/5 hover:bg-shiqing/[0.03] transition-colors">
                <td class="p-3 pl-5">
                  <div class="flex flex-wrap gap-1">
                    <span v-for="e in s.emotion_function.split('、')" :key="e" class="tag !text-[10px]"
                      :style="{ color: detail.theme_color, borderColor: detail.theme_color + '44', background: detail.theme_color + '08' }">{{ e }}</span>
                  </div>
                </td>
                <td class="p-3"><span class="font-semibold">{{ s.poet }}</span><span class="text-qianhui text-xs ml-1">{{ s.dynasty }}</span></td>
                <td class="p-3 max-w-xs truncate" :title="s.representative_verse">
                  <span class="verse-text font-semibold text-moyan/90">{{ s.representative_verse }}</span>
                  <div class="text-[10px] text-qianhui mt-0.5">《{{ s.poetry_title }}》</div>
                </td>
                <td class="p-3 pr-5 text-xs text-qianhui">{{ s.role_in_poem }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="px-5 py-3 bg-shiqing/[0.02] border-t border-shiqing/5 text-xs text-qianhui">
          共 <b class="text-moyan">{{ spectrum.length }}</b> 位诗人 · {{ spectrumTotalVerses }} 条诗句
        </div>
      </div>
      <p v-else class="text-sm text-qianhui/70 py-8 text-center">暂无用法谱系数据</p>
    </section>

    <!-- ═══ 6. AI 功能大板块 ═══ -->
    <section>
      <SectionTitle :color="detail.theme_color" sub="智能问答 · 格律创诗">AI 灵犀</SectionTitle>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <!-- AI 对话 -->
        <div class="card flex flex-col h-[420px]">
          <div class="px-5 py-3 border-b border-black/5 flex items-center gap-2">
            <span class="seal !w-7 !h-7 !text-[10px]">问</span>
            <span class="text-sm font-song font-semibold">向「{{ detail.name }}」提问</span>
          </div>
          <div ref="aiMsgBox" class="flex-1 overflow-y-auto p-4 space-y-3">
            <div v-if="!aiMsgs.length" class="h-full flex flex-col items-center justify-center gap-3 text-center">
              <p class="text-xs text-qianhui">试试这些问题，或自行提问：</p>
              <div class="flex flex-col gap-2 w-full max-w-xs">
                <button v-for="q in presetQuestions" :key="q" @click="askAI(q)"
                  class="text-left text-sm px-3 py-2 rounded-lg border transition-all hover:shadow-card"
                  :style="{ borderColor: detail.theme_color + '44', color: detail.theme_color }">{{ q }}</button>
              </div>
            </div>
            <div v-for="m in aiMsgs" :key="m.id" class="flex" :class="m.role === 'user' ? 'justify-end' : 'justify-start'">
              <div class="max-w-[85%] px-4 py-2.5 text-sm leading-7 rounded-2xl shadow-card"
                :class="m.role === 'user' ? 'text-white rounded-tr-sm' : 'bg-white/85 border border-black/5 rounded-tl-sm'"
                :style="m.role === 'user' ? { background: detail.theme_color } : {}">{{ m.text }}</div>
            </div>
            <div v-if="aiSending" class="flex"><div class="bg-white/85 px-4 py-2 rounded-2xl text-sm text-qianhui border border-black/5">思考中<span class="animate-pulse">…</span></div></div>
          </div>
          <div class="border-t border-black/5 p-3 flex gap-2">
            <input v-model="aiQuestion" @keyup.enter="askAI()" :placeholder="`自行提问，如：「${detail.name}」在古诗词中有哪些含义？`"
              class="flex-1 px-4 py-2 text-sm rounded-full border bg-white/70 focus:outline-none"
              :style="{ borderColor: detail.theme_color + '44' }" />
            <button class="btn-primary !rounded-full !py-2 !px-5 !text-sm" :disabled="aiSending || !aiQuestion.trim()" @click="askAI()">发送</button>
          </div>
        </div>

        <!-- AI 创诗 -->
        <div class="card flex flex-col h-[420px]">
          <div class="px-5 py-3 border-b border-black/5 flex items-center gap-2">
            <span class="seal !w-7 !h-7 !text-[10px]" style="background:#5B7C5F">创</span>
            <span class="text-sm font-song font-semibold">以「{{ detail.name }}」创诗</span>
          </div>
          <div class="flex-1 overflow-y-auto p-4">
            <div class="flex flex-wrap items-center gap-2 text-sm">
              <label v-for="c in composeConceptOptions" :key="c" class="tag cursor-pointer transition-all"
                :class="composeConcepts.includes(c) ? '!text-white' : 'hover:bg-black/5'"
                :style="composeConcepts.includes(c)
                  ? { background: detail.theme_color, borderColor: detail.theme_color }
                  : { borderColor: detail.theme_color + '44', color: detail.theme_color }">
                <input type="checkbox" class="hidden" :value="c" v-model="composeConcepts" />{{ c }}
              </label>
            </div>
            <div class="flex items-center gap-3 mt-4">
              <select v-model="composeStyle" class="px-3 py-2 text-sm rounded-full border bg-white/70 focus:outline-none" :style="{ borderColor: detail.theme_color + '44' }">
                <option v-for="s in composeStyles" :key="s">{{ s }}</option>
              </select>
              <input v-model="composeTheme" placeholder="情感基调（可选）" class="flex-1 px-4 py-2 text-sm rounded-full border bg-white/70 focus:outline-none" :style="{ borderColor: detail.theme_color + '44' }" />
              <button class="btn-primary !rounded-full !py-2 !text-sm" :disabled="composeSending || !composeConcepts.length" @click="composePoem">创诗</button>
            </div>
            <div v-if="composeSending" class="mt-6 text-sm text-qianhui text-center">正在创作<span class="animate-pulse">…</span></div>
            <div v-else-if="composeResult" class="mt-6 rounded-lg p-5 border" :style="{ borderColor: detail.theme_color + '33', background: detail.theme_color + '08' }">
              <h4 class="font-song font-bold text-center" :style="{ color: detail.theme_color }">《{{ composeResult.title }}》</h4>
              <p class="verse-text text-center text-moyan/90 leading-8 mt-3 whitespace-pre-line">{{ composeResult.poem }}</p>
              <p v-if="composeResult.note" class="text-[11px] text-qianhui text-center mt-3">{{ composeResult.note }}</p>
            </div>
            <div v-else class="mt-8 text-center text-xs text-qianhui/70">选择意象与体裁，AI 将依平仄格律为您创作</div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ 7. 扩展工具 ═══ -->
    <section class="card p-6 flex flex-wrap items-center gap-4">
      <span class="text-sm text-qianhui tracking-widest mr-2">扩展工具</span>
      <a :href="shareCardUrl(detail.id)" target="_blank" class="btn-outline !py-1.5 !px-4 !text-xs">生成分享卡片</a>
      <router-link to="/agent" class="btn-outline !py-1.5 !px-4 !text-xs">前往灵犀助手</router-link>
      <router-link :to="`/artworks`" class="btn-outline !py-1.5 !px-4 !text-xs">前往艺术展厅</router-link>
    </section>

    <!-- 共现图谱全屏 -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="showExplorer" class="fixed inset-0 z-[70] flex flex-col" style="background: rgba(20,26,38,0.95)" @click.self="showExplorer = false">
          <div class="flex items-center justify-between px-6 py-4 text-xuanzhi">
            <span class="seal">共现</span>
            <h3 class="font-song text-xl font-bold">「{{ detail?.name }}」共现图谱</h3>
            <p class="text-xs text-xuanzhi/60">线粗=NPMI · 实线句内/虚线跨句/点线全诗 · 灰弧虚线=桥接</p>
            <button class="w-10 h-10 rounded-full bg-white/10 hover:bg-white/25 text-xl transition-all" @click="showExplorer = false">×</button>
          </div>
          <VChart v-if="coocExplorerOption" :option="coocExplorerOption" width="100%" height="calc(100vh - 80px)" />
        </div>
      </Transition>
    </Teleport>

    <!-- 返回顶部 -->
    <BackToTop />

    <!-- 艺术作品详情卡片（意象卡片内就地展开，不跳转） -->
    <Teleport to="body">
      <div v-if="activeArtwork" class="fixed inset-0 z-50 bg-moyan/80 backdrop-blur-sm flex items-center justify-center p-4"
        @click.self="activeArtwork = null">
        <div class="bg-xuanzhi rounded-lg max-w-5xl w-full max-h-[92vh] shadow-2xl rise-in relative flex flex-col md:flex-row overflow-hidden">
          <button class="absolute top-3 right-3 w-10 h-10 z-20 flex items-center justify-center rounded-full bg-black/25 hover:bg-black/45 text-white text-xl transition-all" @click="activeArtwork = null">×</button>
          <!-- 左侧：作品图片（双击全屏） -->
          <div class="md:w-1/2 relative cursor-zoom-in bg-black/5 flex items-center justify-center shrink-0"
            @dblclick="artFullscreen = true" title="双击全屏欣赏">
            <img :src="activeArtwork.image_url" :alt="activeArtwork.name" class="w-full max-h-[42vh] md:max-h-[85vh] object-contain" />
            <span class="absolute bottom-3 right-3 bg-black/40 text-white/70 text-[10px] px-2 py-0.5 rounded">双击全屏</span>
          </div>
          <!-- 右侧：作品介绍 -->
          <div class="md:w-1/2 p-6 md:max-h-[85vh] overflow-y-auto">
            <h3 class="font-song text-2xl font-bold pr-10">《{{ activeArtwork.name }}》</h3>
            <p class="text-sm text-qianhui mt-1">{{ activeArtwork.dynasty_period }} · {{ activeArtwork.artist }}</p>
            <div class="flex gap-1.5 mt-3 flex-wrap">
              <span v-for="s in activeArtwork.subject_names" :key="s" class="tag border-shiqing/30 text-shiqing">{{ s }}</span>
            </div>
            <div class="grid grid-cols-2 gap-3 mt-4 text-sm">
              <div class="bg-white/50 rounded p-3"><span class="text-qianhui text-xs">材质</span><p class="mt-0.5">{{ activeArtwork.material || '—' }}</p></div>
              <div class="bg-white/50 rounded p-3"><span class="text-qianhui text-xs">尺寸</span><p class="mt-0.5">{{ activeArtwork.size || '—' }}</p></div>
            </div>
            <div class="mt-4">
              <span class="text-xs text-qianhui tracking-widest">作品介绍</span>
              <p class="text-sm leading-7 mt-2 text-moyan/85 whitespace-pre-line">{{ activeArtwork.description || '暂无介绍' }}</p>
            </div>
            <p v-if="activeArtworkRel" class="text-sm leading-7 mt-3 pt-3 border-t border-black/5" :style="{ color: detail.theme_color }">{{ activeArtworkRel }}</p>
            <div class="mt-4 flex gap-3">
              <button class="btn-outline !py-1.5 !text-xs" @click="goToGallery(activeArtwork.id)">在艺术展厅中查看</button>
            </div>
          </div>
        </div>
      </div>
      <!-- 全屏欣赏（含放大镜） -->
      <div v-if="artFullscreen && activeArtwork" class="fixed inset-0 z-[60] bg-black flex items-center justify-center"
        @dblclick="artFullscreen = false">
        <div class="relative w-full h-full overflow-hidden" ref="zoomBox"
          @wheel.prevent="onWheel" @mousedown="startPan" @mousemove="onPan" @mouseup="endPan" @mouseleave="endPan">
          <img :src="activeArtwork.image_url" :alt="activeArtwork.name"
            class="absolute select-none max-w-none" draggable="false"
            :style="{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: 'center', left: '50%', top: '50%', marginLeft: '-25vw', marginTop: '-25vh', width: '50vw' }" />
          <!-- 放大镜 -->
          <div v-if="lens.on" class="absolute pointer-events-none rounded-full border-2 border-xuanzhi/70 shadow-2xl overflow-hidden"
            :style="{ left: lens.x - 90 + 'px', top: lens.y - 90 + 'px', width: '180px', height: '180px' }">
            <img :src="activeArtwork.image_url" class="absolute max-w-none"
              :style="{ width: '50vw', transform: `translate(${-(lens.imgX) * 2.5 + 90}px, ${-(lens.imgY) * 2.5 + 90}px) scale(${zoom * 2.5})`, transformOrigin: 'top left' }" />
          </div>
        </div>
        <button class="fixed top-4 right-4 w-12 h-12 z-[61] flex items-center justify-center rounded-full bg-white/20 hover:bg-white/35 text-white text-2xl transition-all" @click="artFullscreen = false">×</button>
        <div class="fixed bottom-4 left-1/2 -translate-x-1/2 z-[61] flex items-center gap-3 bg-black/50 rounded-full px-4 py-2 text-white/70 text-xs">
          <span>滚轮缩放 · 拖拽平移 · 按住 L 放大镜</span>
          <button class="px-3 py-1 rounded-full bg-white/20 hover:bg-white/35 transition-all" @click.stop="zoom = 1; pan = { x: 0, y: 0 }">重置</button>
        </div>
      </div>
    </Teleport>
  </div>

  <div v-else class="py-32 text-center text-qianhui">加载中…</div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  agentAsk, agentCompose, getConceptArtworks, getConceptDetail, getConceptPoetries,
  getConceptUsageSpectrum, shareCardUrl,
} from '../api'
import { getConceptCooccurrence, getUsageSummary } from '../api'
import { getArtworkDetail } from '../api'
import { useExploredImageries } from '../composables/useExploredImageries'
import BackToTop from '../components/BackToTop.vue'
import Pagination from '../components/Pagination.vue'
import ParticleCanvas from '../components/ParticleCanvas.vue'
import SectionTitle from '../components/SectionTitle.vue'
import VChart from '../components/VChart.vue'
import WordCloud from '../components/WordCloud.vue'

const route = useRoute()
const router = useRouter()
const conceptId = Number(route.params.id)

/** 返回上一页；若无站内历史（直接打开/分享链接进入）则回首页 */
function goBack() {
  if (window.history.state?.back) router.back()
  else router.push('/')
}

const detail = ref(null)
const artworks = ref([])
const cooc = ref({ nodes: [], edges: [] })
const showExplorer = ref(false)
const activeArtwork = ref(null)
const activeArtworkRel = ref('')
const artFullscreen = ref(false)

// 用法谱系
const spectrum = ref([])
const spectrumLoading = ref(true)
const usageSummary = ref('')
const summarizeLoading = ref(false)

const { addExplored } = useExploredImageries()

// 名句筛选
const page = ref(1)
const pageSize = 6
const poetryTotal = ref(0)
const poetryItems = ref([])
const filterDynasty = ref('')
const filterEmotionMain = ref('')

// 一级情感标签配色
const EMOTION_MAIN_COLORS = {
  '情感心绪类': '#6E4A7E', '交往离别类': '#9B4423', '人生感悟类': '#8A6D3B',
  '自然山水类': '#5B7C5F', '历史文化类': '#2B4C7E', '志向抱负类': '#9B2C1F',
  '超脱境界类': '#3A7A7C',
}
const emotionMainColor = (m) => EMOTION_MAIN_COLORS[m] || '#8A6D3B'

const particleMode = computed(() => {
  const name = detail.value?.name || ''
  const cat = detail.value?.category_main || ''
  if (/月|霜|雪|星|夜/.test(name)) return 'moon'
  if (/夕阳|日|霞|暮/.test(name)) return 'sunset'
  if (/柳|絮|杨/.test(name)) return 'willow'
  if (cat === '自然类') return 'moon'
  if (cat === '人类自身类') return 'petal'
  return 'ink'
})

const dynastyList = computed(() => (detail.value?.poetry_dynasties || []))

// ═══ 情感分布环形饼图 ═══
const emotionOption = computed(() => {
  const stats = detail.value?.emotion_tag_stats || []
  // 无聚合统计时回退旧数据
  if (!stats.length) {
    const legacy = detail.value?.emotion_stats || []
    return {
      tooltip: { trigger: 'item', formatter: '{b}：{c} 句（{d}%）' },
      legend: { bottom: 0, textStyle: { color: '#6B6B6B', fontSize: 11 }, itemWidth: 12 },
      series: [{ type: 'pie', radius: ['46%', '70%'], center: ['50%', '44%'],
        itemStyle: { borderColor: '#F5F1E8', borderWidth: 2, borderRadius: 4 },
        label: { show: true, formatter: '{b}\n{d}%', fontSize: 10 },
        data: legacy.map((s, i) => ({ name: s.emotion, value: s.count,
          itemStyle: { color: Object.values(EMOTION_MAIN_COLORS)[i % 7] } })) }] }
  }
  const cats = [...new Set(stats.map((s) => s.category).filter(Boolean))]
  return {
    tooltip: {
      trigger: 'item',
      formatter: (p) => `${p.data.name}（${p.data.category}）<br/>占比 ${p.data.ratio}%`,
    },
    legend: { bottom: 0, data: cats, textStyle: { color: '#6B6B6B', fontSize: 11 }, itemWidth: 12, itemGap: 8 },
    series: [{
      type: 'pie', radius: ['44%', '68%'], center: ['50%', '42%'],
      itemStyle: { borderColor: '#F5F1E8', borderWidth: 2, borderRadius: 4 },
      label: { show: true, formatter: (p) => `${p.data.name}\n${p.data.ratio}%`, fontSize: 10, color: '#2C2C2C', lineHeight: 13 },
      labelLine: { length: 8, length2: 6 },
      data: stats.map((s) => ({
        name: s.emotion, value: s.ratio, ratio: s.ratio, count: s.count, category: s.category,
        itemStyle: { color: emotionMainColor(s.category) },
      })),
    }],
  }
})

// ═══ 演变脉络折线图（朝代出现频次） ═══
const dynastyOption = computed(() => {
  const stats = detail.value?.dynasty_occurrence || []
  if (!stats.length) return {}
  const color = detail.value?.theme_color || '#2B4C7E'
  return {
    grid: { left: 56, right: 20, top: 30, bottom: 40 },
    tooltip: { trigger: 'axis', formatter: (p) => `${p[0].name}<br/>出现 ${p[0].value.toLocaleString()} 次` },
    xAxis: {
      type: 'category', data: stats.map((s) => s.dynasty),
      axisLine: { lineStyle: { color: '#00000022' } },
      axisLabel: { color: '#6B6B6B', fontFamily: 'Kaiti SC, KaiTi, serif', fontSize: 13 },
    },
    yAxis: {
      type: 'log',
      min: 1,
      splitLine: { lineStyle: { color: '#0000000D' } },
      axisLabel: { color: '#9A9A9A', formatter: (v) => v >= 10000 ? `${(v/10000).toFixed(0)}万` : v >= 1000 ? `${(v/1000).toFixed(0)}千` : v },
    },
    series: [{
      type: 'line', smooth: true, symbol: 'circle', symbolSize: 9,
      data: stats.map((s) => Math.max(s.count, 1)),
      lineStyle: { width: 2.5, color },
      itemStyle: { color, borderColor: '#F5F1E8', borderWidth: 2 },
      areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [{ offset: 0, color: color + '55' }, { offset: 1, color: color + '05' }] } },
    }],
  }
})

// ═══ 共现图谱全屏（与缩略同数据，放大力导向） ═══
const coocExplorerOption = computed(() => {
  if (!cooc.value.edges?.length) return null
  const color = detail.value?.theme_color || '#2B4C7E'
  const dashOf = (t) => (t === '句内' ? 'solid' : t === '跨句' ? 'dashed' : 'dotted')
  return {
    tooltip: {
      confine: true,
      backgroundColor: '#F5F1E8',
      borderColor: '#c8c0b0',
      borderWidth: 1,
      padding: 0,
      extraCssText: 'max-width:400px;box-shadow:0 8px 30px rgba(0,0,0,0.15);white-space:normal;word-break:break-word',
      textStyle: { color: '#4a4a4a', fontSize: 12, fontFamily: 'Kaiti SC, KaiTi, serif' },
      formatter: (p) => {
        if (p.dataType === 'edge') {
          return '<div style="padding:10px 14px"><div style="font-size:12px;font-weight:700;color:#2C2C2C">' + p.data.name + '</div><div style="font-size:10px;color:#999;margin-top:2px">NPMI ' + p.data.npmi.toFixed(2) + ' · ' + (p.data.ctype || '共现') + '</div></div>'
        }
        // 桥接词：有来自中心的包含边则只显示标签
        const isBridge = cooc.value.edges.some(e => e.target === p.data.id && e.relation_type === '包含')
        if (isBridge) return '<div style="padding:10px 14px"><b style="font-size:14px;font-family:Kaiti SC,KaiTi,serif">' + p.data.name + '</b><div style="font-size:10px;color:#aaa;margin-top:2px">桥接词</div></div>'
        const nodeEdges = cooc.value.edges.filter(e => (e.target === p.data.id || e.source === p.data.id) && e.relation_type !== '包含')
        if (!nodeEdges.length) return '<div style="padding:10px 14px"><b>' + p.data.name + '</b></div>'
        const edge = nodeEdges[0]
        const verse = (edge && edge.verse) || ''
        const desc = (edge && edge.description) || ''
        const poet = (edge && edge.poet) || ''
        const dynasty = (edge && edge.dynasty) || ''
        const poemTitle = (edge && edge.poem_title) || ''
        if (!verse && !desc) return '<div style="padding:12px 16px"><b style="font-size:15px;font-family:Kaiti SC,KaiTi,serif">' + p.data.name + '</b></div>'
        var h = '<div style="padding:14px 16px;min-width:240px;max-width:400px">'
        h += '<div style="font-size:15px;font-family:Kaiti SC,KaiTi,serif;font-weight:700;color:#2C2C2C;margin-bottom:4px">' + p.data.name + '</div>'
        if (poet || dynasty) {
          h += '<div style="font-size:10px;color:#999;margin-bottom:6px">'
          if (dynasty) h += dynasty
          if (dynasty && poet) h += ' · '
          if (poet) h += poet
          if (poemTitle) h += ' 《' + poemTitle + '》'
          h += '</div>'
        }
        if (verse) {
          h += '<div style="background:rgba(0,0,0,0.015);border-radius:4px;padding:10px 12px;margin-bottom:6px;border-left:3px solid ' + color + '">'
          h += '<div style="font-size:13px;line-height:2.2;color:#3a3a3a;font-family:Kaiti SC,KaiTi,serif">'
          // 自动断行：先处理换行符（真实换行 + 字面量 \n），再按标点/诗行切分
          var formattedVerse = verse.replace(/\\n/g, '<br>').replace(/\n/g, '<br>')
          if (formattedVerse.indexOf('<br>') === -1 && !/[。！？；]/.test(verse)) {
            var step = verse.length % 7 === 0 ? 7 : (verse.length % 5 === 0 ? 5 : 0)
            if (step) {
              var parts = verse.match(new RegExp('.{1,' + step + '}', 'g'))
              formattedVerse = parts ? parts.join('<br>') : formattedVerse
            }
          }
          h += formattedVerse
          h += '</div></div>'
        }
        if (desc) {
          h += '<div>'
          h += '<div style="font-size:9px;color:#999;margin-bottom:1px;letter-spacing:2px">共现解读</div>'
          h += '<div style="font-size:11px;color:#777;line-height:1.6;word-break:break-all">' + desc + '</div>'
          h += '</div>'
        }
        h += '</div>'
        return h
      },
    },
    series: [{
      type: 'graph', layout: 'force', roam: true, draggable: true,
      force: { repulsion: 400, edgeLength: 150, gravity: 0.18 },
      label: { show: true, fontSize: 16, fontFamily: 'Kaiti SC, KaiTi, serif', color: '#F5F1E8' },
      data: cooc.value.nodes.map((n) => ({
        id: n.id, name: n.name, concept_id: n.concept_id,
        is_bridge: n.is_bridge || false,
        symbolSize: n.center ? 80 : 52,
        itemStyle: { color: n.center ? color : (n.theme_color || '#8A6D3B'), borderColor: '#F5F1E8', borderWidth: 2, shadowBlur: 8, shadowColor: '#0003' },
      })),
      links: cooc.value.edges.map((e) => {
        const isBridge = e.relation_type === '包含'
        return {
          source: e.source, target: e.target, name: e.name, npmi: e.npmi, ctype: e.type, concept_id: e.concept_id,
          lineStyle: isBridge
            ? { color: '#b0b0b0', width: 0.8, type: 'dashed', opacity: 0.4, curveness: 0.25 }
            : { color, width: 1 + ((e.npmi + 1) / 2) * 5, type: dashOf(e.type), opacity: e.diaphaneity, curveness: 0.08 },
        }
      }),
    }],
  }
})

// ═══ 共现图谱（缩略，ECharts 力导向） ═══
const coocOption = computed(() => {
  if (!cooc.value.edges?.length) return null
  const color = detail.value?.theme_color || '#2B4C7E'
  const dashOf = (t) => (t === '句内' ? 'solid' : t === '跨句' ? 'dashed' : 'dotted')
  return {
    tooltip: {
      formatter: (p) => p.dataType === 'edge'
        ? `${p.data.name} · NPMI ${p.data.npmi.toFixed(2)} · ${p.data.ctype}` : p.data.name,
    },
    legend: { show: false },
    series: [{
      type: 'graph', layout: 'force', roam: false, draggable: true,
      force: {
        repulsion: Math.max(260, 580 - cooc.value.nodes.length * 6),
        edgeLength: [80, 220],
        gravity: 0.32,
        layoutAnimation: true,
      },
      label: { show: true, fontSize: 13, fontFamily: 'Kaiti SC, KaiTi, serif', color: '#F5F1E8' },
      data: cooc.value.nodes.map((n) => ({
        id: n.id, name: n.name, concept_id: n.concept_id,
        is_bridge: n.is_bridge || false,
        symbolSize: n.center ? 64 : Math.max(28, 50 - cooc.value.nodes.length),
        itemStyle: { color: n.center ? color : (n.theme_color || '#8A6D3B'), borderColor: '#F5F1E8', borderWidth: 2, shadowBlur: 6, shadowColor: '#0003' },
      })),
      links: cooc.value.edges.map((e) => {
        const isBridge = e.relation_type === '包含'
        return {
          source: e.source, target: e.target, name: e.name, npmi: e.npmi, ctype: e.type, concept_id: e.concept_id,
          lineStyle: isBridge
            ? { color: '#b0b0b0', width: 0.8, type: 'dashed', opacity: 0.4, curveness: 0.25 }
            : { color, width: 1 + ((e.npmi + 1) / 2) * 5, type: dashOf(e.type), opacity: e.diaphaneity, curveness: 0.08 },
        }
      }),
    }],
  }
})

function onCoocClick(params) {
  if (params.dataType === 'node' && params.data.concept_id && !params.data.is_bridge && params.data.concept_id !== conceptId) {
    router.push(`/concept/${params.data.concept_id}`)
  }
}

// ═══ 词云数据 ═══
const emotionCloudWords = computed(() => {
  const stats = detail.value?.emotion_tag_stats || []
  if (stats.length) return stats.map((s) => ({ text: s.emotion, value: s.count, color: emotionMainColor(s.category) }))
  return (detail.value?.emotion_stats || []).map((s) => ({ text: s.emotion, value: s.count }))
})
// ═══ 意象用法雷达图 ═══
const ROLE_ORDER = ["起兴", "比喻", "拟人", "用典", "对偶", "烘托", "象征"]
const usageRadarOption = computed(() => {
  const acc = {}
  for (const s of spectrum.value) {
    const scores = (s.usage_scores && typeof s.usage_scores === 'object') ? s.usage_scores : null
    if (scores) {
      ROLE_ORDER.forEach(r => { acc[r] = (acc[r] || 0) + (scores[r] || 0) })
    } else if (s.role_in_poem) {
      acc[s.role_in_poem] = (acc[s.role_in_poem] || 0) + 2
    }
  }
  // 平方根压缩数值差距
  const values = ROLE_ORDER.map(r => Math.round(Math.sqrt((acc[r] || 0) + 1) * 10) / 10)
  const sumVal = values.reduce((a, b) => a + b, 0)
  if (sumVal === 0) return {}  // 无数据时不渲染
  const maxVal = Math.max(...values, 1)
  const color = detail.value?.theme_color || '#2B4C7E'
  return {
    tooltip: { show: false },
    legend: { show: false },
    radar: {
      center: ['50%', '52%'],
      radius: '65%',
      indicator: ROLE_ORDER.map(r => ({ name: r, max: maxVal })),
      axisName: { color: '#6B6B6B', fontSize: 12, fontFamily: 'Kaiti SC, KaiTi, serif' },
      splitNumber: 4,
      axisLine: { lineStyle: { color: '#ddd' } },
      splitLine: { lineStyle: { color: '#e8e3d8' } },
      splitArea: { areaStyle: { color: ['#F5F1E8', '#F5F1E8'] } },
    },
    series: [{
      type: 'radar',
      symbol: 'circle', symbolSize: 6,
      data: [{
        value: values,
        name: detail.value?.name || '',
        areaStyle: { color: color + '1A' },
        lineStyle: { color, width: 2.5 },
        itemStyle: { color, borderColor: '#F5F1E8', borderWidth: 2 },
      }],
    }],
  }
})

// ═══ 名句加载 ═══
async function loadPoetries() {
  const data = await getConceptPoetries(conceptId, {
    dynasty: filterDynasty.value, emotion_main: filterEmotionMain.value,
    page: page.value, page_size: pageSize,
  })
  poetryTotal.value = data.total
  poetryItems.value = data.items
}

// 九大朝代段 → 库内诗文朝代（用于点击演变脉络联动筛选名句）
const GROUP_TO_DYNASTY = {
  '先秦': '先秦', '秦汉': '汉', '魏晋南北朝': '魏晋', '隋唐': '唐',
  '五代十国': '五代', '宋': '宋', '元': '元', '明': '明', '清': '清',
}
function onDynastyClick(params) {
  const target = GROUP_TO_DYNASTY[params.name] || ''
  filterDynasty.value = filterDynasty.value === target ? '' : target
  page.value = 1
  loadPoetries()
}

const spectrumTotalVerses = computed(() => spectrum.value.reduce((s, item) => s + item.verse_count, 0))

async function loadSpectrum() {
  try { spectrum.value = (await getConceptUsageSpectrum(conceptId)).spectrum }
  catch { spectrum.value = [] }
  finally { spectrumLoading.value = false }
}

async function loadUsageSummary(refresh = false) {
  summarizeLoading.value = true
  try {
    const d = await getUsageSummary(conceptId, refresh)
    usageSummary.value = d.text
  } catch {
    usageSummary.value = `「${detail.value.name}」意象在历代诗人笔下各具风姿，承载着丰富的文化内涵与情感意蕴。`
  } finally { summarizeLoading.value = false }
}

// ═══ 艺术品就地详情 ═══
async function openArtwork(a) {
  activeArtworkRel.value = a.relation_desc
  try { activeArtwork.value = await getArtworkDetail(a.artwork.id) }
  catch { activeArtwork.value = a.artwork }
}
function goToGallery(id) { activeArtwork.value = null; router.push(`/artworks?id=${id}`) }

// ═══ 全屏缩放/放大镜 ═══
const zoom = ref(1)
const pan = ref({ x: 0, y: 0 })
const lens = ref({ on: false, x: 0, y: 0, imgX: 0, imgY: 0 })
const zoomBox = ref(null)
let panning = false, panStart = { x: 0, y: 0 }, panOrigin = { x: 0, y: 0 }
let lensKey = null

function onWheel(e) { zoom.value = Math.min(6, Math.max(0.5, zoom.value + (e.deltaY < 0 ? 0.25 : -0.25))) }
function startPan(e) { panning = true; panStart = { x: e.clientX, y: e.clientY }; panOrigin = { ...pan.value } }
function onPan(e) {
  if (lens.value.on) { updateLens(e); return }
  if (!panning) return
  pan.value = { x: panOrigin.x + (e.clientX - panStart.x), y: panOrigin.y + (e.clientY - panStart.y) }
}
function endPan() { panning = false }
function updateLens(e) {
  const rect = zoomBox.value.getBoundingClientRect()
  lens.value.x = e.clientX - rect.left
  lens.value.y = e.clientY - rect.top
  lens.value.imgX = lens.value.x - rect.width / 2 - pan.value.x
  lens.value.imgY = lens.value.y - rect.height / 2 - pan.value.y
}
function onKey(e) {
  if (!artFullscreen.value) return
  if (e.key === 'Escape') artFullscreen.value = false
  if (e.key === 'l' || e.key === 'L') lens.value.on = e.type === 'keydown'
}
function onKeyToggle(e) { if (artFullscreen.value && (e.key === 'l' || e.key === 'L')) lens.value.on = true }
function onKeyRelease(e) { if (e.key === 'l' || e.key === 'L') lens.value.on = false }

// ═══ AI 对话 ═══
const aiMsgs = ref([])
const aiQuestion = ref('')
const aiSending = ref(false)
const aiMsgBox = ref(null)
const presetQuestions = computed(() => [
  `「${detail.value?.name}」在古诗词中有哪些核心含义？`,
  `哪些诗人最爱用「${detail.value?.name}」意象？`,
  `「${detail.value?.name}」的情感色彩经历了怎样的演变？`,
])
async function askAI(q) {
  const question = q || aiQuestion.value.trim()
  if (!question || aiSending.value) return
  aiMsgs.value.push({ id: Date.now(), role: 'user', text: question })
  aiQuestion.value = ''
  aiSending.value = true
  await nextTick(); scrollAi()
  try {
    const resp = await agentAsk(question)
    aiMsgs.value.push({ id: Date.now() + 1, role: 'ai', text: resp.answer || '暂无回答' })
  } catch { aiMsgs.value.push({ id: Date.now() + 1, role: 'ai', text: '服务暂不可用，请稍后再试。' }) }
  finally { aiSending.value = false; await nextTick(); scrollAi() }
}
function scrollAi() { if (aiMsgBox.value) aiMsgBox.value.scrollTop = aiMsgBox.value.scrollHeight }

// ═══ AI 创诗 ═══
const composeConcepts = ref([])
const composeStyles = ['五言绝句', '七言绝句', '五言律诗', '七言律诗']
const composeStyle = ref('七言绝句')
const composeTheme = ref('')
const composeSending = ref(false)
const composeResult = ref(null)
const composeConceptOptions = computed(() => {
  const base = [detail.value?.name, ...(detail.value?.aliases || [])].filter(Boolean)
  return [...new Set(base)].slice(0, 5)
})
async function composePoem() {
  if (!composeConcepts.value.length || composeSending.value) return
  composeSending.value = true
  composeResult.value = null
  try {
    composeResult.value = await agentCompose({ concepts: composeConcepts.value, style: composeStyle.value, theme: composeTheme.value })
  } catch { composeResult.value = { title: '创作失败', poem: '请稍后再试。', note: '' } }
  finally { composeSending.value = false }
}

onMounted(async () => {
  try {
    if (!Number.isFinite(conceptId)) throw new Error('invalid id')
    detail.value = await getConceptDetail(conceptId)
    addExplored(detail.value)
    composeConcepts.value = [detail.value.name]
    const [arts, coocData] = await Promise.all([getConceptArtworks(conceptId), getConceptCooccurrence(conceptId)])
    artworks.value = arts
    cooc.value = coocData
    await Promise.all([loadPoetries(), loadSpectrum(), loadUsageSummary(false)])
    document.addEventListener('keydown', onKeyToggle)
    document.addEventListener('keyup', onKeyRelease)
  } catch {
    router.replace({ name: 'not-found' })
  }
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeyToggle)
  document.removeEventListener('keyup', onKeyRelease)
})
</script>
