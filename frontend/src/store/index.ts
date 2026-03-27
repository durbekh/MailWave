import { configureStore } from '@reduxjs/toolkit';
import authReducer from './authSlice';
import campaignReducer from './campaignSlice';
import contactReducer from './contactSlice';
import templateReducer from './templateSlice';
import automationReducer from './automationSlice';
import analyticsReducer from './analyticsSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    campaigns: campaignReducer,
    contacts: contactReducer,
    templates: templateReducer,
    automation: automationReducer,
    analytics: analyticsReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['auth/setTokens'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
