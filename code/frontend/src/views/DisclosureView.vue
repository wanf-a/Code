<template>
  <div class="content-section">
    <div class="header-tabs">
      <div class="tab-bar">
        <button 
          v-for="t in disclosureTabs" 
          :key="t.key"
          :class="['tab-btn', { active: disclosureTab === t.key }]"
          @click="disclosureTab = t.key"
        >
          {{ t.label }}
        </button>
      </div>
      
      <div class="date-tab-bar">
        <button 
          v-for="day in dateTabs" 
          :key="day.key"
          :class="['date-tab-btn', { active: currentDay === day.key }]"
          @click="currentDay = day.key"
        >
          {{ day.label }}
        </button>
      </div>
    </div>



    <div class="card">
      <h3 class="card-title">{{ currentDisclosure.title }}（{{ getCurrentDayLabel }}）</h3>
      <div class="svg-chart-wrap">
        <svg viewBox="0 0 700 220" class="svg-chart">
          <line x1="50" y1="20" x2="50" y2="200" stroke="#e0e0e0" stroke-width="1"/>
          <line x1="50" y1="200" x2="690" y2="200" stroke="#e0e0e0" stroke-width="1"/>
          <text x="50" y="16" font-size="10" fill="#666" text-anchor="middle" font-weight="500">{{ currentDisclosure.unit }}</text>
          <text v-for="(v, i) in disclosureYLabels" :key="i" :x="45" :y="200 - i * (175/3) + 4" text-anchor="end" font-size="11" fill="#999">{{ v }}</text>
          
          <!-- 概率预测区间 -->
          <polygon 
            v-if="disclosureTab === 'price'" 
            :points="disclosureBandPoints" 
            fill="rgba(24,144,255,0.2)" 
            stroke="none"
          />
          
          <!-- 折线 -->
          <polyline 
            :points="disclosureChartPoints" 
            fill="none" 
            :stroke="disclosureTab === 'wind' ? 'rgba(76,175,80,1)' : (disclosureTab === 'solar' ? 'rgba(255,215,0,1)' : '#1890ff')" 
            stroke-width="2"
          />
          
          <!-- 交互式数据点 -->
          <g v-for="(point, index) in chartDataPoints" :key="'point-' + index">
            <!-- 透明感应区域 -->
            <circle
              :cx="point.x"
              :cy="point.y"
              r="8"
              fill="transparent"
              style="cursor: pointer;"
              @mouseenter="showTooltip($event, point, index)"
              @mousemove="moveTooltip($event)"
              @mouseleave="hideTooltip"
              @click="selectDataPoint(point, index)"
            />
            <!-- 高亮点 -->
            <circle
              v-if="selectedPointIndex === index"
              :cx="point.x"
              :cy="point.y"
              r="6"
              fill="#fff"
              :stroke="disclosureTab === 'wind' ? 'rgba(76,175,80,1)' : (disclosureTab === 'solar' ? 'rgba(255,215,0,1)' : '#1890ff')"
              stroke-width="3"
              style="pointer-events: none;"
            />
          </g>
          
          <text v-for="(lbl, i) in periodLabels" :key="'d'+i" :x="50 + i * (640 / (periodLabels.length - 1))" y="218" text-anchor="middle" font-size="10" fill="#666">{{ lbl }}</text>
        </svg>
        
        <!-- Tooltip 提示框 -->
        <div v-if="tooltip.visible" class="chart-tooltip" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
          <div class="tooltip-content">
            <div class="tooltip-period">时段：t{{ tooltip.period }}</div>
            <div class="tooltip-value">{{ tooltip.value.toFixed(2) }} {{ currentDisclosure.unit.replace('(', '').replace(')', '') }}</div>
          </div>
        </div>
      </div>
      
      <!-- 选中数据显示 -->
      <div v-if="selectedPointIndex !== null && disclosureData.length > 0" class="selected-data-card">
        <h4 class="selected-data-title">选中数据详情</h4>
        <div class="selected-data-grid">
          <div class="data-item">
            <span class="data-label">时段：</span>
            <span class="data-value">t{{ selectedPointIndex + 1 }}</span>
          </div>
          <div class="data-item">
            <span class="data-label">数值：</span>
            <span class="data-value highlight">{{ disclosureData[selectedPointIndex].toFixed(2) }}</span>
          </div>
          <div class="data-item">
            <span class="data-label">时间：</span>
            <span class="data-value">{{ getCurrentDayLabel }} - {{ formatPeriodTime(selectedPointIndex) }}</span>
          </div>
        </div>
      </div>
      
      <div class="data-table-wrap" style="margin-top: 16px; overflow-x: auto;">
        <table class="data-table">
          <thead><tr><th>名称</th><th v-for="i in Math.min(disclosureData.length, 96)" :key="i">t{{ i }}</th></tr></thead>
          <tbody>
            <tr><td>{{ currentDisclosure.rowName }}</td><td v-for="(v, i) in disclosureData.slice(0, 96)" :key="i">{{ typeof v === 'number' ? v.toFixed(2) : v }}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { marketApi } from "../api/market";

