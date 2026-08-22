<template>
  <div v-if="detail && ready" class="max-w-6xl mx-auto px-4 pt-4 pb-10 space-y-12"
    :style="{ '--tc': detail.theme_color || '#2B4C7E' }">
    <!-- 返回上一页 -->
    <button class="back-btn" @click="goBack">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="m12 19-7-7 7-7"/></svg>
      返回
    </button>
    <!-- ═══ 1. 头部概览 ═══ -->
    <section class="relative rounded-xl overflow-hidden">
      <div class="relative grid grid-cols-1 lg:grid-cols-5 gap-8 items-center py-4">
        <div class="lg:col-span-3 rise-in">
          <div class="flex flex-wrap items-center gap-5">
            <h1 class="font-kai text-7xl" :style="{ color: detail.theme_color }">{{ detail.name }}</h1>
            <CategoryTag lg :main="detail.category_main" :sub="detail.category_sub" :theme-color="detail.theme_color" />
          </div>
          <p class="mt-3 text-xs text-qianhui tracking-wider">别称：{{ detail.aliases.join('、') || '—' }}</p>
          <p class="meaning-label mt-5">〔本义〕</p>
          <p class="mt-1.5 text-moyan/90 leading-8 font-fang">{{ detail.original_meaning }}</p>
          <p class="meaning-label mt-6">〔文化内涵〕</p>
          <p class="mt-1.5 text-moyan/75 leading-8 text-sm font-song">{{ detail.poetic_meaning }}</p>
          <div class="flex flex-wrap gap-2.5 mt-6">
            <EmotionTag v-for="t in detail.emotion_tags" :key="t" :tag="t" lg />
          </div>
          <div class="flex gap-6 mt-6 text-sm text-qianhui">
            <span>起源 <b class="text-moyan">{{ detail.origin_dynasty }}</b></span>
            <span>鼎盛 <b class="text-moyan">{{ detail.peak_dynasty }}</b></span>
            <span>收录诗文 <b class="text-moyan">{{ detail.poetry_count }}</b> 首</span>
            <span v-if="detail.artwork_count">艺术作品 <b class="text-moyan">{{ detail.artwork_count }}</b> 件</span>
          </div>
        </div>
        <!-- 情感分布：环形饼图（色彩按一级情感标签，文字标注二级情感标签与占比） -->
        <div class="lg:col-span-2 card p-4 rise-in" style="animation-delay:.1s">
          <h3 class="font-song text-lg text-moyan/85 text-center tracking-[0.3em] mb-4">情感分布占比</h3>
          <VChart :option="emotionOption" height="300px" />
        </div>
      </div>
    </section>

    <!-- ═══ 2. 演变脉络 ═══ -->
    <section class="dynasty-section">
      <SectionTitle :color="detail.theme_color" sub="点击朝代可筛选下方名句">演变脉络</SectionTitle>
      <div class="card dynasty-card mt-6">
        <VChart :option="dynastyOption" height="300px" @click="onDynastyClick" ref="dynastyChart" />
        <p class="text-xs font-song text-qianhui text-center mt-1">意象在各朝代的出现频次分布（先秦 · 秦汉 · 魏晋南北朝 · 隋唐 · 五代十国 · 宋 · 元 · 明 · 清）</p>
      </div>
      <p class="mt-5 text-[15px] leading-[2.1] text-moyan/75 indent-8">{{ detail.description }}</p>
    </section>

    <!-- ═══ 3. 经典名句 ═══ -->
    <section ref="mingjuSection" class="mingju-section">
      <SectionTitle :color="mingjuTitleColor" :sub="`共 ${poetryTotal} 条关联句读`">经典名句</SectionTitle>
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
            : { borderColor: 'color-mix(in srgb, ' + emotionMainColor(e) + ' 24%, #E7E0D2)', color: 'color-mix(in srgb, ' + emotionMainColor(e) + ' 64%, #6B6B6B)' }"
          @click="filterEmotionMain = e; page = 1; loadPoetries()">
          {{ e || '全部情感' }}
        </button>
      </div>
      <!-- 列表 -->
      <div class="space-y-3 mt-5">
        <div v-for="(item, i) in poetryItems" :key="item.rel_id"
          class="mingju-card card card-hover p-6 cursor-pointer rise-in" :style="{ animationDelay: i * 0.05 + 's' }"
          @click="$router.push(`/poetry/${item.poetry.id}`)">
          <div class="flex items-start justify-between gap-5">
            <p class="verse-text text-xl font-bold leading-relaxed" :style="{ color: detail.theme_color }">{{ item.clause }}</p>
            <span v-if="item.weight >= 2" class="shrink-0 text-xs font-bold tracking-wider" style="color:#c04040">✦ 经典</span>
          </div>
          <div class="flex items-center gap-3 mt-4 text-[13px] text-qianhui">
            <span>{{ item.poetry.dynasty }} · {{ item.poetry.author }}<span class="text-qianhui/55 ml-2">《{{ item.poetry.title }}》</span></span>
            <EmotionTag v-if="item.emotion" :tag="item.emotion" />
            <EmotionTag v-if="item.emotion_main" :tag="item.emotion_main" />
          </div>
        </div>
        <p v-if="!poetryItems.length && !poetryTotal" class="text-sm text-qianhui/70 py-8 text-center">该筛选条件下暂无名句</p>
      </div>
      <Pagination :page="page" :page-size="pageSize" :total="poetryTotal" @change="onMingjuPageChange" />
    </section>

    <!-- ═══ 4. 对仗与共现关联 ═══ -->
    <section class="title-serif">
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
          <div class="flex flex-col flex-1 min-h-[340px]">
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-sm text-qianhui tracking-widest">共现知识图谱</h3>
              <button v-if="cooc.edges?.length" class="btn-primary !py-1 !px-4 !text-xs transition-all duration-300 hover:scale-105 hover:shadow-lg" @click="showExplorer = true">
                探索 <span class="ml-0.5">⤢</span>
              </button>
            </div>
            <div v-if="cooc.edges?.length" class="flex-1 min-h-0">
              <CooccurrenceMiniGraph :data="cooc" :theme-color="detail.theme_color" class="h-full" />
            </div>
            <p v-else class="text-sm text-qianhui/70 py-8 text-center flex-1">暂无共现分析数据</p>
          </div>
          <p v-if="cooc.edges?.length" class="mt-3 text-[11px] text-qianhui/60 leading-5">
            线粗 = NPMI 强度 · 实线句内 / 虚线跨句 / 点线全诗 · 灰线桥接 · 点击节点进入对应意象
          </p>
        </div>
      </div>
    </section>

    <!-- ═══ 4.5 诗画相映（置于用法谱系之前） ═══ -->
    <section v-if="artworks.length" ref="artworkSection" class="title-serif">
      <SectionTitle :color="detail.theme_color" sub="点击作品展开详情卡片">诗画相映</SectionTitle>
      <div class="artwork-row" ref="artworkRow"
        @wheel.prevent="onRowWheel"
        @mousedown="onRowDragStart" @mousemove="onRowDrag" @mouseup="onRowDragEnd" @mouseleave="onRowDragEnd">
        <div v-for="(a, i) in artworks" :key="a.rel_id"
          class="artwork-card" :data-artwork-id="a.artwork.id"
          :class="{ 'artwork-enter': artworkInView }"
          :style="{ animationDelay: (i * 0.07) + 's' }" @click="onArtworkClick(a)">
          <div class="artwork-card__img">
            <img :src="a.artwork.thumb_url || a.artwork.image_url" :alt="a.artwork.name" loading="lazy" draggable="false" />
          </div>
          <div class="artwork-card__body">
            <h4 class="artwork-card__name">《{{ a.artwork.name }}》</h4>
            <p class="artwork-card__meta">{{ a.artwork.dynasty || a.artwork.dynasty_main }} · {{ a.artwork.artist }}</p>
            <p class="artwork-card__desc">{{ a.relation_desc }}</p>
          </div>
        </div>
      </div>
      <div class="artwork-hint">
        <svg class="artwork-hint__arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>
        <span class="font-kai text-xs tracking-[0.3em]">滑动鼠标查看更多</span>
      </div>
    </section>

    <!-- ═══ 5. 用法谱系（词云 + AI 总结） ═══ -->
    <section class="title-serif">
      <SectionTitle :color="detail.theme_color" sub="同一意象在不同诗人笔下的用法差异">用法谱系</SectionTitle>

      <!-- 两张云朵词云：情感功能 + 意象用法 -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <div class="card p-5">
          <h3 class="text-sm text-qianhui tracking-widest mb-2">情感功能词云</h3>
          <WordCloud :words="emotionCloudWords" :height="240" />
        </div>
        <div class="card p-5">
          <h3 class="text-sm text-qianhui tracking-widest mb-2">意象用法画像</h3>
          <VChart v-if="usageRadarOption" :option="usageRadarOption" height="260px" />
          <p v-else class="text-sm text-qianhui/70 py-8 text-center">暂无用法画像数据</p>
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
                  <div class="flex flex-wrap gap-1.5">
                    <EmotionTag v-for="e in s.emotion_function.split('、')" :key="e" :tag="e" />
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
    <section class="title-serif">
      <SectionTitle :color="detail.theme_color" sub="智能问答 · 格律创诗">AI 灵犀</SectionTitle>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <!-- AI 对话 -->
        <div class="card flex flex-col h-[420px]">
          <div class="px-5 py-3 border-b border-black/5 flex items-center gap-2">
            <span class="seal !w-7 !h-7 !text-[10px]">问</span>
            <span class="text-sm font-song font-semibold">向“{{ detail.name }}”提问</span>
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
              <!-- 用户提问 -->
              <div v-if="m.role === 'user'" class="max-w-[85%] px-4 py-2.5 text-sm leading-7 rounded-2xl shadow-card text-white rounded-tr-sm"
                :style="{ background: detail.theme_color }">{{ m.text }}</div>
              <!-- AI 回答：思考中 → 流式生成 → 完成 / 失败 -->
              <Transition v-else name="ai-phase" mode="out-in">
                <div v-if="m.phase === 'thinking'" key="thinking" class="ai-thinking">
                  <span class="seal ai-thinking__seal" :style="{ background: detail.theme_color }">思</span>
                  <span class="ai-thinking__text">{{ m.statusText }}</span>
                  <span class="ai-thinking__dots"><i></i><i></i><i></i></span>
                </div>
                <div v-else-if="m.phase === 'streaming' || m.phase === 'done'" key="answer"
                  class="max-w-[85%] px-4 py-2.5 text-sm leading-7 rounded-2xl shadow-card bg-white/85 border border-black/5 rounded-tl-sm">
                  {{ m.text }}<span v-if="m.phase === 'streaming'" class="ai-cursor">▌</span>
                  <p v-if="m.phase === 'done'" class="ai-source">已结合诗词语料 · 意象知识库 · 文化典故进行分析</p>
                </div>
                <div v-else key="error" class="max-w-[85%] px-4 py-2.5 text-sm leading-7 rounded-2xl shadow-card bg-white/85 border border-black/5 rounded-tl-sm">
                  <span class="text-qianhui">暂时未能完成解读，请稍后再试</span>
                  <button class="ai-retry" @click="regenerateAI(m)">重新生成</button>
                </div>
              </Transition>
            </div>
          </div>
          <div class="border-t border-black/5 p-3 flex gap-2">
            <input v-model="aiQuestion" @keyup.enter="askAI()" :placeholder="`自行提问，如：“${detail.name}”在古诗词中有哪些含义？`"
              class="flex-1 px-4 py-2 text-sm rounded-full border bg-white/70 focus:outline-none"
              :style="{ borderColor: detail.theme_color + '44' }" />
            <button class="btn-primary !rounded-full !py-2 !px-5 !text-sm" :disabled="aiSending || !aiQuestion.trim()" @click="askAI()">发送</button>
          </div>
        </div>

        <!-- AI 创诗 -->
        <div class="card flex flex-col h-[420px]">
          <div class="px-5 py-3 border-b border-black/5 flex items-center gap-2">
            <span class="seal !w-7 !h-7 !text-[10px]" style="background:#5B7C5F">创</span>
            <span class="text-sm font-song font-semibold">以“{{ detail.name }}”创诗</span>
          </div>
          <div class="flex-1 overflow-y-auto p-4">
            <Transition name="compose" mode="out-in">
              <!-- 创作控件区：生成结果后整体收起 -->
              <div v-if="!composeResult" key="controls">
                <div class="flex flex-wrap items-center gap-2 text-sm">
                  <label v-for="c in composeConceptOptions" :key="c" class="tag cursor-pointer transition-all"
                    :class="composeConcepts.includes(c) ? '!text-white' : 'hover:bg-black/5'"
                    :style="composeConcepts.includes(c)
                      ? { background: detail.theme_color, borderColor: detail.theme_color }
                      : { borderColor: detail.theme_color + '44', color: detail.theme_color }">
                    <input type="checkbox" class="hidden" :value="c" v-model="composeConcepts" />{{ c }}
                  </label>
                </div>
                <div class="flex items-start gap-3 mt-4">
                  <select v-model="composeStyle" class="px-3 py-2 text-sm rounded-full border bg-white/70 focus:outline-none shrink-0" :style="{ borderColor: detail.theme_color + '44' }">
                    <option v-for="s in composeStyles" :key="s">{{ s }}</option>
                  </select>
                  <div class="flex-1 min-w-0">
                    <button type="button" class="compose-tone-trigger" :style="{ borderColor: detail.theme_color + '44' }" @click="composeToneOpen = !composeToneOpen">
                      <template v-if="selectedTones.length">
                        <span v-for="t in selectedTones" :key="t" class="compose-tone-chip" :style="{ background: detail.theme_color + '14', borderColor: detail.theme_color + '44', color: detail.theme_color }">
                          {{ t }}<span class="compose-tone-chip__x" @click.stop="removeComposeTone(t)">×</span>
                        </span>
                        <span class="compose-tone-clear" :style="{ color: detail.theme_color }" @click.stop="clearComposeTones">清除</span>
                      </template>
                      <span v-else class="compose-tone-placeholder">情感基调（可选）</span>
                      <span class="compose-tone-chevron">{{ composeToneOpen ? '▲' : '▼' }}</span>
                    </button>
                    <Transition name="tone">
                      <div v-if="composeToneOpen" class="compose-tone-panel">
                        <div class="flex flex-wrap gap-2">
                          <label v-for="t in EMOTION_TONES" :key="t" class="tag cursor-pointer transition-all compose-tone-tag"
                            :class="composeThemes.includes(t) ? '!text-white' : 'hover:bg-black/5'"
                            :style="composeThemes.includes(t)
                              ? { background: detail.theme_color, borderColor: detail.theme_color }
                              : { borderColor: detail.theme_color + '44', color: detail.theme_color }">
                            <input type="checkbox" class="hidden" :value="t" v-model="composeThemes" />{{ t }}
                          </label>
                        </div>
                      </div>
                    </Transition>
                  </div>
                  <button class="btn-primary !rounded-full !py-2 !text-sm shrink-0" :disabled="composeSending || !composeConcepts.length" @click="composePoem">创诗</button>
                </div>
                <div v-if="composeSending" class="mt-6 text-sm text-qianhui text-center">正在创作<span class="animate-pulse">…</span></div>
                <div v-else class="mt-8 text-center text-xs text-qianhui/70">选择意象与体裁，AI 将依平仄格律为您创作</div>
              </div>

              <!-- 诗歌结果区：完整展示 -->
              <div v-else key="result">
                <div class="mt-2 rounded-lg p-5 border" :style="{ borderColor: detail.theme_color + '33', background: detail.theme_color + '08' }">
                  <h4 class="font-song font-bold text-center" :style="{ color: detail.theme_color }">《{{ composeResult.title }}》</h4>
                  <p class="verse-text text-center text-moyan/90 leading-8 mt-3 whitespace-pre-line">{{ composeResult.poem }}</p>
                  <p v-if="composeResult.note" class="text-[11px] text-qianhui text-center mt-3">{{ composeResult.note }}</p>
                </div>
                <div class="flex justify-center mt-4">
                  <button class="btn-outline !py-1.5 !px-5 !text-xs" @click="resetCompose">重新创作</button>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══ 7. 扩展工具 ═══ -->
    <section class="card p-6 flex flex-wrap items-center gap-4">
      <span class="text-sm text-qianhui tracking-widest mr-2">扩展工具</span>
      <router-link :to="'/share/concept/' + detail.id" class="tool-link" style="--c:#9B6820"><span class="tool-ico font-kai">卡</span>生成分享卡片</router-link>
      <router-link to="/agent" class="tool-link" style="--c:#9B2C1F"><span class="tool-ico font-kai">问</span>前往灵犀助手</router-link>
      <router-link to="/atlas" class="tool-link" style="--c:#5B7C5F"><span class="tool-ico font-kai">鉴</span>前往诗意图鉴</router-link>
      <router-link to="/artworks" class="tool-link" style="--c:#9B4423"><span class="tool-ico font-kai">艺</span>前往艺术展厅</router-link>
    </section>

    <!-- 共现图谱全屏 -->
    <CooccurrenceExplorer :show="showExplorer" :data="cooc" :theme-color="detail?.theme_color || '#2B4C7E'" @close="showExplorer = false" />

    <!-- 返回顶部 -->
    <BackToTop />

    <!-- 艺术作品详情卡片（意象卡片内就地展开，不跳转） -->
    <Teleport to="body">
      <Transition name="artwork">
        <div v-if="activeArtwork" class="artwork-overlay" @click.self="activeArtwork = null">
          <div class="artwork-sheet">
            <button class="artwork-sheet__close" @click="activeArtwork = null">×</button>
            <!-- 左侧：作品图片（双击全屏） -->
            <div class="artwork-sheet__img" @dblclick="artFullscreen = true" title="双击全屏欣赏">
              <img :src="activeArtwork.image_url" :alt="activeArtwork.name" />
              <span class="artwork-sheet__hint">双击全屏</span>
            </div>
            <!-- 右侧：作品介绍（数字展签） -->
            <div class="artwork-sheet__body">
              <h3 class="font-song text-2xl font-bold pr-8">《{{ activeArtwork.name }}》</h3>
              <p class="text-sm text-qianhui mt-1">{{ activeArtwork.dynasty_period || activeArtwork.dynasty }} · {{ activeArtwork.artist }}</p>
              <div class="mt-5">
                <span class="artwork-sheet__label">作品介绍</span>
                <p class="text-sm leading-7 mt-2 text-moyan/85 whitespace-pre-line">{{ activeArtwork.description || '暂无介绍' }}</p>
              </div>
              <div v-if="activeArtwork.concepts && activeArtwork.concepts.length" class="mt-5 pt-4 border-t border-black/5">
                <span class="artwork-sheet__label">对应意象</span>
                <div class="flex flex-wrap gap-2 mt-2">
                  <span v-for="c in activeArtwork.concepts" :key="c.id" class="artwork-sheet__concept"
                    :style="{ color: c.theme_color, borderColor: c.theme_color + '66', background: c.theme_color + '0F' }">{{ c.name }}</span>
                </div>
                <p v-for="c in activeArtwork.concepts" :key="'d' + c.id" class="text-xs text-qianhui leading-6 mt-2">· {{ c.relation_desc }}</p>
              </div>
              <p v-if="activeArtworkRel" class="artwork-sheet__rel" :style="{ color: detail.theme_color, borderColor: detail.theme_color + '33' }">{{ activeArtworkRel }}</p>
              <div class="mt-5 flex gap-3">
                <button class="btn-outline !py-1.5 !text-xs" @click="goToGallery(activeArtwork.id)">在艺术展厅中查看</button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
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
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import {
  agentAsk, agentCompose, getConceptArtworks, getConceptDetail, getConceptPoetries,
  getConceptUsageSpectrum,
} from '../api'
import { getConceptCooccurrence, getUsageSummary } from '../api'
import { getArtworkDetail } from '../api'
import { useExploredImageries } from '../composables/useExploredImageries'
import BackToTop from '../components/BackToTop.vue'
import CategoryTag from '../components/CategoryTag.vue'
import CooccurrenceExplorer from '../components/CooccurrenceExplorer.vue'
import CooccurrenceMiniGraph from '../components/CooccurrenceMiniGraph.vue'
import EmotionTag from '../components/EmotionTag.vue'
import Pagination from '../components/Pagination.vue'
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
const ready = ref(false)
const artworks = ref([])
const cooc = ref({ nodes: [], edges: [] })
const showExplorer = ref(false)
const activeArtwork = ref(null)
const activeArtworkRel = ref('')
const artFullscreen = ref(false)
const artworkSection = ref(null)
const artworkRow = ref(null)
// 进入动画开关：板块滚入视口时才逐张淡入上浮
const artworkInView = ref(false)

