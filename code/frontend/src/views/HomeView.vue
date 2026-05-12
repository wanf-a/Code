<template>
  <MainLayout>
    <div class="page-header">
      <h1 class="page-title">预测结果</h1>
      <div class="header-actions">
        <div class="filter-group">
          <label>数据集选择</label>
          <select class="input">
            <option>广东电价数据</option>
          </select>
        </div>
        <div class="filter-group">
          <label>类型选择</label>
          <select class="input">
            <option>周前概率</option>
          </select>
        </div>
        <div class="filter-group">
          <label>日期选择</label>
          <input v-model="selectedDate" type="date" class="input" @change="handleDateChange" />
        </div>
        <div class="filter-group">
          <label>模型选择</label>
          <select v-model="selectedModel" class="input">
            <option value="ensemble">集成周前</option>            
            <option value="nlinear">nlinear周前</option>
            <option value="mamba">mamba周前</option>
            <option value="tcn">tcn周前</option>
          </select>
        </div>
        <button class="btn primary" @click="handlePredict">预测</button>
      </div>
    </div>

    <div class="dashboard-grid">
      <section class="panel chart-panel">
        <div class="panel-header">
          <h3 class="panel-title">预测结果</h3>
          <button 
            class="btn sm primary" 
            @click="showMetrics = true"
            :disabled="!hasPredicted"
          >
            查看评价结果
          </button>
        </div>
        <div class="chart-container">
          <div class="chart-legend" v-if="hasPredicted">
            <template v-if="selectedModel !== 'tcn'">
              <span class="legend-item"><span class="line-solid blue"></span> 电价实际值</span>
              <span class="legend-item"><span class="line-dashed orange"></span> 点预测值(QR-0.5)</span>
              <span class="legend-item"><span class="square light-blue"></span> 95%概率区间</span>
              <span class="legend-item"><span class="square red"></span> 负荷</span>
            </template>
            <template v-else>
              <span class="legend-item"><span class="line-solid dark"></span> 真实值</span>
              <span class="legend-item"><span class="line-solid green"></span> 点预测值(QR-0.5)</span>
              <span class="legend-item"><span class="square light-blue"></span> 95%概率区间</span>
              <span class="legend-item"><span class="square red"></span> 负荷</span>
            </template>
          </div>
          <div v-if="hasPredicted && chartDataAvailable" class="carousel-wrapper">
            <!-- 轮播控制 -->
            <div class="carousel-header">
              <button class="carousel-btn" @click="prevDay">◀</button>
              <span class="carousel-title">{{ currentDayLabel }} (第 {{ currentDayIndex + 1 }}/{{ dailyChartData.length }} 天)</span>
              <button class="carousel-btn" @click="nextDay">▶</button>
            </div>
            <!-- 轮播指示器 -->
            <div class="carousel-indicators">
              <span 
                v-for="(day, idx) in dailyChartData" 
                :key="idx" 
                :class="['indicator', { active: idx === currentDayIndex }]"
                @click="currentDayIndex = idx"
              ></span>
            </div>
            <!-- 当天图表 - Mamba确定性预测 -->
            <div v-if="selectedModel !== 'tcn'" class="chart-with-axis">
              <div class="y-axis y-axis-left">
                <div class="y-axis-label">电价(元/kWh)</div>
                <div class="y-axis-ticks">
                  <span>{{ priceYAxisLabels[0] }}</span>
                  <span>{{ priceYAxisLabels[1] }}</span>
                  <span>{{ priceYAxisLabels[2] }}</span>
                  <span>{{ priceYAxisLabels[3] }}</span>
                </div>
              </div>
              <div class="chart-main">
                <svg viewBox="0 0 600 200" class="line-chart" preserveAspectRatio="none">
                  <line x1="0" y1="0.5" x2="600" y2="0.5" stroke="#f0f0f0" stroke-width="1"/>
                  <line x1="0" y1="66.6" x2="600" y2="66.6" stroke="#f0f0f0" stroke-width="1"/>
                  <line x1="0" y1="133.3" x2="600" y2="133.3" stroke="#f0f0f0" stroke-width="1"/>
                  <line x1="0" y1="200" x2="600" y2="200" stroke="#f0f0f0" stroke-width="1"/>
                  <polygon :points="currentDayBand95Points" fill="rgba(24,144,255,0.2)" stroke="none"/>
                  <polyline fill="none" stroke="#ff4d4f" stroke-width="2" :points="currentDayLoadPoints"/>
                  <polyline fill="none" stroke="#faad14" stroke-width="2" stroke-dasharray="6,3" :points="currentDayPredictedPoints"/>
                  <polyline fill="none" stroke="#1890ff" stroke-width="2" :points="currentDayActualPoints"/>
                </svg>
                <div class="chart-labels">
                  <span v-for="h in hourLabels" :key="h">{{ h }}</span>
                </div>
              </div>
              <div class="y-axis y-axis-right">
                <div class="y-axis-label">负荷 (kW)</div>
                <div class="y-axis-ticks">
                  <span>{{ loadYAxisLabels[0] }}</span>
                  <span>{{ loadYAxisLabels[1] }}</span>
                  <span>{{ loadYAxisLabels[2] }}</span>
                  <span>{{ loadYAxisLabels[3] }}</span>
                </div>
              </div>
            </div>
            <!-- 当天图表 - TCN概率预测 -->
            <div v-else class="chart-with-axis">
              <div class="y-axis y-axis-left">
                <div class="y-axis-label">电价(元/kWh)</div>
                <div class="y-axis-ticks">
                  <span>{{ tcnPriceYAxisLabels[0] }}</span>
                  <span>{{ tcnPriceYAxisLabels[1] }}</span>
                  <span>{{ tcnPriceYAxisLabels[2] }}</span>
                  <span>{{ tcnPriceYAxisLabels[3] }}</span>
                </div>
              </div>
              <div class="chart-main">
                <svg viewBox="0 0 600 200" class="line-chart" preserveAspectRatio="none">
                  <line x1="0" y1="0.5" x2="600" y2="0.5" stroke="#f0f0f0" stroke-width="1"/>
                  <line x1="0" y1="66.6" x2="600" y2="66.6" stroke="#f0f0f0" stroke-width="1"/>
                  <line x1="0" y1="133.3" x2="600" y2="133.3" stroke="#f0f0f0" stroke-width="1"/>
                  <line x1="0" y1="200" x2="600" y2="200" stroke="#f0f0f0" stroke-width="1"/>
                  <!-- 95%概率区间填充 -->
                  <polygon :points="tcnBand95Points" fill="rgba(24,144,255,0.2)" stroke="none"/>
                  <!-- 负荷 -->
                  <polyline fill="none" stroke="#ff4d4f" stroke-width="1.5" :points="tcnLoadPoints"/>
                  <!-- 点预测值 -->
                  <polyline fill="none" stroke="#52c41a" stroke-width="2" :points="tcnQr50Points"/>
                  <!-- 真实值 -->
                  <polyline fill="none" stroke="#333" stroke-width="2" :points="tcnRealPoints"/>
                </svg>
                <div class="chart-labels">
                  <span v-for="h in hourLabels" :key="h">{{ h }}</span>
                </div>
              </div>
              <div class="y-axis y-axis-right">
                <div class="y-axis-label">负荷 (kW)</div>
                <div class="y-axis-ticks">
                  <span>{{ tcnLoadYAxisLabels[0] }}</span>
                  <span>{{ tcnLoadYAxisLabels[1] }}</span>
                  <span>{{ tcnLoadYAxisLabels[2] }}</span>
                  <span>{{ tcnLoadYAxisLabels[3] }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else-if="hasPredicted && !chartDataAvailable" class="chart-empty">
            所选日期范围无数据。预测数据范围：2024-05-11 至 2024-10-08
          </div>
          <div v-else-if="loading" class="chart-empty">加载中...</div>
          <div v-else class="chart-empty">
            <p v-if="!selectedDate">请先选择日期</p>
            <p v-else>请点击"预测"按钮进行预测</p>
          </div>
        </div>
      </section>

      <section class="panel metrics-panel" v-if="showMetrics">
        <div class="panel-header">
          <h3 class="panel-title">模型效果评估</h3>
        </div>
        <div class="metrics-content">
          <div class="metrics-legend" style="display: flex; justify-content: flex-end;">
            <span class="legend-item"><span class="square blue"></span> {{ currentMetrics.label }}</span>
          </div>
          <div class="metrics-chart">
            <div class="metrics-y-axis">
              <span class="y-tick" style="bottom: 0%">0</span>
              <span class="y-tick" style="bottom: 25%">{{ Math.round(metricsLeftMax * 0.25) }}</span>
              <span class="y-tick" style="bottom: 50%">{{ Math.round(metricsLeftMax * 0.5) }}</span>
              <span class="y-tick" style="bottom: 75%">{{ Math.round(metricsLeftMax * 0.75) }}</span>
              <span class="y-tick" style="bottom: 100%">{{ metricsLeftMax }}</span>
            </div>
            <div class="metrics-plot">
              <div class="metrics-bars">
                <div class="metric-bar">
                  <div class="bar-fill" :style="{ height: (currentMetrics.mae / metricsLeftMax * 100) + '%', background: '#1890ff' }"></div>
                  <span class="bar-value">{{ currentMetrics.mae }}</span>
                  <span class="bar-label">MAE</span>
                </div>
                <div class="metric-bar">
                  <div class="bar-fill" :style="{ height: (currentMetrics.rmse / metricsLeftMax * 100) + '%', background: '#faad14' }"></div>
                  <span class="bar-value">{{ currentMetrics.rmse }}</span>
                  <span class="bar-label">RMSE</span>
                </div>
                <div class="metric-bar">
                  <div class="bar-fill" :style="{ height: (currentMetrics.r2 / metricsRightMax * 100) + '%', background: '#52c41a' }"></div>
                  <span class="bar-value">{{ currentMetrics.r2 }}</span>
                  <span class="bar-label">R2</span>
                </div>
                <div class="metric-bar">
                  <div class="bar-fill" :style="{ height: (currentMetrics.imape / metricsRightMax * 100) + '%', background: '#ff4d4f' }"></div>
                  <span class="bar-value">{{ currentMetrics.imape }}</span>
                  <span class="bar-label">IMAPE</span>
                </div>
              </div>
            </div>
            <div class="metrics-y-axis metrics-y-axis-right">
              <span class="y-tick" style="bottom: 0%">0</span>
              <span class="y-tick" style="bottom: 25%">{{ (metricsRightMax * 0.25).toFixed(2) }}</span>
              <span class="y-tick" style="bottom: 50%">{{ (metricsRightMax * 0.5).toFixed(2) }}</span>
              <span class="y-tick" style="bottom: 75%">{{ (metricsRightMax * 0.75).toFixed(2) }}</span>
              <span class="y-tick" style="bottom: 100%">{{ metricsRightMax.toFixed(2) }}</span>
            </div>
          </div>
        </div>
      </section>
      <section class="panel metrics-panel" v-else>
        <div class="panel-header">
          <h3 class="panel-title">模型效果评估</h3>
        </div>
        <div class="metrics-content">
          <div class="metrics-empty">
            <p v-if="!hasPredicted">请先选择日期并点击"预测"按钮进行预测</p>
            <p v-else>请点击"查看评价结果"按钮查看模型效果评估</p>
          </div>
        </div>
      </section>
    </div>

    <section class="panel weather-panel">
      <div class="panel-header">
        <h3 class="panel-title">天气</h3>
      </div>
      <div class="weather-content">
        <template v-if="weatherData.length > 0">
          <!-- 图例 -->
          <div class="weather-legend">
            <span class="legend-item"><span class="square blue"></span> 温度</span>
            <span class="legend-item"><span class="square orange"></span> 风速</span>
          </div>
          <!-- 带双Y轴的图表 -->
          <div class="weather-chart-with-axis">
            <!-- 左侧Y轴 - 温度 -->
            <div class="y-axis y-axis-left">
              <div class="y-axis-label">温度 (°C)</div>
              <div class="y-axis-ticks">
                <span>{{ tempYAxisLabels[0] }}</span>
                <span>{{ tempYAxisLabels[1] }}</span>
                <span>{{ tempYAxisLabels[2] }}</span>
                <span>{{ tempYAxisLabels[3] }}</span>
              </div>
            </div>
            <!-- 图表主体 -->
            <div class="weather-chart-main">
              <svg viewBox="0 0 600 120" class="weather-line-chart" preserveAspectRatio="none">
                <!-- 网格线 -->
                <line x1="0" y1="0.5" x2="600" y2="0.5" stroke="#f0f0f0" stroke-width="1"/>
                <line x1="0" y1="40" x2="600" y2="40" stroke="#f0f0f0" stroke-width="1"/>
                <line x1="0" y1="80" x2="600" y2="80" stroke="#f0f0f0" stroke-width="1"/>
                <line x1="0" y1="120" x2="600" y2="120" stroke="#f0f0f0" stroke-width="1"/>
                <!-- 温度 (蓝色) -->
                <polyline fill="none" stroke="#1890ff" stroke-width="2" :points="temperaturePoints"/>
                <!-- 风速 (橙色) -->
                <polyline fill="none" stroke="#faad14" stroke-width="2" :points="windSpeedPoints"/>
              </svg>
              <div class="weather-chart-labels">
                <span v-for="(label, idx) in dateLabels" :key="idx">{{ label }}</span>
              </div>
            </div>
            <!-- 右侧Y轴 - 风速 -->
            <div class="y-axis y-axis-right">
              <div class="y-axis-label">风速 (m/s)</div>
              <div class="y-axis-ticks">
                <span>{{ windYAxisLabels[0] }}</span>
                <span>{{ windYAxisLabels[1] }}</span>
                <span>{{ windYAxisLabels[2] }}</span>
                <span>{{ windYAxisLabels[3] }}</span>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="weather-empty">请选择日期显示天气图形</div>
      </div>
    </section>
  </MainLayout>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from "vue";
import MainLayout from "../layouts/MainLayout.vue";
import { fetchRankingSummary, type RankingSummary } from "../api/rankings";

// 使用相对路径，通过 Nginx 代理访问后端 API
const API_BASE = "/api";

type PredictionRecord = {
  record_time: string;
  actual_price: number;
  predicted_price: number;
  qr_025?: number;
  qr_50?: number;
  qr_975?: number;
  load_kw: number;
};

type WeatherRecord = {
  record_time: string;
  temperature: number;
  wind_speed: number;
  cloud_cover: number;
  weather_type: string;
};

type TcnRecord = {
  record_time: string;
  real: number;
  qr_005: number;
  qr_025: number;
  qr_05: number;
  qr_50: number;
  qr_95: number;
  qr_975: number;
  qr_995: number;
  load_kw: number;
};

const selectedDate = ref<string>("");
const selectedModel = ref<string>("ensemble");
const hasPredicted = ref(false);
const showMetrics = ref(false);
const predictionData = ref<PredictionRecord[]>([]);
const tcnData = ref<TcnRecord[]>([]);
const weatherData = ref<WeatherRecord[]>([]);
const loading = ref(false);
const currentDatasetId = ref<number | null>(null);
const currentDayIndex = ref(0);
const rankingSummaries = ref<RankingSummary[]>([]);

const getAuthToken = () => localStorage.getItem("access_token") || "";

const canShowCharts = computed(() => {
  return Boolean(selectedDate.value);
});

const fetchDatasetId = async () => {
  try {
    const res = await fetch(`${API_BASE}/datasets?page=1&size=1`, {
      headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
    if (res.ok) {
      const data = await res.json();
      if (data.items && data.items.length > 0) {
        currentDatasetId.value = data.items[0].id;
      }
    }
  } catch (e) {
    console.error("获取数据集失败", e);
  }
};

const formatLocalDateTime = (d: Date) => {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

const fetchPredictionData = async (dateStr: string) => {
  if (!dateStr) return;
  loading.value = true;
  
  const endDate = new Date(`${dateStr}T23:59:59`);
  const startDate = new Date(endDate);
  startDate.setDate(startDate.getDate() - 6);
  startDate.setHours(0, 0, 0, 0);
  
  const startTime = formatLocalDateTime(startDate);
  const endTime = formatLocalDateTime(endDate);
  const modelName = selectedModel.value || "mamba";
  
  try {
    const res = await fetch(
      `${API_BASE}/chart/epf-probability?model=${encodeURIComponent(modelName)}&start_time=${startTime}&end_time=${endTime}`,
      { headers: { Authorization: `Bearer ${getAuthToken()}` } }
    );
    if (res.ok) {
      const data = await res.json();
      predictionData.value = data.items.map((r: any) => ({
        record_time: r.record_time,
        actual_price: r.real,
        predicted_price: r.qr_50,
        qr_50: r.qr_50,
        qr_025: r.qr_025,
        qr_975: r.qr_975,
        load_kw: r.load_kw || 0,
      }));
    }
  } catch (e) {
    console.error("获取预测数据失败", e);
  } finally {
    loading.value = false;
  }
};

const fetchWeatherData = async (dateStr: string) => {
  if (!dateStr || !currentDatasetId.value) return;
  
  const endDate = new Date(`${dateStr}T23:59:59`);
  const startDate = new Date(endDate);
  startDate.setDate(startDate.getDate() - 6);
  startDate.setHours(0, 0, 0, 0);
  
  const startTime = formatLocalDateTime(startDate);
  const endTime = formatLocalDateTime(endDate);
  
  try {
    const res = await fetch(
      `${API_BASE}/chart/weather?dataset_id=${currentDatasetId.value}&start_time=${startTime}&end_time=${endTime}`,
      { headers: { Authorization: `Bearer ${getAuthToken()}` } }
    );
    if (res.ok) {
      const data = await res.json();
      weatherData.value = data.items;
    }
  } catch (e) {
    console.error("获取天气数据失败", e);
  }
};

onMounted(async () => {
  await fetchDatasetId();
  await loadRankingSummaries();
});

const loadRankingSummaries = async () => {
  try {
    const params: Record<string, string> = { source: "epf" };
    if (selectedDate.value) {
      const endDate = new Date(`${selectedDate.value}T23:59:59`);
      const startDate = new Date(endDate);
      startDate.setDate(startDate.getDate() - 6);
      params.start_time = `${startDate.getFullYear()}-${String(startDate.getMonth() + 1).padStart(2, "0")}-${String(startDate.getDate()).padStart(2, "0")}T00:00:00`;
      params.end_time = `${selectedDate.value}T23:59:59`;
    }
    const data = await fetchRankingSummary(params);
    rankingSummaries.value = data;
  } catch (e) {
    console.error("获取评分数据失败", e);
  }
};

const fetchTcnData = async (dateStr: string) => {
  if (!dateStr) return;
  loading.value = true;

  const endDate = new Date(`${dateStr}T23:59:59`);
  const startDate = new Date(endDate);
  startDate.setDate(startDate.getDate() - 6);
  startDate.setHours(0, 0, 0, 0);

  const startTime = formatLocalDateTime(startDate);
  const endTime = formatLocalDateTime(endDate);

  try {
    const res = await fetch(
      `${API_BASE}/chart/epf-probability?model=tcn&start_time=${startTime}&end_time=${endTime}`,
      { headers: { Authorization: `Bearer ${getAuthToken()}` } }
    );
    if (res.ok) {
      const data = await res.json();
      tcnData.value = data.items;
    }
  } catch (e) {
    console.error("获取TCN数据失败", e);
  } finally {
    loading.value = false;
  }
};

const handleDateChange = async () => {
  hasPredicted.value = false;
  showMetrics.value = false;
  predictionData.value = [];
  tcnData.value = [];
  
  if (!selectedDate.value) {
    weatherData.value = [];
    return;
  }
  if (!currentDatasetId.value) {
    await fetchDatasetId();
  }
  await fetchWeatherData(selectedDate.value);
};

const handlePredict = async () => {
  if (!selectedDate.value) {
    alert("请先选择日期");
    return;
  }
  if (!currentDatasetId.value) {
    await fetchDatasetId();
  }
  if (selectedModel.value === 'tcn') {
    await fetchTcnData(selectedDate.value);
  } else {
    await fetchPredictionData(selectedDate.value);
  }
  hasPredicted.value = true;
  showMetrics.value = false;
  currentDayIndex.value = 0;
  await loadRankingSummaries();
};

// 模型效果评估指标
const currentMetrics = computed(() => {
  const modelName = selectedModel.value;
  const summary = rankingSummaries.value.find(item => 
    item.model.toLowerCase().includes(modelName.toLowerCase())
  );
  
  if (summary) {
    return {
      label: summary.model,
      mae: parseFloat(summary.mae.toFixed(2)),
      rmse: parseFloat(summary.rmse.toFixed(2)),
      r2: parseFloat(summary.r2.toFixed(4)),
      imape: parseFloat(summary.imape.toFixed(4))
    };
  }
  
  //  fallback values if no data
  const fallbackData: Record<string, { label: string; mae: number; rmse: number; r2: number; imape: number }> = {
    mamba: { label: "mamba周前", mae: 20.03, rmse: 40.64, r2: 0.81, imape: 0.08 },
    tcn: { label: "tcn周前", mae: 22.15, rmse: 43.28, r2: 0.78, imape: 0.09 },
    nlinear: { label: "nlinear周前", mae: 21.50, rmse: 42.00, r2: 0.79, imape: 0.085 },
    ensemble: { label: "集成周前", mae: 19.50, rmse: 39.00, r2: 0.82, imape: 0.075 }
  };
  
  return fallbackData[modelName] || fallbackData.mamba;
});
const metricsLeftMax = computed(() => Math.ceil(Math.max(currentMetrics.value.mae, currentMetrics.value.rmse) * 1.2));
const metricsRightMax = computed(() => {
  const maxVal = Math.max(currentMetrics.value.r2, currentMetrics.value.imape);
  return Math.ceil(maxVal * 12) / 10;
});

// 按天分组数据 (7天)
const dailyChartData = computed(() => {
  if (!selectedDate.value) return [];
  const sourceData = selectedModel.value === 'tcn' ? tcnData.value : predictionData.value;
  if (sourceData.length === 0) return [];
  
  const endDate = new Date(`${selectedDate.value}T23:59:59`);
  const days: { date: string; data: any[] }[] = [];
  
  for (let i = 6; i >= 0; i--) {
    const dayDate = new Date(endDate);
    dayDate.setDate(dayDate.getDate() - i);
    const dateStr = `${dayDate.getFullYear()}-${String(dayDate.getMonth() + 1).padStart(2, '0')}-${String(dayDate.getDate()).padStart(2, '0')}`;
    
    const dayData = sourceData.filter((r: any) => {
      const recordDate = r.record_time.split('T')[0];
      return recordDate === dateStr;
    }).sort((a: any, b: any) => new Date(a.record_time).getTime() - new Date(b.record_time).getTime());
    
    days.push({ date: dateStr, data: dayData });
  }
  
  return days;
});

const chartDataAvailable = computed(() => {
  if (selectedModel.value === 'tcn') return tcnData.value.length > 0;
  return predictionData.value.length > 0;
});

const currentDayData = computed(() => {
  if (dailyChartData.value.length === 0) return [];
  return dailyChartData.value[currentDayIndex.value]?.data || [];
});

const currentDayLabel = computed(() => {
  if (dailyChartData.value.length === 0) return '';
  return dailyChartData.value[currentDayIndex.value]?.date || '';
});

const hourLabels = ['0', '4', '8', '12', '16', '20', '24'];

const currentDayPriceRange = computed(() => {
  const data = currentDayData.value;
  if (data.length === 0) return { min: 0, max: 1500 };
  const prices = data.flatMap(r => {
    const vals = [r.actual_price, r.predicted_price];
    if (r.qr_025 !== undefined) vals.push(r.qr_025);
    if (r.qr_975 !== undefined) vals.push(r.qr_975);
    return vals;
  });
  const minVal = Math.min(...prices);
  const maxVal = Math.max(...prices);
  const padding = (maxVal - minVal) * 0.1 || 50;
  return { min: Math.max(0, minVal - padding), max: maxVal + padding };
});

const currentDayLoadRange = computed(() => {
  const data = currentDayData.value;
  if (data.length === 0) return { min: 0, max: 80000 };
  const loads = data.map(r => r.load_kw).filter(v => v > 0);
  if (loads.length === 0) return { min: 0, max: 80000 };
  const minVal = Math.min(...loads);
  const maxVal = Math.max(...loads);
  const padding = (maxVal - minVal) * 0.1 || 1000;
  return { min: Math.max(0, minVal - padding), max: maxVal + padding };
});

const currentDayActualPoints = computed(() => {
  const data = currentDayData.value;
  if (data.length === 0) return "";
  const { min: minPrice, max: maxPrice } = currentDayPriceRange.value;
  const width = 600, height = 200;
  const step = width / Math.max(data.length - 1, 1);
  return data.map((r, i) => {
    const x = i * step;
    const y = height - ((r.actual_price - minPrice) / (maxPrice - minPrice)) * height;
    return `${x.toFixed(1)},${Math.max(0, Math.min(height, y)).toFixed(1)}`;
  }).join(" ");
});

const currentDayPredictedPoints = computed(() => {
  const data = currentDayData.value;
  if (data.length === 0) return "";
  const { min: minPrice, max: maxPrice } = currentDayPriceRange.value;
  const width = 600, height = 200;
  const step = width / Math.max(data.length - 1, 1);
  return data.map((r, i) => {
    const x = i * step;
    const y = height - ((r.predicted_price - minPrice) / (maxPrice - minPrice)) * height;
    return `${x.toFixed(1)},${Math.max(0, Math.min(height, y)).toFixed(1)}`;
  }).join(" ");
});

const currentDayBand95Points = computed(() => {
  const data = currentDayData.value;
  if (data.length === 0) return "";
  const { min: minPrice, max: maxPrice } = currentDayPriceRange.value;
  const width = 600, height = 200;
  const step = width / Math.max(data.length - 1, 1);
  const upper = data.map((r, i) => {
    const x = i * step;
    const val = r.qr_975 ?? r.predicted_price;
    const y = height - ((val - minPrice) / (maxPrice - minPrice)) * height;
    return `${x.toFixed(1)},${Math.max(0, Math.min(height, y)).toFixed(1)}`;
  });
  const lower = data.map((r, i) => {
    const x = i * step;
    const val = r.qr_025 ?? r.predicted_price;
    const y = height - ((val - minPrice) / (maxPrice - minPrice)) * height;
    return `${x.toFixed(1)},${Math.max(0, Math.min(height, y)).toFixed(1)}`;
  }).reverse();
  return [...upper, ...lower].join(" ");
});

const currentDayLoadPoints = computed(() => {
  const data = currentDayData.value;
  if (data.length === 0) return "";
  const { min: minLoad, max: maxLoad } = currentDayLoadRange.value;
  const width = 600, height = 200;
  const step = width / Math.max(data.length - 1, 1);
  return data.map((r, i) => {
    const x = i * step;
    const y = height - ((r.load_kw - minLoad) / (maxLoad - minLoad)) * height;
    return `${x.toFixed(1)},${Math.max(0, Math.min(height, y)).toFixed(1)}`;
  }).join(" ");
});

const priceYAxisLabels = computed(() => {
  const { min, max } = currentDayPriceRange.value;
  const step = (max - min) / 3;
  return [Math.round(max), Math.round(min + step * 2), Math.round(min + step), Math.round(min)];
});

const loadYAxisLabels = computed(() => {
  const { min, max } = currentDayLoadRange.value;
  const step = (max - min) / 3;
  return [Math.round(max), Math.round(min + step * 2), Math.round(min + step), Math.round(min)];
});

const prevDay = () => {
  const len = dailyChartData.value.length || 7;
  currentDayIndex.value = (currentDayIndex.value - 1 + len) % len;
};

const nextDay = () => {
  const len = dailyChartData.value.length || 7;
  currentDayIndex.value = (currentDayIndex.value + 1) % len;
};

// ===== TCN概率预测图表计算 =====
const tcnCurrentDayData = computed(() => {
  if (selectedModel.value !== 'tcn') return [];
  return currentDayData.value as TcnRecord[];
});

const tcnPriceRange = computed(() => {
  const data = tcnCurrentDayData.value;
  if (data.length === 0) return { min: 0, max: 600 };
  const allVals = data.flatMap(r => [r.real, r.qr_50, r.qr_025, r.qr_975]);
  const minVal = Math.min(...allVals);
  const maxVal = Math.max(...allVals);
  const padding = (maxVal - minVal) * 0.15 || 50;
  return { min: Math.max(0, minVal - padding), max: maxVal + padding };
});

const tcnLoadRange = computed(() => {
  const data = tcnCurrentDayData.value;
  if (data.length === 0) return { min: 0, max: 80000 };
  const loads = data.map(r => r.load_kw).filter(v => v > 0);
  if (loads.length === 0) return { min: 0, max: 80000 };
  const minVal = Math.min(...loads);
  const maxVal = Math.max(...loads);
  const padding = (maxVal - minVal) * 0.1 || 1000;
  return { min: Math.max(0, minVal - padding), max: maxVal + padding };
});

const toY = (val: number, min: number, max: number, height: number) => {
  return Math.max(0, Math.min(height, height - ((val - min) / (max - min)) * height));
};

const tcnRealPoints = computed(() => {
  const data = tcnCurrentDayData.value;
  if (data.length === 0) return "";
  const { min: minP, max: maxP } = tcnPriceRange.value;
  const w = 600, h = 200;
  const step = w / Math.max(data.length - 1, 1);
  return data.map((r, i) => `${(i * step).toFixed(1)},${toY(r.real, minP, maxP, h).toFixed(1)}`).join(" ");
});

const tcnQr50Points = computed(() => {
  const data = tcnCurrentDayData.value;
  if (data.length === 0) return "";
  const { min: minP, max: maxP } = tcnPriceRange.value;
  const w = 600, h = 200;
  const step = w / Math.max(data.length - 1, 1);
  return data.map((r, i) => `${(i * step).toFixed(1)},${toY(r.qr_50, minP, maxP, h).toFixed(1)}`).join(" ");
});

const tcnBand95Points = computed(() => {
  const data = tcnCurrentDayData.value;
  if (data.length === 0) return "";
  const { min: minP, max: maxP } = tcnPriceRange.value;
  const w = 600, h = 200;
  const step = w / Math.max(data.length - 1, 1);
  // 上边界 (QR-0.975) 从左到右
  const upper = data.map((r, i) => `${(i * step).toFixed(1)},${toY(r.qr_975, minP, maxP, h).toFixed(1)}`);
  // 下边界 (QR-0.025) 从右到左
  const lower = data.map((r, i) => `${(i * step).toFixed(1)},${toY(r.qr_025, minP, maxP, h).toFixed(1)}`).reverse();
  return [...upper, ...lower].join(" ");
});

const tcnLoadPoints = computed(() => {
  const data = tcnCurrentDayData.value;
  if (data.length === 0) return "";
  const { min: minL, max: maxL } = tcnLoadRange.value;
  const w = 600, h = 200;
  const step = w / Math.max(data.length - 1, 1);
  return data.map((r, i) => `${(i * step).toFixed(1)},${toY(r.load_kw, minL, maxL, h).toFixed(1)}`).join(" ");
});

const tcnPriceYAxisLabels = computed(() => {
  const { min, max } = tcnPriceRange.value;
  const step = (max - min) / 3;
  return [Math.round(max), Math.round(min + step * 2), Math.round(min + step), Math.round(min)];
});

const tcnLoadYAxisLabels = computed(() => {
  const { min, max } = tcnLoadRange.value;
  const step = (max - min) / 3;
  return [Math.round(max), Math.round(min + step * 2), Math.round(min + step), Math.round(min)];
});

const dateLabels = computed(() => {
  const data = weatherData.value;
  if (data.length === 0) return [];
  const totalPoints = data.length;
  const labelCount = 7;
  const step = Math.max(Math.floor(totalPoints / (labelCount - 1)), 1);
  const labels: string[] = [];
  for (let i = 0; i < totalPoints; i += step) {
    const rt = data[i].record_time;
    const d = new Date(rt);
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    labels.push(`${mm}-${dd}`);
  }
  if (labels.length < labelCount) {
    const last = data[totalPoints - 1].record_time;
    const d = new Date(last);
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    labels.push(`${mm}-${dd}`);
  }
  return labels;
});

const temperaturePoints = computed(() => {
  const data = weatherData.value;
  if (data.length === 0) return "";
  const temps = data.map(r => r.temperature);
  const minTemp = Math.min(...temps) - 2;
  const maxTemp = Math.max(...temps) + 2;
  const width = 600, height = 120;
  const step = width / Math.max(data.length - 1, 1);
  return data.map((r, i) => {
    const x = i * step;
    const y = height - ((r.temperature - minTemp) / (maxTemp - minTemp)) * height;
    return `${x.toFixed(1)},${Math.max(0, Math.min(height, y)).toFixed(1)}`;
  }).join(" ");
});

const windSpeedPoints = computed(() => {
  const data = weatherData.value;
  if (data.length === 0) return "";
  const speeds = data.map(r => r.wind_speed);
  const minSpeed = 0;
  const maxSpeed = Math.max(...speeds) + 2;
  const width = 600, height = 120;
  const step = width / Math.max(data.length - 1, 1);
  return data.map((r, i) => {
    const x = i * step;
    const y = height - ((r.wind_speed - minSpeed) / (maxSpeed - minSpeed)) * height;
    return `${x.toFixed(1)},${Math.max(0, Math.min(height, y)).toFixed(1)}`;
  }).join(" ");
});

const tempYAxisLabels = computed(() => {
  const data = weatherData.value;
  if (data.length === 0) return [40, 30, 20, 0];
  const temps = data.map(r => r.temperature);
  const min = Math.min(...temps) - 2;
  const max = Math.max(...temps) + 2;
  const step = (max - min) / 3;
  return [Math.round(max), Math.round(min + step * 2), Math.round(min + step), Math.round(min)];
});

const windYAxisLabels = computed(() => {
  const data = weatherData.value;
  if (data.length === 0) return [9, 6, 3, 0];
  const speeds = data.map(r => r.wind_speed);
  const max = Math.max(...speeds) + 2;
  const step = max / 3;
  return [Math.round(max), Math.round(step * 2), Math.round(step), 0];
});
</script>

<style scoped>
/* 轮播样式 */
.carousel-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.carousel-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 8px 0;
}
.carousel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary);
  min-width: 180px;
  text-align: center;
}
.carousel-btn {
  width: 32px;
  height: 32px;
  border: 1px solid var(--border);
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  transition: all 0.2s;
}
.carousel-btn:hover {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.carousel-indicators {
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 4px 0;
}
.indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e0e0e0;
  cursor: pointer;
  transition: all 0.2s;
}
.indicator:hover {
  background: #bbb;
}
.indicator.active {
  background: var(--primary);
  transform: scale(1.2);
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
}
.header-actions {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
  background: #fff;
  padding: 16px;
  border-radius: 4px;
  border: 1px solid var(--border);
}
.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.filter-group label {
  font-size: 12px;
  color: var(--muted);
}
.filter-group .input {
  min-width: 120px;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}
.chart-panel, .metrics-panel, .weather-panel {
  background: #fff;
}
.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary);
  margin: 0;
}
.chart-container {
  padding: 20px;
}
.chart-legend {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  font-size: 13px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.square {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}
.square.blue { background: #1890ff; }
.square.orange { background: #faad14; }
.square.red { background: #ff4d4f; }
.line-solid {
  width: 20px;
  height: 2px;
  background: currentColor;
}
.line-solid.blue { background: #1890ff; }
.line-solid.dark { background: #333; }
.line-solid.green { background: #52c41a; }
.square.light-blue { background: rgba(24,144,255,0.3); }
.line-dashed {
  width: 20px;
  height: 2px;
  background: repeating-linear-gradient(90deg, currentColor 0, currentColor 4px, transparent 4px, transparent 7px);
}
.line-dashed.orange { color: #faad14; }
.chart-with-axis {
  display: flex;
  align-items: stretch;
  height: 220px;
}
.y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding-bottom: 28px;
}
.y-axis-left {
  width: 80px;
  align-items: flex-start;
  padding-right: 8px;
}
.y-axis-right {
  width: 80px;
  align-items: flex-end;
  padding-left: 8px;
}
.y-axis-label {
  font-size: 12px;
  color: var(--muted);
  white-space: nowrap;
}
.y-axis-ticks {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  flex: 1;
  font-size: 12px;
  color: var(--muted);
  padding-top: 4px;
}
.y-axis-left .y-axis-ticks {
  text-align: left;
}
.y-axis-right .y-axis-ticks {
  text-align: right;
}
.chart-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.line-chart {
  flex: 1;
  width: 100%;
  border-left: 1px solid #e8e8e8;
  border-right: 1px solid #e8e8e8;
  border-bottom: 1px solid #e8e8e8;
}
.chart-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--muted);
  padding-top: 8px;
}
.chart-empty {
  height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  font-size: 13px;
}
.link-btn {
  color: var(--primary);
  border: none;
  background: none;
}
.link-btn:hover {
  color: var(--primary-light);
  background: none;
}
.metrics-panel .panel-header {
  border-bottom: none;
  padding-bottom: 0;
}
.metrics-content {
  padding: 0 20px 40px 20px;
}
.metrics-empty {
  height: 170px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  font-size: 13px;
}
.metrics-empty p {
  margin: 0;
}
.metrics-legend {
  margin-bottom: 10px;
  font-size: 13px;
  color: #333;
}
.metrics-chart {
  display: grid;
  grid-template-columns: 35px 1fr 35px;
  gap: 0;
  height: 170px;
}
.metrics-panel .panel-title {
  color: #333;
}
.metrics-y-axis {
  position: relative;
  width: 100%;
}
.metrics-y-axis .y-tick {
  position: absolute;
  right: 4px;
  transform: translateY(50%);
  font-size: 11px;
  color: #94a3b8;
  display: flex;
  align-items: center;
}
.metrics-y-axis .y-tick::after {
  content: "";
  position: absolute;
  right: -4px;
  top: 50%;
  width: 4px;
  height: 1px;
  background: #1890ff;
}
.metrics-y-axis-right .y-tick {
  right: auto;
  left: 4px;
}
.metrics-y-axis-right .y-tick::after {
  right: auto;
  left: -4px;
}
.metrics-plot {
  position: relative;
  height: 100%;
  border-left: 1px solid #1890ff;
  border-right: 1px solid #52c41a;
  border-bottom: 1px solid #ccc;
}
.metrics-bars {
  position: relative;
  height: 100%;
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  padding: 0 16px;
}
.metric-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  width: 30px;
  height: 100%;
  position: relative;
  bottom: -1px;
}
.bar-fill {
  width: 100%;
  border-radius: 0;
  min-height: 2px;
}
.bar-value {
  font-size: 10px;
  color: #666;
  white-space: nowrap;
  order: -1;
}
.bar-label {
  position: absolute;
  bottom: -25px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 12px;
  color: #333;
  font-weight: 500;
  white-space: nowrap;
}
.weather-content {
  padding: 20px;
}
.weather-icons-row {
  display: flex;
  justify-content: space-around;
  margin-bottom: 16px;
  padding: 0 80px;
}
.weather-day {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.weather-label {
  font-size: 12px;
  color: #94a3b8;
}
.weather-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  line-height: 1;
}
.weather-icon.sun {
  color: #fbbf24;
}
.weather-icon.cloud-sun {
  color: #fbbf24;
  position: relative;
}
.weather-icon.overcast {
  color: #94a3b8;
}
.weather-icon.sun::before {
  content: "☀";
}
.weather-icon.cloud-sun::before {
  content: "☁";
  position: absolute;
  color: #93c5fd;
  font-size: 24px;
  left: 50%;
  top: 50%;
  transform: translate(-65%, -35%);
  z-index: 2;
}
.weather-icon.cloud-sun::after {
  content: "☀";
  position: absolute;
  color: #fbbf24;
  font-size: 16px;
  left: 50%;
  top: 50%;
  transform: translate(-20%, -80%);
  z-index: 1;
}
.weather-icon.overcast::before {
  content: "☁";
}
.weather-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-bottom: 12px;
  font-size: 13px;
}
.weather-chart-with-axis {
  display: flex;
  align-items: stretch;
  height: 160px;
}
.weather-chart-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.weather-line-chart {
  flex: 1;
  width: 100%;
  border-left: 1px solid #e8e8e8;
  border-right: 1px solid #e8e8e8;
  border-bottom: 1px solid #e8e8e8;
}
.weather-chart-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--muted);
  padding-top: 8px;
}
.weather-empty {
  height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  font-size: 13px;
}
</style>