// 1. 定义数据类型接口
interface ItemData {
  name?: string;
  values: number[];
  q05_values?: number[];
  q95_values?: number[];
}

// 2. 扩展接口参数类型
interface GetOutResultsParams {
  sheet: string;
  row_index?: number;
  day?: number;
}

// 3. 电价预测参数类型
interface GetPricePredictionsParams {
  day: number;
  model: string;
}

// 4. 功能标签配置
const disclosureTabs = [
  { key: "price", label: "电价预测" },
  { key: "load", label: "负荷预测" },
  { key: "wind", label: "风电功率预测" },
  { key: "solar", label: "光伏功率预测" },
];

// 5. 日期标签配置
const dateTabs = [
  { key: 1, label: "第一天" },
  { key: 2, label: "第二天" },
  { key: 3, label: "第三天" },
  { key: 4, label: "第四天" },
  { key: 5, label: "第五天" },
  { key: 6, label: "第六天" },
  { key: 7, label: "第七天" }
];

// 6. 响应式变量
const disclosureTab = ref<string>("price");
const currentDay = ref<number>(1);
const disclosureData = ref<number[]>([]);
const q05Data = ref<number[]>([]); // 95%概率区间下限
const q95Data = ref<number[]>([]); // 95%概率区间上限

// 新增：交互状态
const tooltip = ref({
  visible: false,
  x: 0,
  y: 0,
  period: 1,
  value: 0,
});
const selectedPointIndex = ref<number | null>(null);

// 7. 功能配置映射
const disclosureSheetMap: Record<string, string> = {
  price: "energy_price", 
  load: "load_load_bid_power",
  wind: "wind_wt_opera_power", 
  solar: "solar_pv_opera_power",
};

const disclosureConfig: Record<string, { title: string; unit: string; rowName: string }> = {
  price: { title: "电价预测", unit: "电价 (元/MWh)", rowName: "预测电价" },
  load: { title: "负荷预测", unit: "负荷 (MW)", rowName: "负荷消耗功率" },
  wind: { title: "风电功率预测", unit: "风电功率 (MW)", rowName: "风电消纳功率" },
  solar: { title: "光伏功率预测", unit: "光伏功率 (MW)", rowName: "光伏消纳功率" },
};

// 8. 计算属性
const currentDisclosure = computed(() => disclosureConfig[disclosureTab.value]);
const getCurrentDayLabel = computed(() => {
  const dayItem = dateTabs.find(item => item.key === currentDay.value);
  return dayItem?.label || "第一天";
});

