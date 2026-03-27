import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../utils/api';
import type { Campaign, PaginatedResponse } from '../types';

interface CampaignState {
  campaigns: Campaign[];
  currentCampaign: Campaign | null;
  totalCount: number;
  currentPage: number;
  loading: boolean;
  error: string | null;
}

const initialState: CampaignState = {
  campaigns: [],
  currentCampaign: null,
  totalCount: 0,
  currentPage: 1,
  loading: false,
  error: null,
};

export const fetchCampaigns = createAsyncThunk(
  'campaigns/fetchAll',
  async (params: { page?: number; status?: string; search?: string } = {}) => {
    const response = await api.get<PaginatedResponse<Campaign>>('/campaigns/', { params });
    return response.data;
  },
);

export const fetchCampaign = createAsyncThunk(
  'campaigns/fetchOne',
  async (id: string) => {
    const response = await api.get<Campaign>(`/campaigns/${id}/`);
    return response.data;
  },
);

export const createCampaign = createAsyncThunk(
  'campaigns/create',
  async (data: Partial<Campaign>) => {
    const response = await api.post<Campaign>('/campaigns/', data);
    return response.data;
  },
);

export const updateCampaign = createAsyncThunk(
  'campaigns/update',
  async ({ id, data }: { id: string; data: Partial<Campaign> }) => {
    const response = await api.patch<Campaign>(`/campaigns/${id}/`, data);
    return response.data;
  },
);

export const deleteCampaign = createAsyncThunk(
  'campaigns/delete',
  async (id: string) => {
    await api.delete(`/campaigns/${id}/`);
    return id;
  },
);

export const sendCampaign = createAsyncThunk(
  'campaigns/send',
  async ({ id, data }: { id: string; data: { send_immediately?: boolean; scheduled_at?: string; test_email?: string } }) => {
    const response = await api.post(`/campaigns/${id}/send/`, data);
    return response.data;
  },
);

export const duplicateCampaign = createAsyncThunk(
  'campaigns/duplicate',
  async (id: string) => {
    const response = await api.post<Campaign>(`/campaigns/${id}/duplicate/`);
    return response.data;
  },
);

const campaignSlice = createSlice({
  name: 'campaigns',
  initialState,
  reducers: {
    clearCurrentCampaign(state) {
      state.currentCampaign = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchCampaigns.pending, (state) => { state.loading = true; })
      .addCase(fetchCampaigns.fulfilled, (state, action) => {
        state.loading = false;
        state.campaigns = action.payload.results;
        state.totalCount = action.payload.count;
        state.currentPage = action.payload.current_page;
      })
      .addCase(fetchCampaigns.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch campaigns';
      })
      .addCase(fetchCampaign.fulfilled, (state, action) => {
        state.currentCampaign = action.payload;
      })
      .addCase(createCampaign.fulfilled, (state, action) => {
        state.campaigns.unshift(action.payload);
        state.currentCampaign = action.payload;
      })
      .addCase(updateCampaign.fulfilled, (state, action) => {
        state.currentCampaign = action.payload;
        const idx = state.campaigns.findIndex((c) => c.id === action.payload.id);
        if (idx !== -1) state.campaigns[idx] = action.payload;
      })
      .addCase(deleteCampaign.fulfilled, (state, action) => {
        state.campaigns = state.campaigns.filter((c) => c.id !== action.payload);
      })
      .addCase(duplicateCampaign.fulfilled, (state, action) => {
        state.campaigns.unshift(action.payload);
      });
  },
});

export const { clearCurrentCampaign } = campaignSlice.actions;
export default campaignSlice.reducer;
