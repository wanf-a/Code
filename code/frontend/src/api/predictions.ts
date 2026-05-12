import apiClient from "./client";

export type PredictionRequest = {
  model_id: number;
  dataset_id: number;
  test_start_date: string;
  test_end_date: string;
};

export type MetricsData = {
  mae: number;
  rmse: number;
  accuracy: number;
};

export type PredictionRecord = {
  record_time: string;
  actual_value: number;
  base_model_value: number;
  user_model_value: number;
};

export type PredictionResult = {
  records: PredictionRecord[];
  base_model_metrics: MetricsData;
  user_model_metrics: MetricsData;
};

export const calculatePrediction = async (request: PredictionRequest) => {
  const { data } = await apiClient.post<PredictionResult>("/predictions/calculate", request);
  return data;
};
