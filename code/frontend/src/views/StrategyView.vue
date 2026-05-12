<template>
  <div class="strategy-page">
    <h2 class="page-title">策略报价分析 - {{ currentPlant }}</h2>
    <div class="action-buttons">
      <button class="btn-run" @click="runStrategy" :disabled="running">{{ running ? '策略生成中...' : '生成策略' }}</button>
      <!-- <button class="btn-run eval" @click="runEval" :disabled="running">{{ running ? '评价中...' : '评价' }}</button> -->
      <span v-if="runMsg" class="run-msg" :class="runOk ? 'ok' : 'err'">{{ runMsg }}</span>
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-if="summary" class="summary-cards">
      <div class="card highlight">
        <div class="card-label">推荐最优加价率</div>
        <div class="card-value">{{ avgMarkup }}%</div>
        <div class="card-sub">物理信号: {{ avgPhys }}% | 预测信号: {{ avgPred }}%</div>
      </div>
      <div class="card">
        <div class="card-label">基线收益（万元）</div>
        <div class="card-value">{{ fmtNum(summary.total_base_revenue) }}</div>
      </div>
      <div class="card">
        <div class="card-label">策略收益（万元）</div>
        <div class="card-value green">{{ fmtNum(summary.total_strat_revenue) }}</div>
      </div>
      <div class="card">
        <div class="card-label">收益变化</div>
        <div class="card-value" :class="summary.revenue_change_pct > 0 ? 'green' : 'red'">
          {{ summary.revenue_change_pct > 0 ? '+' : '' }}{{ summary.revenue_change_pct.toFixed(2) }}%
        </div>
      </div>
      <!-- <div class="card">
        <div class="card-label">出清均价变化</div>
        <div class="card-value" :class="postClearing?.price_change_pct < 0 ? 'red' : 'green'">{{ postClearing?.price_change_pct?.toFixed(2) }}%</div>
      </div>
      <div class="card">
        <div class="card-label">HHI 变化</div>
        <div class="card-value">{{ (postClearing?.hhi_strat - postClearing?.hhi_base)?.toFixed(0) }}</div>
      </div> -->
    </div>
    <div v-if="filteredDailyMarkups.length" class="section">
      <h3>每日加价率明细</h3>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>日期</th><th>物理信号</th><th>预测信号</th><th>总加价率</th>
            <th>策略报价</th><th>基线报价</th><th>供需比</th><th>尖峰概率</th>
          </tr></thead>
          <tbody>
            <tr v-for="row in filteredDailyMarkups" :key="row.dayIndex">
              <td>{{ row.dayIndex }}</td>
              <td :class="row.alpha_phys > 0 ? 'green' : 'red'">{{ (row.alpha_phys * 100).toFixed(2) }}%</td>
              <td :class="row.alpha_pred > 0 ? 'green' : 'red'">{{ (row.alpha_pred * 100).toFixed(2) }}%</td>
              <td :class="row.markup > 0 ? 'green' : 'red'"><strong>{{ (row.markup * 100).toFixed(2) }}%</strong></td>
              <td>{{ row.sec1_price?.toFixed(2) }}</td>
              <td>{{ row.bs3_sec1?.toFixed(2) }}</td>
              <td>{{ row.sdr?.toFixed(3) }}</td>
              <td>{{ (row.pred_spike * 100).toFixed(1) }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <!-- <div v-if="postClearing" class="section">
      <h4>收益对比</h4>
      <div class="table-wrap">
        <table>
          <thead><tr><th>公司</th><th>基线净收益（万）</th><th>策略净收益（万）</th><th>收益变化（万）</th><th>变化率</th><th>角色</th></tr></thead>
          <tbody>
            <tr v-for="co in filteredCompanies" :key="co.plant_name">
              <td><strong>{{ co.plant_name }}</strong></td>
              <td>{{ co.base_net_rev?.toFixed(1) }}</td>
              <td>{{ co.strat_net_rev?.toFixed(1) }}</td>
              <td :class="co.delta > 0 ? 'green' : 'red'">{{ co.delta > 0 ? '+' : '' }}{{ co.delta?.toFixed(1) }}</td>
              <td :class="co.pct > 0 ? 'green' : 'red'">{{ co.pct?.toFixed(2) }}%</td>
              <td>{{ co.is_target ? '⭐ 目标' : '竞争对手' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div> -->
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import apiClient from "../api/client";

// 从 JWT token 中解析当前登录用户的电厂名称
const getCurrentPlant = () => {
  const token = localStorage.getItem("access_token");
  if (!token) return "G13";
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.sub || "G13";
  } catch (e) {
    return "G13";
  }
};

const currentPlant = getCurrentPlant();
const loading = ref(false);
const summary = ref<any>(null);
const dailyMarkups = ref<any[]>([]);
const postClearing = ref<any>(null);

const fmtNum = (n: number) => n?.toFixed(1) ?? "-";
const avgMarkup = computed(() => {
  if (!dailyMarkups.value.length) return "-";
  return (dailyMarkups.value.reduce((s, r) => s + r.markup, 0) / dailyMarkups.value.length * 100).toFixed(2);
});
const avgPhys = computed(() => {
  if (!dailyMarkups.value.length) return "-";
  return (dailyMarkups.value.reduce((s, r) => s + r.alpha_phys, 0) / dailyMarkups.value.length * 100).toFixed(2);
});
const avgPred = computed(() => {
  if (!dailyMarkups.value.length) return "-";
  return (dailyMarkups.value.reduce((s, r) => s + r.alpha_pred, 0) / dailyMarkups.value.length * 100).toFixed(2);
});

const filteredDailyMarkups = computed(() => {
  if (!dailyMarkups.value.length) return [];
  const dayLabels = ["第一天", "第二天", "第三天", "第四天", "第五天", "第六天", "第七天"];
  return dailyMarkups.value.slice(0, 7).map((row, index) => ({
    ...row,
    dayIndex: dayLabels[index]
  }));
});

// 只显示当前公司和目标公司
const filteredCompanies = computed(() => {
  if (!postClearing.value?.companies) return [];
  return postClearing.value.companies.filter((co: { is_target: any; plant_name: any; }) => co.is_target || co.plant_name === currentPlant);
});

const loadDetail = async () => {
  loading.value = true;
  try {
    const res = await apiClient.get(`/market/strategy-detail/${currentPlant}`);
    summary.value = res.data.summary || null;
    dailyMarkups.value = res.data.daily_markups || [];
    postClearing.value = res.data.post_clearing || null;
  } catch (e) { console.error(e); }
  finally { loading.value = false; }
};

const running = ref(false);
const runMsg = ref("");
const runOk = ref(false);

const runStrategy = async () => {
  running.value = true; runMsg.value = "";
  try {
    const res = await apiClient.post(`/market/run-strategy/${currentPlant}`);
    runOk.value = res.data.success;
    runMsg.value = res.data.success ? "策略生成完成! 正在刷新..." : "失败：" + (res.data.error || res.data.stderr?.slice(0,200));
    if (res.data.success) { await loadDetail(); }
  } catch (e) { runMsg.value = "请求失败"; runOk.value = false; }
  finally { running.value = false; }
};

const runEval = async () => {
  running.value = true; runMsg.value = "";
  try {
    const res = await apiClient.post(`/market/run-evaluation/${currentPlant}`);
    runOk.value = res.data.success;
    runMsg.value = res.data.success ? "评价完成! 正在刷新..." : "失败：" + (res.data.error || res.data.stderr?.slice(0,200));
    if (res.data.success) { await loadDetail(); }
  } catch (e) { runMsg.value = "请求失败"; runOk.value = false; }
  finally { running.value = false; }
};

onMounted(() => { loadDetail(); });
</script>

<style scoped>
.strategy-page { max-width: 1200px; }
.page-title { font-size: 20px; font-weight: 700; margin-bottom: 16px; color: #1a1a2e; }
.page-title .plant-name { color: #1890ff; font-weight: 600; }
.loading { text-align: center; padding: 40px; color: #999; }
.section { margin-top: 24px; }
.section h3 { font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #1a1a2e; border-left: 3px solid #1890ff; padding-left: 8px; }
.section h4 { font-size: 14px; font-weight: 600; color: #333; }
.summary-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-bottom: 16px; }
.card { background: #fff; border-radius: 8px; padding: 16px; border: 1px solid #e8e8e8; }
.card.highlight { border-color: #1890ff; background: #e6f7ff; }
.card-label { font-size: 12px; color: #999; margin-bottom: 6px; }
.card-value { font-size: 22px; font-weight: 700; color: #1a1a2e; }
.card-sub { font-size: 11px; color: #666; margin-top: 4px; }
.green { color: #52c41a; }
.red { color: #f5222d; }
.blue { color: #1890ff; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; background: #fff; border-radius: 6px; overflow: hidden; }
th { background: #fafafa; padding: 10px 12px; text-align: left; font-weight: 600; color: #333; border-bottom: 2px solid #e8e8e8; white-space: nowrap; }
td { padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }
tr:hover { background: #fafafa; }
.row-highlight { background: #e6f7ff !important; }
.action-buttons { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.btn-run { padding: 8px 20px; border: 1px solid #1890ff; background: #1890ff; color: #fff; border-radius: 4px; cursor: pointer; font-size: 14px; }
.btn-run:hover { background: #40a9ff; }
.btn-run:disabled { background: #d9d9d9; border-color: #d9d9d9; cursor: not-allowed; }
.btn-run.eval { background: #52c41a; border-color: #52c41a; }
.btn-run.eval:hover { background: #73d13d; }
.run-msg { font-size: 13px; }
.run-msg.ok { color: #52c41a; }
.run-msg.err { color: #f5222d; }
</style>
