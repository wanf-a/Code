<template>
  <MainLayout>
    <!-- 数据集列表 -->
    <section v-if="!showDetail" class="panel">
      <div class="panel-header">
        <h3 class="panel-title">电价数据管理</h3>
        <button class="btn primary" @click="openUploadModal">上传数据集</button>
      </div>
      <div class="sub-panel">
        <h4 class="sub-title">数据集列表</h4>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>数据集名称</th>
                <th>描述</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ds in datasets" :key="ds.id">
                <td>{{ ds.name }}</td>
                <td>{{ ds.description || '-' }}</td>
                <td>{{ ds.created_at }}</td>
                <td class="action-cell">
                  <a class="link primary" @click="viewDataset(ds)">查看</a>
                  <a class="link" @click="handleDownload(ds)">下载</a>
                  <a class="link danger" @click="handleDelete(ds)">删除</a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 数据集详情 -->
    <section v-else class="panel">
      <div class="panel-header">
        <h3 class="panel-title">数据集展示 - {{ currentDataset?.name }}</h3>
        <button class="btn" @click="backToList">返回列表</button>
      </div>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>时间</th>
              <th>电价(元/kWh)</th>
              <th>负荷(kW)</th>
              <th>温度(℃)</th>
              <th>风速(m/s)</th>
              <th>云量(%)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="recordsLoading">
              <td colspan="6" class="loading-text">加载中...</td>
            </tr>
            <tr v-else-if="error">
              <td colspan="6" class="error-text">{{ error }}</td>
            </tr>
            <tr v-else-if="displayRecords.length === 0">
              <td colspan="6" class="empty-text">暂无数据</td>
            </tr>
            <tr v-else v-for="item in displayRecords" :key="item.id">
              <td>{{ item.record_time }}</td>
              <td>{{ item.price_kwh }}</td>
              <td>{{ item.load_kw }}</td>
              <td>{{ item.temperature ?? '-' }}</td>
              <td>{{ item.wind_speed ?? '-' }}</td>
              <td>{{ item.cloud_cover ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="pagination-bar">
        <span class="pagination-info">共 {{ totalRecords }} 条记录，第 {{ currentPage }}/{{ totalPages }} 页</span>
        <div class="pagination-controls">
          <button class="btn pagination-btn" :disabled="currentPage <= 1" @click="goToPage(currentPage - 1)">上一页</button>
          <select v-model="pageSize" class="input page-size-select" @change="onPageSizeChange">
            <option :value="10">10条/页</option>
            <option :value="20">20条/页</option>
            <option :value="50">50条/页</option>
            <option :value="100">100条/页</option>
          </select>
          <button class="btn pagination-btn" :disabled="currentPage >= totalPages" @click="goToPage(currentPage + 1)">下一页</button>
        </div>
      </div>
    </section>
    <!-- 上传数据集弹窗 -->
    <div v-if="showUploadModal" class="modal-overlay" @click.self="closeUploadModal">
      <div class="modal">
        <div class="modal-header">
          <h3>上传数据集</h3>
          <button class="close-btn" @click="closeUploadModal">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>数据集名称</label>
            <input v-model="uploadForm.name" class="input" placeholder="请输入数据集名称" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <input v-model="uploadForm.description" class="input" placeholder="请输入描述（可选）" />
          </div>
          <div class="form-group">
            <label>选择文件</label>
            <input type="file" accept=".xlsx" @change="onFileChange" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="closeUploadModal">取消</button>
          <button class="btn primary" :disabled="uploading" @click="handleUpload">
            {{ uploading ? '上传中...' : '上传' }}
          </button>
        </div>
      </div>
    </div>
  </MainLayout>
</template>

<script setup lang="ts">
import axios from "axios";
import { computed, onMounted, reactive, ref } from "vue";
import MainLayout from "../layouts/MainLayout.vue";
import {
  fetchDatasets,
  fetchDatasetRecords,
  uploadDataset,
  downloadDataset,
  deleteDataset,
  type Dataset,
  type DatasetRecord,
} from "../api/datasets";

const datasets = ref<Dataset[]>([]);
const showDetail = ref(false);
const currentDataset = ref<Dataset | null>(null);

const records = ref<DatasetRecord[]>([]);
const recordsLoading = ref(false);
const error = ref("");

const currentPage = ref(1);
const pageSize = ref(10);
const totalRecords = ref(0);
const totalPages = computed(() => Math.ceil(totalRecords.value / pageSize.value) || 1);

const displayRecords = computed<DatasetRecord[]>(() => records.value);

const loadDatasets = async () => {
  try {
    const data = await fetchDatasets();
    datasets.value = data.items;
  } catch (err) {
    console.error("加载数据集失败", err);
  }
};

const viewDataset = (ds: Dataset) => {
  currentDataset.value = ds;
  currentPage.value = 1;
  showDetail.value = true;
  loadRecords();
};

const backToList = () => {
  showDetail.value = false;
  currentDataset.value = null;
  records.value = [];
  error.value = "";
  currentPage.value = 1;
};

const loadRecords = async () => {
  if (!currentDataset.value) {
    return;
  }

  recordsLoading.value = true;
  error.value = "";
  try {
    const data = await fetchDatasetRecords(currentDataset.value.id, {
      page: currentPage.value,
      size: pageSize.value,
    });
    records.value = data.items;
    totalRecords.value = data.total;
  } catch (err) {
    error.value = "加载数据失败";
  } finally {
    recordsLoading.value = false;
  }
};

const goToPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return;
  currentPage.value = page;
  loadRecords();
};

const onPageSizeChange = () => {
  currentPage.value = 1;
  loadRecords();
};

const showUploadModal = ref(false);
const uploading = ref(false);
const uploadForm = reactive({
  name: "",
  description: "",
  file: null as File | null,
});

const openUploadModal = () => {
  uploadForm.name = "";
  uploadForm.description = "";
  uploadForm.file = null;
  showUploadModal.value = true;
};

const closeUploadModal = () => {
  showUploadModal.value = false;
  uploadForm.name = "";
  uploadForm.description = "";
  uploadForm.file = null;
};

const onFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    uploadForm.file = target.files[0];
  }
};

