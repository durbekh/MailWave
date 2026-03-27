import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../utils/api';
import type { EmailTemplate, PaginatedResponse } from '../types';

interface TemplateState {
  templates: EmailTemplate[];
  currentTemplate: EmailTemplate | null;
  totalCount: number;
  loading: boolean;
  error: string | null;
}

const initialState: TemplateState = {
  templates: [],
  currentTemplate: null,
  totalCount: 0,
  loading: false,
  error: null,
};

export const fetchTemplates = createAsyncThunk(
  'templates/fetchAll',
  async (params: { search?: string; template_type?: string; is_starred?: boolean } = {}) => {
    const response = await api.get<PaginatedResponse<EmailTemplate>>('/templates/', { params });
    return response.data;
  },
);

export const fetchTemplate = createAsyncThunk(
  'templates/fetchOne',
  async (id: string) => {
    const response = await api.get<EmailTemplate>(`/templates/${id}/`);
    return response.data;
  },
);

export const createTemplate = createAsyncThunk(
  'templates/create',
  async (data: Partial<EmailTemplate>) => {
    const response = await api.post<EmailTemplate>('/templates/', data);
    return response.data;
  },
);

export const updateTemplate = createAsyncThunk(
  'templates/update',
  async ({ id, data }: { id: string; data: Partial<EmailTemplate> }) => {
    const response = await api.patch<EmailTemplate>(`/templates/${id}/`, data);
    return response.data;
  },
);

export const deleteTemplate = createAsyncThunk(
  'templates/delete',
  async (id: string) => {
    await api.delete(`/templates/${id}/`);
    return id;
  },
);

export const duplicateTemplate = createAsyncThunk(
  'templates/duplicate',
  async (id: string) => {
    const response = await api.post<EmailTemplate>(`/templates/${id}/duplicate/`);
    return response.data;
  },
);

export const toggleTemplateStar = createAsyncThunk(
  'templates/toggleStar',
  async (id: string) => {
    const response = await api.post<{ is_starred: boolean }>(`/templates/${id}/toggle_star/`);
    return { id, is_starred: response.data.is_starred };
  },
);

const templateSlice = createSlice({
  name: 'templates',
  initialState,
  reducers: {
    clearCurrentTemplate(state) {
      state.currentTemplate = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchTemplates.pending, (state) => { state.loading = true; })
      .addCase(fetchTemplates.fulfilled, (state, action) => {
        state.loading = false;
        state.templates = action.payload.results;
        state.totalCount = action.payload.count;
      })
      .addCase(fetchTemplates.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch templates';
      })
      .addCase(fetchTemplate.fulfilled, (state, action) => {
        state.currentTemplate = action.payload;
      })
      .addCase(createTemplate.fulfilled, (state, action) => {
        state.templates.unshift(action.payload);
      })
      .addCase(updateTemplate.fulfilled, (state, action) => {
        state.currentTemplate = action.payload;
        const idx = state.templates.findIndex((t) => t.id === action.payload.id);
        if (idx !== -1) state.templates[idx] = action.payload;
      })
      .addCase(deleteTemplate.fulfilled, (state, action) => {
        state.templates = state.templates.filter((t) => t.id !== action.payload);
      })
      .addCase(duplicateTemplate.fulfilled, (state, action) => {
        state.templates.unshift(action.payload);
      })
      .addCase(toggleTemplateStar.fulfilled, (state, action) => {
        const idx = state.templates.findIndex((t) => t.id === action.payload.id);
        if (idx !== -1) state.templates[idx].is_starred = action.payload.is_starred;
      });
  },
});

export const { clearCurrentTemplate } = templateSlice.actions;
export default templateSlice.reducer;
