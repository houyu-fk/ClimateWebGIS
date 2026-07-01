<template>
  <div class="app-wrapper">
    <div class="sidebar">
      <div class="sidebar-logo"><h2>ClimateWebGIS</h2><p>气象数据可视化平台</p></div>
      <div class="sidebar-menu">
        <el-button class="menu-btn" type="primary" plain @click="openStatsDrawer">📊 气温数据统计</el-button>
        <el-button class="menu-btn" :type="isHeatmapActive ? 'warning' : 'info'" plain @click="toggleHeatmap">
          {{ isHeatmapActive ? '🔴 关闭热力分布' : '🔥 开启热力分布' }}
        </el-button>
        <el-button class="menu-btn" type="success" plain @click="openFeedbackDialog">💬 系统评价与反馈</el-button>
        <el-divider border-style="dashed" />
        <el-button class="menu-btn" type="default" @click="openProfileDialog">👤 个人信息管理</el-button>

        <el-button class="menu-btn" type="success" plain @click="resetMapView" style="margin-top: 20px;">
          🗺️ 恢复全国视角
        </el-button>
      </div>
      <div class="sidebar-footer">
        <div>© 2026 Climate Project</div>
        <div style="margin-top: 5px; font-weight: bold; color: #909399;">制作者：HPQ、唐神</div>
      </div>
    </div>

    <div class="main-content">
      <div class="user-header">
        <div style="display: flex; align-items: center;">
          <el-select v-model="globalSearchQuery" filterable placeholder="🔍 搜索气象站名称或站号..." @change="handleGlobalSearch" style="width: 300px;" clearable>
            <el-option v-for="item in stationsList" :key="item.station_id" :label="`${item.station_name} (${item.station_id})`" :value="item.station_id" />
          </el-select>
        </div>
        <div style="margin-left: auto;">
          <span v-if="isLoggedIn">
            欢迎, {{ userProfile.nickname || username }} 
            <el-button type="success" size="small" style="margin-left: 10px;" @click="adminDrawerVisible = true">⚙️ 后台数据管理</el-button>
            <el-button type="danger" link style="margin-left: 10px;" @click="logout">退出</el-button>
          </span>
          <el-button v-else type="primary" size="small" @click="loginDialogVisible = true">登录 / 注册</el-button>
        </div>
      </div>

      <div id="map"></div>

      <div class="map-legend">
        <h4 style="margin: 0 0 8px 0; font-size: 14px; text-align: center;">2024年均气温 (°C)</h4>
        <div class="legend-item"><span class="color-box" style="background: #d73027;"></span> ≥ 20 (非常热)</div>
        <div class="legend-item"><span class="color-box" style="background: #fc8d59;"></span> 15 ~ 20 (温暖)</div>
        <div class="legend-item"><span class="color-box" style="background: #fee090;"></span> 10 ~ 15 (舒适)</div>
        <div class="legend-item"><span class="color-box" style="background: #e0f3f8;"></span> 5 ~ 10 (微凉)</div>
        <div class="legend-item"><span class="color-box" style="background: #91bfdb;"></span> 0 ~ 5 (寒冷)</div>
        <div class="legend-item"><span class="color-box" style="background: #4575b4;"></span> &lt; 0 (严寒)</div>
        <div class="legend-item"><span class="color-box" style="background: #808080;"></span> 暂无数据</div>
      </div>
    </div>

    <el-dialog v-model="profileDialogVisible" title="个人信息中心" width="500px">
      <div v-if="isLoggedIn">
        <div style="text-align: center; margin-bottom: 20px;">
          <el-avatar :size="70" style="background: #409EFF; font-size: 24px;">
            {{ (userProfile.nickname || username).charAt(0).toUpperCase() }}
          </el-avatar>
          <h3 style="margin: 10px 0 0 0;">{{ userProfile.nickname || username }}</h3>
          <span style="color: #999; font-size: 12px;">登录账号: {{ username }}</span>
        </div>
        
        <el-form :model="userProfile" label-width="80px" size="default">
          <el-form-item label="昵称">
            <el-input v-model="userProfile.nickname" placeholder="请输入昵称" />
          </el-form-item>
          <el-form-item label="性别">
            <el-radio-group v-model="userProfile.gender">
              <el-radio label="男">男</el-radio>
              <el-radio label="女">女</el-radio>
              <el-radio label="保密">保密</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="年龄">
            <el-input-number v-model="userProfile.age" :min="1" :max="120" />
          </el-form-item>
          <el-form-item label="出生年月">
            <el-date-picker v-model="userProfile.birth_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item label="所在地">
            <el-input v-model="userProfile.location" placeholder="如：江苏省南京市" />
          </el-form-item>
          <el-divider border-style="dashed" />
          <el-form-item label="修改密码">
            <el-input v-model="userProfile.new_password" type="password" placeholder="不修改请留空" show-password />
          </el-form-item>
        </el-form>
      </div>
      <div v-else style="text-align: center; padding: 40px 20px;">
        <p style="color: #666; margin-bottom: 15px;">请先登录以查看和修改个人信息</p>
        <el-button type="primary" @click="profileDialogVisible = false; loginDialogVisible = true">去登录</el-button>
      </div>
      <template #footer v-if="isLoggedIn">
        <el-button @click="profileDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveUserProfile">保存修改</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="statsDrawerVisible" title="全国气象站点气温统计分析" direction="ltr" size="45%" @opened="renderStatsChart">
      <div style="padding: 10px;">
        <div ref="statsChartDom" style="width: 100%; height: 500px;"></div>
      </div>
    </el-drawer>

    <el-drawer v-model="adminDrawerVisible" title="站点数据管理中心" size="55%">
      <div style="margin-bottom: 15px; display: flex; align-items: center;">
        <el-button type="primary" @click="openAddStation"> + 新增站点</el-button>
        <el-input v-model="adminSearchQuery" placeholder="输入站名或站号快速过滤..." style="width: 250px; margin-left: 20px;" clearable />
        <span style="color: #999; font-size: 13px; margin-left: auto;">共找到 {{ filteredStationsList.length }} 个站点</span>
      </div>
      <el-table :data="filteredStationsList" height="calc(100vh - 120px)" stripe border>
        <el-table-column prop="station_id" label="站号" width="90" />
        <el-table-column prop="station_name" label="站名" width="120" />
        <el-table-column prop="province" label="省份" width="100" />
        <el-table-column prop="avg_temp" label="年均温(°C)" width="100">
          <template #default="scope">{{ scope.row.avg_temp !== null ? scope.row.avg_temp : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="160">
          <template #default="scope">
            <el-button size="small" @click="openEditStation(scope.row)">编辑</el-button>
            <el-popconfirm title="确定要删除该站点吗？" @confirm="handleDeleteStation(scope.row.station_id)">
              <template #reference><el-button size="small" type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>

    <el-dialog v-model="stationFormVisible" :title="isEditMode ? '编辑站点' : '新增气象站点'" width="450px">
      <el-form :model="stationForm" label-width="80px">
        <el-form-item label="站号"><el-input v-model="stationForm.station_id" :disabled="isEditMode" /></el-form-item>
        <el-form-item label="站名"><el-input v-model="stationForm.station_name" /></el-form-item>
        <el-form-item label="省份"><el-input v-model="stationForm.province" /></el-form-item>
        <el-form-item label="海拔"><el-input v-model="stationForm.elevation_sensor" type="number" /></el-form-item>
        <el-form-item label="纬度"><el-input v-model="stationForm.lat" type="number" /></el-form-item>
        <el-form-item label="经度"><el-input v-model="stationForm.lon" type="number" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="stationFormVisible = false">取消</el-button><el-button type="primary" @click="submitStationForm">保存提交</el-button></template>
    </el-dialog>

    <el-dialog v-model="loginDialogVisible" title="用户登录" width="400px">
      <el-form :model="userForm" label-width="60px">
        <el-form-item label="账号"><el-input v-model="userForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="userForm.password" type="password" show-password /></el-form-item>
      </el-form>
      <template #footer><el-button @click="handleRegister">注 册</el-button><el-button type="primary" @click="handleLogin">登 录</el-button></template>
    </el-dialog>

    <el-dialog v-model="dialogVisible" :title="`${currentStationName} (${currentStationId})`" width="70%" destroy-on-close>
      <div style="margin-bottom: 15px; display: flex; align-items: center;">
        <span style="margin-right: 10px;">选择年份:</span>
        <el-select v-model="selectedYear" @change="fetchWeatherData" style="width: 120px;">
          <el-option label="2023年" :value="2023" />
          <el-option label="2024年" :value="2024" />
          <el-option label="2025年" :value="2025" />
        </el-select>
      </div>
      <div v-loading="loading">
        <WeatherChart 
          v-if="!loading && currentWeatherData.times.length > 0" 
          :weatherData="currentWeatherData" 
          :year="selectedYear"
          :province="currentProvince"
          :stationName="currentStationName"
        />
        <el-empty v-if="!loading && currentWeatherData.times.length === 0" description="暂无观测数据" />
      </div>
      <el-divider>该站点的天气评价</el-divider>
      <div class="evaluation-list" style="max-height: 200px; overflow-y: auto; margin-bottom: 20px;">
        <div v-for="(item, index) in evaluations" :key="index" class="eval-item">
          <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <strong>{{ item.username }}</strong><span style="color: #999; font-size: 12px;">{{ item.time }}</span>
          </div>
          <el-rate v-model="item.rating" disabled show-score text-color="#ff9900" />
          <p style="margin: 5px 0 0 0;">{{ item.text }}</p>
        </div>
      </div>
      <div v-if="isLoggedIn" class="evaluation-form">
        <el-rate v-model="newEval.rating" />
        <el-input v-model="newEval.text" type="textarea" placeholder="你觉得这里的天气怎么样？" style="margin-top: 10px;" />
        <el-button type="primary" style="margin-top: 10px; width: 100%;" @click="submitEvaluation">发布评价</el-button>
      </div>
    </el-dialog>

    <el-dialog v-model="feedbackDialogVisible" title="系统评价与反馈" width="500px">
      <el-tabs v-model="activeFeedbackTab">
        <el-tab-pane label="大家的评价" name="list">
          <div class="evaluation-list" style="max-height: 300px; overflow-y: auto; padding-right: 10px;">
            <div v-for="(item, index) in sysEvaluations" :key="index" class="eval-item">
              <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <strong>{{ item.username }}</strong><span style="color: #999; font-size: 12px;">{{ item.time }}</span>
              </div>
              <el-rate v-model="item.rating" disabled show-score text-color="#ff9900" size="small" />
              <p style="margin: 5px 0 0 0; font-size: 14px;">{{ item.text }}</p>
            </div>
          </div>
        </el-tab-pane>
        <el-tab-pane label="我要评价" name="submit">
          <div v-if="isLoggedIn" style="padding: 10px 0;">
            <el-rate v-model="sysFeedback.rating" size="large" />
            <el-input v-model="sysFeedback.text" type="textarea" :rows="4" placeholder="优化建议..." style="margin-top: 15px;" />
            <el-button type="primary" style="margin-top: 20px; width: 100%;" @click="submitSysFeedback">提交反馈</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts' 
