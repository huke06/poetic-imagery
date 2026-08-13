// 分享卡片导出工具：SVG → 图片下载 / PNG 转换

/** 从 SVG 文本解析出宽高 */
export function svgSize(svgText) {
  const m = /width="(\d+(?:\.\d+)?)"\s+height="(\d+(?:\.\d+)?)"/.exec(svgText)
  if (m) return { width: Number(m[1]), height: Number(m[2]) }
  return { width: 720, height: 440 }
}

/** SVG 文本 → data URL（用于 <img> 展示） */
export function svgDataUrl(svgText) {
  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgText)
}

/** SVG 文本 → PNG data URL（纯 SVG 元素可转；依赖浏览器字体回退） */
export function svgToPngDataUrl(svgText, width, height) {
  return new Promise((resolve, reject) => {
    const size = svgSize(svgText)
    const w = width || size.width
    const h = height || size.height
    const url = svgDataUrl(svgText)
    const img = new Image()
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas')
        canvas.width = w
        canvas.height = h
        const ctx = canvas.getContext('2d')
        ctx.fillStyle = '#F5F1E8'
        ctx.fillRect(0, 0, w, h)
        ctx.drawImage(img, 0, 0, w, h)
        resolve(canvas.toDataURL('image/png'))
      } catch (e) { reject(e) }
    }
    img.onerror = reject
    img.src = url
  })
}

/** 触发浏览器下载 */
export function downloadDataUrl(dataUrl, filename) {
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
}

export function downloadText(text, filename, mime = 'image/svg+xml;charset=utf-8') {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  downloadDataUrl(url, filename)
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
