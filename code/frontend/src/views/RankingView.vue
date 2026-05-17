<template>
  <MainLayout>
    <div class="page-header">
      <h1 class="page-title">评分管理</h1>
    </div>

    <section class="panel">
      <div class="panel-header">
        <h3 class="panel-title">模型排名</h3>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th class="filterable" @click="toggleFilter('dataset')">
                <div class="header-content">
                  <span class="filter-text">数据集</span>
                  <div class="filter-dropdown" v-if="activeFilter === 'dataset'">
                    <div class="filter-menu">
                      <div class="filter-options">
                        <label v-for="option in datasetOptions" :key="option">
                          <input 
                            type="checkbox" 
                            :checked="filters.dataset.includes(option)"
                            @click.stop="toggleFilterOption('dataset', option)"
                          />
                          {{ option }}
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </th>
              <th class="filterable" @click="toggleFilter('type')">
                <div class="header-content">
                  <span class="filter-text">类型</span>
                  <div class="filter-dropdown" v-if="activeFilter === 'type'">
                    <div class="filter-menu">
                      <div class="filter-options">
                        <label v-for="option in typeOptions" :key="option">
                          <input 
                            type="checkbox" 
                            :checked="filters.type.includes(option)"
                            @click.stop="toggleFilterOption('type', option)"
                          />
                          {{ option }}
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </th>
              <th class="filterable" @click="toggleFilter('model')">
                <div class="header-content">
                  <span class="filter-text">模型名称</span>
                  <div class="filter-dropdown" v-if="activeFilter === 'model'">
                    <div class="filter-menu">
                      <div class="filter-options">
                        <label v-for="option in modelOptions" :key="option">
                          <input 
                            type="checkbox" 
                            :checked="filters.model.includes(option)"
                            @click.stop="toggleFilterOption('model', option)"
                          />
                          {{ option }}
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </th>
              <th class="filterable" @click="toggleFilter('period')">
                <div class="header-content">
                  <span class="filter-text">预测时间段</span>
                  <div class="filter-dropdown" v-if="activeFilter === 'period'">
                    <div class="filter-menu">
                      <div class="filter-options">
                        <label v-for="option in periodOptions" :key="option">
                          <input 
                            type="checkbox" 
                            :checked="filters.period.includes(option)"
                            @click.stop="toggleFilterOption('period', option)"
                          />
                          {{ option }}
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </th>
              <th class="filterable" @click="toggleFilter('load')">
                <div class="header-content">
                  <span class="filter-text">负荷</span>
                  <div class="filter-dropdown" v-if="activeFilter === 'load'">
                    <div class="filter-menu">
                      <div class="filter-options">
                        <label v-for="option in loadOptions" :key="option">
                          <input 
                            type="checkbox" 
                            :checked="filters.load.includes(option)"
                            @click.stop="toggleFilterOption('load', option)"
                          />
                          {{ option }}
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </th>
              <th class="filterable" @click="toggleFilter('wind')">
                <div class="header-content">
                  <span class="filter-text">风速</span>
                  <div class="filter-dropdown" v-if="activeFilter === 'wind'">
                    <div class="filter-menu">
                      <div class="filter-options">
                        <label v-for="option in windOptions" :key="option">
                          <input 
                            type="checkbox" 
                            :checked="filters.wind.includes(option)"
                            @click.stop="toggleFilterOption('wind', option)"
                          />
                          {{ option }}
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </th>
              <th class="filterable" @click="toggleFilter('weather_type')">
                <div class="header-content">
                  <span class="filter-text">天气</span>
                  <div class="filter-dropdown" v-if="activeFilter === 'weather_type'">
                    <div class="filter-menu">
                      <div class="filter-options">
                        <label v-for="option in weatherOptions" :key="option">
                          <input 
                            type="checkbox" 
                            :checked="filters.weather_type.includes(option)"
                            @click.stop="toggleFilterOption('weather_type', option)"
                          />
                          {{ option }}
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
              </th>
              <th>MAE</th>
              <th>RMSE</th>
              <th>R2</th>
              <th>IMAPE</th>
              <th>分数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredRankings" :key="item.id">
              <td>{{ item.dataset }}</td>
              <td>{{ item.type }}</td>
              <td><a class="link">{{ item.model }}</a></td>
              <td>{{ item.period }}</td>
              <td>{{ item.load }}</td>
              <td>{{ item.wind }}</td>
              <td>{{ item.weather_type }}</td>
              <td>{{ item.mae }}</td>
              <td>{{ item.rmse }}</td>
              <td>{{ item.r2 }}</td>
              <td>{{ item.imape }}</td>
              <td>{{ item.score }}</td>
            </tr>
            <tr v-if="!loading && filteredRankings.length === 0">
              <td colspan="12" class="empty-row">暂无评分数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </MainLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import MainLayout from "../layouts/MainLayout.vue";
import { fetchRankingSummary, type RankingSummary } from "../api/rankings";

type RankingRow = {
  id: number;
  dataset: string;
  type: string;
  model: string;
  period: string;
  load: string;
  wind: string;
  weather_type: string;
  mae: string;
  rmse: string;
  r2: string;
  imape: string;
  score: string;
};

const rankings = ref<RankingRow[]>([]);
const loading = ref(false);
const storedStartDate = ref("");
const storedEndDate = ref("");