import WeatherChart from './components/WeatherChart.vue'

// ================= 全局状态 =================

let mapInstance = null;
let stationLayer = null;
let heatLayer = null; 
let provinceLayer = null; 
let cityLayer = null; // 市级边界图层

let isNavigating = false;


let highlightedLayer = null;   // 用于高亮管理
const currentMapLevel = ref('nation');   // 原始声明
const allCityData = ref(null);           // 原始声明（或 const allCityData = ref([]) 等）
const isLoggedIn = ref(false)
const username = ref('')
const token = ref('')
const loginDialogVisible = ref(false)
const userForm = ref({ username: '', password: '' })

// ================= 个人信息管理状态与逻辑 =================
const profileDialogVisible = ref(false)
const userProfile = ref({
  nickname: '', gender: '', age: null, location: '', birth_date: '', new_password: ''
})

const openProfileDialog = async () => {
  profileDialogVisible.value = true;
  if (isLoggedIn.value) {
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/user/profile', {
        headers: { Authorization: `Bearer ${token.value}` }
      });
      userProfile.value = { ...res.data, new_password: '' };
    } catch (e) {
      console.error("获取个人信息失败", e);
    }
  }
}

const saveUserProfile = async () => {
  try {
    await axios.put('http://127.0.0.1:8000/api/user/profile', userProfile.value, {
      headers: { Authorization: `Bearer ${token.value}` }
    });
    ElMessage.success("个人信息已保存！");
    profileDialogVisible.value = false;
    if (userProfile.value.new_password) {
      ElMessage.warning("密码已修改，请重新登录");
      logout();
    }
  } catch (e) {
    ElMessage.error("保存失败，请重试");
  }
}