// 打开艺术作品详情卡片时锁定背景滚动，避免鼠标在卡片外滚动导致页面跟着滚动
watch(activeArtwork, (v) => { document.body.style.overflow = v ? 'hidden' : '' })
watch(artFullscreen, (v) => { if (v) document.body.style.overflow = 'hidden' })

// 用法谱系
const spectrum = ref([])
const spectrumLoading = ref(true)
const usageSummary = ref('')
const summarizeLoading = ref(false)

const { addExplored } = useExploredImageries()

// 名句筛选
const mingjuSection = ref(null)
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

// 经典名句标题色：主题色掺墨降饱和，更典雅
const mingjuTitleColor = computed(() =>
  `color-mix(in srgb, ${detail.value?.theme_color || '#2B4C7E'} 74%, #2C2C2C)`)

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
  const SERIF = "'Noto Serif SC', 'Songti SC', STSong, SimSun, serif"
  return {
    // 全图默认字体：现代宋体（朝代名 / 轴数值 / tooltip 统一）
    textStyle: { fontFamily: SERIF, color: '#6B6B6B' },
    grid: { left: 56, right: 20, top: 30, bottom: 40 },
    tooltip: { trigger: 'axis', textStyle: { fontFamily: SERIF, fontSize: 12, color: '#2C2C2C' },
      formatter: (p) => `${p[0].name}<br/>出现 ${p[0].value.toLocaleString()} 次` },
    xAxis: {
      type: 'category', data: stats.map((s) => s.dynasty),
      axisLine: { lineStyle: { color: '#00000014' } },
      axisTick: { show: false },
      axisLabel: { color: '#6B6B6B', fontFamily: SERIF, fontSize: 12 },
    },
    yAxis: {
      type: 'log',
      min: 1,
      axisLine: { lineStyle: { color: '#00000014' } },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#00000008' } },
      axisLabel: { color: '#9A9A9A', fontSize: 11, fontFamily: SERIF,
        formatter: (v) => v >= 10000 ? `${(v/10000).toFixed(0)}万` : v >= 1000 ? `${(v/1000).toFixed(0)}千` : v },
    },
    series: [{
      type: 'line', smooth: true, symbol: 'circle', symbolSize: 7,
      data: stats.map((s) => Math.max(s.count, 1)),
      lineStyle: { width: 2, color },
      itemStyle: { color, borderColor: '#F5F1E8', borderWidth: 1.5 },
      areaStyle: { color: color + '18' },
    }],
  }
})

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
  // 平方根压缩数值差距（去掉 +1 基线，无分值的角色为 0，避免各意象雷达雷同）
  const values = ROLE_ORDER.map(r => Math.round(Math.sqrt(acc[r] || 0) * 10) / 10)
  const sumVal = values.reduce((a, b) => a + b, 0)
  if (sumVal === 0) return null  // 无数据时不渲染（显示占位提示）
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

