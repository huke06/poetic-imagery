/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        xuanzhi: '#F5F1E8',   // 宣纸米白
        shiqing: '#2B4C7E',   // 石青（主色）
        zheshi: '#9B4423',    // 赭石
        zhuqing: '#5B7C5F',   // 竹青
        moyan: '#2C2C2C',     // 墨（正文深灰）
        zhusha: '#9B2C1F',    // 朱砂（印章）
        qianhui: '#6B6B6B',   // 浅灰（次要文字）
      },
      fontFamily: {
        song: ['"Noto Serif SC"', '"Songti SC"', 'STSong', 'SimSun', 'serif'],
        kai: ['"Kaiti SC"', 'STKaiti', 'KaiTi', '"Noto Serif SC"', 'serif'],
        fang: ['FangSong', 'STFangsong', 'FangSong_GB2312', '仿宋', 'serif'],
        hei: ['"Noto Sans SC"', '"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 12px rgba(44, 44, 44, 0.06)',
        'card-hover': '0 10px 28px rgba(44, 44, 44, 0.12)',
      },
    },
  },
  plugins: [],
}
