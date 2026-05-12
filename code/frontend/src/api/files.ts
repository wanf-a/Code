import apiClient from "./client";
import type { Paginated } from "./types";

export type DatasetFile = {
  id: number;
  dataset_id: number;
  original_name: string;
  stored_path: string;
  size_kb: number;
  description?: string;
  created_by: number;
  created_at: string;
};

export type FilesQuery = {
  page?: number;
  size?: number;
  dataset_id?: number;
  keyword?: string;
};

export const fetchFiles = async (query: FilesQuery = {}) => {
  const { data } = await apiClient.get<Paginated<DatasetFile>>("/files", { params: query });
  return data;
};

export const deleteFile = async (fileId: number) => {
  const { data } = await apiClient.delete<{ message: string }>(`/files/${fileId}`);
  return data;
};

export const downloadFile = (fileId: number) => {
  return apiClient.get(`/files/${fileId}/download`, { responseType: "blob" });
};