function scrollToMingju() {
  const el = mingjuSection.value
  if (!el) return
  window.scrollTo({ top: Math.max(0, el.getBoundingClientRect().top + window.scrollY - 88), behavior: 'smooth' })
}

function onMingjuPageChange(p) {
  page.value = p
  loadPoetries().then(() => nextTick(scrollToMingju))
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
    usageSummary.value = `“${detail.value.name}”意象在历代诗人笔下各具风姿，承载着丰富的文化内涵与情感意蕴。`
  } finally { summarizeLoading.value = false }
}

// ═══ 艺术品就地详情 ═══
async function openArtwork(a) {
  activeArtworkRel.value = a.relation_desc
  try { activeArtwork.value = await getArtworkDetail(a.artwork.id) }
  catch { activeArtwork.value = a.artwork }
}
function goToGallery(id) {
  activeArtwork.value = null
  router.push({ path: '/artworks', query: { id, concept: detail.value.id, conceptName: detail.value.name } })
}

/** 从艺术展厅返回本意象时：定位到「诗画相映」板块对应艺术品卡片（垂直滚到板块 + 水平居中该卡片 + 主题色高亮） */
function scrollToArtwork(targetId) {
  const section = artworkSection.value
  if (!section) return
  window.scrollTo(0, Math.max(0, section.getBoundingClientRect().top + window.scrollY - 88))
  const card = section.querySelector(`[data-artwork-id="${targetId}"]`)
  if (card && artworkRow.value) {
    artworkRow.value.scrollTo({
      left: card.offsetLeft - (artworkRow.value.clientWidth - card.offsetWidth) / 2,
      behavior: 'smooth',
    })
  }
  if (card) {
    card.classList.add('is-highlighted')
    setTimeout(() => card.classList.remove('is-highlighted'), 1500)
  }
}

