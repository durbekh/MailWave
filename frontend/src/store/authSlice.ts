import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import api from '../utils/api';
import type { User, AuthTokens } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  loading: boolean;
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  token: localStorage.getItem('mailwave_access_token'),
  refreshToken: localStorage.getItem('mailwave_refresh_token'),
  loading: false,
  error: null,
};

export const login = createAsyncThunk(
  'auth/login',
  async (credentials: { email: string; password: string }, { rejectWithValue }) => {
    try {
      const response = await api.post('/auth/login/', credentials);
      return response.data as { user: User; tokens: AuthTokens };
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      return rejectWithValue(error.response?.data?.message || 'Login failed');
    }
  },
);

export const register = createAsyncThunk(
  'auth/register',
  async (
    data: {
      email: string;
      password: string;
      password_confirm: string;
      first_name: string;
      last_name: string;
      organization_name: string;
    },
    { rejectWithValue },
  ) => {
    try {
      const response = await api.post('/auth/register/', data);
      return response.data as { user: User; tokens: AuthTokens };
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      return rejectWithValue(error.response?.data?.message || 'Registration failed');
    }
  },
);

export const fetchCurrentUser = createAsyncThunk(
  'auth/fetchCurrentUser',
  async (_, { rejectWithValue }) => {
    try {
      const response = await api.get('/auth/me/');
      return response.data as User;
    } catch (err: unknown) {
      const error = err as { response?: { data?: { message?: string } } };
      return rejectWithValue(error.response?.data?.message || 'Failed to fetch user');
    }
  },
);

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    logout(state) {
      state.user = null;
      state.token = null;
      state.refreshToken = null;
      state.error = null;
      localStorage.removeItem('mailwave_access_token');
      localStorage.removeItem('mailwave_refresh_token');
    },
    setTokens(state, action: PayloadAction<{ access: string; refresh: string }>) {
      state.token = action.payload.access;
      state.refreshToken = action.payload.refresh;
      localStorage.setItem('mailwave_access_token', action.payload.access);
      localStorage.setItem('mailwave_refresh_token', action.payload.refresh);
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Login
      .addCase(login.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
        state.token = action.payload.tokens.access;
        state.refreshToken = action.payload.tokens.refresh;
        localStorage.setItem('mailwave_access_token', action.payload.tokens.access);
        localStorage.setItem('mailwave_refresh_token', action.payload.tokens.refresh);
      })
      .addCase(login.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      // Register
      .addCase(register.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(register.fulfilled, (state, action) => {
        state.loading = false;
        state.user = action.payload.user;
        state.token = action.payload.tokens.access;
        state.refreshToken = action.payload.tokens.refresh;
        localStorage.setItem('mailwave_access_token', action.payload.tokens.access);
        localStorage.setItem('mailwave_refresh_token', action.payload.tokens.refresh);
      })
      .addCase(register.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      // Fetch Current User
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.user = action.payload;
      })
      .addCase(fetchCurrentUser.rejected, (state) => {
        state.user = null;
        state.token = null;
        state.refreshToken = null;
        localStorage.removeItem('mailwave_access_token');
        localStorage.removeItem('mailwave_refresh_token');
      });
  },
});

export const { logout, setTokens, clearError } = authSlice.actions;
export default authSlice.reducer;
