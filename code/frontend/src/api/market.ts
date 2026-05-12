import apiClient from "./client";

export interface GetPricePredictionsParams {
  day: number;
  model: string;
}

export interface GetPowerBalanceParams {
  date_str: string;
  case_id?: string;
}

export interface GetEnergyBalanceParams {
  day_index?: number;
  use_default_case?: boolean;
}

export interface GetClearingPriceParams {
  unit_id: string;
  day_index?: number;
  use_default_case?: boolean;
}

export interface GetUnitBidResultsParams {
  unit_id: string;
  day_index?: number;
}

export interface UnitBidResultsData {
  output_values: number[];   // 中标出力数据 (MW), 96 个时段
  price_values: number[];    // 中标均价数据 (元/MWh), 96 个时段
  revenue_values: number[];  // 中标收益数据 (元), 96 个时段
  case_id: string;           // 案例 ID (如 Output14)
  date_str: string;          // 日期字符串 (如 20260319)
  unit_id: string;           // 机组 ID (如 Thermal_1)
}

export interface SubmitInputDayAheadQuotesPayload {
  unit_id: string;
  data_date: string;
  use_default_case?: boolean;
  segments: Array<{
    start: number;
    end: number;
    price: number;
    quote_time?: number;
    quote_section?: string;
    market_name?: string;
  }>;
}

export const marketApi = {
  getCompanies: () => apiClient.get("/market/companies"),
  getWindUnits: () => apiClient.get("/market/wind-units"),
  getSolarUnits: () => apiClient.get("/market/solar-units"),
  getClearingHistory: (params?: { metric?: string; start?: number; limit?: number }) =>
    apiClient.get("/market/clearing-history", { params }),
  getOutResults: (params: { sheet: string; row_index?: number }) =>
    apiClient.get("/market/out-results", { params }),
  getPricePredictions: async (params: GetPricePredictionsParams) => {
    const response = await apiClient.get("/market/price-predictions", { params });
    return response.data;
  },
  getDayAheadQuotes: (params?: { unit_id?: string }) =>
    apiClient.get("/market/day-ahead-quotes", { params }),
  getInputDayAheadQuotes: (params?: { unit_id?: string; data_date?: string; use_default_case?: boolean }) =>
    apiClient.get("/market/input-day-ahead-quotes", { params }),
  submitInputDayAheadQuotes: (payload: SubmitInputDayAheadQuotesPayload) =>
    apiClient.post("/market/input-day-ahead-quotes", payload),
  getSettlementOverview: (dayIndex?: number, useDefaultCase: boolean = false) => apiClient.get("/market/settlement-overview", { 
    params: { day_index: dayIndex || 1, use_default_case: useDefaultCase } 
  }),
  getSettlementDetail: (dayIndex?: number, useDefaultCase: boolean = false) => apiClient.get("/market/settlement-detail", { 
    params: { day_index: dayIndex || 1, use_default_case: useDefaultCase } 
  }),
  getBalanceChart: () => apiClient.get("/market/balance-chart"),
  getPowerBalance: async (params: GetPowerBalanceParams) => {
    const response = await apiClient.get("/market/power-balance", { params });
    return response.data;
  },
  /**
   * 获取电力电量平衡结果（自主申报页面用）
   * @param dayIndex 第几天，从 1 开始（第一天=20260319）
   * @param useDefaultCase 是否使用默认案例 Output0（基线申报），false 则使用用户关联案例（自主申报）
   */
  getEnergyBalance: (dayIndex?: number, useDefaultCase: boolean = false) => 
    apiClient.get("/market/energy-balance", { 
      params: { 
        day_index: dayIndex || 1, 
        use_default_case: useDefaultCase 
      } 
    }),
  /**
   * 获取电能量市场出清电价
   * @param unitId 机组 ID，如 Thermal_1
   * @param dayIndex 第几天，从 1 开始（第一天=20260319）
   * @param useDefaultCase 是否使用默认案例 Output0（基线申报），false 则使用用户关联案例（自主申报）
   */
  getClearingPrice: (unitId: string, dayIndex?: number, useDefaultCase: boolean = false) => 
    apiClient.get("/market/clearing-price", { 
      params: { 
        unit_id: unitId,
        day_index: dayIndex || 1, 
        use_default_case: useDefaultCase 
      } 
    }),
  /**
   * 获取机组中标结果数据 (中标出力、均价、收益)
   * @param unitId 机组 ID，如 Thermal_1
   * @param dayIndex 第几天，从 1 开始 (第一天=20260319)
   * @returns Promise<UnitBidResultsData> 包含出力、均价、收益的 96 时段数据
   */
  getUnitBidResults: async (unitId: string, dayIndex?: number, useDefaultCase?: boolean): Promise<UnitBidResultsData> => {
    const response = await apiClient.get("/market/unit-bid-results", { 
      params: { 
        unit_id: unitId,
        day_index: dayIndex || 1,
        use_default_case: useDefaultCase || false
      } 
    });
    return response.data;
  },

};