const defaultStyle = {
  color: '#409EFF',
  weight: 1,
  fillColor: '#f2f6fc',
  fillOpacity: 0.1,
  dashArray: '3'
};

const hoverStyle = {
  weight: 2,
  fillColor: '#67C23A',
  fillOpacity: 0.4
};
const handleHighlight = (layer, isHover) => {
  if (isHover) {
    // 清除上一个高亮
    if (highlightedLayer && highlightedLayer !== layer) {
      highlightedLayer.setStyle(defaultStyle);
    }
    layer.setStyle(hoverStyle);
    layer.bringToFront();
    highlightedLayer = layer;
  } else {
    if (highlightedLayer === layer) {
      layer.setStyle(defaultStyle);
      highlightedLayer = null;
    }
  }
};
// ================= 省级加载 =================
const loadProvincePolygons = async () => {
  try {
    const res = await axios.get('/province.json');
    provinceLayer = L.geoJSON(res.data, {
      style: defaultStyle,
      onEachFeature: (feature, layer) => {
        const provinceName = feature.properties.name || feature.properties.NAME;
        if (provinceName) {
          layer.bindTooltip(provinceName, { sticky: true, direction: 'auto' });
        }
        layer.on({
          mouseover: () => handleHighlight(layer, true),
          mouseout: () => handleHighlight(layer, false),
          click: () => {
            // 清除高亮
            if (highlightedLayer) {
              highlightedLayer.setStyle(defaultStyle);
              highlightedLayer = null;
            }
            const adcode = feature.properties.adcode || feature.properties.ADCODE;
            if (adcode) {
              // 先飞入省级范围，再加载市级
              if (layer.getBounds && layer.getBounds().isValid()) {
                mapInstance.flyToBounds(layer.getBounds(), { padding: [50, 50], duration: 1.2 });
              }
              loadCityPolygons(adcode, provinceName);
            } else {
              ElMessage.error('该省份缺少 adcode，无法下钻');
            }
          }
        });
      }
    });
    provinceLayer.addTo(mapInstance);
  } catch (error) {
    console.error('加载省级边界失败:', error);
    ElMessage.error('省级边界加载失败，请检查 province.json');
  }
};
// ================= 市级加载（优化版） =================
const loadCityPolygons = async (provinceAdcode, provinceName) => {
  try {
    // 使用 allCityData.value
    if (!allCityData.value) {
      const res = await axios.get('/city.json');
      allCityData.value = res.data;
    }

    const adcodeStr = String(provinceAdcode);
    const provincePrefix = adcodeStr.substring(0, 2);

    const filteredFeatures = allCityData.value.features.filter(feature => {
      const cityAdcode = String(feature.properties.adcode || feature.properties.ADCODE || '');
      return cityAdcode.startsWith(provincePrefix) && cityAdcode !== adcodeStr;
    });

    if (filteredFeatures.length === 0) {
      ElMessage.info(`${provinceName} 为直辖市或暂无市级划分，已为您放大省级视角`);
      if (provinceLayer && mapInstance.hasLayer(provinceLayer)) {
        mapInstance.flyToBounds(provinceLayer.getBounds(), { padding: [50, 50], duration: 1.2 });
      }
      return;
    }

    // 移除省级图层
    if (provinceLayer && mapInstance.hasLayer(provinceLayer)) {
      mapInstance.removeLayer(provinceLayer);
    }
    if (cityLayer && mapInstance.hasLayer(cityLayer)) {
      mapInstance.removeLayer(cityLayer);
      cityLayer = null;
    }

    const cityGeoJSON = {
      type: 'FeatureCollection',
      features: filteredFeatures
    };

    cityLayer = L.geoJSON(cityGeoJSON, {
      style: defaultStyle,
      interactive: true,
      onEachFeature: (feature, layer) => {
        const cityName = feature.properties.name || feature.properties.NAME || '未知市';
        layer.bindTooltip(cityName, { sticky: true, direction: 'auto' });

        layer.on({
          mouseover: () => handleHighlight(layer, true),
          mouseout: () => handleHighlight(layer, false),
          click: () => {
            if (highlightedLayer) {
              highlightedLayer.setStyle(defaultStyle);
              highlightedLayer = null;
            }
            currentMapLevel.value = 'city';
            ElMessage.success(`当前区域：${cityName}`);
            if (layer.getBounds && layer.getBounds().isValid()) {
              mapInstance.flyToBounds(layer.getBounds(), { padding: [50, 50], duration: 1.2 });
            }
          }
        });
      }
    });

    cityLayer.addTo(mapInstance);
    currentMapLevel.value = 'province';

    // 确保站点图层存在
    if (stationLayer) {
      if (!mapInstance.hasLayer(stationLayer)) {
        mapInstance.addLayer(stationLayer);
      }
      stationLayer.bringToFront();
    } else {
      loadStationsAndMap();
    }

    if (cityLayer.getBounds && cityLayer.getBounds().isValid()) {
      mapInstance.flyToBounds(cityLayer.getBounds(), { padding: [50, 50], duration: 1.2 });
    }

  } catch (error) {
    console.error('加载市级数据失败:', error);
    ElMessage.error('无法加载市级边界，请检查 city.json 文件');
  }
};

