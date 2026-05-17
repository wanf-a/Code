<template>
  <MainLayout>
    <div class="page-header">
      <h1 class="page-title">预测管理</h1>
      <div class="header-actions">
        <button class="btn primary" @click="handleSave">保存</button>
        <button class="btn" @click="goBack">返回</button>
      </div>
    </div>

    <section class="panel">
      <div class="panel-header">
        <h3 class="panel-title">电价预测方案</h3>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>模型名称</th>
              <th>数据集名称</th>
              <th>类型</th>
              <th>预测时间段</th>
              <th>描述</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{{ planDisplayName }}</td>
              <td>{{ plan.dataset }}</td>
              <td>{{ plan.type }}</td>
              <td class="period-cell">
                <input v-model="periodStart" type="date" class="input period-input" />
                <span>至</span>
                <input v-model="periodEnd" type="date" class="input period-input" />
              </td>
              <td>{{ plan.description }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div class="detail-grid">
      <section class="panel">
        <div class="panel-header">
          <h3 class="panel-title">模型名称</h3>
        </div>
        <div class="model-list" ref="modelListRef">
          <div
            class="model-item"
            v-for="model in models"
            :key="model.id"
            @click="selectModel(model.id)"
          >
            <span class="model-name" :class="{ active: model.selected }">{{ model.name }}</span>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h3 class="panel-title">预测结果</h3>
          <span v-if="hasCalculated && dataMode" class="data-mode-tag" :class="dataMode">
            {{ dataMode === 'realtime' ? '实时预测' : 'CSV历史数据' }}
          </span>
          <span v-if="dataError" class="data-error-tag">{{ dataError }}</span>
          <button
            class="btn primary sm"
            @click="handleCalculate"
            :disabled="selectedModels.length === 0 || !selectedDate"
          >
            计算
          </button>
          <button
            class="btn sm"
            @click="triggerWeightsUpload"
            :disabled="selectedModels.length === 0"
          >
            上传权重文件
          </button>
          <input
            ref="weightsFileInput"
            type="file"
            style="display: none"
            accept=".zip"
            @change="handleWeightsFileSelect"
          />
        </div>
        <div class="chart-container">
          <div class="chart-legend" v-if="hasCalculated && chartDataAvailable">
            <template v-if="!isTcnPlan">
              <span class="legend-item"><span class="line-solid blue"></span> 电价实际值</span>
              <span class="legend-item"><span class="line-dashed orange"></span> {{ modelDisplayName }} (QR-0.5)</span>
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
          <div v-if="hasCalculated && chartDataAvailable" class="carousel-wrapper">
            <div class="carousel-header">
              <button class="carousel-btn" @click="prevDay">◀</button>
              <span class="carousel-title">{{ currentDayLabel }} (第 {{ currentDayIndex + 1 }}/{{ totalDays }} 天)</span>
              <button class="carousel-btn" @click="nextDay">▶</button>
            </div>
            <div class="carousel-indicators">
              <span 
                v-for="(day, idx) in dailyChartData" 
                :key="idx" 
                :class="['indicator', { active: idx === currentDayIndex }]"
                @click="currentDayIndex = idx"
              ></span>
            </div>
            <!-- Mamba确定性预测图 -->
            <div v-if="!isTcnPlan" class="chart-with-axis">
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
            <!-- TCN概率预测图 -->
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
                  <polygon :points="tcnBand95Points" fill="rgba(24,144,255,0.2)" stroke="none"/>
                  <polyline fill="none" stroke="#ff4d4f" stroke-width="1.5" :points="tcnLoadPoints"/>
                  <polyline fill="none" stroke="#52c41a" stroke-width="2" :points="tcnQr50Points"/>
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
          <div v-else-if="loading" class="chart-empty">加载中...</div>
          <div v-else-if="hasCalculated && !chartDataAvailable" class="chart-empty">
            所选日期范围无数据。
            <span v-if="availableRange.start && availableRange.end">
              预测数据范围：{{ availableRange.start }} 至 {{ availableRange.end }}
            </span>
          </div>
          <div v-else class="chart-empty">
            <p v-if="selectedModels.length === 0">请先选择至少一个模型</p>
            <p v-else-if="!selectedDate">请选择日期</p>
            <p v-else>请点击"计算"按钮进行预测计算</p>
          </div>
        </div>
      </section>
    </div>

  </MainLayout>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import MainLayout from "../layouts/MainLayout.vue";
import { fetchModels, uploadModelWeights } from "../api/models";
import { updatePlan } from "../api/plans";

const router = useRouter();
const route = useRoute();
// 使用相对路径，通过 Nginx 代理访问后端 API
const API_BASE = "/api";

const planId = computed(() => Number(route.params.id) || 1);

type PredictionRecord = {
  record_time: string;
  actual_price: number;
  predicted_price: number;
  qr_025?: number;
  qr_50?: number;
  qr_975?: number;
  load_kw: number;
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

const SAVE_KEY = "prediction_saved_state";

const hasCalculated = ref(false);
const predictionData = ref<PredictionRecord[]>([]);
const tcnData = ref<TcnRecord[]>([]);
const loading = ref(false);
const currentDatasetId = ref<number | null>(null);
const currentDayIndex = ref(0);
const dataMode = ref<string>("");
const dataError = ref<string>("");

const periodStart = ref("2024-06-25");
const periodEnd = ref("2024-07-01");

const selectedDate = computed(() => periodEnd.value);

const plan = ref<{ name: string; dataset: string; type: string; description: string }>({
  name: "电价预测方案",
  dataset: "广东电价数据",
  type: "周前概率",
  description: "",
});

const models = ref<{ id: number; name: string; selected: boolean }[]>([]);
const planModelId = ref<number | null>(null);
const currentRunId = ref<number | null>(null);
const modelListRef = ref<HTMLDivElement | null>(null);
const weightsFileInput = ref<HTMLInputElement | null>(null);
const availableRange = ref<{ start: string; end: string }>({ start: "", end: "" });

const isTcnPlan = computed(() => {
  const name = (selectedModels.value[0]?.name || plan.value.name || "").toLowerCase();
  return name.includes("tcn");
});

const selectedModels = computed(() => models.value.filter((m) => m.selected));
const modelDisplayName = computed(() => {
  const name = selectedModels.value[0]?.name;
  return name ? `${name}预测值` : "模型预测值";
});
const planDisplayName = computed(() => {
  return selectedModels.value[0]?.name || plan.value.name;
});
const getAuthToken = () => localStorage.getItem("access_token") || "";

const fetchDatasetId = async () => {
  try {
    const res = await fetch(`${API_BASE}/datasets?page=1&size=1`, {
      headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
    if (res.ok) {
      const data = await res.json();
      if (data.items && data.items.length > 0) {
        currentDatasetId.value = data.items[0].id;
        await loadDatasetRange(currentDatasetId.value || 0);
      }
    }
  } catch (e) {
    console.error("获取数据集失败", e);
  }
};

const loadDatasetRange = async (datasetId: number) => {
  try {
    const res = await fetch(`${API_BASE}/datasets/${datasetId}/records/range`, {
      headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
    if (res.ok) {
      const data = await res.json();
      availableRange.value = {
        start: data.start_time ? data.start_time.slice(0, 10) : "",
        end: data.end_time ? data.end_time.slice(0, 10) : "",
      };
    }
  } catch (e) {
    console.error("获取数据范围失败", e);
  }
};

const formatLocalDateTime = (d: Date) => {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
};

const fetchPredictionData = async () => {
  if (!periodEnd.value) return;
  const modelId = selectedModels.value[0]?.id;
  if (!modelId) return;

  const startDate = new Date(`${periodStart.value}T00:00:00`);
  const endDate = new Date(`${periodEnd.value}T23:59:59`);
  const startTime = formatLocalDateTime(startDate);
  const endTime = formatLocalDateTime(endDate);

  try {
    const res = await fetch(
      `${API_BASE}/chart/epf-probability?model_id=${modelId}&start_time=${startTime}&end_time=${endTime}&mode=realtime`,
      { headers: { Authorization: `Bearer ${getAuthToken()}` } }
    );
    if (res.ok) {
      const data = await res.json();
      dataMode.value = data.mode || "";
      dataError.value = data.error || "";
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
  }
};

const fetchTcnData = async () => {
  if (!periodStart.value || !periodEnd.value) return;
  const modelId = selectedModels.value[0]?.id;
  if (!modelId) return;

  const startDate = new Date(`${periodStart.value}T00:00:00`);
  const endDate = new Date(`${periodEnd.value}T23:59:59`);
  const startTime = formatLocalDateTime(startDate);
  const endTime = formatLocalDateTime(endDate);

  try {
    const res = await fetch(
      `${API_BASE}/chart/epf-probability?model_id=${modelId}&start_time=${startTime}&end_time=${endTime}&mode=realtime`,
      { headers: { Authorization: `Bearer ${getAuthToken()}` } }
    );
    if (res.ok) {
      const data = await res.json();
      dataMode.value = data.mode || "";
      dataError.value = data.error || "";
      tcnData.value = data.items.map((r: any) => ({
        record_time: r.record_time,
        real: r.real,
        qr_005: r.qr_005,
        qr_025: r.qr_025,
        qr_05: r.qr_05,
        qr_50: r.qr_50,
        qr_95: r.qr_95,
        qr_975: r.qr_975,
        qr_995: r.qr_995,
        load_kw: r.load_kw || 0,
      }));
    }
  } catch (e) {
    console.error("获取TCN数据失败", e);
  }
};

const doFetchData = async () => {
  if (isTcnPlan.value) {
    await fetchTcnData();
  } else {
    await fetchPredictionData();
  }
};

const persistPlanModel = async () => {
  const selected = selectedModels.value[0];
  if (!selected || selected.id <= 0) return;
  if (planModelId.value === selected.id) return;
  try {
    await updatePlan(planId.value, { model_id: selected.id });
    planModelId.value = selected.id;
  } catch (e) {
    console.error("更新方案模型失败", e);
  }
};

const handleSave = async () => {
  if (!periodStart.value || !periodEnd.value) {
    alert("请选择预测时间段");
    return;
  }
  if (!currentDatasetId.value) {
    await fetchDatasetId();
  }
  if (!currentDatasetId.value) {
    alert("无法获取数据集，请刷新页面重试");
    return;
  }
  loading.value = true;
  try {
    await persistPlanModel();
    await doFetchData();
    hasCalculated.value = true;
    currentDayIndex.value = 0;
  } finally {
    loading.value = false;
  }

  localStorage.setItem(SAVE_KEY, JSON.stringify({
    periodStart: periodStart.value,
    periodEnd: periodEnd.value,
    predictionData: predictionData.value,
  }));
  localStorage.setItem("prediction_period", JSON.stringify({
    start: periodStart.value,
    end: periodEnd.value,
  }));
  alert("保存成功");
};

const handleCalculate = async () => {
  if (!periodStart.value || !periodEnd.value) {
    alert("请选择预测时间段");
    return;
  }
  if (!currentDatasetId.value) {
    await fetchDatasetId();
  }
  if (!currentDatasetId.value) {
    alert("无法获取数据集，请刷新页面重试");
    return;
  }
  loading.value = true;
  try {
    await persistPlanModel();
    await doFetchData();
    hasCalculated.value = true;
    currentDayIndex.value = 0;
    localStorage.setItem("prediction_period", JSON.stringify({
      start: periodStart.value,
      end: periodEnd.value,
    }));
  } finally {
    loading.value = false;
  }
};

const loadSavedState = () => {
  const saved = localStorage.getItem(SAVE_KEY);
  if (saved) {
    try {
      const state = JSON.parse(saved);
      periodStart.value = state.periodStart;
      periodEnd.value = state.periodEnd;
      predictionData.value = state.predictionData || [];
      if (predictionData.value.length > 0) {
        hasCalculated.value = true;
      }
    } catch {}
  }
};

const loadPlanInfo = async () => {
  try {
    const res = await fetch(`${API_BASE}/plans/${planId.value}`, {
      headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
      if (res.ok) {
        const data = await res.json();
        plan.value = {
          name: data.name,
          dataset: "广东电价数据",
          type: "周前概率",
          description: data.description || "",
        };
        planModelId.value = data.model_id || null;
        currentDatasetId.value = data.dataset_id || null;
      if (currentDatasetId.value) {
        await loadDatasetRange(currentDatasetId.value);
      }
      if (models.value.length === 0) {
        models.value = [
          {
            id: data.id || 1,
            name: data.name || "周前概率",
            selected: true,
          },
        ];
      }
    }
  } catch (e) {
    console.error("获取方案失败", e);
    if (!plan.value.name) {
      plan.value.name = `方案${planId.value}`;
    }
  }
};

const loadModels = async () => {
  try {
    const data = await fetchModels({ page: 1, size: 200 });
    models.value = data.items.map((item) => ({
      id: item.id,
      name: item.name,
      selected: false,
    }));
    if (models.value.length > 0) {
      const matched = planModelId.value
        ? models.value.find((m) => m.id === planModelId.value)
        : null;
      (matched || models.value[0]).selected = true;
      return;
    }
    if (!models.value.length) {
      models.value = [
        {
          id: 0,
          name: plan.value.name || "默认模型",
          selected: true,
        },
      ];
    }
  } catch (e) {
    console.error("获取模型列表失败", e);
    if (!models.value.length) {
      models.value = [
        {
          id: 0,
          name: plan.value.name || "默认模型",
          selected: true,
        },
      ];
    }
  }
};

const triggerWeightsUpload = () => {
  weightsFileInput.value?.click();
};

const handleWeightsFileSelect = async (e: Event) => {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  const modelId = selectedModels.value[0]?.id;
  if (!file || !modelId) return;

  try {
    const result = await uploadModelWeights(modelId, file);
    let msg = `权重文件上传成功：${result.extracted_files.join(", ")}`;
    if (result.warnings.length > 0) {
      msg += `\n\n警告：\n${result.warnings.join("\n")}`;
    }
    alert(msg);
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || "未知错误";
    alert("上传权重文件失败: " + detail);
  } finally {
    target.value = "";
  }
};

const selectModel = (modelId: number) => {
  models.value = models.value.map((m) => ({
    ...m,
    selected: m.id === modelId,
  }));
  planModelId.value = modelId;
  if (!plan.value.name) {
    const current = models.value.find((m) => m.selected);
    if (current) {
      plan.value.name = current.name;
    }
  }
};

const loadLatestRun = async () => {
  try {
    const res = await fetch(`${API_BASE}/plans/${planId.value}/runs/latest`, {
      headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
    if (res.ok) {
      const data = await res.json();
      currentRunId.value = data.id;
      if (data.start_time) {
        periodStart.value = data.start_time.slice(0, 10);
      }
      if (data.end_time) {
        periodEnd.value = data.end_time.slice(0, 10);
      }
    }
  } catch (e) {
    // no latest run yet
  }
};

const createRun = async () => {
  try {
    const selected = selectedModels.value[0];
    if (!selected) {
      alert("请先选择模型名称");
      return;
    }
    const payload = {
      task_type: "prediction_run",
      payload_json: JSON.stringify({
        plan_id: planId.value,
        model_id: selected.id > 0 ? selected.id : null,
        start_time: periodStart.value ? `${periodStart.value}T00:00:00` : null,
        end_time: periodEnd.value ? `${periodEnd.value}T23:59:59` : null,
      }),
      max_retries: 1,
    };
    const res = await fetch(`${API_BASE}/tasks`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAuthToken()}`,
      },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const data = await res.json();
      await waitForTask(data.id);
    } else {
      const err = await res.json();
      alert("计算失败: " + (err?.detail || "未知错误"));
    }
  } catch (e) {
    alert("计算失败，请稍后重试");
  }
};

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const waitForTask = async (taskId: number) => {
  const maxWait = 120000;
  const started = Date.now();
  while (Date.now() - started < maxWait) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
      headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
    if (res.ok) {
      const data = await res.json();
      if (data.status === "completed") {
        await loadLatestRun();
        return;
      }
      if (data.status === "failed") {
        alert("计算失败: " + (data.last_error || "未知错误"));
        return;
      }
    }
    await sleep(1000);
  }
  alert("计算超时，请稍后在运行记录查看结果");
};

onMounted(async () => {
  loadSavedState();
  await loadPlanInfo();
  await loadModels();
  await loadLatestRun();
  if (currentRunId.value) {
    await doFetchData();
    if ((isTcnPlan.value && tcnData.value.length > 0) || (!isTcnPlan.value && predictionData.value.length > 0)) {
      hasCalculated.value = true;
    }
  }
});

const goBack = () => {
  router.push("/predictions");
};

const chartDataAvailable = computed(() => {
  if (isTcnPlan.value) return tcnData.value.length > 0;
  return predictionData.value.length > 0;
});

const dailyChartData = computed(() => {
  if (!periodStart.value || !periodEnd.value) return [];
  const sourceData: any[] = isTcnPlan.value ? tcnData.value : predictionData.value;
  if (sourceData.length === 0) return [];
  
  const start = new Date(`${periodStart.value}T00:00:00`);
  const end = new Date(`${periodEnd.value}T23:59:59`);
  const days: { date: string; data: any[] }[] = [];
  
  const current = new Date(start);
  while (current <= end) {
    const dateStr = `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, '0')}-${String(current.getDate()).padStart(2, '0')}`;
    
    const dayData = sourceData.filter((r: any) => {
      const recordDate = r.record_time.split('T')[0];
      return recordDate === dateStr;
    }).sort((a: any, b: any) => new Date(a.record_time).getTime() - new Date(b.record_time).getTime());
    
    days.push({ date: dateStr, data: dayData });
    current.setDate(current.getDate() + 1);
  }
  
  return days;
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

const totalDays = computed(() => dailyChartData.value.length || 1);

const prevDay = () => {
  currentDayIndex.value = (currentDayIndex.value - 1 + totalDays.value) % totalDays.value;
};

const nextDay = () => {
  currentDayIndex.value = (currentDayIndex.value + 1) % totalDays.value;
};

// ===== TCN概率预测图表计算 =====
const tcnCurrentDayData = computed(() => {
  if (!isTcnPlan.value) return [];
  return currentDayData.value as TcnRecord[];
});

const toY = (val: number, min: number, max: number, h: number) => {
  return Math.max(0, Math.min(h, h - ((val - min) / (max - min)) * h));
};

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
  const upper = data.map((r, i) => `${(i * step).toFixed(1)},${toY(r.qr_975, minP, maxP, h).toFixed(1)}`);
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
</script>

<style scoped>
.data-mode-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  margin-left: 10px;
}
.data-mode-tag.realtime {
  background: #e6f7ff;
  color: #1890ff;
  border: 1px solid #91d5ff;
}
.data-mode-tag.csv {
  background: #fff7e6;
  color: #fa8c16;
  border: 1px solid #ffd591;
}
.data-error-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #fff2f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
  margin-left: 10px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header-actions {
  display: flex;
  gap: 10px;
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
  color: var(--text);
  margin: 0;
}
.detail-grid {
  display: grid;
  grid-template-columns: 250px 1fr;
  gap: 20px;
}
.model-list {
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  scrollbar-width: thin;
  max-height: 300px;
}
.model-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  white-space: nowrap;
}
.model-name {
  color: #333;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.2s;
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #fff;
}
.model-name.active {
  color: var(--primary);
  border-color: var(--primary);
  background: rgba(24, 144, 255, 0.08);
}
.period-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}
.period-input {
  width: 140px;
  padding: 4px 8px;
  font-size: 13px;
}
.filter-section {
  padding: 16px 20px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.filter-section label {
  font-size: 12px;
  color: var(--muted);
}
.filter-section .input {
  width: 100%;
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
.square {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}
.square.red { background: #ff4d4f; }
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
.chart-empty p {
  margin: 0;
}
</style>