// ═══ 横向画廊拖拽 / 滚轮平移 ═══
const rowDrag = { active: false, moved: false, startX: 0, startLeft: 0 }
let rowScrollRaf = null   // 合帧句柄：每帧至多更新一次 scrollLeft
let rowTargetLeft = null  // 记录最新目标位置，帧末取最新值，避免高频事件被丢弃导致「阶梯感」

function scheduleRowScroll(left) {
  rowTargetLeft = left
  if (rowScrollRaf == null) {
    rowScrollRaf = requestAnimationFrame(() => {
      rowScrollRaf = null
      const t = rowTargetLeft
      rowTargetLeft = null
      if (t != null && artworkRow.value) artworkRow.value.scrollLeft = t
    })
  }
}
function onRowDragStart(e) {
  rowDrag.active = true
  rowDrag.moved = false
  rowDrag.startX = e.clientX
  rowDrag.startLeft = artworkRow.value.scrollLeft
  artworkRow.value.classList.add('is-dragging')
}
function onRowDrag(e) {
  if (!rowDrag.active) return
  const dx = e.clientX - rowDrag.startX
  if (Math.abs(dx) > 4) rowDrag.moved = true   // 位移超阈值视为拖拽，抑制后续 click
  scheduleRowScroll(rowDrag.startLeft - dx)
}
function onRowDragEnd() {
  rowDrag.active = false
  if (artworkRow.value) artworkRow.value.classList.remove('is-dragging')
}
function onRowWheel(e) {
  scheduleRowScroll(artworkRow.value.scrollLeft + e.deltaY)
}
function onArtworkClick(a) {
  if (rowDrag.moved) return   // 拖拽平移后不触发展开
  openArtwork(a)
}

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
const aiHistory = ref([])   // 多轮对话历史
const presetQuestions = computed(() => [
  `“${detail.value?.name}”在古诗词中有哪些核心含义？`,
  `哪些诗人最爱用“${detail.value?.name}”意象？`,
  `“${detail.value?.name}”的情感色彩经历了怎样的演变？`,
])
// 思考状态文案（概括性处理状态，不暴露真实内部推理）
const THINKING_STEPS = ['正在理解你的问题……', '正在检索相关诗词资料……', '正在梳理意象内涵……', '正在组织回答……']
const THINKING_DELAY = '正在继续梳理相关资料……'
const THINKING_STEP_MS = 400
const THINKING_MIN_MS = 1000
const STREAM_CHUNK = 2
const STREAM_TICK_MS = 55
let aiStepTimer = null
let aiStreamTimer = null

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)) }