const resetMapView = () => {
  // 1. 清除高亮效果
  if (highlightedLayer) {
    highlightedLayer.setStyle(defaultStyle);
    highlightedLayer = null;
  }

  // 2. 移除市级图层（如果存在）
  if (cityLayer && mapInstance.hasLayer(cityLayer)) {
    mapInstance.removeLayer(cityLayer);
    cityLayer = null;
  }

  // 3. 确保省级图层已加载并显示
  if (!provinceLayer) {
    // 未加载过，重新加载
    loadProvincePolygons();
  } else if (!mapInstance.hasLayer(provinceLayer)) {
    // 已加载但被移除（例如进入市级时被移除），重新添加
    mapInstance.addLayer(provinceLayer);
  } else {
    // 已存在且在地图上，提到最前
    provinceLayer.bringToFront();
  }

  // 4. 重置地图视角到全国（中心点 35.86°N, 104.19°E，缩放级别 4）
  mapInstance.flyTo([35.86, 104.19], 4, { duration: 1.2 });

  // 5. 确保站点图层处于最上层（避免被省级图层遮挡）
  if (stationLayer && mapInstance.hasLayer(stationLayer)) {
    stationLayer.bringToFront();
  }
};
// ================= 其他原有逻辑保留 =================
const globalSearchQuery = ref('') 
const adminSearchQuery = ref('')  
const adminDrawerVisible = ref(false)
const stationsList = ref([]) 
const stationFormVisible = ref(false)
const isEditMode = ref(false)
const stationForm = ref({ station_id: '', station_name: '', province: '', elevation_sensor: 0, lat: 0, lon: 0 })

