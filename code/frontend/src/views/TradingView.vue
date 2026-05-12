<template>
  <div class="content-section">
    <h2 class="section-title">市场交易</h2>
    <!-- 机组报价详情 -->
    <div v-if="g13Company" class="card">
      <div v-if="uiNotice" class="toast">{{ uiNotice }}</div>
      <div v-if="isCoreModelRunning" class="core-model-mask">
        <div class="core-model-panel">
          <div class="core-model-title">{{ coreTitle }}</div>
          <div class="core-model-subtitle">{{ coreSubtitle }}</div>
          <div class="core-progress">
            <div class="core-progress-bar" :style="{ width: coreProgress + '%' }"></div>
          </div>
          <div class="core-progress-text">{{ coreProgress }}%</div>
          <div class="core-steps">
            <div
              v-for="(step, index) in coreSteps"
              :key="step"
              :class="['core-step', { active: index === coreStep, done: index < coreStep }]"
            >
              <span class="core-dot"></span>
              <span class="core-step-text">{{ step }}</span>
            </div>
          </div>
          <div class="core-log">[{{ coreProgress }}%] {{ coreSteps[coreStep] }}</div>
        </div>
      </div>
      <!-- 调整后的顶端栏：左侧机组 + 中部日期 + 右侧按钮 -->
      <div class="card-header-row">
        <!-- 左侧：机组下拉筛选 -->
        <div class="unit-selector">
          <label for="unit-select">选择机组：</label>
          <select id="unit-select" v-model="tradingUnit" class="select-input">
            <option v-for="u in g13Company.units" :key="u.id" :value="u.id">
              机组{{ u.id.replace('Thermal_','') }}
            </option>
          </select>
        </div>

        <!-- 新增：中部日期标签卡 -->
        <div class="date-tab-bar">
          <button 
            v-for="day in dateTabs" 
            :key="day.key"
            :class="['tab-btn', { active: currentDay === day.key }]"
            @click="handleDayChange(day.key)"
          >
            {{ day.label }}
          </button>
        </div>

        <!-- 右侧：功能按钮 -->
        <div>
          <button class="btn primary sm" :disabled="isCoreModelRunning || isSubmitting || isRefreshing" @click="handleSubmitQuote">提交报价</button>
          <button class="btn outline sm" :disabled="isCoreModelRunning || isSubmitting || isRefreshing" style="margin-left: 8px;" @click="tradingSelected = null">取消</button>
          <button class="btn primary sm" :disabled="isCoreModelRunning || isSubmitting || isRefreshing" style="margin-left: 8px;" @click="handleRefresh">刷新数据</button>
        </div>
      </div>

      <div class="trading-grid">
        <div class="trading-left">
          <h4>电能量市场申报</h4>
          <button class="btn outline sm" :disabled="isCoreModelRunning" style="margin-bottom: 12px;" @click="handleStrategyQuote">选择策略报价</button>
          <button class="btn outline sm" :disabled="isCoreModelRunning" style="margin-left: 8px;" @click="handleMarketClear">市场出清</button>
          <div class="data-table-wrap">
            <table class="data-table">
              <thead><tr><th>分段</th><th>起始出力(MW)</th><th>终止出力(MW)</th><th>分段报价(元/MWh)</th></tr></thead>
              <tbody>
                <tr v-for="(s, index) in bidSegments" :key="s.seg">
                  <td>{{ s.seg }}</td>
                  <td><input type="number" v-model.number="customBidSegments[index].start" min="0" step="1" class="input-sm"/></td>
                  <td><input type="number" v-model.number="customBidSegments[index].end" min="0" step="1" class="input-sm"/></td>
                  <td><input type="number" v-model.number="customBidSegments[index].price" min="0" step="0.1" class="input-sm"/></td>
                </tr>
                <tr v-if="bidSegments.length === 0">
                  <td colspan="4" style="text-align: center; color: #999;">暂无报价数据</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="trading-right">
          <h4>报价曲线</h4>
          <p class="chart-unit">电价(元/MWh)</p>
          <div class="svg-chart-wrap" style="height: 200px;">
            <svg viewBox="0 0 960 180" class="svg-chart">
              <line x1="40" y1="10" x2="40" y2="140" stroke="#e0e0e0" stroke-width="1"/>
              <line x1="40" y1="140" x2="920" y2="140" stroke="#e0e0e0" stroke-width="1"/>
              <text v-for="(v, i) in bidYLabels" :key="'by'+i" :x="36" :y="140 - (i / 5) * 130 + 4" text-anchor="end" font-size="9" fill="#999">{{ v }}</text>
              <line v-for="(v, i) in bidYLabels.slice(1)" :key="'bg'+i" x1="40" :y1="140 - ((i+1) / 5) * 130" x2="920" :y2="140 - ((i+1) / 5) * 130" stroke="#f0f0f0" stroke-width="0.5"/>
              <polyline :points="bidCurvePoints" fill="none" stroke="#1890ff" stroke-width="2"/>
              <text v-for="(v, i) in bidXLabels" :key="'bx'+i" :x="40 + (i / 9) * 880" y="155" text-anchor="middle" font-size="9" fill="#999">{{ v }}</text>
              <text x="480" y="172" text-anchor="middle" font-size="9" fill="#666">出力(MW)</text>
            </svg>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="card">
      <h3 class="card-title">加载中...</h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import apiClient from "../api/client";