// 逐段揭示答案：稳定节奏，末尾光标由模板渲染
function streamText(msg, full) {
  return new Promise((resolve) => {
    let i = 0
    aiStreamTimer = setInterval(() => {
      i = Math.min(i + STREAM_CHUNK, full.length)
      msg.text = full.slice(0, i)
      scrollAi()
      if (i >= full.length) { clearInterval(aiStreamTimer); aiStreamTimer = null; resolve() }
    }, STREAM_TICK_MS)
  })
}

// 一次完整的「思考 → 流式生成」；msg 为 aiMsgs 中已存在的 AI 消息对象
async function runAiResponse(question, msg) {
  msg.step = 0
  msg.phase = 'thinking'
  msg.statusText = THINKING_STEPS[0]
  msg.text = ''
  const startedAt = Date.now()

  aiStepTimer = setInterval(() => {
    const idx = msg.step + 1
    msg.step = idx
    msg.statusText = THINKING_STEPS[idx] || THINKING_DELAY
    if (idx >= THINKING_STEPS.length) { clearInterval(aiStepTimer); aiStepTimer = null }
  }, THINKING_STEP_MS)

  let answer = null
  try {
    answer = (await agentAsk(question, aiHistory.value.slice(-8)))?.answer || '暂无回答'
    answer = answer.replace(/「/g, '“').replace(/」/g, '”')   // 回答里的「」统一为中文双引号
  } catch { answer = null }

  if (answer == null) {
    if (aiStepTimer) { clearInterval(aiStepTimer); aiStepTimer = null }
    msg.phase = 'error'
    aiSending.value = false
    await nextTick(); scrollAi()
    return
  }

  // 思考状态至少持续 THINKING_MIN_MS，让过程自然可感
  const elapsed = Date.now() - startedAt
  if (elapsed < THINKING_MIN_MS) await sleep(THINKING_MIN_MS - elapsed)
  if (aiStepTimer) { clearInterval(aiStepTimer); aiStepTimer = null }

  msg.phase = 'streaming'
  await nextTick(); scrollAi()
  await streamText(msg, answer)

  msg.phase = 'done'
  aiHistory.value.push({ role: 'ai', content: answer })
  aiSending.value = false
  await nextTick(); scrollAi()
}

