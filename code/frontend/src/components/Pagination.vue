<template>
  <div v-if="totalPages > 1" class="pagination">
    <button
      class="pagination-btn"
      :disabled="currentPage <= 1"
      @click="$emit('change', currentPage - 1)"
    >
      上一页
    </button>
    <span class="pagination-info">
      第 {{ currentPage }} / {{ totalPages }} 页，共 {{ total }} 条
    </span>
    <button
      class="pagination-btn"
      :disabled="currentPage >= totalPages"
      @click="$emit('change', currentPage + 1)"
    >
      下一页
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  total: number;
  currentPage: number;
  pageSize: number;
}>();

defineEmits<{
  (e: "change", page: number): void;
}>();

const totalPages = computed(() => Math.ceil(props.total / props.pageSize));
</script>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 16px 20px;
  border-top: 1px solid var(--border);
}

.pagination-btn {
  height: 32px;
  padding: 0 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-1);
  color: var(--text);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.pagination-btn:hover:not(:disabled) {
  background: var(--bg-2);
  border-color: var(--primary);
  color: var(--primary);
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 13px;
  color: var(--muted);
}
</style>