import { marketApi } from "../api/market";
import { getCurrentAdmin } from "../api/admin";

// 日期标签配置 - 对应数据表中的data_date
const dateTabs = [
  { key: "20260319", label: "第一天" },
  { key: "20260320", label: "第二天" },
  { key: "20260321", label: "第三天" },
  { key: "20260322", label: "第四天" },
  { key: "20260323", label: "第五天" },
  { key: "20260324", label: "第六天" },
  { key: "20260325", label: "第七天" }
];
// 当前选中日期（默认第一天）
const currentDay = ref<string>("20260319");

const g13Company = ref<any>(null);
const tradingUnit = ref("");
const tradingMode = ref("clear");
const dayAheadQuotes = ref<any[]>([]);
const tradingSelected = ref<any>(null);
const customBidSegments = ref<any[]>([]);
const currentUser = ref<any>(null);

const isCoreModelRunning = ref(false);
const coreProgress = ref(0);
const coreStep = ref(0);
const coreTitle = "\u6838\u5fc3\u6a21\u578b\u8c03\u7528\u4e2d";
const coreSubtitle = "\u6b63\u5728\u751f\u6210\u6700\u4f18\u62a5\u4ef7\u66f2\u7ebf";
const coreSteps = [
  "\u52a0\u8f7d\u5e02\u573a\u6570\u636e",
  "\u8c03\u7528\u7b56\u7565\u5e93",
  "\u751f\u6210\u62a5\u4ef7\u66f2\u7ebf",
  "\u6821\u9a8c\u7ea6\u675f\u6761\u4ef6",
  "\u8f93\u51fa\u6700\u4f18\u62a5\u4ef7"
];
let coreTimer: number | undefined;

const startCoreModelSimulation = () => {
  if (isCoreModelRunning.value) return;
  isCoreModelRunning.value = true;
  coreProgress.value = 0;
  coreStep.value = 0;

  const totalMs = 2200;
  const stepMs = 120;
  const ticks = Math.max(1, Math.ceil(totalMs / stepMs));
  let count = 0;

  coreTimer = window.setInterval(() => {
    count += 1;
    const pct = Math.min(100, Math.round((count / ticks) * 100));
    coreProgress.value = pct;
    const idx = Math.min(coreSteps.length - 1, Math.floor((pct / 100) * coreSteps.length));
    coreStep.value = idx;

    if (pct >= 100) {
      window.clearInterval(coreTimer);
      coreTimer = undefined;
      window.setTimeout(() => {
        isCoreModelRunning.value = false;
        coreStep.value = coreSteps.length - 1;
      }, 300);
    }
  }, stepMs);
};
const uiNotice = ref("");
const isSubmitting = ref(false);
const isRefreshing = ref(false);
let noticeTimer: number | undefined;

const showNotice = (message: string, timeout = 1600) => {
  uiNotice.value = message;
  if (noticeTimer) {
    window.clearTimeout(noticeTimer);
  }
  noticeTimer = window.setTimeout(() => {
    uiNotice.value = "";
  }, timeout);
};