const activeFilter = ref<string | null>(null);

const filters = ref({
  dataset: [] as string[],
  type: [] as string[],
  model: [] as string[],
  period: [] as string[],
  load: [] as string[],
  wind: [] as string[],
  weather_type: [] as string[],
});

// 获取所有唯一的选项
const datasetOptions = computed(() => [...new Set(rankings.value.map(r => r.dataset))]);
const typeOptions = computed(() => [...new Set(rankings.value.map(r => r.type))]);
const modelOptions = computed(() => [...new Set(rankings.value.map(r => r.model))]);
const periodOptions = computed(() => [...new Set(rankings.value.map(r => r.period))]);
const loadOptions = computed(() => [...new Set(rankings.value.map(r => r.load))]);
const windOptions = computed(() => [...new Set(rankings.value.map(r => r.wind))]);
const weatherOptions = computed(() => [...new Set(rankings.value.map(r => r.weather_type))]);

// 筛选后的数据
const filteredRankings = computed(() => {
  return rankings.value
    .filter(item => {
      const datasetMatch = filters.value.dataset.length === 0 || filters.value.dataset.includes(item.dataset);
      const typeMatch = filters.value.type.length === 0 || filters.value.type.includes(item.type);
      const modelMatch = filters.value.model.length === 0 || filters.value.model.includes(item.model);
      const periodMatch = filters.value.period.length === 0 || filters.value.period.includes(item.period);
      const loadMatch = filters.value.load.length === 0 || filters.value.load.includes(item.load);
      const windMatch = filters.value.wind.length === 0 || filters.value.wind.includes(item.wind);
      const weatherMatch = filters.value.weather_type.length === 0 || filters.value.weather_type.includes(item.weather_type);

      return datasetMatch && typeMatch && modelMatch && periodMatch && loadMatch && windMatch && weatherMatch;
    })
    .sort((a, b) => {
      const order = ["tcn", "mamba", "nlinear", "ensemble", "集成"];
      const aKey = order.findIndex(k => a.model.toLowerCase().includes(k));
      const bKey = order.findIndex(k => b.model.toLowerCase().includes(k));
      if (aKey !== -1 || bKey !== -1) {
        if (aKey === -1) return 1;
        if (bKey === -1) return -1;
        if (aKey !== bKey) return bKey - aKey;
      }
      return Number(b.score) - Number(a.score);
    });
});

const toggleFilter = (field: string) => {
  activeFilter.value = activeFilter.value === field ? null : field;
};

const toggleFilterOption = (field: string, option: string) => {
  const filterArray = filters.value[field as keyof typeof filters.value];
  const index = filterArray.indexOf(option);
  
  if (index > -1) {
    filterArray.splice(index, 1);
  } else {
    filterArray.push(option);
  }
};

const toDateTime = (date: string, end: boolean) => {
  if (!date) return undefined;
  return `${date}T${end ? "23:59:59" : "00:00:00"}`;
};

const toRow = (item: RankingSummary, index: number): RankingRow => ({
  id: item.plan_id || index + 1,
  dataset: item.dataset,
  type: item.type,
  model: item.model,
  period: item.period,
  load: item.load,
  wind: item.wind,
  weather_type: item.weather_type,
  mae: item.mae.toFixed(2),
  rmse: item.rmse.toFixed(2),
  r2: item.r2.toFixed(4),
  imape: item.imape.toFixed(4),
  score: item.score.toFixed(2),
});

// 函数定义保持不变，支持默认参数
const loadRankings = async (allowFallback = false) => {
  loading.value = true;
  try {
    const data = await fetchRankingSummary({
      start_time: toDateTime(storedStartDate.value, false),
      end_time: toDateTime(storedEndDate.value, true),
    });
    rankings.value = data.map(toRow);
    if (
      allowFallback &&
      rankings.value.length === 0 &&
      (storedStartDate.value || storedEndDate.value)
    ) {
      storedStartDate.value = "";
      storedEndDate.value = "";
      await loadRankings(false);
    }
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || "未知错误";
    alert("加载评分失败: " + detail);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  const savedPeriod = localStorage.getItem("prediction_period");
  if (savedPeriod) {
    try {
      const parsed = JSON.parse(savedPeriod);
      storedStartDate.value = parsed.start || "";
      storedEndDate.value = parsed.end || "";
    } catch {
      // ignore invalid cache
    }
  }
  loadRankings(true);
});
</script>

<style scoped>
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin: 0;
}

.filterable {
  position: relative;
  cursor: pointer;
  user-select: none;
  text-align: center;
}

.filterable:hover {
  background-color: #f5f5f5;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 0;
  position: relative;
}

.filter-text {
  cursor: pointer;
}

.filter-dropdown {
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}

.filter-menu {
  background: white;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-width: 150px;
  margin-top: 4px;
}

.filter-options {
  padding: 8px;
  max-height: 300px;
  overflow-y: auto;
}

.filter-options label {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  cursor: pointer;
  font-size: 13px;
  border-radius: 3px;
  transition: background-color 0.2s;
}

.filter-options label:hover {
  background-color: #f5f5f5;
}

.filter-options input[type="checkbox"] {
  cursor: pointer;
}
.empty-row {
  text-align: center;
  color: var(--muted);
  padding: 24px 0;
}
</style>