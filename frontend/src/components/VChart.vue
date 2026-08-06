<template>
  <div ref="el" :style="{ width, height }"></div>
</template>

<script setup>
import * as echarts from 'echarts/core'
import { GraphChart, LineChart, PieChart, RadarChart } from 'echarts/charts'
import {
  GridComponent, LegendComponent, RadarComponent, TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

echarts.use([LineChart, PieChart, GraphChart, RadarChart, GridComponent, LegendComponent, RadarComponent, TooltipComponent, CanvasRenderer])

const props = defineProps({
  option: { type: Object, required: true },
  width: { type: String, default: '100%' },
  height: { type: String, default: '320px' },
})
const emit = defineEmits(['click'])

const el = ref(null)
let chart = null
let observer = null

onMounted(() => {
  chart = echarts.init(el.value)
  chart.setOption(props.option)
  chart.on('click', (params) => emit('click', params))
  observer = new ResizeObserver(() => chart && chart.resize())
  observer.observe(el.value)
})

watch(() => props.option, (opt) => chart && chart.setOption(opt, true), { deep: true })

onBeforeUnmount(() => {
  observer && observer.disconnect()
  chart && chart.dispose()
})
</script>