// 9. 核心：数据请求函数
async function fetchDisclosureData() {
  try {
    if (disclosureTab.value === 'price') {
      // 从 price_predictions 表获取电价预测数据（默认使用集成模型）
      const params: GetPricePredictionsParams = { 
        day: currentDay.value,
        model: "ensemble"
      };
      const response = await marketApi.getPricePredictions(params);
      
      const items: ItemData[] = response?.items || [];
      if (items.length > 0) {
        disclosureData.value = items[0].values;
        q05Data.value = items[0].q05_values || [];
        q95Data.value = items[0].q95_values || [];
      } else {
        disclosureData.value = [];
        q05Data.value = [];
        q95Data.value = [];
      }
    } else {
      // 负荷预测、风电预测、光伏预测使用 power-balance API
      // 计算日期字符串：起始日期 20260319 + (currentDay - 1) 天
      const startDate = 20260319;
      const currentDayOffset = currentDay.value - 1;
      
      // 解析起始日期
      const year = Math.floor(startDate / 10000);
      const month = Math.floor((startDate % 10000) / 100) - 1; // 月份从 0 开始
      const day = startDate % 100;
      
      // 创建日期对象并加上偏移量
      const dateObj = new Date(year, month, day);
      dateObj.setDate(dateObj.getDate() + currentDayOffset);
      
      // 格式化为 YYYYMMDD
      const dateStr = `${dateObj.getFullYear()}${(dateObj.getMonth() + 1).toString().padStart(2, '0')}${dateObj.getDate().toString().padStart(2, '0')}`;
      
      console.log(`请求功率平衡数据：date_str=${dateStr}, currentDay=${currentDay.value}`);
      
      const response = await marketApi.getPowerBalance({ date_str: dateStr });
      const items: ItemData[] = response?.items || [];
      
      // 根据当前标签页选择对应的数据
      const rowNameMap: Record<string, string> = {
        load: "负荷消耗功率",
        wind: "风电消纳功率",
        solar: "光伏消纳功率"
      };
      
      const targetName = rowNameMap[disclosureTab.value];
      const targetItem = items.find(item => item.name === targetName);
      
      if (targetItem) {
        disclosureData.value = targetItem.values;
      } else {
        console.warn(`未找到 ${targetName} 的数据`);
        disclosureData.value = [];
      }
    }
  } catch (e) { 
    console.error("数据请求失败：", e);
    disclosureData.value = []; 
  }
}

// 10. 监听事件
watch(disclosureTab, fetchDisclosureData);
watch(currentDay, fetchDisclosureData);

// 11. 图表相关计算属性
// 统一的Y轴最大值计算（考虑所有数据）
const chartMaxValue = computed(() => {
  const vals = disclosureData.value;
  if (!vals.length) return 1;
  
  // 考虑概率预测区间的数据
  const allVals = [...vals];
  if (disclosureTab.value === 'price') {
    allVals.push(...q05Data.value, ...q95Data.value);
  }
  
  return Math.max(...allVals, 1);
});

const disclosureChartPoints = computed(() => {
  const vals = disclosureData.value;
  if (!vals.length) return "";
  const maxVal = chartMaxValue.value;
  const step = 640 / Math.max(vals.length - 1, 1);
  return vals.map((v, i) => `${(50 + i * step).toFixed(1)},${(200 - (v / maxVal) * 175).toFixed(1)}`).join(" ");
});