const filteredStationsList = computed(() => {
  if (!adminSearchQuery.value) return stationsList.value;
  const keyword = adminSearchQuery.value.toLowerCase();
  return stationsList.value.filter(station => station.station_name.toLowerCase().includes(keyword) || station.station_id.toString().includes(keyword));
});

const statsDrawerVisible = ref(false)
const statsChartDom = ref(null)
let statsChart = null
const openStatsDrawer = () => { statsDrawerVisible.value = true; }
const renderStatsChart = () => {
  if (!statsChartDom.value) return;
  if (!statsChart) statsChart = echarts.init(statsChartDom.value);
  const ranges = { '< 0°C': 0, '0~5°C': 0, '5~10°C': 0, '10~15°C': 0, '15~20°C': 0, '≥ 20°C': 0 };
  stationsList.value.forEach(s => {
    const t = s.avg_temp;
    if (t === null || t === undefined) return;
    if (t < 0) ranges['< 0°C']++; else if (t < 5) ranges['0~5°C']++; else if (t < 10) ranges['5~10°C']++; else if (t < 15) ranges['10~15°C']++; else if (t < 20) ranges['15~20°C']++; else ranges['≥ 20°C']++;
  });
  statsChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: Object.keys(ranges), axisLabel: { interval: 0 } },
    yAxis: { type: 'value', name: '站点数量 (个)' },
    series: [{ name: '站点数', type: 'bar', barWidth: '50%', data: Object.values(ranges), label: { show: true, position: 'top' }, itemStyle: { color: (params) => ['#4575b4', '#91bfdb', '#e0f3f8', '#fee090', '#fc8d59', '#d73027'][params.dataIndex] } }]
  });
}

