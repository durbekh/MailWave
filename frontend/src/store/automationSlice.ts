import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../utils/api';
import type { AutomationWorkflow, PaginatedResponse } from '../types';

interface AutomationState {
  workflows: AutomationWorkflow[];
  currentWorkflow: AutomationWorkflow | null;
  totalCount: number;
  loading: boolean;
  error: string | null;
}

const initialState: AutomationState = {
  workflows: [],
  currentWorkflow: null,
  totalCount: 0,
  loading: false,
  error: null,
};

export const fetchWorkflows = createAsyncThunk(
  'automation/fetchAll',
  async (params: { status?: string; search?: string } = {}) => {
    const response = await api.get<PaginatedResponse<AutomationWorkflow>>('/automation/', { params });
    return response.data;
  },
);

export const fetchWorkflow = createAsyncThunk(
  'automation/fetchOne',
  async (id: string) => {
    const response = await api.get<AutomationWorkflow>(`/automation/${id}/`);
    return response.data;
  },
);

export const createWorkflow = createAsyncThunk(
  'automation/create',
  async (data: Partial<AutomationWorkflow>) => {
    const response = await api.post<AutomationWorkflow>('/automation/', data);
    return response.data;
  },
);

export const updateWorkflow = createAsyncThunk(
  'automation/update',
  async ({ id, data }: { id: string; data: Partial<AutomationWorkflow> }) => {
    const response = await api.patch<AutomationWorkflow>(`/automation/${id}/`, data);
    return response.data;
  },
);

export const deleteWorkflow = createAsyncThunk(
  'automation/delete',
  async (id: string) => {
    await api.delete(`/automation/${id}/`);
    return id;
  },
);

export const activateWorkflow = createAsyncThunk(
  'automation/activate',
  async (id: string) => {
    await api.post(`/automation/${id}/activate/`);
    return id;
  },
);

export const pauseWorkflow = createAsyncThunk(
  'automation/pause',
  async (id: string) => {
    await api.post(`/automation/${id}/pause/`);
    return id;
  },
);

const automationSlice = createSlice({
  name: 'automation',
  initialState,
  reducers: {
    clearCurrentWorkflow(state) {
      state.currentWorkflow = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchWorkflows.pending, (state) => { state.loading = true; })
      .addCase(fetchWorkflows.fulfilled, (state, action) => {
        state.loading = false;
        state.workflows = action.payload.results;
        state.totalCount = action.payload.count;
      })
      .addCase(fetchWorkflows.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch workflows';
      })
      .addCase(fetchWorkflow.fulfilled, (state, action) => {
        state.currentWorkflow = action.payload;
      })
      .addCase(createWorkflow.fulfilled, (state, action) => {
        state.workflows.unshift(action.payload);
        state.currentWorkflow = action.payload;
      })
      .addCase(updateWorkflow.fulfilled, (state, action) => {
        state.currentWorkflow = action.payload;
        const idx = state.workflows.findIndex((w) => w.id === action.payload.id);
        if (idx !== -1) state.workflows[idx] = action.payload;
      })
      .addCase(deleteWorkflow.fulfilled, (state, action) => {
        state.workflows = state.workflows.filter((w) => w.id !== action.payload);
      })
      .addCase(activateWorkflow.fulfilled, (state, action) => {
        const idx = state.workflows.findIndex((w) => w.id === action.payload);
        if (idx !== -1) state.workflows[idx].status = 'active';
        if (state.currentWorkflow?.id === action.payload) state.currentWorkflow.status = 'active';
      })
      .addCase(pauseWorkflow.fulfilled, (state, action) => {
        const idx = state.workflows.findIndex((w) => w.id === action.payload);
        if (idx !== -1) state.workflows[idx].status = 'paused';
        if (state.currentWorkflow?.id === action.payload) state.currentWorkflow.status = 'paused';
      });
  },
});

export const { clearCurrentWorkflow } = automationSlice.actions;
export default automationSlice.reducer;
