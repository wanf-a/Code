import apiClient from "./client";
import type { Paginated } from "./types";

export type Ranking = {
  id: number;
  score: number;
  time_range: string;
  mae_ratio: number;
  rmse_ratio: number;
  rank_type: string;
  weather: string;
  is_holiday: boolean;
  model_name: string;
  author: string;
  plan_id?: number | null;
  created_at: string;
};

export type RankingQuery = {
  page?: number;
  size?: number;
  rank_type?: string;
  weather?: string;
  is_holiday?: boolean;
  model_name?: string;
};

export const fetchRankings = async (query: RankingQuery = {}) => {
  const { data } = await apiClient.get<Paginated<Ranking>>("/rankings", { params: query });
  return data;
};

export type RankingSummary = {
  plan_id: number;
  dataset: string;
  type: string;
  model: string;
  period: string;
  load: string;
  wind: string;
  weather_type: string;
  mae: number;
  rmse: number;
  r2: number;
  imape: number;
  score: number;
  sample_count: number;
};

export type RankingSummaryQuery = {
  start_time?: string;
  end_time?: string;
  model_name?: string;
  rank_type?: string;
  source?: string;
};

export const fetchRankingSummary = async (query: RankingSummaryQuery = {}) => {
  const { data } = await apiClient.get<RankingSummary[]>("/rankings/summary", { params: query });
  return data;
};

