import apiClient from "./client";
import type { Paginated } from "./types";

export type Plan = {
  id: number;
  name: string;
  plan_type: string;
  dataset_id?: number | null;
  model_id?: number | null;
  status: string;
  description?: string | null;
  created_by: number;
  created_at: string;
  updated_at: string;
};

export type PlanResult = {
  id: number;
  plan_id: number;
  model_name: string;
  weather: string;
  mae: number;
  nmae: number;
  rmse: number;
  nrmse: number;
  score: number;
};

export type PlansQuery = {
  page?: number;
  size?: number;
  keyword?: string;
};

export const fetchPlans = async (query: PlansQuery = {}) => {
  const { data } = await apiClient.get<Paginated<Plan>>("/plans", { params: query });
  return data;
};

export const fetchPlan = async (planId: number) => {
  const { data } = await apiClient.get<Plan>(`/plans/${planId}`);
  return data;
};

export const updatePlan = async (planId: number, payload: Partial<Plan>) => {
  const { data } = await apiClient.put<Plan>(`/plans/${planId}`, payload);
  return data;
};

export const deletePlan = async (planId: number) => {
  const { data } = await apiClient.delete<{ message: string }>(`/plans/${planId}`);
  return data;
};

export const fetchPlanResults = async (planId: number) => {
  const { data } = await apiClient.get<PlanResult[]>(`/plans/${planId}/results`);
  return data;
};

export type PredictionRun = {
  id: number;
  plan_id: number;
  model_id?: number | null;
  status: string;
  start_time?: string | null;
  end_time?: string | null;
  record_count: number;
  mae?: number | null;
  rmse?: number | null;
  r2?: number | null;
  imape?: number | null;
  score?: number | null;
  message?: string | null;
  created_at: string;
  finished_at?: string | null;
};

export type PredictionRunRecord = {
  id: number;
  run_id: number;
  record_time: string;
  actual_price: number;
  predicted_price: number;
  load_kw: number;
};

export const createPredictionRun = async (planId: number, payload: {
  start_time?: string;
  end_time?: string;
  model_id?: number;
}) => {
  const { data } = await apiClient.post<PredictionRun>(`/plans/${planId}/runs`, payload);
  return data;
};

export const fetchLatestPredictionRun = async (planId: number) => {
  const { data } = await apiClient.get<PredictionRun>(`/plans/${planId}/runs/latest`);
  return data;
};

export const fetchPredictionRunRecords = async (
  planId: number,
  runId: number,
  query: { page?: number; size?: number; start_time?: string; end_time?: string } = {},
) => {
  const { data } = await apiClient.get<Paginated<PredictionRunRecord>>(
    `/plans/${planId}/runs/${runId}/records`,
    { params: query },
  );
  return data;
};

