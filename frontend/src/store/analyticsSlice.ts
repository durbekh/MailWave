import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../utils/api';
import type { DashboardSummary, DailyStats } from '../types';

interface AnalyticsState {
  dashboard: DashboardSummary | null;
  dailyStats: DailyStats[];
  loading: boolean;
  error: string | null;
}

const initialState: AnalyticsState = {
  dashboard: null,
  dailyStats: [],
  loading: false,
  error: null,
};

export const fetchDashboard = createAsyncThunk(
  'analytics/fetchDashboard',
  async () => {
    const response = await api.get<DashboardSummary>('/analytics/dashboard/');
    return response.data;
  },
);

export const fetchDailyStats = createAsyncThunk(
  'analytics/fetchDaily',
  async (params: { start_date: string; end_date: string }) => {
    const response = await api.get<DailyStats[]>('/analytics/daily/', { params });
    return response.data;
  },
);

export const fetchCampaignAnalytics = createAsyncThunk(
  'analytics/fetchCampaign',
  async (campaignId: string) => {
    const response = await api.get(`/analytics/campaigns/${campaignId}/`);
    return response.data;
  },
);

const analyticsSlice = createSlice({
  name: 'analytics',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboard.pending, (state) => { state.loading = true; })
      .addCase(fetchDashboard.fulfilled, (state, action) => {
        state.loading = false;
        state.dashboard = action.payload;
      })
      .addCase(fetchDashboard.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch dashboard';
      })
      .addCase(fetchDailyStats.fulfilled, (state, action) => {
        state.dailyStats = action.payload;
      });
  },
});

export default analyticsSlice.reducer;
