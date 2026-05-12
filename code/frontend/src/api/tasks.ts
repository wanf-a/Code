import apiClient from "./client";
import type { Paginated } from "./types";

export type Task = {
  id: number;
  task_type: string;
  status: "queued" | "running" | "completed" | "failed" | string;
  payload_json: string;
  result_json?: string | null;
  retries: number;
  max_retries: number;
  last_error?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
};

export type TaskLog = {
  id: number;
  task_id: number;
  level: string;
  message: string;
  created_at: string;
};

export const fetchTask = async (taskId: number) => {
  const { data } = await apiClient.get<Task>(`/tasks/${taskId}`, { timeout: 15000 });
  return data;
};

export const fetchTaskLogs = async (taskId: number, page = 1, size = 50) => {
  const { data } = await apiClient.get<Paginated<TaskLog>>(`/tasks/${taskId}/logs`, {
    params: { page, size },
    timeout: 15000,
  });
  return data;
};