async function askAI(q) {
  const question = q || aiQuestion.value.trim()
  if (!question || aiSending.value) return
  aiMsgs.value.push({ id: Date.now(), role: 'user', text: question })
  aiQuestion.value = ''
  aiSending.value = true
  aiHistory.value.push({ role: 'user', content: question })
  const aiMsg = reactive({ id: Date.now() + 1, role: 'ai', phase: 'thinking', statusText: THINKING_STEPS[0], text: '', step: 0, question })
  aiMsgs.value.push(aiMsg)
  await nextTick(); scrollAi()
  runAiResponse(question, aiMsg)
}

// 失败后重试：复用原问题，不重复写历史
function regenerateAI(msg) {
  if (aiSending.value || !msg.question) return
  aiSending.value = true
  msg.step = 0
  runAiResponse(msg.question, msg)
}
function scrollAi() { if (aiMsgBox.value) aiMsgBox.value.scrollTop = aiMsgBox.value.scrollHeight }

// ═══ AI 创诗 ═══
const composeConcepts = ref([])
const composeStyles = ['五言绝句', '七言绝句', '五言律诗', '七言律诗']
const composeStyle = ref('七言绝句')
// 通用情感基调（24 种固定选项，全平台一致，不随意象变化）
const EMOTION_TONES = [
  '喜悦', '欢愉', '赞美', '旷达', '豪迈', '闲适',   // 正向情感
  '思乡', '怀人', '思念', '离愁', '惜别', '闺怨',   // 思念与离别
  '惆怅', '忧愁', '孤寂', '感伤', '悲凉', '悲壮',   // 忧愁与感伤
  '怀古', '感时', '惜时', '身世感怀',               // 人生与历史
  '宁静', '清冷',                                  // 审美与精神意境
]
const composeThemes = ref([])          // 已选情感基调（checkbox 数组绑定）
const composeToneOpen = ref(false)     // 情感标签面板展开状态
const selectedTones = computed(() => EMOTION_TONES.filter(t => composeThemes.value.includes(t)))
function removeComposeTone(t) { const i = composeThemes.value.indexOf(t); if (i >= 0) composeThemes.value.splice(i, 1) }
function clearComposeTones() { composeThemes.value = [] }
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
    composeResult.value = await agentCompose({ concepts: composeConcepts.value, style: composeStyle.value, theme: selectedTones.value.join('、') })
  } catch { composeResult.value = { title: '创作失败', poem: '请稍后再试。', note: '' } }
  finally { composeSending.value = false }
}
function resetCompose() {
  composeResult.value = null
  composeToneOpen.value = false
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
    // 从「经典名句」跳诗歌详情后返回：先就绪、恢复滚动，再揭示内容，直接落在名句位置，避免可见跳动
    const savedScroll = sessionStorage.getItem(`scroll:concept:${conceptId}`)
    if (savedScroll != null) sessionStorage.removeItem(`scroll:concept:${conceptId}`)
    ready.value = true
    await nextTick()
    // 诗画相映进入动画：板块滚入视口才逐张淡入上浮（触发一次即断开）
    if (artworkSection.value) {
      const artObserver = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
          artworkInView.value = true
          artObserver.disconnect()
        }
      }, { threshold: 0.15 })
      artObserver.observe(artworkSection.value)
    }
    if (route.query.artwork) scrollToArtwork(Number(route.query.artwork))
    else if (savedScroll != null) window.scrollTo(0, Number(savedScroll))
    document.addEventListener('keydown', onKeyToggle)
    document.addEventListener('keyup', onKeyRelease)
  } catch {
    router.replace({ name: 'not-found' })
  }
})
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeyToggle)
  document.removeEventListener('keyup', onKeyRelease)
  if (rowScrollRaf != null) cancelAnimationFrame(rowScrollRaf)
  if (aiStepTimer) clearInterval(aiStepTimer)
  if (aiStreamTimer) clearInterval(aiStreamTimer)
})

// 跳转到诗歌详情前记录滚动位置，便于返回时回到对应的「经典名句」处
onBeforeRouteLeave((to) => {
  if (to.name === 'poetry-detail') {
    sessionStorage.setItem(`scroll:concept:${conceptId}`, String(window.scrollY))
  }
})
</script>

<style scoped>
/* ═══ 诗画相映：数字博物馆式古画展陈 ═══ */
.artwork-row {
  display: flex;
  gap: 20px;
  overflow-x: auto;
  scrollbar-width: none;          /* Firefox 隐藏横向滚动条 */
  -ms-overflow-style: none;        /* IE/Edge 隐藏 */
  overscroll-behavior-x: contain;  /* 滚到两端阻断横向滚动链，避免触发前进/后退手势 */
  cursor: grab;
  user-select: none;               /* 拖拽时避免选中文字/图片 */
  padding: 8px 2px 18px;           /* 为悬停上浮留出空间，避免阴影被裁切 */
}
.artwork-row::-webkit-scrollbar { display: none; }
.artwork-row:active { cursor: grabbing; }
/* 拖拽平移时禁用卡片悬停过渡，避免拖动过程反复触发位移/阴影动画造成卡顿 */
.artwork-row.is-dragging .artwork-card,
.artwork-row.is-dragging .artwork-card__img img {
  transition: none;
}

