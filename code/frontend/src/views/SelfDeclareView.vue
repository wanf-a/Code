<template>
  <div class="content-section">
    <!-- 调整后的顶部栏：左侧Tab + 右侧日期标签 -->
    <div class="top-operation-bar">
      <div class="tab-bar">
        <button :class="['tab-btn', { active: settlementTab === 'overview' }]" @click="handleTabChange('overview')">市场总览</button>
        <button :class="['tab-btn', { active: settlementTab === 'analysis' }]" @click="handleTabChange('analysis')">详情分析</button>
      </div>
      
      <!-- 新增：右上角日期标签栏 -->
      <div class="date-tab-bar">
        <button 
          v-for="day in dateTabs" 
          :key="day.key"
          :class="['date-tab-btn', { active: currentDay === day.key }]"
          @click="handleDayChange(day.key)"
        >
          {{ day.label }}
        </button>
      </div>
    </div>

    <!-- 市场总览 -->
    <div v-if="settlementTab === 'overview'">
      <!-- 调试信息（已注释）
      <div style="background: #f0f0f0; padding: 10px; margin-bottom: 10px; font-size: 12px; border: 1px solid #ddd;">
        <strong>[调试]</strong> settlementTab: {{ settlementTab }}<br>
        <strong>[调试]</strong> overviewData 是否存在：{{ !!overviewData }}<br>
        <strong>[调试]</strong> overviewData 类型：{{ typeof overviewData }}<br>
        <strong>[调试]</strong> energy_market 是否存在：{{ !!overviewData?.energy_market }}<br>
        <strong>[调试]</strong> energy_market 类型：{{ typeof overviewData?.energy_market }}<br>
        <strong>[调试]</strong> avg_price 值：{{ overviewData?.energy_market?.avg_price }}<br>
        <strong>[调试]</strong> avg_price 是否为空：{{ !overviewData?.energy_market?.avg_price }}<br>
        <strong>[调试]</strong> total_generation 值：{{ overviewData?.energy_market?.total_generation }}<br>
        <strong>[调试]</strong> 完整 energy_market: {{ JSON.stringify(overviewData?.energy_market) }}<br>
        <strong>[调试]</strong> overviewData.energy_market.avg_price: {{ overviewData?.energy_market?.avg_price }}<br>
        <strong>[调试]</strong> 直接访问 avg_price: {{ (overviewData as any)?.energy_market?.avg_price }}
      </div>
      -->
      
      <div class="card">
        <div class="card-header-row">
          <!-- 标题随日期变化 -->
          <h3 class="card-title">{{ currentDayLabel }} 电能量市场结果</h3>
          <!-- <span class="score-badge">评分：80</span> -->
        </div>
        <div class="market-results">
          <!-- 第一行：电价相关 -->
          <div class="result-row row-1">
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.avg_price) }}</div>
              <div class="result-label">成交均价(元/MWh)</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.max_node_price) }}</div>
              <div class="result-label">最高节点电价(元/MWh)</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.min_node_price) }}</div>
              <div class="result-label">最低节点电价(元/MWh)</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.avg_quote_price) }}</div>
              <div class="result-label">申报均价(元/MWh)</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.supply_demand_ratio) }}</div>
              <div class="result-label">供需比</div>
            </div>
          </div>
          <!-- 第二行：电量相关 -->
          <div class="result-row row-2">
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.total_generation) }}</div>
              <div class="result-label">总发电量(MWh)</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.total_consumption) }}</div>
              <div class="result-label">总用电量(MWh)</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.re_curtailment) }}</div>
              <div class="result-label">新能源总弃电量(MWh)</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.quote_quantity) }}</div>
              <div class="result-label">申报出力(MW)</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.total_output) }}</div>
              <div class="result-label">成交总出力(100MW)</div>
            </div>
          </div>
          <!-- 第三行：其他指标 -->
          <div class="result-row row-3">
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.total_capacity) }}</div>
              <div class="result-label">总装机容量(100MW)</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.plant_count) }}</div>
              <div class="result-label">发电企业数目</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.quote_unit_count) }}</div>
              <div class="result-label">申报机组数目</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.bid_units) }}</div>
              <div class="result-label">中标机组数目</div>
            </div>
            <div class="result-item">
              <div class="result-value">{{ formatNumber(overviewData.energy_market.total_revenue) }}</div>
              <div class="result-label">总交易额(万元)</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 饼状图：机组数量 & 装机容量 -->
      <div class="card" style="margin-top: 20px;">
        <div class="pie-chart-row">
          <div class="pie-chart-item">
            <h4 class="pie-title">机组数量分布</h4>
            <svg viewBox="0 0 180 180" class="pie-svg">
              <path v-for="(arc, i) in countArcs" :key="'c'+i" :d="arc.path" :fill="arc.color" stroke="#fff" stroke-width="1.5"/>
              <text v-for="(arc, i) in countArcs" :key="'cl'+i" :x="arc.lx" :y="arc.ly" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#fff" font-weight="600">{{ arc.pct }}%</text>
            </svg>
            <div class="pie-legend">
              <span v-for="(arc, i) in countArcs" :key="'clg'+i" class="legend-item">
                <span class="legend-color" :style="{ background: arc.color }"></span>{{ arc.name }} {{ arc.value }}
              </span>
            </div>
          </div>
          <div class="pie-chart-item">
            <h4 class="pie-title">装机容量分布(100MW)</h4>
            <svg viewBox="0 0 180 180" class="pie-svg">
              <path v-for="(arc, i) in capacityArcs" :key="'p'+i" :d="arc.path" :fill="arc.color" stroke="#fff" stroke-width="1.5"/>
              <text v-for="(arc, i) in capacityArcs" :key="'pl'+i" :x="arc.lx" :y="arc.ly" text-anchor="middle" dominant-baseline="central" font-size="11" fill="#fff" font-weight="600">{{ arc.pct }}%</text>
            </svg>
            <div class="pie-legend">
              <span v-for="(arc, i) in capacityArcs" :key="'plg'+i" class="legend-item">
                <span class="legend-color" :style="{ background: arc.color }"></span>{{ arc.name }} {{ arc.value }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 电力电量平衡表单图 -->
      <div class="card" style="margin-top: 20px;">
        <h3 class="card-title">电力电量平衡结果</h3>
        <div class="svg-chart-wrap" style="height: 260px;">
          <svg viewBox="0 0 700 260" class="svg-chart">
            <line x1="50" y1="10" x2="50" y2="230" stroke="#e0e0e0" stroke-width="1"/>
            <line x1="50" y1="230" x2="690" y2="230" stroke="#e0e0e0" stroke-width="1"/>
            <text x="50" y="10" font-size="10" fill="#666" text-anchor="middle">功率(MW)</text>
            <text v-for="(v, i) in balanceYLabels" :key="i" :x="46" :y="230 - (i/3)*210 + 4" text-anchor="end" font-size="10" fill="#999">{{ v }}</text>
            <polygon :points="balanceAreaPoints" fill="rgba(255,72,72,0.8)" stroke="none"/>
            <polygon :points="windAreaPoints" fill="rgba(76,175,80,0.8)" stroke="none"/>
            <polygon :points="solarAreaPoints" fill="rgba(255,215,0.8)" stroke="none"/>
            <polygon :points="hydroAreaPoints" fill="rgba(24,144,255,0.8)" stroke="none"/>
            <polyline :points="loadLinePoints" fill="none" stroke="#333" stroke-width="2"/>
            
            <!-- X轴刻度和标签（适配96时段） -->
            <template v-for="i in maxPeriods" :key="'x-balance-'+i">
              <text v-if="i % 8 === 0" :x="50 + (i - 0.5) * 6.67" y="250" text-anchor="middle" font-size="9" fill="#666">{{ i }}</text>
              <line :x1="50 + i * 6.67" :y1="230" :x2="50 + i * 6.67" :y2="235" stroke="#e0e0e0" stroke-width="1"/>
            </template>
          </svg>
        </div>
        <div class="legend-row">
          <span class="legend-item"><span class="legend-color" style="background:rgba(255,72,72,0.8)"></span>火电功率</span>
          <span class="legend-item"><span class="legend-color" style="background:rgba(76,175,80,0.8)"></span>风电功率</span>
          <span class="legend-item"><span class="legend-color" style="background:rgba(255,215,0.8)"></span>光伏功率</span>
          <span class="legend-item"><span class="legend-color" style="background:rgba(24,144,255,0.8)"></span>水电功率</span>
          <span class="legend-item"><span class="legend-color" style="background:#333"></span>总负荷功率</span>
        </div>
      </div>

      <!-- 出清电价图表 -->
      <div class="card" style="margin-top: 20px;">
        <h3 class="card-title">电能量市场出清电价</h3>
        <div class="svg-chart-wrap">
          <svg viewBox="0 0 700 220" class="svg-chart">
            <line x1="50" y1="10" x2="50" y2="200" stroke="#e0e0e0" stroke-width="1"/>
            <line x1="50" y1="200" x2="690" y2="200" stroke="#e0e0e0" stroke-width="1"/>
            <text x="50" y="10" font-size="10" fill="#666" text-anchor="middle">电价(元/MWh)</text>
            <text v-for="(v, i) in [0, 100, 200, 300]" :key="i" :x="45" :y="200 - i * 60 + 4" text-anchor="end" font-size="11" fill="#999">{{ v }}</text>
            <polyline :points="clearingChartPoints" fill="none" stroke="#1890ff" stroke-width="2"/>
            
            <!-- X轴刻度和标签（适配96时段） -->
            <template v-for="i in maxPeriods" :key="'x-clearing-'+i">
              <text v-if="i % 8 === 0" :x="50 + (i - 0.5) * 6.67" y="218" text-anchor="middle" font-size="9" fill="#666">{{ i }}</text>
              <line :x1="50 + i * 6.67" :y1="200" :x2="50 + i * 6.67" :y2="205" stroke="#e0e0e0" stroke-width="1"/>
            </template>
          </svg>
        </div>
      </div>


    </div>

    <!-- 详情分析 -->
    <div v-if="settlementTab === 'analysis'">
      <div class="card">
        <!-- 标题随日期变化 -->
        <h3 class="card-title">{{ currentDayLabel }} 公司中标结果</h3>
        <!-- 企业中标结果 - 标签数据格式（两行，每行四个） -->
        <div v-if="g13SettlementData" class="g13-settlement-results">
          <!-- 第一行：成本相关 -->
          <div class="result-row row-4">
            <div class="result-item">
              <div class="result-label">火电厂名称</div>
              <div class="result-value">{{ g13SettlementData.name || 'G13' }}</div>
            </div>
            <div class="result-item">
              <div class="result-label">运行成本 (万元)</div>
              <div class="result-value">{{ formatNumber(g13SettlementData.opCost) }}</div>
            </div>
            <div class="result-item">
              <div class="result-label">开机成本 (万元)</div>
              <div class="result-value">{{ formatNumber(g13SettlementData.startCost) }}</div>
            </div>
            <div class="result-item">
              <div class="result-label">关机成本 (万元)</div>
              <div class="result-value">{{ formatNumber(g13SettlementData.stopCost) }}</div>
            </div>
          </div>
          <!-- 第二行：出力与收益相关 -->
          <div class="result-row row-4">
            <div class="result-item">
              <div class="result-label">总中标出力 (MW)</div>
              <div class="result-value">{{ formatNumber(g13SettlementData.output) }}</div>
            </div>
            <div class="result-item">
              <div class="result-label">中标电量均价 (元/MWh)</div>
              <div class="result-value">{{ formatNumber(g13SettlementData.avgPrice) }}</div>
            </div>
            <div class="result-item">
              <div class="result-label">总中标收益 (万元)</div>
              <div class="result-value">{{ formatNumber(g13SettlementData.revenue) }}</div>
            </div>
            <div class="result-item">
              <div class="result-label">净收益 (万元)</div>
              <div class="result-value">{{ formatNumber(g13SettlementData.netIncome) }}</div>
            </div>
          </div>
        </div>
        <div v-else class="no-data">
          <p>暂无企业的中标结果数据</p>
        </div>
      </div>

      <!-- 自主报价结果 -->
      <div class="card" style="margin-top: 20px; overflow: visible;">
        
        <div>
          
          
          <!-- 中标出力与均价折线图 -->
          <div class="card" style="margin-top: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <h3 class="card-title" style="margin: 0;">中标出力与均价</h3>
              <select 
                v-model="selectedUnitId" 
                style="padding: 4px 8px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 12px; color: #333;"
                :disabled="!currentCompany || !currentCompany.units || currentCompany.units.length === 0"
              >
                <option 
                  v-for="unit in currentCompany?.units || []" 
                  :key="unit.id"
                  :value="unit.id"
                >
                  机组{{ unit.id.replace('Thermal_', '') }}
                </option>
              </select>
            </div>
            <div class="svg-chart-wrap">
              <svg viewBox="0 0 750 220" class="svg-chart" @click="handleChartClick">
                <!-- 左侧 Y 轴 -->
                <line x1="80" y1="10" x2="80" y2="200" stroke="#e0e0e0" stroke-width="1"/>
                <!-- 右侧 Y 轴（副坐标轴） -->
                <line x1="720" y1="10" x2="720" y2="200" stroke="#e0e0e0" stroke-width="1"/>
                <!-- X 轴 -->
                <line x1="80" y1="200" x2="720" y2="200" stroke="#e0e0e0" stroke-width="1"/>
                <!-- 左侧 Y 轴标签（出力） -->
                <text x="80" y="10" font-size="10" fill="#1890ff" text-anchor="middle">出力 (MW)</text>
                <!-- Y 轴刻度标签 - 显示全部 6 个刻度 (5 等分) -->
                <text v-for="(v, i) in barYLabels" :key="'left-'+i" :x="75" :y="200 - i * 36 + 4" text-anchor="end" font-size="11" fill="#1890ff">{{ v }}</text>
                <!-- 右侧 Y 轴标签（均价） -->
                <text x="720" y="10" font-size="10" fill="#faad14" text-anchor="middle">均价 (元/MWh)</text>
                <!-- Y 轴刻度标签 - 显示在右侧 Y 轴右边 (5 等分) -->
                <text v-for="(v, i) in priceYLabels" :key="'right-'+i" :x="725" :y="200 - i * 36 + 4" text-anchor="start" font-size="11" fill="#faad14">{{ v }}</text>
                <!-- 中标出力折线 -->
                <polyline v-if="outputLinePath" :points="outputLinePath" fill="none" stroke="#1890ff" stroke-width="2"/>
                <!-- 中标均价折线（副坐标轴） -->
                <polyline v-if="priceLinePathDual" :points="priceLinePathDual" fill="none" stroke="#faad14" stroke-width="2"/>
                
                <!-- 数据点圆圈 - 出力 -->
                <template v-if="selectedPeriod !== null && unitBidOutputValues[selectedPeriod]">
                  <circle 
                    :cx="80 + selectedPeriod * 6.67" 
                    :cy="200 - (Number(unitBidOutputValues[selectedPeriod]) / (maxOutput || 1)) * 180"
                    r="6"
                    fill="#1890ff"
                    stroke="#fff"
                    stroke-width="2"
                    style="pointer-events: none;"
                  />
                </template>
                
                <!-- 数据点圆圈 - 均价 -->
                <template v-if="selectedPeriod !== null && unitBidPriceValues[selectedPeriod]">
                  <circle 
                    :cx="80 + selectedPeriod * 6.67" 
                    :cy="200 - (Number(unitBidPriceValues[selectedPeriod]) / (maxPrice || 1)) * 180"
                    r="6"
                    fill="#faad14"
                    stroke="#fff"
                    stroke-width="2"
                    style="pointer-events: none;"
                  />
                </template>
                
                <!-- 图例 -->
                <g transform="translate(300, 10)">
                  <line x1="0" y1="4" x2="20" y2="4" stroke="#1890ff" stroke-width="2"/>
                  <text x="25" y="8" font-size="10" fill="#666">中标出力</text>
                  <line x1="80" y1="4" x2="100" y2="4" stroke="#faad14" stroke-width="2"/>
                  <text x="105" y="8" font-size="10" fill="#666">中标均价</text>
                </g>
                
                <template v-for="i in maxPeriods" :key="'x-output-'+i">
                  <text v-if="i % 8 === 0" :x="80 + (i - 0.5) * 6.67" y="218" text-anchor="middle" font-size="9" fill="#666">{{ i }}</text>
                  <line :x1="80 + i * 6.67" :y1="200" :x2="80 + i * 6.67" :y2="205" stroke="#e0e0e0" stroke-width="1"/>
                </template>
                
                <!-- 提示框背景 -->
                <g v-if="selectedPeriod !== null" :transform="`translate(${Math.min(550, 80 + selectedPeriod * 6.67)}, 10)`">
                  <rect x="-5" y="-5" width="160" height="85" fill="rgba(255, 255, 255, 0.95)" stroke="#d9d9d9" stroke-width="1" rx="4"/>
                  <text x="5" y="12" font-size="11" font-weight="bold" fill="#333">时段 {{ selectedPeriod + 1 }}</text>
                  <line x1="5" y1="20" x2="150" y2="20" stroke="#e0e0e0" stroke-width="1"/>
                  <text x="5" y="35" font-size="10" fill="#1890ff">出力：<tspan font-weight="bold">{{ unitBidOutputValues[selectedPeriod]?.toFixed(2) || 0 }}</tspan> MW</text>
                  <text x="5" y="52" font-size="10" fill="#faad14">均价：<tspan font-weight="bold">{{ unitBidPriceValues[selectedPeriod]?.toFixed(2) || 0 }}</tspan> 元/MWh</text>
                  <text x="5" y="69" font-size="10" fill="#52c41a">收益：<tspan font-weight="bold">{{ unitBidRevenueValues[selectedPeriod]?.toFixed(2) || 0 }}</tspan> 元</text>
                </g>
              </svg>
            </div>
          </div>

          <!-- 中标收益折线图 -->
          <div class="card" style="margin-top: 20px;">
            <h3 class="card-title">中标收益</h3>
            <div class="svg-chart-wrap">
              <svg viewBox="0 0 750 220" class="svg-chart" @click="handleRevenueChartClick">
                <line x1="80" y1="10" x2="80" y2="200" stroke="#e0e0e0" stroke-width="1"/>
                <line x1="80" y1="200" x2="720" y2="200" stroke="#e0e0e0" stroke-width="1"/>
                <text x="80" y="10" font-size="10" fill="#666" text-anchor="middle">收益 (元)</text>
                <!-- Y 轴刻度标签 - 显示全部 6 个刻度 (5 等分) -->
                <text v-for="(v, i) in revenueYLabels" :key="i" :x="75" :y="200 - i * 36 + 4" text-anchor="end" font-size="11" fill="#999">{{ v }}</text>
                <polyline v-if="revenueLinePath" :points="revenueLinePath" fill="none" stroke="#52c41a" stroke-width="2"/>
                
                <!-- 数据点圆圈 - 收益 -->
                <template v-if="selectedPeriod !== null && unitBidRevenueValues[selectedPeriod]">
                  <circle 
                    :cx="80 + selectedPeriod * 6.67" 
                    :cy="200 - (Number(unitBidRevenueValues[selectedPeriod]) / (maxRevenue || 1)) * 180"
                    r="6"
                    fill="#52c41a"
                    stroke="#fff"
                    stroke-width="2"
                    style="pointer-events: none;"
                  />
                </template>

                <template v-for="i in maxPeriods" :key="'x-revenue-'+i">
                  <text v-if="i % 8 === 0" :x="80 + (i - 0.5) * 6.67" y="218" text-anchor="middle" font-size="9" fill="#666">{{ i }}</text>
                  <line :x1="80 + i * 6.67" :y1="200" :x2="80 + i * 6.67" :y2="205" stroke="#e0e0e0" stroke-width="1"/>
                </template>
                
                <!-- 提示框背景 -->
                <g v-if="selectedPeriod !== null" :transform="`translate(${Math.min(550, 80 + selectedPeriod * 6.67)}, 10)`">
                  <rect x="-5" y="-5" width="120" height="50" fill="rgba(255, 255, 255, 0.95)" stroke="#d9d9d9" stroke-width="1" rx="4"/>
                  <text x="5" y="12" font-size="11" font-weight="bold" fill="#333">时段 {{ selectedPeriod + 1 }}</text>
                  <line x1="5" y1="20" x2="110" y2="20" stroke="#e0e0e0" stroke-width="1"/>
                  <text x="5" y="35" font-size="10" fill="#52c41a">收益：<tspan font-weight="bold">{{ unitBidRevenueValues[selectedPeriod]?.toFixed(2) || 0 }}</tspan> 元</text>
                </g>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from "vue";
import { marketApi } from "../api/market";
import { getCurrentAdmin } from "../api/admin";

// 定义类型接口 - 解决 any 类型问题
interface HistoryEnergyItem {
  row_index: number | string;
  values: (number | string)[];
}

interface DateTab {
  key: number;
  label: string;
}

// 电力电量平衡图表数据结构
interface BalanceChartData {
  thermal: number[];  // 火电功率
  wind: number[];     // 风电功率
  solar: number[];    // 光伏功率
  hydro: number[];    // 水电功率
  load: number[];     // 总负荷功率
  periods: number;    // 时段数 (通常为 96)
}

// 机组中标结果数据结构
interface OutputUnitBidResults {
  output_values: number[];   // 中标出力数据 (MW), 96 个时段
  price_values: number[];    // 中标均价数据 (元/MWh), 96 个时段
  revenue_values: number[];  // 中标收益数据 (元), 96 个时段
  case_id: string;           // 案例 ID (如 Output14)
  date_str: string;          // 日期字符串 (如 20260319)
  unit_id: string;           // 机组 ID (如 Thermal_1)
}

// 中标数据相关响应式变量
const unitBidOutputValues = ref<number[]>([]);   // 中标出力
const unitBidPriceValues = ref<number[]>([]);    // 中标均价
const unitBidRevenueValues = ref<number[]>([]);  // 中标收益
const unitBidLoading = ref<boolean>(false);
const selectedPeriod = ref<number | null>(null); // 当前选中的时段索引 (0-95)

// 柱状图颜色配置
const barColors = [
  "#1890ff", "#722ed1", "#f5222d", "#fa8c16", 
  "#52c41a", "#13c2c2", "#eb2f96", "#fadb14"
];

// 选中机组ID（响应式）
const selectedUnitId = ref<string>("");

// 最大时段数（基于中标出力数据）
const maxPeriods = computed<number>(() => {
  return unitBidOutputValues.value.length || 96;
});

// 中标出力数据（用于折线图）
const selectedUnitOutputData = computed(() => {
  if (!unitBidOutputValues.value.length) return null;
  return {
    values: unitBidOutputValues.value
  };
});

// 中标均价数据（用于折线图）
const selectedUnitPriceData = computed(() => {
  if (!unitBidPriceValues.value.length) return null;
  return {
    values: unitBidPriceValues.value
  };
});

// 中标出力最大值计算
const maxOutput = computed<number>(() => {
  if (!unitBidOutputValues.value.length) return 1;
  let max = 1;
  unitBidOutputValues.value.forEach((v) => {
    const numVal = Number(v);
    if (!isNaN(numVal) && numVal > max) max = numVal;
  });
  // 向上取整到百位，并确保有足够的显示空间
  return Math.ceil(max / 100) * 100;
});

// Y 轴刻度标签 (出力)
const barYLabels = computed<number[]>(() => {
  const max = maxOutput.value;
  // 使用更合理的刻度间隔，确保清晰易读
  const step = max / 5;
  return [
    0,
    Math.round(step),
    Math.round(step * 2),
    Math.round(step * 3),
    Math.round(step * 4),
    max
  ];
});

// 中标均价最大值计算 - 修复初始值过大导致图表压缩的问题
const maxPrice = computed<number>(() => {
  if (!unitBidPriceValues.value.length) return 500; // 降低默认值到合理范围
  let max = 0;
  // 找出实际最大值
  unitBidPriceValues.value.forEach((v) => {
    const numVal = Number(v);
    if (!isNaN(numVal) && numVal > max) max = numVal;
  });
  // 如果最大值为 0，使用默认值
  if (max === 0) return 500;
  // 向上取整到十位，确保显示更精确
  return Math.ceil(max / 10) * 10;
});

// 中标均价 Y 轴刻度标签
const priceYLabels = computed<number[]>(() => {
  const max = maxPrice.value;
  // 使用 5 等分刻度，确保清晰易读
  const step = max / 5;
  return [
    0,
    Math.round(step),
    Math.round(step * 2),
    Math.round(step * 3),
    Math.round(step * 4),
    max
  ];
});

// 中标均价副坐标轴路径 (与出力共用 X 轴，但使用右侧 Y 轴比例)
const priceLinePathDual = computed<string>(() => {
  if (!selectedUnitPriceData.value || !selectedUnitPriceData.value.values.length) {
    return "";
  }
  
  const maxVal = maxPrice.value;
  // SVG 图表 Y 轴范围：从 y=200(底部) 到 y=20(顶部)，共 180px
  // 数据值 0 对应 y=200，最大值对应 y=20
  const points = selectedUnitPriceData.value.values.map((value, idx) => {
    const x = 80 + idx * 6.67;
    // 正确的坐标转换：y = 200 - (实际值 / 最大值) * 180
    const y = 200 - (Number(value) / maxVal) * 180;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  
  return points.join(" ");
});

// 中标出力折线路径
const outputLinePath = computed<string>(() => {
  if (!selectedUnitOutputData.value || !selectedUnitOutputData.value.values.length) return "";
  const maxVal = maxOutput.value;
  const points = selectedUnitOutputData.value.values.map((value, idx) => {
    const x = 80 + idx * 6.67;
    // 坐标转换：y = 200 - (实际值 / 最大值) * 180
    const y = 200 - (Number(value) / maxVal) * 180;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return points.join(" ");
});

// 中标收益折线路径
const revenueLinePath = computed<string>(() => {
  if (!unitBidRevenueValues.value.length) return "";
  const maxVal = maxRevenue.value || 1;
  const points = unitBidRevenueValues.value.map((value, idx) => {
    const x = 80 + idx * 6.67;  // 与出力折线保持一致的 X 轴起始位置
    const y = 200 - (Number(value) / maxVal) * 180;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return points.join(" ");
});

// 中标收益最大值计算 - 根据实际数据动态调整 (优化默认值和取整逻辑)
const maxRevenue = computed<number>(() => {
  if (!unitBidRevenueValues.value.length) return 40000; // 提高默认值以覆盖更大数据范围
  let max = 0;
  // 找出实际最大值
  unitBidRevenueValues.value.forEach((v) => {
    const numVal = Number(v);
    if (!isNaN(numVal) && numVal > max) max = numVal;
  });
  // 如果最大值为 0，使用默认值
  if (max === 0) return 40000;
  // 向上取整到千位，并增加 15% 余量使图表更美观且留出足够空间
  const withMargin = max * 1.15;
  return Math.ceil(withMargin / 1000) * 1000;
});

// 中标收益 Y 轴刻度标签
const revenueYLabels = computed<number[]>(() => {
  const max = maxRevenue.value;
  // 使用 5 等分刻度，确保清晰易读
  const step = max / 5;
  return [
    0,
    Math.round(step),
    Math.round(step * 2),
    Math.round(step * 3),
    Math.round(step * 4),
    max
  ];
});

// 饼状图数据
const pieColors = ["rgba(76,175,80,0.8)", "rgba(255,215,0.8)", "rgba(24,144,255,0.8)", "rgba(255,72,72,0.8)", "rgba(114,46,209,0.8)"];
const pieTypes = ["风电", "光伏", "水电", "火电", "电化学储能", "抽蓄电站"];

// 机组数量分布数据
const countPieData = computed(() => {
  const em = overviewData.value.energy_market;
  if (!em) return [];
  const raw = [
    { name: "风电", value: em.wind_count || 0 },
    { name: "光伏", value: em.solar_count || 0 },
    { name: "水电", value: em.hydro_count || 0 },
    { name: "火电", value: em.thermal_count || 0 },
    { name: "电化学储能", value: em.storage_count || 0 },
    { name: "抽蓄电站", value: em.pumped_storage_count || 0 },
  ];
  return raw.filter(d => d.value > 0);
});

// 装机容量分布数据
const capacityPieData = computed(() => {
  const em = overviewData.value.energy_market;
  if (!em) return [];
  const raw = [
    { name: "风电", value: em.wind_capacity || 0 },
    { name: "光伏", value: em.solar_capacity || 0 },
    { name: "水电", value: em.hydro_capacity || 0 },
    { name: "火电", value: em.thermal_capacity || 0 },
    { name: "电化学储能", value: 0 },
    { name: "抽蓄电站", value: 0 },
  ];
  return raw.filter(d => d.value > 0);
});

// 生成饼状图路径
function pieArcs(data: { name: string; value: number }[]) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return [];
  const cx = 90, cy = 90, r = 80;
  let startAngle = -Math.PI / 2;
  return data.map((d, i) => {
    const angle = (d.value / total) * Math.PI * 2;
    const endAngle = startAngle + angle;
    const x1 = cx + r * Math.cos(startAngle);
    const y1 = cy + r * Math.sin(startAngle);
    const x2 = cx + r * Math.cos(endAngle);
    const y2 = cy + r * Math.sin(endAngle);
    const large = angle > Math.PI ? 1 : 0;
    const path = data.length === 1
      ? `M ${cx} ${cy - r} A ${r} ${r} 0 1 1 ${cx - 0.01} ${cy - r} Z`
      : `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2} Z`;
    const midAngle = startAngle + angle / 2;
    const labelR = r * 0.6;
    const lx = cx + labelR * Math.cos(midAngle);
    const ly = cy + labelR * Math.sin(midAngle);
    const pct = Math.round(d.value / total * 100);
    startAngle = endAngle;
    const colorIdx = pieTypes.indexOf(d.name);
    return { path, color: pieColors[colorIdx >= 0 ? colorIdx : i], name: d.name, value: d.value, pct, lx, ly };
  });
}

// 机组数量饼图
const countArcs = computed(() => pieArcs(countPieData.value));
// 装机容量饼图
const capacityArcs = computed(() => pieArcs(capacityPieData.value));

// 平衡图表最大 Y 值
const balanceMaxY = computed(() => {
  const bc = balanceChart.value || {};
  const thermal = bc.thermal || [];
  const load = bc.load || [];
  const wind = bc.wind || [];
  const solar = bc.solar || [];
  const hydro = bc.hydro || [];
  
  const all = [
    ...thermal,
    ...load,
    ...(thermal.map((v: number, i: number) => v + (wind[i] || 0) + (solar[i] || 0) + (hydro[i] || 0))),
  ];
  return Math.max(...all, 1);
});

// 平衡图表 Y 坐标转换
const toBalanceY = (v: number) => {
  const max = balanceMaxY.value;
  return 230 - (v / max) * 210;
};

// 火电区域坐标
const balanceAreaPoints = computed(() => {
  const data = balanceChart.value?.thermal || [];
  if (!data.length) return "";
  const n = data.length;
  const step = 640 / (n - 1);
  const top = data.map((v: number, i: number) => `${(50 + i * step).toFixed(1)},${toBalanceY(v).toFixed(1)}`);
  const bottom = `${(50 + (n - 1) * step).toFixed(1)},${toBalanceY(0)} 50,${toBalanceY(0)}`;
  return top.join(" ") + " " + bottom;
});

// 风电区域坐标
const windAreaPoints = computed(() => {
  const thermal = balanceChart.value?.thermal || [];
  const wind = balanceChart.value?.wind || [];
  if (!thermal.length || !wind.length) return "";
  const n = thermal.length;
  const step = 640 / (n - 1);
  const top = wind.map((_: number, i: number) => `${(50 + i * step).toFixed(1)},${toBalanceY(thermal[i] + wind[i]).toFixed(1)}`);
  const bottom = thermal.map((v: number, i: number) => `${(50 + i * step).toFixed(1)},${toBalanceY(v).toFixed(1)}`).reverse();
  return top.join(" ") + " " + bottom.join(" ");
});

// 光伏区域坐标
const solarAreaPoints = computed(() => {
  const thermal = balanceChart.value?.thermal || [];
  const wind = balanceChart.value?.wind || [];
  const solar = balanceChart.value?.solar || [];
  if (!thermal.length || !wind.length || !solar.length) return "";
  const n = thermal.length;
  const step = 640 / (n - 1);
  const top = solar.map((_: number, i: number) => `${(50 + i * step).toFixed(1)},${toBalanceY(thermal[i] + wind[i] + solar[i]).toFixed(1)}`);
  const bottom = wind.map((_: number, i: number) => `${(50 + i * step).toFixed(1)},${toBalanceY(thermal[i] + wind[i]).toFixed(1)}`).reverse();
  return top.join(" ") + " " + bottom.join(" ");
});

// 水电区域坐标
const hydroAreaPoints = computed(() => {
  const thermal = balanceChart.value?.thermal || [];
  const wind = balanceChart.value?.wind || [];
  const solar = balanceChart.value?.solar || [];
  const hydro = balanceChart.value?.hydro || [];
  if (!thermal.length || !wind.length || !solar.length || !hydro.length) return "";
  const n = thermal.length;
  const step = 640 / (n - 1);
  const top = hydro.map((_: number, i: number) => `${(50 + i * step).toFixed(1)},${toBalanceY(thermal[i] + wind[i] + solar[i] + hydro[i]).toFixed(1)}`);
  const bottom = solar.map((_: number, i: number) => `${(50 + i * step).toFixed(1)},${toBalanceY(thermal[i] + wind[i] + solar[i]).toFixed(1)}`).reverse();
  return top.join(" ") + " " + bottom.join(" ");
});

// 负荷线坐标
const loadLinePoints = computed(() => {
  const data = balanceChart.value?.load || [];
  if (!data.length) return "";
  const n = data.length;
  const step = 640 / (n - 1);
  return data.map((v: number, i: number) => `${(50 + i * step).toFixed(1)},${toBalanceY(v).toFixed(1)}`).join(" ");
});

// 平衡图表Y轴标签
const balanceYLabels = computed(() => {
  const max = balanceMaxY.value;
  return [0, Math.round(max / 3), Math.round(max * 2 / 3), Math.round(max)];
});

// 出清电价图表坐标
const clearingChartPoints = computed(() => {
  const vals = energyPriceData.value;
  if (!vals.length) return "";
  const maxVal = Math.max(...vals, 1);
  const step = 640 / Math.max(vals.length - 1, 1);
  return vals.map((v, i) => `${(50 + i * step).toFixed(1)},${(200 - (v / maxVal) * 180).toFixed(1)}`).join(" ");
});

// 日期标签配置
const dateTabs: DateTab[] = [
  { key: 1, label: "第一天" },
  { key: 2, label: "第二天" },
  { key: 3, label: "第三天" },
  { key: 4, label: "第四天" },
  { key: 5, label: "第五天" },
  { key: 6, label: "第六天" },
  { key: 7, label: "第七天" }
];

// 核心状态
const settlementTab = ref<string>("overview");
const currentDay = ref<number>(1);
const overviewData = ref<any>({ energy_market: {} });
const settlementRows = ref<any[]>([]);
const g13SettlementData = ref<any>(null);
const historyEnergyDetail = ref<HistoryEnergyItem[]>([]); // 修复：指定具体类型
const balanceChart = ref<BalanceChartData>({ thermal: [], wind: [], solar: [], hydro: [], load: [], periods: 96 });
const energyPriceData = ref<number[]>([]);
const currentUser = ref<any>(null);
const currentCompany = ref<any>(null);

// 当前日期标签文本
const currentDayLabel = computed(() => {
  const dayItem = dateTabs.find(item => item.key === currentDay.value);
  return dayItem?.label || "第一天";
});

// Tab切换处理
const handleTabChange = (tabKey: string) => {
  settlementTab.value = tabKey;
  refreshAllData();
};

// 日期切换处理
const handleDayChange = (dayKey: number) => {
  currentDay.value = dayKey;
  refreshAllData();
};

// 数字格式化方法
const formatNumber = (val: any): string => {
  if (val === null || val === undefined || val === '') {
    return '0';
  }
  const num = parseFloat(val);
  if (isNaN(num)) {
    return '0';
  }
  // 保留两位小数，末尾0舍去
  let str = num.toFixed(2);
  if (str.includes('.')) {
    str = str.replace(/\.?0+$/, '');
  }
  return str;
};

// 数据刷新统一入口
const refreshAllData = async () => {
  console.log(`刷新数据：${currentDayLabel.value} - ${settlementTab.value === 'overview' ? '市场总览' : '详情分析'}`);
  await fetchCurrentCompany();
  fetchSettlementData();
  fetchHistoryDetail();
  fetchBalanceChart();
  fetchEnergyPriceChart();
};

// 获取当前用户信息
async function fetchCurrentUser() {
  try {
    const user = await getCurrentAdmin();
    currentUser.value = user;
    console.log("当前用户:", user);
    return user;
  } catch (e: any) {
    console.error("获取用户信息失败", e);
    return null;
  }
}

// 获取当前用户的企业信息
async function fetchCurrentCompany() {
  try {
    const user = await fetchCurrentUser();
    if (!user) {
      return null;
    }
    
    const { data } = await marketApi.getCompanies();
    const companies = data.items || [];
    const companyCode = user.username;
    currentCompany.value = companies.find((c: any) => c.name === companyCode) || null;
    console.log("当前企业:", currentCompany.value);
    // 设置默认选中的机组
    if (currentCompany.value && currentCompany.value.units && currentCompany.value.units.length > 0) {
      selectedUnitId.value = currentCompany.value.units[0].id;
    }
    return currentCompany.value;
  } catch (e: any) {
    console.error("获取企业信息失败", e);
    return null;
  }
}

// 获取结算数据
async function fetchSettlementData() {
  try {
    console.log("=== [调试] 开始获取结算数据 ===");
    console.log(`[调试] 当前选择的日期：第 ${currentDay.value} 天`);
    
    const user = await fetchCurrentUser();
    console.log("[调试] 当前用户:", user);
    console.log("[调试] 用户名:", user?.username);
    
    console.log("[调试] 调用 settlement-overview API...");
    // 传递当前选择的日期索引
    const ov = await marketApi.getSettlementOverview(currentDay.value);
    console.log("[调试] API 返回状态码:", ov.status);
    console.log("[调试] API 返回 headers:", JSON.stringify(ov.headers));
    console.log("[调试] API 返回完整响应对象:", ov);
    console.log("[调试] API 返回 data 属性:", ov.data);
    console.log("[调试] API 返回完整数据 JSON:", JSON.stringify(ov.data, null, 2));
    
    // 检查响应数据结构
    if (!ov.data) {
      console.error("[调试] ❌ 错误：API 返回的 data 为 null!");
      overviewData.value = { energy_market: {} };
      return;
    }
    
    // 检查 data 是否有 energy_market 字段
    console.log("[调试] ov.data 的键名列表:", Object.keys(ov.data));
    console.log("[调试] ov.data.energy_market 类型:", typeof ov.data.energy_market);
    console.log("[调试] ov.data.energy_market 是否为对象:", ov.data.energy_market instanceof Object);
    
    if (ov.data.energy_market) {
      console.log("[调试] energy_market 数据:", ov.data.energy_market);
      console.log("[调试] avg_price:", ov.data.energy_market.avg_price);
      console.log("[调试] total_generation:", ov.data.energy_market.total_generation);
      console.log("[调试] energy_market 字段数量:", Object.keys(ov.data.energy_market).length);
      
      // 逐个字段检查
      console.log("[调试] 检查 avg_price 字段值:", ov.data.energy_market.avg_price);
      console.log("[调试] avg_price 是否为 undefined:", ov.data.energy_market.avg_price === undefined);
      console.log("[调试] avg_price 是否为 null:", ov.data.energy_market.avg_price === null);
    } else {
      console.warn("[调试] ⚠️ 警告：energy_market 为空或不存在!");
      console.log("[调试] ov.data 的所有键名:", Object.keys(ov.data));
    }
    
    overviewData.value = ov.data;
    console.log("[调试] overviewData 已赋值:", overviewData.value);
    console.log("[调试] overviewData.energy_market:", overviewData.value?.energy_market);
    console.log("[调试] overviewData.energy_market.avg_price:", overviewData.value?.energy_market?.avg_price);
    
    // 使用 nextTick 确保响应式更新完成
    await nextTick();
    console.log("[调试] [nextTick 后] overviewData:", overviewData.value);
    console.log("[调试] [nextTick 后] energy_market.avg_price:", overviewData.value?.energy_market?.avg_price);
    
    console.log("\n[调试] 调用 settlement-detail API...");
    // 传递当前选择的日期索引
    const dt = await marketApi.getSettlementDetail(currentDay.value);
    console.log("[调试] settlement-detail 返回数据:", dt.data);
    
    settlementRows.value = dt.data.energy_rows || [];
    console.log("[调试] settlementRows 长度:", settlementRows.value.length);
    console.log("[调试] settlementRows 数据:", settlementRows.value);
    
    // 根据用户的用户名查找对应的企业结算数据
    const companyCode = user?.username || "G13";
    g13SettlementData.value = settlementRows.value.find((row: any) => row.name === companyCode) || null;
    console.log("[调试] 企业结算数据 (companyCode=" + companyCode + "):", g13SettlementData.value);
    
    console.log("\n=== [调试] 结算数据获取完成 ===");
  } catch (e: any) { 
    console.error("❌ 获取结算数据失败", e);
    console.error("错误堆栈:", e.stack);
    // 只在 overviewData 为空时才设置默认值，避免覆盖已有数据
    if (!overviewData.value || !overviewData.value.energy_market) {
      overviewData.value = { energy_market: {} };
    }
  }
}

// 获取历史详情数据（添加兜底测试数据）
async function fetchHistoryDetail() {
  try {
    const res = await marketApi.getOutResults({ sheet: "thermal_tg_opera_power" });
    const rawItems = res.data?.items || [];
    // 过滤有效数据 - 修复：指定item类型
    historyEnergyDetail.value = rawItems.filter((item: HistoryEnergyItem) => 
      Array.isArray(item?.values) && item.values.length > 0
    );
    // 兜底：无数据时生成测试数据（8个机组，96时段）
    if (historyEnergyDetail.value.length === 0) {
      historyEnergyDetail.value = Array.from({ length: 8 }, (_, idx) => ({
        row_index: idx,
        values: Array.from({ length: 96 }, () => Math.floor(Math.random() * 200) + 50)
      }));
    }
  } catch (e: any) { 
    console.error("获取历史详情失败", e);
    // 报错时生成测试数据
    historyEnergyDetail.value = Array.from({ length: 8 }, (_, idx) => ({
      row_index: idx,
      values: Array.from({ length: 96 }, () => Math.floor(Math.random() * 200) + 50)
    }));
  }
}

// 获取平衡图表数据（自主申报页面用）
async function fetchBalanceChart() {
  try {
    // 调用新的 energy-balance API，传递当前选择的日期索引
    // useDefaultCase=false 表示使用用户关联的 case_id（自主申报）
    const { data } = await marketApi.getEnergyBalance(currentDay.value, false);
    balanceChart.value = data;
    console.log(`[电力电量平衡] 第${currentDay.value}天数据:`, data);
  } catch (e: any) { 
    console.error("获取电力电量平衡数据失败", e);
    // 报错时使用空数据
    balanceChart.value = { thermal: [], wind: [], solar: [], hydro: [], load: [], periods: 96 };
  }
}

// 获取出清电价数据（保留用于其他可能需要的地方）
async function fetchEnergyPriceChart() {
  try {
    // 使用新的出清价格 API，根据当前选择的机组和日期获取数据
    // useDefaultCase=false 表示使用用户关联的 case_id（自主申报）
    let unitId = selectedUnitId.value;
    
    // 如果没有选择机组，尝试从当前公司获取第一个机组
    if (!unitId && currentCompany.value && currentCompany.value.units && currentCompany.value.units.length > 0) {
      unitId = currentCompany.value.units[0].id;
      selectedUnitId.value = unitId; // 设置默认选中
    }
    
    // 如果仍然没有机组ID，使用默认值
    unitId = unitId || "Thermal_1";
    
    const { data } = await marketApi.getClearingPrice(unitId, currentDay.value, false);
    const items = data.items || []; // API 返回的数据结构是 {items: [...], case_id: "...", date_str: "..."}
    energyPriceData.value = items.length > 0 ? items[0].values : [];
    console.log(`[出清电价] 第${currentDay.value}天，机组${unitId}:`, energyPriceData.value);
  } catch (e: any) { 
    console.error("获取出清电价失败", e);
    energyPriceData.value = [];
  }
}

// 获取机组中标结果数据（中标出力、均价、收益）
async function fetchUnitBidResults() {
  if (!selectedUnitId.value) {
    console.warn("[中标数据] 未选择机组");
    return;
  }
  
  unitBidLoading.value = true;
  
  try {
    console.log(`[中标数据] 开始获取 - 机组:${selectedUnitId.value}, 日期：第${currentDay.value}天`);
    
    const data = await marketApi.getUnitBidResults(
      selectedUnitId.value,
      currentDay.value
    );
    
    console.log("[中标数据] API 返回:", data);

    // 赋值给响应式变量
    unitBidOutputValues.value = data.output_values || [];
    unitBidPriceValues.value = data.price_values || [];
    unitBidRevenueValues.value = data.revenue_values || [];
    
    console.log(`[中标数据] 成功获取 - 出力:${unitBidOutputValues.value.length}点，均价:${unitBidPriceValues.value.length}点，收益:${unitBidRevenueValues.value.length}点`);
    
    // 显示前 3 个时段的详细数据用于调试
    if (unitBidOutputValues.value.length > 0 && unitBidPriceValues.value.length > 0) {
      console.log('[中标数据] 前 3 个时段详情:');
      for (let i = 0; i < Math.min(3, unitBidOutputValues.value.length); i++) {
        console.log(`  时段${i + 1}: 出力=${unitBidOutputValues.value[i]} MW, 均价=${unitBidPriceValues.value[i]} 元/MWh, 收益=${unitBidRevenueValues.value[i]} 元`);
      }
      // 检查均价数据是否全部相同
      const firstPrice = Number(unitBidPriceValues.value[0]);
      const allSame = unitBidPriceValues.value.every(v => Number(v) === firstPrice);
      if (allSame) {
        console.error('[中标数据] ⚠️ 警告：所有时段的中标均价都相同！这可能是直线的原因:', firstPrice);
      } else {
        console.log('[中标数据] ✅ 均价数据有变化，不是直线');
        const prices = unitBidPriceValues.value.map(v => Number(v));
        console.log('[中标数据] 均价范围：min=', Math.min(...prices), 'max=', Math.max(...prices));
      }
    }

  } catch (error: any) {
    console.error("[中标数据] 获取失败", error);
    unitBidOutputValues.value = [];
    unitBidPriceValues.value = [];
    unitBidRevenueValues.value = [];
  } finally {
    unitBidLoading.value = false;
  }
}

// 处理图表点击事件 - 计算点击的时段
function handleChartClick(event: MouseEvent) {
  const svg = (event.target as SVGElement).closest('svg');
  if (!svg) return;
  
  const rect = svg.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const svgWidth = svg.viewBox.baseVal.width;
  
  // 将点击坐标转换为 viewBox 坐标
  const viewBoxX = (x / rect.width) * svgWidth;

  // 计算对应的时段索引 (X 轴从 80 开始，每个时段 6.67 像素)
  const periodIndex = Math.floor((viewBoxX - 80) / 6.67);
  
  // 确保索引在有效范围内 (0-95)
  if (periodIndex >= 0 && periodIndex < maxPeriods.value) {
    selectedPeriod.value = periodIndex;
    console.log(`[图表点击] 选中时段 ${periodIndex + 1}, 出力：${unitBidOutputValues.value[periodIndex]}, 均价：${unitBidPriceValues.value[periodIndex]}`);
  } else {
    selectedPeriod.value = null;
  }
}

// 处理收益图表点击事件
function handleRevenueChartClick(event: MouseEvent) {
  const svg = (event.target as SVGElement).closest('svg');
  if (!svg) return;
  
  const rect = svg.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const svgWidth = svg.viewBox.baseVal.width;
  
  // 将点击坐标转换为 viewBox 坐标
  const viewBoxX = (x / rect.width) * svgWidth;
  
  // 计算对应的时段索引 (X 轴从 80 开始，每个时段 6.67 像素)
  const periodIndex = Math.floor((viewBoxX - 80) / 6.67);
  
  // 确保索引在有效范围内
  if (periodIndex >= 0 && periodIndex < maxPeriods.value) {
    selectedPeriod.value = periodIndex;
    console.log(`[收益图表点击] 选中时段 ${periodIndex + 1}, 收益：${unitBidRevenueValues.value[periodIndex]}`);
  } else {
    selectedPeriod.value = null;
  }
}

// 当机组选择变化时，重新获取中标数据
watch(selectedUnitId, () => {
  if (selectedUnitId.value) {
    selectedPeriod.value = null; // 重置选中的时段
    fetchUnitBidResults();
  }
});

// 当日期变化时，也重新获取中标数据
watch(currentDay, () => {
  selectedPeriod.value = null; // 重置选中的时段
  fetchUnitBidResults();
});

// 初始化数据
onMounted(async () => {
  await fetchCurrentCompany();
  // 设置默认选中的机组
  if (currentCompany.value && currentCompany.value.units && currentCompany.value.units.length > 0) {
    selectedUnitId.value = currentCompany.value.units[0].id;
  }
  fetchSettlementData();
  fetchHistoryDetail();
  fetchBalanceChart();
  // 确保 selectedUnitId 已设置后再获取出清电价数据
  await nextTick(); // 等待响应式更新完成
  fetchEnergyPriceChart(); // 调用出清电价数据获取函数
  fetchUnitBidResults(); // 新增：获取中标数据
});

</script>

<style scoped>
.content-section {
  max-width: 1300px;
  margin: 0 auto;
  padding: 16px;
}

/* 顶部操作栏 */
.top-operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.tab-bar {
  display: flex;
  gap: 0;
  height: 36px;
}

.tab-btn {
  padding: 8px 20px;
  border: 1px solid #d9d9d9;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.2s;
  height: 100%;
  box-sizing: border-box;
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

/* 日期标签栏 */
.date-tab-bar {
  display: flex;
  gap: 0;
  height: 36px;
}

.date-tab-btn {
  padding: 8px 16px;
  border: 1px solid #d9d9d9;
  border-radius: 0;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
  color: #333;
  transition: all 0.2s;
  height: 100%;
  box-sizing: border-box;
}

.date-tab-btn + .date-tab-btn {
  border-left: none;
}

.date-tab-btn.active {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}

/* 卡片样式 */
.card {
  background: #fff;
  border-radius: 8px;
  padding: 20px 24px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  margin-bottom: 20px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #333;
  margin: 0 0 12px;
}

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.score-badge {
  font-size: 18px;
  font-weight: 700;
  color: #333;
}

/* 结果行样式 */
.result-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
  padding: 16px;
  border-radius: 8px;
}

.result-row.row-1 {
  background: #f0f8ff;
  border: 1px solid #e6f7ff;
}

.result-row.row-2 {
  background: #f6ffed;
  border: 1px solid #d9f7be;
}

.result-row.row-3 {
  background: #fffbe6;
  border: 1px solid #ffe58f;
}

.result-row.row-4 {
  background: #f0f8ff;
  border: 1px solid #e6f7ff;
}

.result-item {
  flex: 1;
  min-width: 140px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 6px;
  text-align: center;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.result-value {
  font-size: 18px;
  font-weight: 600;
  color: #1890ff;
  margin-bottom: 8px;
}

.result-label {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

/* 饼状图样式 */
.pie-chart-row {
  display: flex;
  gap: 40px;
  justify-content: center;
  margin: 16px 0;
  flex-wrap: wrap;
}

.pie-chart-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 200px;
}

.pie-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0 0 8px;
}

.pie-svg {
  width: 180px;
  height: 180px;
}

.pie-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  justify-content: center;
  margin-top: 8px;
  font-size: 12px;
  color: #555;
}

/* 图例样式 */
.legend-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 8px;
  font-size: 12px;
  color: #555;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.legend-color {
  display: inline-block;
  width: 14px;
  height: 10px;
  border-radius: 2px;
}

/* 图表容器 */
.svg-chart-wrap {
  width: 100%;
  height: 220px;
  position: relative;
  overflow: hidden;
}

.svg-chart {
  width: 100%;
  height: 100%;
  cursor: crosshair;
}

.svg-chart:hover {
  opacity: 0.95;
}

.chart-unit {
  font-size: 12px;
  color: #666;
  margin: 0 0 4px;
}

/* 表格样式 */
.data-table-wrap {
  overflow-x: hidden;
  margin: 16px 0;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 600px;
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
  border-bottom: 1px solid #f0f8ff;
  color: #555;
  white-space: nowrap;
}

/* 无数据样式 */
.no-data {
  padding: 40px 0;
  text-align: center;
  color: #999;
  font-size: 14px;
}

/* 适配96时段柱状图容器 */
.note {
  font-size: 12px;
  color: #999;
  margin: 0 0 8px;
}
</style>