const isHeatmapActive = ref(false)
const toggleHeatmap = () => {
  isHeatmapActive.value = !isHeatmapActive.value;
  if (isHeatmapActive.value) {
    if (stationLayer && mapInstance.hasLayer(stationLayer)) {
      mapInstance.removeLayer(stationLayer);
    }
    if (!heatLayer) {
      // ... 创建热力图代码不变 ...
    }
    heatLayer.addTo(mapInstance);
  } else {
    if (heatLayer && mapInstance.hasLayer(heatLayer)) {
      mapInstance.removeLayer(heatLayer);
    }
    if (stationLayer && !mapInstance.hasLayer(stationLayer)) {
      stationLayer.addTo(mapInstance);
      stationLayer.bringToFront();   // 关键！
    }
  }
};

const handleGlobalSearch = (selectedStationId) => {
  if (!selectedStationId) return;
  const targetStation = stationsList.value.find(s => s.station_id === selectedStationId);
  if (targetStation) {
    if (isHeatmapActive.value) toggleHeatmap(); 
    mapInstance.flyTo([targetStation.lat, targetStation.lon], 10, { animate: true, duration: 1.5 });
    currentProvince.value = targetStation.province;
    currentStationName.value = targetStation.station_name; currentStationId.value = targetStation.station_id; selectedYear.value = 2024; dialogVisible.value = true;
    fetchWeatherData(); fetchEvaluations(); globalSearchQuery.value = ''; 
  }
}

const getTempColor = (temp) => {
  if (temp === null || temp === undefined) return '#808080'; 
  if (temp >= 20) return '#d73027'; if (temp >= 15) return '#fc8d59'; if (temp >= 10) return '#fee090'; if (temp >= 5)  return '#e0f3f8'; if (temp >= 0)  return '#91bfdb'; return '#4575b4';                 
}

// ================= 完美修复：加载本地省份面要素并实现防弹级交互 =================
// 1. 单独定义标准样式和高亮样式，防止丢失




// ================= 新增：重置视角函数 =================


