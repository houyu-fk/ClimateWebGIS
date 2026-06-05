<template>
  <div ref="chartDom" class="chart-container"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  weatherData: { type: Object, default: () => ({ times: [], temps: [] }) },
  // 新增：接收从 App.vue 传来的年份、省份、站名
  year: { type: [Number, String], default: '' },
  province: { type: String, default: '' },
  stationName: { type: String, default: '' }
})

const chartDom = ref(null)
let myChart = null

const initChart = () => {
  if (chartDom.value) {
    if (myChart != null && myChart !== "" && myChart !== undefined) { myChart.dispose(); }
    myChart = echarts.init(chartDom.value)
    updateChart()
  }
}

const updateChart = () => {
  if (!myChart) return

  // 动态拼接标题字符串
  const dynamicTitle = props.province && props.stationName 
    ? `${props.year}年 ${props.province}-${props.stationName} 年度气温变化趋势`
    : '年度气温变化趋势';

  const option = {
    title: { 
      text: dynamicTitle, // 使用动态标题
      left: 'center' 
    },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    toolbox: { 
      feature: { 
        dataZoom: { yAxisIndex: 'none' }, 
        restore: {}, 
        // 导出图片配置：ECharts 会自动使用 title.text 作为下载的文件名
        saveAsImage: { pixelRatio: 2 } // pixelRatio: 2 可以让导出的图片更高清
      } 
    },
    xAxis: {
      type: 'category', boundaryGap: false, data: props.weatherData.times,
      axisLabel: { formatter: function (value) { return value ? value.substring(5, 10) : ''; } }
    },
    yAxis: { type: 'value', name: '气温 (°C)', axisLabel: { formatter: '{value} °C' } },
    dataZoom: [ { type: 'inside', start: 0, end: 100 }, { start: 0, end: 100 } ],
    visualMap: {
      show: false,
      type: 'continuous',
      dimension: 1, 
      min: -20,
      max: 40,
      inRange: {
        color: ['#313695', '#74add1', '#e0f3f8', '#fdae61', '#f46d43', '#a50026']
      }
    },
    series: [
      {
        name: '气温',
        type: 'line',
        smooth: true, 
        symbol: 'none', 
        sampling: 'lttb',
        areaStyle: { opacity: 0.6 },
        lineStyle: { width: 2 },
        data: props.weatherData.temps
      }
    ]
  }
  myChart.setOption(option, true)
}

// 深度监听所有相关的 props 变化，只要年份、站点或数据变了，就重绘图表
watch(
  () => [props.weatherData, props.year, props.province, props.stationName], 
  () => { updateChart() }, 
  { deep: true }
)

onMounted(() => { initChart(); window.addEventListener('resize', () => myChart && myChart.resize()) })
onUnmounted(() => { window.removeEventListener('resize', () => myChart && myChart.resize()); if (myChart) myChart.dispose() })
</script>

<style scoped>
.chart-container {
  width: 100%;
  height: 400px;
}
</style>