const handleSubmitQuote = async () => {
  if (isSubmitting.value) return;
  if (!tradingUnit.value) {
    showNotice("\u8bf7\u5148\u9009\u62e9\u673a\u7ec4", 1400);
    return;
  }
  isSubmitting.value = true;
  showNotice("\u6b63\u5728\u63d0\u4ea4\u62a5\u4ef7\u5230\u6570\u636e\u5e93...", 1400);
  try {
    await marketApi.submitInputDayAheadQuotes({
      unit_id: tradingUnit.value,
      data_date: currentDay.value,
      use_default_case: tradingMode.value !== "bid",
      segments: customBidSegments.value.map((seg: any, idx: number) => ({
        start: Number(seg.start) || 0,
        end: Number(seg.end) || 0,
        price: Number(seg.price) || 0,
        quote_time: seg.quote_time ?? idx + 1,
        quote_section: seg.quote_section || `Q${idx + 1}`,
        market_name: seg.market_name || "\u7535\u80fd\u91cf\u5e02\u573a\u7533\u62a5"
      }))
    });
    showNotice("\u62a5\u4ef7\u5df2\u4fdd\u5b58", 1400);
    await fetchInputDayAheadQuotes();
  } catch (e) {
    showNotice("\u63d0\u4ea4\u5931\u8d25", 1600);
  } finally {
    isSubmitting.value = false;
  }
};

const handleRefresh = async () => {
  if (isRefreshing.value) return;
  isRefreshing.value = true;
  showNotice("\u6b63\u5728\u5237\u65b0\u6570\u636e...", 1200);
  await refreshData();
  showNotice("\u6570\u636e\u5df2\u5237\u65b0", 1400);
  isRefreshing.value = false;
};

const lastUnit = ref<string | null>(null);



// 日期切换处理方法
const handleDayChange = (dayKey: string) => {
  currentDay.value = dayKey;
  // 重新获取数据并初始化报价分段
  fetchInputDayAheadQuotes();
};

// 选择策略报价处理方法 - 调用step2竞价策略程序
const handleStrategyQuote = async () => {
  if (isCoreModelRunning.value) return;
  const plantName = currentUser.value?.username;
  if (!plantName) { showNotice("未获取到用户信息"); return; }
  
  isCoreModelRunning.value = true;
  coreProgress.value = 0;
  coreStep.value = 0;
  
  // 真实进度更新
  const steps = coreSteps;
  coreStep.value = 0; coreProgress.value = 10;
  
  try {
    coreStep.value = 1; coreProgress.value = 30;
    // 调用后端step2竞价策略程序
    const res = await apiClient.post("/market/run-strategy/" + plantName);
    
    if (res.data.success) {
      coreStep.value = 2; coreProgress.value = 60;
      tradingMode.value = 'bid';
      
      coreStep.value = 3; coreProgress.value = 80;
      // 重新获取策略报价数据
      await fetchInputDayAheadQuotes();
      
      coreStep.value = 4; coreProgress.value = 100;
      showNotice("策略报价生成成功");
    } else {
      const errorMsg = res.data.error || res.data.stderr || "未知错误";
      console.error("策略生成失败:", errorMsg);
      console.error("STDOUT:", res.data.stdout);
      console.error("STDERR:", res.data.stderr);
      showNotice("策略生成失败：" + errorMsg);
    }
  } catch (e) {
    console.error("策略报价调用失败", e);
    showNotice("策略报价调用失败");
  } finally {
    setTimeout(() => { isCoreModelRunning.value = false; }, 500);
  }
};

// 市场出清处理方法
const handleMarketClear = async () => {
  if (isCoreModelRunning.value) return;
  
  isCoreModelRunning.value = true;
  coreProgress.value = 0;
  coreStep.value = 0;
  
  // 临时修改步骤描述为市场出清相关
  const originalSteps = [...coreSteps];
  coreSteps[0] = "执行数据转换程序";
  coreSteps[1] = "生成 xlsm 文件";
  coreSteps[2] = "执行市场出清计算";
  coreSteps[3] = "加载出清结果";
  coreSteps[4] = "更新市场数据";
  
  try {
    coreStep.value = 1;
    coreProgress.value = 20;
    showNotice("开始执行市场出清...");
    
    // 调用后端 execute.bat
    const res = await apiClient.post("/market/run-market-clearing");
    
    if (res.data.success) {
      coreStep.value = 2;
      coreProgress.value = 60;
      showNotice("市场出清执行完成");
      
      coreStep.value = 3;
      coreProgress.value = 80;
      tradingMode.value = 'clear';
      
      coreStep.value = 4;
      coreProgress.value = 100;
      // 重新获取数据并初始化报价分段
      await fetchInputDayAheadQuotes();
      showNotice("市场出清完成，数据已更新");
    } else {
      const errorMsg = res.data.error || res.data.stderr || "未知错误";
      console.error("市场出清失败:", errorMsg);
      console.error("STDOUT:", res.data.stdout);
      console.error("STDERR:", res.data.stderr);
      showNotice("市场出清失败：" + errorMsg);
    }
  } catch (e) {
    console.error("市场出清调用失败", e);
    showNotice("市场出清调用失败");
  } finally {
    // 恢复原始步骤描述
    coreSteps[0] = originalSteps[0];
    coreSteps[1] = originalSteps[1];
    coreSteps[2] = originalSteps[2];
    coreSteps[3] = originalSteps[3];
    coreSteps[4] = originalSteps[4];
    setTimeout(() => { isCoreModelRunning.value = false; }, 500);
  }
};