const loadStationsAndMap = async () => {
  try {
    const res = await axios.get('http://127.0.0.1:8000/api/stations');
    stationsList.value = res.data.features.map(f => ({
      station_id: f.properties.station_id,
      station_name: f.properties.station_name,
      province: f.properties.province,
      elevation_sensor: f.properties.elevation,
      avg_temp: f.properties.avg_temp,
      lon: f.geometry.coordinates[0],
      lat: f.geometry.coordinates[1]
    }));

    if (stationLayer && mapInstance.hasLayer(stationLayer)) {
      mapInstance.removeLayer(stationLayer);
    }

    stationLayer = L.geoJSON(res.data, {
      pointToLayer: (feature, latlng) => {
        return L.circleMarker(latlng, {
          radius: 6,               
          fillColor: getTempColor(feature.properties.avg_temp),
          color: '#fff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.9,
          interactive: true,
          className: 'station-marker'     // 方便调试样式
        });
      },
      pane: 'stations',
      onEachFeature: (feature, layer) => {
        layer.bindTooltip(`<b>${feature.properties.province} - ${feature.properties.station_name}</b><br/>2024年均温: ${feature.properties.avg_temp !== null ? feature.properties.avg_temp + ' °C' : '无数据'}`);

        layer.on('click', (e) => {
          // 阻止事件继续传播到城市/省级图层
          if (e.originalEvent) {
            e.originalEvent.stopPropagation();
            e.originalEvent.preventDefault();
          }
          // 阻止 Leaflet 默认传播
          L.DomEvent.stopPropagation(e);

          currentProvince.value = feature.properties.province;
          currentStationName.value = feature.properties.station_name;
          currentStationId.value = feature.properties.station_id;
          selectedYear.value = 2024;
          dialogVisible.value = true;
          fetchWeatherData();
          fetchEvaluations();
        });
      }
    });

    // 无论热力图状态，先添加图层（后续由 toggle 控制显隐）
    if (!isHeatmapActive.value) {
      stationLayer.addTo(mapInstance);
      // 立即置于最前
      stationLayer.bringToFront();
    } else {
      // 若热力图开启，暂不添加，由 toggle 控制
    }

    // 关键：监听地图移动/缩放，始终将站点图层提到最前
    mapInstance.on('zoomend moveend', () => {
      if (stationLayer && mapInstance.hasLayer(stationLayer)) {
        stationLayer.bringToFront();
      }
    });

  } catch (error) {
    console.error('加载站点失败', error);
  }
};
onMounted(async () => {
  const savedToken = localStorage.getItem('gis_token'); const savedUser = localStorage.getItem('gis_user')
  if (savedToken && savedUser) { token.value = savedToken; username.value = savedUser; isLoggedIn.value = true; openProfileDialog(); profileDialogVisible.value = false; } 
  
  window.L = L; await import('leaflet.heat');

  mapInstance = L.map('map').setView([35.86, 104.19], 4);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
  }).addTo(mapInstance);

  // 创建自定义 pane 用于站点（早于加载站点）
  mapInstance.createPane('stations');
  mapInstance.getPane('stations').style.zIndex = 1000;

  // 加载省级边界
  await loadProvincePolygons();

  // 加载站点
  await loadStationsAndMap();

  // 窗口 resize 处理
  window.addEventListener('resize', () => {
    if (statsChart) statsChart.resize();
  });
});

const openAddStation = () => { isEditMode.value = false; stationForm.value = { station_id: '', station_name: '', province: '', elevation_sensor: 0, lat: 0, lon: 0 }; stationFormVisible.value = true }
const openEditStation = (row) => { isEditMode.value = true; stationForm.value = { ...row }; stationFormVisible.value = true }
const submitStationForm = async () => { try { const config = { headers: { Authorization: `Bearer ${token.value}` } }; if (isEditMode.value) { await axios.put(`http://127.0.0.1:8000/api/admin/stations/${stationForm.value.station_id}`, stationForm.value, config); ElMessage.success("修改成功！") } else { await axios.post('http://127.0.0.1:8000/api/admin/stations', stationForm.value, config); ElMessage.success("新增成功！") }; stationFormVisible.value = false; loadStationsAndMap() } catch (e) { ElMessage.error("操作失败，请登录") } }
const handleDeleteStation = async (id) => { try { await axios.delete(`http://127.0.0.1:8000/api/admin/stations/${id}`, { headers: { Authorization: `Bearer ${token.value}` } }); ElMessage.success("站点已删除"); loadStationsAndMap() } catch (e) { ElMessage.error("删除失败") } }
const handleRegister = async () => { try { await axios.post('http://127.0.0.1:8000/api/auth/register', userForm.value); ElMessage.success("注册成功！请登录") } catch (e) {} }
const handleLogin = async () => { try { const res = await axios.post('http://127.0.0.1:8000/api/auth/login', userForm.value); token.value = res.data.access_token; username.value = res.data.username; isLoggedIn.value = true; localStorage.setItem('gis_token', token.value); localStorage.setItem('gis_user', username.value); loginDialogVisible.value = false; ElMessage.success("登录成功"); openProfileDialog(); profileDialogVisible.value = false; } catch (e) {} }
const logout = () => { isLoggedIn.value = false; token.value = ''; username.value = ''; userProfile.value = {}; localStorage.clear(); ElMessage.info("已退出") }
const dialogVisible = ref(false); const loading = ref(false); const currentStationName = ref(''); const currentProvince = ref(''); const currentStationId = ref(''); const selectedYear = ref(2024); const currentWeatherData = ref({ times: [], temps: [] }); const evaluations = ref([]); const newEval = ref({ rating: 5, text: '' })
const fetchWeatherData = async () => { loading.value = true; try { const weatherRes = await axios.get(`http://127.0.0.1:8000/api/weather/${currentStationId.value}?year=${selectedYear.value}`); currentWeatherData.value = { times: weatherRes.data.times, temps: weatherRes.data.temps }; } catch (e) { currentWeatherData.value = { times: [], temps: [] }; } finally { loading.value = false; } }
const fetchEvaluations = async () => { try { const res = await axios.get(`http://127.0.0.1:8000/api/evaluations/${currentStationId.value}`); evaluations.value = res.data } catch (e) { } }
const submitEvaluation = async () => { try { await axios.post('http://127.0.0.1:8000/api/evaluations', { station_id: currentStationId.value, rating: newEval.value.rating, evaluation_text: newEval.value.text }, { headers: { Authorization: `Bearer ${token.value}` } }); ElMessage.success("发布成功！"); newEval.value.text = ''; fetchEvaluations() } catch (e) {} }
const feedbackDialogVisible = ref(false); const activeFeedbackTab = ref('list'); const sysEvaluations = ref([]); const sysFeedback = ref({ rating: 5, text: '' })
const openFeedbackDialog = () => { feedbackDialogVisible.value = true; activeFeedbackTab.value = 'list'; fetchSysEvaluations() }
const fetchSysEvaluations = async () => { try { const res = await axios.get('http://127.0.0.1:8000/api/feedback'); sysEvaluations.value = res.data } catch (e) {} }
const submitSysFeedback = async () => { try { await axios.post('http://127.0.0.1:8000/api/feedback', { rating: sysFeedback.value.rating, feedback_text: sysFeedback.value.text }, { headers: { Authorization: `Bearer ${token.value}` } }); ElMessage.success("提交成功"); sysFeedback.value.text = ''; activeFeedbackTab.value = 'list'; fetchSysEvaluations() } catch (e) {} }
</script>

