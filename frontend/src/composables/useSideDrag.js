import { onBeforeUnmount, ref } from 'vue'

/**
 * 沿屏幕侧边垂直拖拽（用于悬浮组件），位置持久化到 localStorage。
 * - bottom: 距视口底部的像素偏移（响应式）
 * - onPointerDown: 绑到拖拽手柄的 @pointerdown
 * - wasDragged: 最近一次按下-抬起是否发生了拖拽（用于区分点击/拖拽）
 * - reclamp: 外部状态变化（如面板展开）后重新收敛到合法区间
 * @param getMaxBottom 可选，返回当前允许的最大 bottom（随面板展开收紧，避免顶部溢出）
 */
export function useSideDrag(storageKey, defaultBottom = 20, getMaxBottom = null) {
  const bottom = ref(defaultBottom)
  const dragging = ref(false)
  let startY = 0
  let startBottom = 0
  let moved = false

  const clampMax = () => (getMaxBottom
    ? Math.max(8, getMaxBottom())
    : Math.max(8, (window.innerHeight || 800) - 70))
  const clamp = (v) => Math.min(Math.max(8, v), clampMax())

  try {
    const saved = localStorage.getItem(storageKey)
    if (saved !== null) {
      const v = parseInt(saved, 10)
      if (!Number.isNaN(v)) bottom.value = clamp(v)
    }
  } catch { /* ignore */ }

  function onPointerMove(e) {
    if (!dragging.value) return
    const dy = startY - e.clientY
    if (Math.abs(dy) > 4) moved = true
    bottom.value = clamp(startBottom + dy)
  }

  function onPointerUp() {
    dragging.value = false
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
    try { localStorage.setItem(storageKey, String(bottom.value)) } catch { /* ignore */ }
  }

  function onPointerDown(e) {
    // 手柄内的交互控件（缩放/关闭/输入等，带 .no-drag）不触发拖拽；
    // 注意：收起手柄本身就是 button，不能用 closest('button') 排除
    if (e.target.closest('.no-drag, input, select, textarea, a')) return
    dragging.value = true
    moved = false
    startY = e.clientY
    startBottom = bottom.value
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
    // 不调用 preventDefault，避免部分浏览器抑制随后的 click（点击展开仍走 click）
  }

  const wasDragged = () => moved
  const reclamp = () => { bottom.value = clamp(bottom.value) }

  onBeforeUnmount(() => {
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
  })

  return { bottom, dragging, onPointerDown, wasDragged, reclamp }
}