.artwork-card {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  width: 300px;
  aspect-ratio: 3 / 4;             /* 尺寸/比例恒定，不随文字增减 */
  overflow: hidden;
  border-radius: 6px;
  background: #FBF8F1;             /* 宣纸白 */
  border: 1px solid rgba(44, 44, 44, 0.08);
  box-shadow: 0 1px 6px rgba(44, 44, 44, 0.05);
  cursor: pointer;
  transition: transform 0.35s ease-out, box-shadow 0.35s ease-out, border-color 0.35s ease-out;
}
.artwork-card__img {
  height: 56%;
  flex-shrink: 0;
  overflow: hidden;
  background: #F3EEE2;
}
.artwork-card__img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center;
  transition: transform 0.4s ease-out;
}
.artwork-card__body {
  flex: 1;
  padding: 15px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.artwork-card__name {
  font-family: 'Noto Serif SC', 'Songti SC', STSong, SimSun, serif;
  font-weight: 600;
  font-size: 18px;
  line-height: 1.4;
  color: #2C2C2C;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.35s ease-out;
}
.artwork-card__meta {
  font-size: 12px;
  line-height: 1.6;
  color: #6B6B6B;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.artwork-card__desc {
  font-size: 12px;
  line-height: 1.9;
  color: #6B6B6B;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 悬停：古画缓缓展开（微放大 + 上浮 + 名称现主题色） */
.artwork-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 26px rgba(44, 44, 44, 0.10);
  border-color: color-mix(in srgb, var(--tc) 40%, rgba(44, 44, 44, 0.08));
}
.artwork-card:hover .artwork-card__img img { transform: scale(1.04); }
.artwork-card:hover .artwork-card__name { color: color-mix(in srgb, var(--tc) 80%, #2C2C2C); }

/* 返回定位高亮（--tc 由页面根注入 = 意象主题色） */
.artwork-card.is-highlighted {
  box-shadow:
    0 0 0 2px color-mix(in srgb, var(--tc) 50%, transparent),
    0 0 28px color-mix(in srgb, var(--tc) 26%, transparent);
}

/* 进入动画：滚入视口时自下方 10px 淡入，逐张级差（animationDelay 内联注入） */
@keyframes artwork-rise {
  from { opacity: 0; transform: translateY(10px); }
  to   { opacity: 1; transform: translateY(0); }
}
.artwork-card.artwork-enter { animation: artwork-rise 0.5s ease-out both; }

/* 诗画相映滑动提示（随意象主题色 --tc） */
.artwork-hint {
  display: flex; align-items: center; justify-content: center;
  gap: 8px; margin-top: 4px;
  color: var(--tc);
  opacity: 0.55;
  user-select: none; pointer-events: none;
}
.artwork-hint__arrow { width: 15px; height: 15px; animation: artwork-hint-drift 1.6s ease-in-out infinite; }
@keyframes artwork-hint-drift {
  0% { opacity: 0; transform: translateX(-6px); }
  40% { opacity: 1; }
  100% { opacity: 0; transform: translateX(6px); }
}
@media (prefers-reduced-motion: reduce) {
  .artwork-hint__arrow { animation: none; }
}

/* 展开详情：柔和暖暗遮罩 + 展签卡 */
.artwork-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(44, 44, 44, 0.5);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
}
.artwork-sheet {
  position: relative;
  width: 100%;
  max-width: 56rem;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border-radius: 8px;
  background: #FBF8F1;
  border: 1px solid rgba(44, 44, 44, 0.08);
  box-shadow: 0 20px 60px rgba(44, 44, 44, 0.18);
}
@media (min-width: 768px) { .artwork-sheet { flex-direction: row; } }
.artwork-sheet__close {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  z-index: 20;
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: rgba(0, 0, 0, 0.25);
  color: #fff;
  font-size: 1.25rem;
  transition: background 0.2s ease;
}
.artwork-sheet__close:hover { background: rgba(0, 0, 0, 0.45); }
.artwork-sheet__img {
  position: relative;
  width: 100%;
  flex-shrink: 0;
  background: rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: zoom-in;
}
@media (min-width: 768px) { .artwork-sheet__img { width: 50%; } }
.artwork-sheet__img img {
  width: 100%;
  max-height: 42vh;
  object-fit: contain;
}
@media (min-width: 768px) { .artwork-sheet__img img { max-height: 85vh; } }
.artwork-sheet__hint {
  position: absolute;
  bottom: 0.75rem;
  right: 0.75rem;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.4);
  color: rgba(255, 255, 255, 0.7);
  font-size: 10px;
}
.artwork-sheet__body {
  width: 100%;
  padding: 1.5rem;
  overflow-y: auto;
  max-height: 42vh;
}
@media (min-width: 768px) {
  .artwork-sheet__body { width: 50%; max-height: 85vh; }
}
.artwork-sheet__label {
  font-size: 12px;
  color: #6B6B6B;
  letter-spacing: 0.2em;
}
.artwork-sheet__concept {
  display: inline-block;
  font-size: 12px;
  line-height: 1.6;
  padding: 2px 10px;
  border: 1px solid;
  border-radius: 9999px;
}
.artwork-sheet__rel {
  margin-top: 1.25rem;
  padding-top: 1rem;
  border-top: 1px solid;
  font-size: 14px;
  line-height: 1.9;
}

/* 展签浮层过渡：遮罩淡入 + 卡身轻微上浮放大，柔和缓动 */
.artwork-enter-active { transition: opacity 0.3s ease; }
.artwork-leave-active { transition: opacity 0.24s ease; }
.artwork-enter-from, .artwork-leave-to { opacity: 0; }
.artwork-enter-active .artwork-sheet,
.artwork-leave-active .artwork-sheet {
  transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.3s ease;
}
.artwork-enter-from .artwork-sheet,
.artwork-leave-to .artwork-sheet {
  opacity: 0;
  transform: translateY(20px) scale(0.96);
}

/* 古籍式批注小标识：主题色低饱和 + 右侧极细短线 */
.meaning-label {
  display: flex; align-items: center;
  font-family: 'Noto Serif SC', 'Songti SC', STSong, SimSun, serif;
  font-size: 13px; font-weight: 600; letter-spacing: 0.22em;
  color: color-mix(in srgb, var(--tc) 68%, #2C2C2C);
}
.meaning-label::after {
  content: ''; width: 2.2em; height: 1px; margin-left: 10px;
  background: color-mix(in srgb, var(--tc) 30%, transparent);
}

/* 演变脉络标题：古籍题名气质（宋体 + 字距 + 适中字重，仅本模块） */
.dynasty-section :deep(.section-title) {
  font-weight: 500;
  letter-spacing: 0.14em;
}
/* 图表容器：宣纸白 + 更轻阴影 + 舒展留白 */
.dynasty-card {
  border-radius: 10px;
  padding: 1.5rem;
  box-shadow: 0 1px 8px rgba(44, 44, 44, 0.05);
}

/* 经典名句标题：宋体古籍章节气质 */
.mingju-section :deep(.section-title) {
  font-weight: 500;
  letter-spacing: 0.14em;
}
/* 副标题「共N条关联句读」：降为浅灰小字 */
.mingju-section :deep(.section-sub) {
  font-size: 11px;
  color: rgba(107, 107, 107, 0.72);
  letter-spacing: 0.05em;
}
/* 统一其余板块标题为「演变脉络/经典名句」的古籍题名字体气质 */
.title-serif :deep(.section-title) {
  font-weight: 500;
  letter-spacing: 0.14em;
}
/* 名句卡片：宣纸米白 + 浅暖灰边 + 低圆角 + 极轻阴影 */
.mingju-card {
  background: #FAF7F0;
  border-color: #E7E0D2;
  border-radius: 6px;
  box-shadow: 0 1px 5px rgba(44, 44, 44, 0.04);
}
.mingju-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 16px rgba(44, 44, 44, 0.05);
}

/* ═══ AI 灵犀：思考中 → 流式生成 ═══ */
.ai-thinking {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: 0 1px 3px rgba(44, 44, 44, 0.04);
  min-height: 44px;
  color: color-mix(in srgb, var(--tc) 72%, #6B6B6B);
}
.ai-thinking__seal {
  width: 28px;
  height: 28px;
  font-size: 10px;
  flex-shrink: 0;
}
.ai-thinking__text {
  font-size: 12px;
  letter-spacing: 0.03em;
}
.ai-thinking__dots {
  display: flex;
  gap: 4px;
  align-items: flex-end;
  padding-bottom: 2px;
}
.ai-thinking__dots i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
  animation: ai-dot-breathe 1.2s ease-in-out infinite;
}
.ai-thinking__dots i:nth-child(2) { animation-delay: 0.15s; }
.ai-thinking__dots i:nth-child(3) { animation-delay: 0.3s; }
@keyframes ai-dot-breathe {
  0%, 100% { opacity: 0.3; transform: translateY(0); }
  50% { opacity: 1; transform: translateY(-2px); }
}
.ai-cursor {
  display: inline-block;
  margin-left: 1px;
  color: var(--tc);
  animation: ai-cursor-blink 0.9s steps(1, end) infinite;
}
@keyframes ai-cursor-blink {
  0%, 100% { opacity: 0; }
  50% { opacity: 1; }
}
.ai-source {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
  font-size: 11px;
  line-height: 1.6;
  color: rgba(107, 107, 107, 0.6);
  letter-spacing: 0.02em;
}
.ai-retry {
  margin-left: 8px;
  font-size: 12px;
  color: var(--tc);
  text-decoration: underline;
  cursor: pointer;
}
.ai-phase-enter-active { transition: opacity 0.35s ease; }
.ai-phase-leave-active { transition: opacity 0.3s ease; }
.ai-phase-enter-from, .ai-phase-leave-to { opacity: 0; }

/* ═══ AI 创诗：情感基调多选 ═══ */
.compose-tone-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
  min-height: 38px;
  padding: 5px 14px;
  border-radius: 999px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.compose-tone-trigger:hover { box-shadow: 0 1px 4px rgba(44, 44, 44, 0.06); }
.compose-tone-placeholder { color: rgba(107, 107, 107, 0.75); }
.compose-tone-chevron { margin-left: auto; font-size: 11px; color: rgba(107, 107, 107, 0.6); }
.compose-tone-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 12px;
  line-height: 1.6;
}
.compose-tone-chip__x { cursor: pointer; opacity: 0.65; transition: opacity 0.15s ease; }
.compose-tone-chip__x:hover { opacity: 1; }
.compose-tone-clear { font-size: 12px; cursor: pointer; margin-left: 2px; }
.compose-tone-clear:hover { text-decoration: underline; }
.compose-tone-panel {
  margin-top: 8px;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(255, 255, 255, 0.6);
}
.compose-tone-tag { font-size: 12px; }
.tone-enter-active, .tone-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.tone-enter-from, .tone-leave-to { opacity: 0; transform: translateY(-4px); }

/* AI 创诗：控件 ↔ 结果 切换过渡 */
.compose-enter-active, .compose-leave-active { transition: opacity 0.28s ease, transform 0.28s ease; }
.compose-enter-from { opacity: 0; transform: translateY(10px); }
.compose-leave-to { opacity: 0; transform: translateY(-6px); }

/* ─────────── 扩展工具 ─────────── */
.tool-link {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 8px 14px 8px 10px; border-radius: 8px;
  border: 1px solid var(--c); color: var(--c);
  background: transparent; font-size: 13px; font-weight: 600;
  letter-spacing: 0.06em; transition: all .2s;
}
.tool-link:hover {
  background: var(--c); color: #F5F1E8;
  transform: translateY(-1px); box-shadow: 0 6px 16px -8px var(--c);
}
.tool-ico {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 6px; font-size: 13px;
  background: var(--c); color: #F5F1E8; flex: none;
  box-shadow: inset 0 0 0 1.5px rgba(245,241,232,0.5);
  transition: background .2s, box-shadow .2s;
}
.tool-link:hover .tool-ico {
  background: rgba(245,241,232,0.22);
  box-shadow: inset 0 0 0 1px rgba(245,241,232,0.65);
}
</style>