<style>
html, body { margin: 0; padding: 0; width: 100%; height: 100%; background: #f0f2f5; }
.app-wrapper { display: flex; height: 100vh; width: 100vw; overflow: hidden; }

.sidebar { width: 260px; background-color: #ffffff; box-shadow: 2px 0 10px rgba(0,0,0,0.08); z-index: 1000; display: flex; flex-direction: column; }
.sidebar-logo { padding: 30px 20px; text-align: center; border-bottom: 1px solid #f0f0f0; }
.sidebar-logo h2 { margin: 0; color: #409EFF; font-size: 24px; }
.sidebar-logo p { margin: 5px 0 0; color: #999; font-size: 13px; }
.sidebar-menu { flex: 1; padding: 20px 15px; display: flex; flex-direction: column; gap: 15px; }
.menu-btn { width: 100%; height: 45px; font-size: 15px; margin-left: 0 !important; justify-content: flex-start; padding-left: 20px; }
.sidebar-footer { padding: 15px; text-align: center; color: #c0c4cc; font-size: 12px; border-top: 1px solid #f0f0f0; }

.main-content { flex: 1; position: relative; display: flex; flex-direction: column; }
.user-header { height: 60px; background: rgba(255, 255, 255, 0.95); padding: 0 20px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); z-index: 999; display: flex; align-items: center; }
#map { flex: 1; width: 100%; z-index: 1; }

.map-legend { position: absolute; bottom: 30px; right: 20px; z-index: 999; background: rgba(255, 255, 255, 0.9); padding: 12px 18px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); font-size: 13px; color: #333; }
.legend-item { display: flex; align-items: center; margin-bottom: 6px; }
.legend-item:last-child { margin-bottom: 0; }
.color-box { width: 16px; height: 16px; display: inline-block; margin-right: 10px; border: 1px solid #b4b4b4; border-radius: 3px; }
.eval-item { padding: 10px; border-bottom: 1px solid #ebeef5; background: #f9fafc; border-radius: 4px; margin-bottom: 8px; }
.eval-item:last-child { border-bottom: none; }
</style>