async function fetchCurrentUser() {
  try {
    const user = await getCurrentAdmin();
    currentUser.value = user;
    console.log("当前用户:", user);
    return user;
  } catch (e) {
    console.error("获取用户信息失败", e);
    return null;
  }
}

async function fetchG13Company() {
  try {
    const user = await fetchCurrentUser();
    if (!user) {
      return;
    }
    
    const { data } = await marketApi.getCompanies();
    const companies = data.items || [];
    // 根据用户的用户名查找对应的企业（假设用户名为企业代码，如 G13）
    const companyCode = user.username;
    g13Company.value = companies.find((c: any) => c.name === companyCode) || null;
    if (g13Company.value && g13Company.value.units.length > 0) {
      // 设置默认机组
      tradingUnit.value = g13Company.value.units[0].id;
    }
  } catch (e) { 
    console.error("获取企业信息失败", e); 
  }
}

async function fetchInputDayAheadQuotes() {
  try {
    const params: any = { 
      data_date: currentDay.value,
      use_default_case: tradingMode.value !== 'bid' // 未点击策略报价按钮时使用默认case
    };
    if (tradingUnit.value) {
      params.unit_id = tradingUnit.value;
    }
    const da = await marketApi.getInputDayAheadQuotes(params);
    // 标准化API响应数据格式
    dayAheadQuotes.value = normalizeQuoteData(da.data.items || []);
    // 初始化自定义报价数据
    initCustomBidSegments();
  } catch (e) { 
    console.error("获取输入交易数据失败", e); 
  }
}

async function fetchTradingData() {
  try {
    const da = await marketApi.getDayAheadQuotes();
    dayAheadQuotes.value = da.data.items || [];
    // 初始化自定义报价数据
    initCustomBidSegments();
  } catch (e) { 
    console.error("获取交易数据失败", e); 
  }
}

async function refreshData() {
  await fetchG13Company();
  // 切换到市场出清模式，使用Input0 case_id
  tradingMode.value = 'clear';
  // 重新获取数据
  await fetchInputDayAheadQuotes();
  // 不需要重置表单数据，因为fetchInputDayAheadQuotes会自动初始化customBidSegments
}

function resetFormData() {
  // 将所有表单数值清0
  customBidSegments.value = customBidSegments.value.map((seg: any) => ({
    ...seg,
    start: 0,
    end: 0,
    price: 0
  }));
}

function initCustomBidSegments() {
  // 过滤当前机组和当前日期的数据
  const filtered = dayAheadQuotes.value.filter(
    (q: any) => q.unit_id === tradingUnit.value
  );
  
  // 按照quote_time和quote_section排序（提取数字部分进行数值排序）
  const sortedQuotes = filtered.sort((a: any, b: any) => {
    if (a.quote_time !== b.quote_time) {
      return a.quote_time - b.quote_time;
    }
    // 提取quote_section中的数字部分进行数值排序
    const getSectionNum = (section: string) => {
      const match = section.match(/\d+/);
      return match ? parseInt(match[0], 10) : 0;
    };
    return getSectionNum(a.quote_section) - getSectionNum(b.quote_section);
  });
  
  // 第一阶段的起始出力固定为0，每个阶段的QuoteCapacity值为终止出力减去起始出力
  let currentOutput = 0;
  const segments = sortedQuotes.map((q: any, i: number) => {
    const start = currentOutput;
    const end = start + q.quote_capacity;
    currentOutput = end;
    return { 
      seg: i + 1, 
      start, 
      end, 
      price: q.quote_price,
      quote_capacity: q.quote_capacity,
      quote_section: q.quote_section,
      quote_time: q.quote_time
    };
  });
  
  customBidSegments.value = segments;
}