// 概率预测区间点
const disclosureBandPoints = computed(() => {
  const q05Vals = q05Data.value;
  const q95Vals = q95Data.value;
  const vals = disclosureData.value;
  if (!vals.length || !q05Vals.length || !q95Vals.length) return "";
  
  const maxVal = chartMaxValue.value;
  const step = 640 / Math.max(vals.length - 1, 1);
  
  // 生成上限点
  const upperPoints = q95Vals.map((v, i) => {
    const x = 50 + i * step;
    const y = 200 - (v / maxVal) * 175;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  
  // 生成下限点（反向）
  const lowerPoints = q05Vals.map((v, i) => {
    const x = 50 + i * step;
    const y = 200 - (v / maxVal) * 175;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).reverse();
  
  return [...upperPoints, ...lowerPoints].join(" ");
});

// 新增：计算每个数据点的坐标
const chartDataPoints = computed(() => {
  const vals = disclosureData.value;
  if (!vals.length) return [];
  const maxVal = chartMaxValue.value;
  const step = 640 / Math.max(vals.length - 1, 1);
  
  return vals.map((v, i) => ({
    x: 50 + i * step,
    y: 200 - (v / maxVal) * 175,
    value: v,
    period: i + 1,
  }));
});

const periodLabels = computed(() => {
  return ["0:00", "4:00", "8:00", "12:00", "16:00", "20:00", "24:00"];
});

const disclosureYLabels = computed(() => {
  const maxVal = chartMaxValue.value;
  if (maxVal <= 1) return [0, 100, 200, 300];
  
  const step = maxVal / 3;
  return [0, Math.round(step), Math.round(step * 2), Math.round(maxVal)];
});

// 12. 交互函数
function showTooltip(event: MouseEvent, point: any, index: number) {
  tooltip.value.visible = true;
  tooltip.value.x = point.x + 10;
  tooltip.value.y = point.y - 10;
  tooltip.value.period = point.period;
  tooltip.value.value = point.value;
}

function moveTooltip(event: MouseEvent) {
  if (tooltip.value.visible) {
    tooltip.value.x = event.offsetX + 10;
    tooltip.value.y = event.offsetY - 10;
  }
}

function hideTooltip() {
  tooltip.value.visible = false;
}

function selectDataPoint(point: any, index: number) {
  selectedPointIndex.value = index;
  // 可以在这里添加额外的处理逻辑，比如滚动到对应表格位置
}

// 格式化时段为具体时间（例如 t1 -> 00:00, t2 -> 00:15）
function formatPeriodTime(periodIndex: number): string {
  const totalMinutes = periodIndex * 15;
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
}

// 13. 初始化
onMounted(() => {
  fetchDisclosureData();
});
</script>


<style scoped>
.content-section {
  max-width: 1300px;
  margin: 0 auto;
  padding: 16px;
}

.header-tabs {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.tab-bar {
  display: flex;
  gap: 0;
}
.tab-btn {
  padding: 8px 20px;
  border: 1px solid #d9d9d9;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.2s;
}
.tab-btn:first-child {
  border-radius: 4px 0 0 4px;
}
.tab-btn:last-child {
  border-radius: 0 4px 4px 0;
}
.tab-btn + .tab-btn {
  border-left: none;
}
.tab-btn.active {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}

.date-tab-bar {
  display: flex;
  gap: 0;
}
.date-tab-btn {
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 0;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.2s;
}
.date-tab-btn.active {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}

.card {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin: 0 0 12px;
}
.svg-chart-wrap {
  width: 100%;
  height: 220px;
  position: relative;
}
.svg-chart {
  width: 100%;
  height: 100%;
}
.chart-unit {
  font-size: 12px;
  color: #1890ff;
  margin: 0 0 4px;
}
.data-table-wrap {
  overflow-x: auto;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.data-table th {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #e8e8e8;
  white-space: nowrap;
}
.data-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  color: #555;
  white-space: nowrap;
}

/* Chart Tooltip */
.chart-tooltip {
  position: absolute;
  background: rgba(0, 0, 0, 0.8);
  color: #fff;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  pointer-events: none;
  z-index: 1000;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: opacity 0.2s;
}

.tooltip-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tooltip-period {
  font-weight: 600;
  color: #1890ff;
}

.tooltip-value {
  font-size: 14px;
  font-weight: 500;
}

/* Selected Data Card */
.selected-data-card {
  margin-top: 16px;
  padding: 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e6f7ff 100%);
  border: 1px solid #bae7ff;
  border-radius: 8px;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.selected-data-title {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #1890ff;
}

.selected-data-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.data-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.data-label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.data-value {
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

.data-value.highlight {
  color: #1890ff;
  font-size: 16px;
}


</style>
