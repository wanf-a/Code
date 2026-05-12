<template>
  <MainLayout>
    <template #breadcrumb>文件管理</template>

    <div class="page-header">
      <div>
        <h1 class="page-title">数据文件管理</h1>
        <p class="page-desc">管理上传的数据文件</p>
      </div>
      <div style="display: flex; gap: 10px">
        <button class="btn success">上传数据</button>
        <button class="btn">刷新</button>
        <button class="btn">导出</button>
      </div>
    </div>

    <section class="panel">
      <div class="toolbar">
        <input v-model="filters.keyword" class="input" placeholder="请输入数据名称" />
        <button class="btn primary" type="button" @click="loadFiles">搜索</button>
        <button class="btn" type="button" @click="resetFilters">重置</button>
      </div>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th style="width: 160px">数据集名称</th>
              <th>文件名</th>
              <th style="width: 90px">作者</th>
              <th style="width: 170px">创建时间</th>
              <th style="width: 140px">描述</th>
              <th style="width: 90px">大小</th>
              <th style="width: 120px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in files" :key="item.id">
              <td>电价数据-导入</td>
              <td>{{ item.original_name }}</td>
              <td>admin</td>
              <td>{{ item.created_at }}</td>
              <td>{{ item.description || "" }}</td>
              <td>{{ item.size_kb }}KB</td>
              <td>
                <a class="link" href="#" @click.prevent="handleDownload(item)">下载</a>
                <span style="opacity: .35; margin: 0 6px">|</span>
                <a class="link danger" href="#" @click.prevent="handleDelete(item)">删除</a>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="loading" style="padding: 16px; color: var(--muted); font-size: 13px">
          加载中...
        </div>
        <div v-if="error" style="padding: 16px; color: var(--red); font-size: 13px">
          {{ error }}
        </div>
      </div>
    </section>
  </MainLayout>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import MainLayout from "../layouts/MainLayout.vue";
import { deleteFile, downloadFile, fetchFiles, type DatasetFile } from "../api/files";

const files = ref<DatasetFile[]>([]);
const loading = ref(false);
const error = ref("");

const filters = reactive({
  keyword: "",
});

const loadFiles = async () => {
  error.value = "";
  loading.value = true;
  try {
    const data = await fetchFiles({ page: 1, size: 50, keyword: filters.keyword || undefined });
    files.value = data.items;
  } catch (err) {
    error.value = "加载文件失败";
  } finally {
    loading.value = false;
  }
};

const resetFilters = () => {
  filters.keyword = "";
  loadFiles();
};

const handleDownload = async (item: DatasetFile) => {
  try {
    const response = await downloadFile(item.id);
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a");
    link.href = url;
    link.download = item.original_name;
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    error.value = "下载失败";
  }
};

const handleDelete = async (item: DatasetFile) => {
  if (!confirm("确定删除该文件吗？")) {
    return;
  }
  try {
    await deleteFile(item.id);
    loadFiles();
  } catch (err) {
    error.value = "删除失败";
  }
};

onMounted(loadFiles);
</script>

