import apiClient from "./client";
import type { Paginated } from "./types";

export type Dataset = {
  id: number;
  name: string;
  description?: string | null;
  verify_status?: string;
  created_by: number;
  created_at: string;
  updated_at: string;
};

export type DatasetRecord = {
  id: number;
  dataset_id: number;
  record_time: string;
  price_kwh: number;
  generation_kwh: number;
  load_kw: number;
  weather_type: string;
  temperature?: number | null;
  wind_speed?: number | null;
  cloud_cover?: number | null;
  is_holiday: boolean;
  created_at: string;
};

export type RecordsQuery = {
  page?: number;
  size?: number;
  start_time?: string;
  end_time?: string;
  weather_type?: string;
  is_holiday?: boolean;
};

export type DatasetsQuery = {
  page?: number;
  size?: number;
  keyword?: string;
};

export const fetchDatasets = async (query: DatasetsQuery = {}) => {
  const { data } = await apiClient.get<Paginated<Dataset>>("/datasets", { params: query });
  return data;
};

export const fetchDataset = async (datasetId: number) => {
  const { data } = await apiClient.get<Dataset>(`/datasets/${datasetId}`);
  return data;
};

export const fetchDatasetRecords = async (datasetId: number, query: RecordsQuery = {}) => {
  const { data } = await apiClient.get<Paginated<DatasetRecord>>(`/datasets/${datasetId}/records`, {
    params: query,
  });
  return data;
};

export const uploadDataset = async (formData: FormData) => {
  const { data } = await apiClient.post<Dataset>("/datasets/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 600000,
  });
  return data;
};

export const downloadDataset = async (datasetId: number) => {
  const response = await apiClient.get(`/datasets/${datasetId}/download`, {
    responseType: "blob",
  });
  return response;
};

export const deleteDataset = async (datasetId: number) => {
  await apiClient.delete(`/datasets/${datasetId}`);
};

export const verifyDataset = async (datasetId: number) => {
  const { data } = await apiClient.post<Dataset>(`/datasets/${datasetId}/verify`);
  return data;
};

export const verifyDatasetAsync = async (datasetId: number) => {
  const { data } = await apiClient.post<Dataset>(`/datasets/${datasetId}/verify-async`);
  return data;
};

export const compareDatasets = async (datasetId: number, targetDatasetId: number) => {
  const formData = new FormData();
  formData.append("target_dataset_id", String(targetDatasetId));
  const { data } = await apiClient.post<Dataset>(`/datasets/${datasetId}/compare`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
};

export const compareDatasetWithUpload = async (datasetId: number, file: File) => {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await apiClient.post<Dataset>(`/datasets/${datasetId}/compare-upload`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 600000,
  });
  return data;
};

export type BaseRecord = {
  id: number;
  record_time: string;
  price_kwh: number;
  load_kw: number;
  temperature: number;
  wind_speed: number;
  cloud_cover: number;
};

export const fetchBaseRecords = async (query: RecordsQuery = {}) => {
  const { data } = await apiClient.get<Paginated<BaseRecord>>("/chart/base-records", { params: query });
  return data;
};