// 检查API响应格式并转换为前端需要的格式
function normalizeQuoteData(quotes: any[]) {
  return quotes.map(quote => {
    // 处理可能的字段名差异（PascalCase vs snake_case）
    return {
      quote_id: quote.quote_id || quote.QuoteId,
      unit_id: quote.unit_id || quote.UnitId,
      market_name: quote.market_name || quote.MarketName,
      quote_time: quote.quote_time || quote.QuoteTime,
      quote_section: quote.quote_section || quote.QuoteSection,
      quote_price: quote.quote_price || quote.QuotePrice,
      quote_capacity: quote.quote_capacity || quote.QuoteCapacity,
      is_used: quote.is_used || quote.IsUsed,
      case_id: quote.case_id,
      data_date: quote.data_date
    };
  });
}

const bidSegments = computed(() => {
  return customBidSegments.value;
});

// 监听交易单位变化，重新获取数据
watch(tradingUnit, () => {
  fetchInputDayAheadQuotes();
  if (tradingUnit.value && lastUnit.value && tradingUnit.value != lastUnit.value) {
    const label = tradingUnit.value.replace('Thermal_', 'G');
    showNotice(`\u5df2\u5207\u6362\u81f3\u673a\u7ec4 ${label}`, 1200);
  }
  lastUnit.value = tradingUnit.value || null;
});

// 监听日期变化，重新获取数据
watch(currentDay, () => {
  fetchInputDayAheadQuotes();
});

// 监听 customBidSegments 变化，保证分段出力的连续性
watch(customBidSegments, (newSegments) => {
  // 遍历所有分段，检查并调整相邻分段的出力值
  for (let i = 0; i < newSegments.length; i++) {
    if (i > 0) {
      // 当前分段的起始出力必须等于前一段的终止出力
      if (newSegments[i].start !== newSegments[i - 1].end) {
        newSegments[i].start = newSegments[i - 1].end;
      }
    }
    if (i < newSegments.length - 1) {
      // 下一段的起始出力必须等于当前段的终止出力
      if (newSegments[i + 1].start !== newSegments[i].end) {
        newSegments[i + 1].start = newSegments[i].end;
      }
    }
  }
}, { deep: true });

const bidCurveMaxOutput = computed(() => {
  const segs = bidSegments.value;
  return segs.length ? segs[segs.length - 1].end : 600;
});

const bidPriceRange = computed(() => {
  const segs = bidSegments.value;
  if (!segs.length) return { min: 0, max: 400 };
  const prices = segs.map((s: any) => s.price);
  const minP = Math.min(...prices);
  const maxP = Math.max(...prices);
  const range = maxP - minP;
  const padding = Math.max(range * 0.1, 5);
  const yMin = Math.max(0, Math.floor((minP - padding) / 5) * 5);
  const yMax = Math.ceil((maxP + padding) / 5) * 5;
  return { min: yMin, max: yMax };
});

const bidCurvePoints = computed(() => {
  const segs = bidSegments.value;
  if (!segs.length) return "";
  const maxOut = bidCurveMaxOutput.value;
  const { min: yMin, max: yMax } = bidPriceRange.value;
  const chartL = 40, chartR = 920, chartT = 10, chartB = 140;
  const w = chartR - chartL, h = chartB - chartT;
  const pts: string[] = [];
  for (const s of segs) {
    const x1 = chartL + (s.start / maxOut) * w;
    const x2 = chartL + (s.end / maxOut) * w;
    const y = chartB - ((s.price - yMin) / (yMax - yMin)) * h;
    pts.push(`${x1.toFixed(1)},${y.toFixed(1)}`);
    pts.push(`${x2.toFixed(1)},${y.toFixed(1)}`);
  }
  return pts.join(" ");
});

const bidXLabels = computed(() => {
  const max = bidCurveMaxOutput.value;
  const step = max / 9;
  return [0, Math.round(step), Math.round(step * 2), Math.round(step * 3), Math.round(step * 4), Math.round(step * 5), Math.round(step * 6), Math.round(step * 7), Math.round(step * 8), Math.round(max)];
});

const bidYLabels = computed(() => {
  const { min: yMin, max: yMax } = bidPriceRange.value;
  const step = (yMax - yMin) / 5;
  return [yMin, Math.round(yMin + step), Math.round(yMin + step * 2), Math.round(yMin + step * 3), Math.round(yMin + step * 4), yMax];
});

onMounted(() => {
  fetchG13Company().then(() => {
    // 确保机组信息加载完成后，再获取报价数据
    fetchInputDayAheadQuotes();
  });
});
</script>