const getUploadErrorMessage = (err: unknown) => {
  if (axios.isAxiosError(err)) {
    return err.response?.data?.detail || err.message || "上传失败";
  }
  return "上传失败";
};

const handleUpload = async () => {
  if (!uploadForm.name || !uploadForm.file) {
    alert("请填写数据集名称并选择Excel文件");
    return;
  }
  if (!uploadForm.file.name.toLowerCase().endsWith(".xlsx")) {
    alert("只支持Excel文件(.xlsx)");
    return;
  }

  uploading.value = true;
  try {
    const formData = new FormData();
    formData.append("name", uploadForm.name);
    formData.append("file", uploadForm.file);
    if (uploadForm.description) {
      formData.append("description", uploadForm.description);
    }
    await uploadDataset(formData);
    alert("上传成功");
    closeUploadModal();
    loadDatasets();
  } catch (err) {
    alert(getUploadErrorMessage(err));
    console.error(err);
  } finally {
    uploading.value = false;
  }
};

const handleDownload = async (ds: Dataset) => {
  try {
    const response = await downloadDataset(ds.id);
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${ds.name}.xlsx`;
    a.click();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert("下载失败");
    console.error(err);
  }
};

const handleDelete = async (ds: Dataset) => {
  if (!confirm(`确定要删除数据集 "${ds.name}" 吗？`)) return;
  try {
    await deleteDataset(ds.id);
    alert("删除成功");
    loadDatasets();
  } catch (err) {
    alert("删除失败");
    console.error(err);
  }
};

onMounted(loadDatasets);
</script>

<style scoped>
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
}
.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
}
.sub-panel {
  padding: 16px 24px;
}
.sub-title {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}
.action-cell a.link {
  margin-right: 8px;
  cursor: pointer;
}
.action-cell a.link.primary {
  color: var(--primary);
}
.action-cell a.link.danger {
  color: var(--red);
}
.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-top: 1px solid var(--border);
}
.pagination-info {
  font-size: 14px;
  color: var(--primary);
}
.pagination-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}
.pagination-btn {
  min-width: 70px;
}
.page-size-select {
  width: 110px;
  padding: 6px 10px;
}
.loading-text, .error-text, .empty-text {
  padding: 16px;
  font-size: 13px;
  text-align: center;
}
.loading-text { color: var(--muted); }
.error-text { color: var(--red); }
.empty-text { color: var(--muted); }

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}
.modal {
  background: #fff;
  border-radius: 12px;
  width: 480px;
  max-width: 90%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  animation: modalFadeIn 0.2s ease-out;
}
@keyframes modalFadeIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #eee;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  border-radius: 12px 12px 0 0;
}
.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}
.close-btn {
  background: rgba(255, 255, 255, 0.2);
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #fff;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}
.close-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}
.modal-body {
  padding: 24px;
}
.form-group {
  margin-bottom: 20px;
}
.form-group:last-child {
  margin-bottom: 0;
}
.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}
.form-group .input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}
.form-group .input:focus {
  border-color: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.1);
  outline: none;
}
.form-group .input::placeholder {
  color: #bbb;
}
.form-group input[type="file"] {
  display: block;
  width: 100%;
  padding: 12px;
  border: 2px dashed #d9d9d9;
  border-radius: 6px;
  background: #fafafa;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.form-group input[type="file"]:hover {
  border-color: #1890ff;
  background: #f0f7ff;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid #eee;
  background: #fafafa;
  border-radius: 0 0 12px 12px;
}
</style>
