import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../utils/api';
import type { Contact, ContactList, Tag, Segment, PaginatedResponse } from '../types';

interface ContactState {
  contacts: Contact[];
  lists: ContactList[];
  tags: Tag[];
  segments: Segment[];
  totalCount: number;
  currentPage: number;
  loading: boolean;
  error: string | null;
}

const initialState: ContactState = {
  contacts: [],
  lists: [],
  tags: [],
  segments: [],
  totalCount: 0,
  currentPage: 1,
  loading: false,
  error: null,
};

export const fetchContacts = createAsyncThunk(
  'contacts/fetchAll',
  async (params: { page?: number; status?: string; search?: string; list_id?: string } = {}) => {
    const response = await api.get<PaginatedResponse<Contact>>('/contacts/', { params });
    return response.data;
  },
);

export const createContact = createAsyncThunk(
  'contacts/create',
  async (data: Partial<Contact>) => {
    const response = await api.post<Contact>('/contacts/', data);
    return response.data;
  },
);

export const updateContact = createAsyncThunk(
  'contacts/update',
  async ({ id, data }: { id: string; data: Partial<Contact> }) => {
    const response = await api.patch<Contact>(`/contacts/${id}/`, data);
    return response.data;
  },
);

export const deleteContact = createAsyncThunk(
  'contacts/delete',
  async (id: string) => {
    await api.delete(`/contacts/${id}/`);
    return id;
  },
);

export const bulkImportContacts = createAsyncThunk(
  'contacts/bulkImport',
  async (data: { contacts: Record<string, string>[]; list_id?: string; update_existing?: boolean }) => {
    const response = await api.post('/contacts/bulk-import/', data);
    return response.data;
  },
);

export const fetchLists = createAsyncThunk(
  'contacts/fetchLists',
  async () => {
    const response = await api.get<PaginatedResponse<ContactList>>('/contacts/lists/');
    return response.data.results;
  },
);

export const createList = createAsyncThunk(
  'contacts/createList',
  async (data: { name: string; description?: string }) => {
    const response = await api.post<ContactList>('/contacts/lists/', data);
    return response.data;
  },
);

export const fetchTags = createAsyncThunk(
  'contacts/fetchTags',
  async () => {
    const response = await api.get<PaginatedResponse<Tag>>('/contacts/tags/');
    return response.data.results;
  },
);

export const fetchSegments = createAsyncThunk(
  'contacts/fetchSegments',
  async () => {
    const response = await api.get<PaginatedResponse<Segment>>('/contacts/segments/');
    return response.data.results;
  },
);

const contactSlice = createSlice({
  name: 'contacts',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchContacts.pending, (state) => { state.loading = true; })
      .addCase(fetchContacts.fulfilled, (state, action) => {
        state.loading = false;
        state.contacts = action.payload.results;
        state.totalCount = action.payload.count;
        state.currentPage = action.payload.current_page;
      })
      .addCase(fetchContacts.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch contacts';
      })
      .addCase(createContact.fulfilled, (state, action) => {
        state.contacts.unshift(action.payload);
      })
      .addCase(updateContact.fulfilled, (state, action) => {
        const idx = state.contacts.findIndex((c) => c.id === action.payload.id);
        if (idx !== -1) state.contacts[idx] = action.payload;
      })
      .addCase(deleteContact.fulfilled, (state, action) => {
        state.contacts = state.contacts.filter((c) => c.id !== action.payload);
      })
      .addCase(fetchLists.fulfilled, (state, action) => {
        state.lists = action.payload;
      })
      .addCase(createList.fulfilled, (state, action) => {
        state.lists.unshift(action.payload);
      })
      .addCase(fetchTags.fulfilled, (state, action) => {
        state.tags = action.payload;
      })
      .addCase(fetchSegments.fulfilled, (state, action) => {
        state.segments = action.payload;
      });
  },
});

export default contactSlice.reducer;
