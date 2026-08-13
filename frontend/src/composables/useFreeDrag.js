import { onBeforeUnmount, ref } from 'vue'

/**
 * 悬浮组件自由拖拽（上下 + 左右），位置持久化到 localStorage。
 * - right / bottom: 距视口右/下边缘的像素偏移（响应式）
 * - onPointerDown: 绑到拖拽手柄的 @pointerdown
 * - wasDragged: 最近一次按下-抬起是否发生拖拽（用于区分点击/拖拽）
 * - resetRight: 收起后把组件吸附回右侧默认位置
 */
export function useFreeDrag(storageKey, defaultRight = 20, defaultBottom = 20) {
  const right = ref(defaultRight)
  const bottom = ref(defaultBottom)
  const dragging = ref(false)
  let startX = 0, startY = 0, startRight = 0, startBottom = 0, moved = false

  const clampRight = (v) => Math.min(Math.max(0, v), Math.max(0, (window.innerWidth || 800) - 56))
  const clampBottom = (v) => Math.min(Math.max(8, v), Math.max(8, (window.innerHeight || 800) - 56))

  try {
    const saved = localStorage.getItem(storageKey)
    if (saved) {
      const o = JSON.parse(saved)
      if (o && typeof o.right === 'number') right.value = clampRight(o.right)
      if (o && typeof o.bottom === 'number') bottom.value = clampBottom(o.bottom)
    }
  } catch { /* ignore */ }

  function onPointerMove(e) {
    if (!dragging.value) return
    const dx = e.clientX - startX
    const dy = e.clientY - startY
    if (Math.abs(dx) + Math.abs(dy) > 4) moved = true
    right.value = clampRight(startRight - dx)
    bottom.value = clampBottom(startBottom - dy)
  }

  function onPointerUp() {
    dragging.value = false
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
    try { localStorage.setItem(storageKey, JSON.stringify({ right: right.value, bottom: bottom.value })) } catch { /* ignore */ }
  }

  function onPointerDown(e) {
    // 手柄内的交互控件（输入/链接等，带 .no-drag）不触发拖拽
    if (e.target.closest('.no-drag, input, select, textarea, a')) return
    dragging.value = true
    moved = false
    startX = e.clientX
    startY = e.clientY
    startRight = right.value
    startBottom = bottom.value
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
  }

  const wasDragged = () => moved
  const resetRight = () => { right.value = defaultRight }

  onBeforeUnmount(() => {
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
  })

  return { right, bottom, dragging, onPointerDown, wasDragged, resetRight }
}
