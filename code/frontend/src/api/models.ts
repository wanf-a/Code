import apiClient from "./client";
import type { Paginated } from "./types";

export type Model = {
  id: number;
  name: string;
  description?: string | null;
  file_path: string;
  original_name: string;
  dataset_id: number;
  dataset_name?: string | null;
  verify_status?: string | null;
  train_start_date: string;
  train_end_date: string;
  prediction_type: "week_ahead";
  status: "untrained" | "trained";
  trained_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type EpfCandidate = {
  model_name: string;
  score: number;
  mape_150: number;
  mae: number;
  rmse: number;
  r2: number;
  source_file: string;
};

export type EpfAutoTrainResult = {
  selected_model: string;
  selected_score: number;
  retrained: boolean;
  used_cache: boolean;
  candidates: EpfCandidate[];
  message: string;
};

export type ModelsQuery = {
  page?: number;
  size?: number;
  keyword?: string;
  status?: string;
};

export const fetchModels = async (query: ModelsQuery = {}) => {
  const { data } = await apiClient.get<Paginated<Model>>("/models", { params: query });
  return data;
};

export const uploadModel = async (formData: FormData) => {
  const { data } = await apiClient.post<Model>("/models/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const trainModel = async (modelId: number) => {
  const { data } = await apiClient.post<{
    id: number;
    status: string;
    trained_at?: string | null;
    task_id: number;
    message: string;
  }>(`/models/${modelId}/train`);
  return data;
};

export const autoTrainEpfModels = async () => {
  const { data } = await apiClient.post<EpfAutoTrainResult>("/models/auto-train");
  return data;
};

export const seedEpfModels = async (datasetId?: number) => {
  const { data } = await apiClient.post<{
    dataset_id: number;
    created: number;
    existing: number;
    items: { id: number; name: string }[];
  }>("/models/seed-epf", null, {
    params: datasetId ? { dataset_id: datasetId } : undefined,
  });
  return data;
};

export const uploadTrainedModelFile = async (modelName: string, file: File) => {
  const formData = new FormData();
  formData.append("model_name", modelName);
  formData.append("file", file);
  const { data } = await apiClient.post<{
    message: string;
    model_name: string;
    stored_name: string;
  }>("/models/trained-files/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const uploadModelWeights = async (modelId: number, file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<{
    message: string;
    model_id: number;
    model_name: string;
    status: string;
    extracted_files: string[];
    warnings: string[];
  }>(`/models/${modelId}/upload-weights`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const downloadTrainedModelFile = async (modelName: string) => {
  return apiClient.get("/models/trained-files/download", {
    params: { model_name: modelName },
    responseType: "blob",
  });
};

export const deleteModel = async (modelId: number) => {
  await apiClient.delete(`/models/${modelId}`);
};