<style scoped>
.content-section {
  max-width: 1300px;
  margin: 0 auto;
  padding: 16px;
}
.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin: 0 0 16px;
}
.card {
  position: relative;
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
/* 调整顶端栏样式：保证三部分垂直齐平 */
.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 16px; /* 增加元素间间距，避免拥挤 */
}
/* 新增：日期标签容器样式 */
.date-tab-bar {
  display: flex;
  gap: 0; /* 无间隙 */
  flex: 1; /* 占据中间剩余空间 */
  justify-content: center; /* 日期标签居中 */
  height: 36px; /* 与机组标签高度一致 */
}
.tab-bar {
  display: flex;
  gap: 0;
  margin-bottom: 16px;
  height: 36px; /* 统一高度 */
}

.unit-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
}

.unit-selector label {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.select-input {
  padding: 6px 12px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 14px;
  color: #333;
  background: #fff;
  transition: all 0.2s;
  height: 100%;
  box-sizing: border-box;
}

.select-input:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}
.tab-btn {
  padding: 8px 20px;
  border: 1px solid #d9d9d9;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: all 0.2s;
  border-radius: 0; /* 去掉所有圆角 */
  height: 100%; /* 高度铺满父容器 */
  box-sizing: border-box;
}
/* 移除原有圆角样式，保证无圆角 */
.tab-btn:first-child {
  border-radius: 0;
}
.tab-btn:last-child {
  border-radius: 0;
}
.tab-btn + .tab-btn {
  border-left: none;
}
.tab-btn.active {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}
.simple-table {
  font-size: 13px;
}
.table-header {
  display: flex;
  padding: 10px 16px;
  font-weight: 600;
  color: #666;
  border-bottom: 2px solid #e8e8e8;
}
.table-row {
  display: flex;
  padding: 10px 16px;
  border-bottom: 1px solid #f0f0f0;
}
.table-row.clickable {
  cursor: pointer;
}
.table-row.clickable:hover {
  background: #f5f7fa;
}

.trading-grid {
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-top: 16px;
}
.trading-left h4,
.trading-right h4 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 8px;
}
.trading-right {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
}

.trading-right h4 {
  width: 100%;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 8px;
}

.trading-right .chart-unit {
  width: 100%;
  text-align: left;
  margin-left: 20px;
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
.input-sm {
  width: 100px;
  padding: 4px 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
  font-size: 13px;
  transition: all 0.2s;
}
.input-sm:focus {
  outline: none;
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}
.svg-chart-wrap {
  width: 100%;
  height: 200px;
  position: relative;
  display: block;
  margin-left: 20px;
}
.svg-chart {
  width: 100%;
  height: 100%;
}
.chart-unit {
  font-size: 12px;
  color: #666;
  margin: 0 0 4px;
}
.btn {
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.btn.primary {
  background: #1890ff;
  color: #fff;
  border-color: #1890ff;
}
.btn.primary:hover {
  background: #40a9ff;
}
.btn.outline {
  background: #fff;
  color: #333;
  border-color: #d9d9d9;
}
.btn.outline:hover {
  border-color: #1890ff;
  color: #1890ff;
}
.btn.sm {
  padding: 4px 12px;
  font-size: 12px;
}

.core-model-mask {
  position: absolute;
  inset: 0;
  background: rgba(7, 15, 30, 0.55);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
  border-radius: 8px;
}
.core-model-panel {
  width: min(520px, 92%);
  background: #0c1b2a;
  color: #e6f0ff;
  border: 1px solid rgba(120, 170, 255, 0.25);
  border-radius: 12px;
  padding: 20px 24px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.25);
}
.core-model-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 6px;
}
.core-model-subtitle {
  font-size: 12px;
  color: #b7c7e6;
  margin-bottom: 12px;
}
.core-progress {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 999px;
  overflow: hidden;
}
.core-progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #4cc3ff 0%, #66ffb3 100%);
  transition: width 0.2s ease;
}
.core-progress-text {
  font-size: 12px;
  color: #d6e6ff;
  margin: 6px 0 10px;
}
.core-steps {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 16px;
  margin-bottom: 10px;
}
.core-step {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #8fa6c8;
}
.core-step.active {
  color: #e6f0ff;
}
.core-step.done {
  color: #7fe3b8;
}
.core-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.core-log {
  font-size: 12px;
  color: #9fb8dd;
}


.toast {
  position: absolute;
  top: 12px;
  right: 16px;
  background: rgba(12, 27, 42, 0.9);
  color: #e6f0ff;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.2);
  z-index: 6;
}

</style>
