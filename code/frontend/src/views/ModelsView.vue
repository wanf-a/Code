<template>
  <MainLayout>
    <div class="page-header">
      <h1 class="page-title">模型管理</h1>
      <div class="header-actions">
        <button class="btn" :disabled="seeding" @click="handleSeedEpfModels">
          {{ seeding ? "初始化中..." : "初始化EPF模型" }}
        </button>
        <button class="btn primary" @click="showUploadModal = true">上传模型文件</button>
      </div>
    </div>

    <section class="panel">
      <div class="panel-header">
        <h3 class="panel-title">模型列表</h3>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>模型名称</th>
              <th>描述</th>
              <th>数据集</th>
              <th>类型</th>
              <th>训练状态</th>
              <th>数据集校核状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="model in staticModels" :key="model.id">
              <td>{{ model.name }}</td>
              <td>{{ model.description }}</td>
              <td>{{ model.dataset }}</td>
              <td>{{ model.type }}</td>
              <td>
                <span :class="['status-tag', model.status === 'trained' ? 'verified' : 'unverified']">
                  {{ model.status === "trained" ? "已训练" : "未训练" }}
                </span>
              </td>
              <td>
                <span :class="['status-tag', getStatusClass(model.verify_status)]">
                  {{ normalizeVerifyStatus(model.verify_status) }}
                </span>
              </td>
              <td>
                <a class="link" href="#" @click.prevent="openVerifyModal(model)">数据集校核</a>
                <a class="link" href="#" @click.prevent="handleTrainModel(model)">训练模型</a>
                <a class="link" href="#" @click.prevent="handleUploadTrainedModel(model)">上传文件</a>
                <a class="link" href="#" @click.prevent="handleDownloadTrainedModel(model)">下载训练文件</a>
                <a class="link danger" href="#" @click.prevent="handleDeleteModel(model)">删除</a>
              </td>
            </tr>
            <tr v-if="staticModels.length === 0">
              <td colspan="7" class="empty-row">暂无模型数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-if="trainingTaskId" class="panel training-panel">
      <div class="panel-header">
        <h3 class="panel-title">训练任务 #{{ trainingTaskId }}</h3>
        <span :class="['status-tag', taskStatusClass]">{{ taskStatusLabel }}</span>
      </div>
      <div class="task-body">
        <div v-if="trainingTaskStatus === 'running' || trainingTaskStatus === 'queued'" class="progress-section">
          <div class="progress-info">
            <span class="progress-label">{{ progressLabel }}</span>
            <span class="progress-percent">{{ progressPercent }}%</span>
          </div>
          <div class="progress-bar">
            <div
              class="progress-bar-fill"
              :class="{ indeterminate: progressPercent === 0 }"
              :style="{ width: progressPercent > 0 ? progressPercent + '%' : '100%' }"
            ></div>
          </div>
        </div>
        <div v-if="trainingMessage" class="task-message">{{ trainingMessage }}</div>
        <div class="task-log">
          <div v-for="log in taskLogs" :key="log.id" class="task-log-line">
            <span class="task-log-time">{{ formatDateTime(log.created_at) }}</span>
            <span>{{ log.message }}</span>
          </div>
          <div v-if="taskLogs.length === 0" class="empty-row">暂无日志</div>
        </div>
      </div>
    </section>

    <div v-if="showUploadModal" class="modal-overlay" @click.self="showUploadModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>上传模型文件</h3>
          <button class="modal-close" @click="showUploadModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>模型名称 <span class="required">*</span></label>
            <input class="input" v-model="uploadForm.name" placeholder="请输入模型名称" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea class="input" rows="2" v-model="uploadForm.description" placeholder="请输入描述"></textarea>
          </div>
          <div class="form-group">
            <label>模型文件 <span class="required">*</span></label>
            <input type="file" accept=".py" @change="handleModelFileSelect" />
          </div>
          <div class="form-group">
            <label>选择数据集 <span class="required">*</span></label>
            <select class="input" v-model.number="uploadForm.dataset_id">
              <option value="">请选择数据集</option>
              <option v-for="ds in datasetOptions" :key="ds.id" :value="ds.id">
                {{ ds.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>预测类型 <span class="required">*</span></label>
            <select class="input" v-model="uploadForm.prediction_type">
              <option value="week_ahead">周前概率</option>
            </select>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>训练开始日期</label>
              <input class="input" type="date" v-model="uploadForm.train_start_date" />
            </div>
            <div class="form-group">
              <label>训练结束日期</label>
              <input class="input" type="date" v-model="uploadForm.train_end_date" />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showUploadModal = false">取消</button>
          <button class="btn primary" :disabled="uploading" @click="handleUploadModel">
            {{ uploading ? "上传中..." : "上传" }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showVerifyModal" class="modal-overlay" @click.self="showVerifyModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>数据集校核 - {{ currentModel?.name }}</h3>
          <button class="modal-close" @click="showVerifyModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>数据集名称 <span class="required">*</span></label>
            <select class="input" v-model.number="verifyForm.source_dataset_id">
              <option value="">请选择数据集1</option>
              <option v-for="ds in datasetOptions" :key="ds.id" :value="ds.id">
                {{ ds.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>数据集文件 <span class="required">*</span></label>
            <input type="file" accept=".xlsx" @change="handleVerifyFileSelect" />
            <p class="form-hint">请选择需要与数据集1比对的 xlsx 数据集2，系统会直接比对两者是否一致。</p>
            <p class="form-hint">校核按小数点后两位四舍五入后比较。</p>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showVerifyModal = false">取消</button>
          <button class="btn primary" :disabled="verifying" @click="handleCompareDatasets">
            {{ verifying ? "处理中..." : "开始校核" }}
          </button>
        </div>
      </div>
    </div>

    <input
      ref="trainedFileInput"
      type="file"
      style="display: none"
      accept=".pt,.pth,.pkl,.joblib,.onnx,.zip,.bin,.json,.csv,.xlsx,.xls"
      @change="handleTrainedFileSelect"
    />
  </MainLayout>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import MainLayout from "../layouts/MainLayout.vue";
import { compareDatasetWithUpload, fetchDatasets } from "../api/datasets";
import {
  deleteModel,
  downloadTrainedModelFile,
  fetchModels,
  seedEpfModels,
  trainModel,
  uploadModel,
  uploadTrainedModelFile,
} from "../api/models";
import { fetchTask, fetchTaskLogs, type TaskLog } from "../api/tasks";

type ModelItem = {
  id: number;
  name: string;
  description: string;
  dataset_id: number;
  dataset: string;
  type: string;
  status: string;
  verify_status?: string;
};

const showUploadModal = ref(false);
const showVerifyModal = ref(false);
const verifying = ref(false);
const training = ref(false);
const seeding = ref(false);
const uploading = ref(false);
const trainedFileInput = ref<HTMLInputElement | null>(null);
const pendingUploadModelName = ref("");
const currentModel = ref<ModelItem | null>(null);
const datasetOptions = ref<{ id: number; name: string; verify_status?: string }[]>([]);
const trainingTaskId = ref<number | null>(null);
const trainingTaskStatus = ref("");
const trainingMessage = ref("");
const taskLogs = ref<TaskLog[]>([]);
let pollTimer: number | undefined;
let pollFailCount = 0;

const uploadForm = reactive({
  name: "",
  description: "",
  dataset_id: "" as number | "",
  prediction_type: "week_ahead",
  train_start_date: "2024-01-01",
  train_end_date: "2024-12-31",
  file: null as File | null,
});

const verifyForm = reactive({
  source_dataset_id: "" as number | "",
  file: null as File | null,
});

const staticModels = ref<ModelItem[]>([]);

const taskStatusLabel = computed(() => {
  if (trainingTaskStatus.value === "completed") return "已完成";
  if (trainingTaskStatus.value === "failed") return "失败";
  if (trainingTaskStatus.value === "running") return "运行中";
  return "排队中";
});

const taskStatusClass = computed(() => {
  if (trainingTaskStatus.value === "completed") return "verified";
  if (trainingTaskStatus.value === "failed") return "failed";
  return "unverified";
});

const progressInfo = computed(() => {
  let currentEpoch = 0;
  let totalEpochs = 0;
  let currentBatch = 0;
  let totalBatches = 0;
  for (const log of taskLogs.value) {
    const totalMatch = log.message.match(/max_epochs:\s*(\d+)/);
    if (totalMatch) {
      totalEpochs = parseInt(totalMatch[1], 10);
    }
    const epochMatch = log.message.match(/Epoch\s+(\d+)\s*\/\s*(\d+)/);
    if (epochMatch) {
      const ep = parseInt(epochMatch[1], 10);
      const total = parseInt(epochMatch[2], 10);
      if (ep > currentEpoch) currentEpoch = ep;
      if (total > totalEpochs) totalEpochs = total;
    } else {
      const simpleMatch = log.message.match(/Epoch\s+(\d+)/);
      if (simpleMatch) {
        const ep = parseInt(simpleMatch[1], 10);
        if (ep > currentEpoch) currentEpoch = ep;
      }
    }
    const batchMatch = log.message.match(/batch\s+(\d+)\s*\/\s*(\d+)/);
    if (batchMatch) {
      currentBatch = parseInt(batchMatch[1], 10);
      totalBatches = parseInt(batchMatch[2], 10);
    }
    const stopMatch = log.message.match(/早停于\s*Epoch\s+(\d+)/);
    if (stopMatch) {
      currentEpoch = parseInt(stopMatch[1], 10);
      if (totalEpochs === 0) totalEpochs = currentEpoch;
    }
  }
  return { currentEpoch, totalEpochs, currentBatch, totalBatches };
});

const progressPercent = computed(() => {
  const { currentEpoch, totalEpochs, currentBatch, totalBatches } = progressInfo.value;
  if (totalEpochs > 0) {
    const epochProgress = (currentEpoch - 1) / totalEpochs;
    const batchFraction = totalBatches > 0 ? currentBatch / totalBatches / totalEpochs : 0;
    return Math.min(Math.round((epochProgress + batchFraction) * 100), 99);
  }
  return 0;
});

const progressLabel = computed(() => {
  const { currentEpoch, totalEpochs, currentBatch, totalBatches } = progressInfo.value;
  if (totalEpochs > 0) {
    if (totalBatches > 0 && currentBatch < totalBatches) {
      return `Epoch ${currentEpoch} / ${totalEpochs} (batch ${currentBatch}/${totalBatches})`;
    }
    return `Epoch ${currentEpoch} / ${totalEpochs}`;
  }
  if (trainingTaskStatus.value === "queued") return "排队中...";
  return "训练中...";
});

const toPlanTypeLabel = (predictionType: string) => {
  const text = (predictionType || "").toLowerCase();
  if (text.includes("week")) return "周前概率";
  if (text.includes("day")) return "日前预测";
  return predictionType || "未知";
};

const formatDateTime = (value: string) => new Date(value).toLocaleString();

const loadModels = async () => {
  try {
    const [modelRes, datasetRes] = await Promise.all([
      fetchModels({ page: 1, size: 200 }),
      fetchDatasets({ page: 1, size: 200 }),
    ]);
    const datasetMap = new Map<number, { name: string; verify_status?: string }>(
      datasetRes.items.map((item) => [item.id, { name: item.name, verify_status: item.verify_status }]),
    );
    datasetOptions.value = datasetRes.items.map((item) => ({
      id: item.id,
      name: item.name,
      verify_status: item.verify_status,
    }));
    staticModels.value = modelRes.items.map((item) => {
      const dataset = datasetMap.get(item.dataset_id);
      return {
        id: item.id,
        name: item.name,
        description: item.description || "-",
        dataset_id: item.dataset_id,
        dataset: item.dataset_name || dataset?.name || "未绑定",
        type: toPlanTypeLabel(item.prediction_type),
        status: item.status,
        verify_status: item.verify_status || dataset?.verify_status || "未校核",
      };
    });
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || "未知错误";
    alert("加载模型失败: " + detail);
  }
};

const handleModelFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement;
  uploadForm.file = target.files?.[0] || null;
};

const handleUploadModel = async () => {
  if (uploading.value) return;
  if (!uploadForm.name.trim() || !uploadForm.dataset_id || !uploadForm.file) {
    alert("请填写模型名称、选择数据集并选择模型文件");
    return;
  }
  uploading.value = true;
  try {
    const formData = new FormData();
    formData.append("name", uploadForm.name.trim());
    formData.append("description", uploadForm.description || "");
    formData.append("dataset_id", String(uploadForm.dataset_id));
    formData.append("train_start_date", uploadForm.train_start_date);
    formData.append("train_end_date", uploadForm.train_end_date);
    formData.append("prediction_type", uploadForm.prediction_type);
    formData.append("file", uploadForm.file);
    await uploadModel(formData);
    showUploadModal.value = false;
    uploadForm.name = "";
    uploadForm.description = "";
    uploadForm.dataset_id = "";
    uploadForm.file = null;
    await loadModels();
    alert("模型上传成功");
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || "未知错误";
    alert("模型上传失败: " + detail);
  } finally {
    uploading.value = false;
  }
};

const handleSeedEpfModels = async () => {
  if (seeding.value) return;
  seeding.value = true;
  try {
    const result = await seedEpfModels();
    await loadModels();
    alert(`初始化完成：新增 ${result.created}，已存在 ${result.existing}`);
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || "未知错误";
    alert("初始化失败: " + detail);
  } finally {
    seeding.value = false;
  }
};

const openVerifyModal = (model: ModelItem) => {
  currentModel.value = model;
  verifyForm.source_dataset_id = model.dataset_id;
  verifyForm.file = null;
  showVerifyModal.value = true;
};

const handleVerifyFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement;
  verifyForm.file = target.files?.[0] || null;
};

const handleCompareDatasets = async () => {
  if (!verifyForm.source_dataset_id || !verifyForm.file) {
    alert("请选择要校核的数据集1并上传数据集2文件");
    return;
  }

  verifying.value = true;
  try {
    await compareDatasetWithUpload(verifyForm.source_dataset_id, verifyForm.file);
    // 校核成功，直接更新本地状态
    const verifiedDatasetId = Number(verifyForm.source_dataset_id);
    staticModels.value = staticModels.value.map((model) => {
      if (model.dataset_id === verifiedDatasetId) {
        return { ...model, verify_status: "校核通过" };
      }
      return model;
    });
    showVerifyModal.value = false;
    alert("校核完成: 校核成功");
  } catch (err: any) {
    // 校核失败，更新本地状态
    const failedDatasetId = Number(verifyForm.source_dataset_id);
    staticModels.value = staticModels.value.map((model) => {
      if (model.dataset_id === failedDatasetId) {
        return { ...model, verify_status: "校核失败" };
      }
      return model;
    });
    const detail = err?.response?.data?.detail || err?.message || "未知错误";
    alert("校核失败: " + detail);
  } finally {
    verifying.value = false;
  }
};

const stopPolling = () => {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = undefined;
  }
};

const pollTrainingTask = async (taskId: number) => {
  try {
    const [task, logs] = await Promise.all([fetchTask(taskId), fetchTaskLogs(taskId)]);
    pollFailCount = 0;
    trainingTaskStatus.value = task.status;
    if (task.status === "failed") {
      trainingMessage.value = task.last_error || "训练失败，请查看任务日志";
    } else if (task.status === "completed") {
      trainingMessage.value = "训练完成，已生成 checkpoint.zip";
    } else {
      trainingMessage.value = "";
    }
    taskLogs.value = logs.items.slice().reverse();
    if (task.status === "completed" || task.status === "failed") {
      stopPolling();
      training.value = false;
      await loadModels();
      if (task.status === "completed") {
        alert("训练完成，已生成 checkpoint.zip");
      } else {
        alert("训练失败: " + (task.last_error || "请查看任务日志"));
      }
    }
  } catch (err: any) {
    pollFailCount++;
    if (pollFailCount >= 5) {
      stopPolling();
      training.value = false;
      const detail = err?.response?.data?.detail || err?.message || "未知错误";
      alert("获取训练任务状态失败: " + detail);
    }
  }
};

const startPolling = (taskId: number) => {
  stopPolling();
  trainingTaskId.value = taskId;
  trainingTaskStatus.value = "queued";
  taskLogs.value = [];
  pollFailCount = 0;
  void pollTrainingTask(taskId);
  pollTimer = window.setInterval(() => void pollTrainingTask(taskId), 3000);
};

const handleTrainModel = async (model: ModelItem) => {
  if (training.value) return;
  training.value = true;
  try {
    const result = await trainModel(model.id);
    trainingMessage.value = result.message;
    startPolling(result.task_id);
  } catch (err: any) {
    training.value = false;
    const detail = err?.response?.data?.detail || err?.message || "未知错误";
    alert("训练提交失败: " + detail);
  }
};

const handleUploadTrainedModel = (model: ModelItem) => {
  pendingUploadModelName.value = model.name;
  trainedFileInput.value?.click();
};

const handleTrainedFileSelect = async (e: Event) => {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file || !pendingUploadModelName.value) return;

  try {
    await uploadTrainedModelFile(pendingUploadModelName.value, file);
    alert(`已上传文件：${file.name}`);
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || "未知错误";
    alert("上传文件失败: " + detail);
  } finally {
    target.value = "";
    pendingUploadModelName.value = "";
  }
};

const handleDownloadTrainedModel = async (model: ModelItem) => {
  try {
    const response = await downloadTrainedModelFile(model.name);
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;

    const disposition = response.headers["content-disposition"] as string | undefined;
    const matched = disposition?.match(/filename="?([^"]+)"?/i);
    link.download = matched?.[1] || `${model.name}_checkpoint.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || "未知错误";
    alert("下载训练文件失败: " + detail);
  }
};

const handleDeleteModel = async (model: ModelItem) => {
  if (!confirm(`确定删除模型 "${model.name}" 吗？`)) return;
  try {
    await deleteModel(model.id);
    staticModels.value = staticModels.value.filter((item) => item.id !== model.id);
    alert("删除成功");
  } catch (err: any) {
    const detail = err?.response?.data?.detail || err?.message || "未知错误";
    alert("删除失败: " + detail);
  }
};

const getStatusClass = (status?: string) => {
  const normalized = normalizeVerifyStatus(status);
  if (normalized === "校核成功") return "verified";
  if (normalized === "校核失败") return "failed";
  return "unverified";
};

const normalizeVerifyStatus = (status?: string) => {
  if (!status) return "未校核";
  if (status.includes("通过") || status.includes("閫氳繃") || status.includes("成功")) return "校核成功";
  if (status.includes("失败") || status.includes("澶辫触")) return "校核失败";
  if (status.includes("中") || status.includes("涓")) return "校核中";
  if (status.includes("未") || status.includes("鏈")) return "未校核";
  return status;
};

onMounted(loadModels);
onBeforeUnmount(stopPolling);
</script>

<style scoped>
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}
.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.table td a.link {
  margin-right: 12px;
}
.training-panel {
  margin-top: 16px;
}
.task-body {
  padding: 16px 20px;
}
.task-message {
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--muted);
  word-break: break-all;
}
.task-log {
  max-height: 220px;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #fff;
}
.task-log-line {
  display: flex;
  gap: 12px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}
.task-log-line:last-child {
  border-bottom: 0;
}
.task-log-time {
  flex: 0 0 150px;
  color: var(--muted);
}

.progress-section {
  margin-bottom: 16px;
}
.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
  color: var(--text);
}
.progress-label {
  font-weight: 500;
}
.progress-percent {
  color: var(--muted);
}
.progress-bar {
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #2563eb);
  border-radius: 4px;
  transition: width 0.5s ease;
}
.progress-bar-fill.indeterminate {
  width: 30% !important;
  animation: indeterminate 1.5s infinite ease-in-out;
}
@keyframes indeterminate {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: var(--card);
  border-radius: 8px;
  width: 520px;
  max-width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.modal-header h3 {
  margin: 0;
  font-size: 16px;
}
.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: var(--muted);
}
.modal-body {
  padding: 20px;
}
.modal-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.form-group {
  margin-bottom: 16px;
}
.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 500;
}
.form-group .required {
  color: var(--red);
}
.form-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
}
.form-row {
  display: flex;
  gap: 16px;
}
.form-row .form-group {
  flex: 1;
}

.status-tag {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}
.status-tag.verified {
  background: rgba(34, 197, 94, 0.15);
  color: #15803d;
}
.status-tag.failed {
  background: rgba(239, 68, 68, 0.15);
  color: #dc2626;
}
.status-tag.unverified {
  background: rgba(156, 163, 175, 0.15);
  color: #6b7280;
}
</style>
