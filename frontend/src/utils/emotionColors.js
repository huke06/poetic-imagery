// 一级情感标签配色（全站统一：卡片、画廊筛选、详情页共用）
export const EMOTION_COLORS = {
  '情感心绪类': '#6E4A7E', '交往离别类': '#9B4423', '人生感悟类': '#8A6D3B',
  '自然山水类': '#5B7C5F', '历史文化类': '#2B4C7E', '志向抱负类': '#9B2C1F',
  '超脱境界类': '#3A7A7C',
}

export const emotionColor = (m) => EMOTION_COLORS[m] || '#8A6D3B'
