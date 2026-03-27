import { Routes, Route, Navigate } from 'react-router-dom';
import { useAppSelector } from './hooks/useRedux';
import DashboardLayout from './components/layout/DashboardLayout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import CampaignsPage from './pages/CampaignsPage';
import CampaignBuilderPage from './pages/CampaignBuilderPage';
import TemplatesPage from './pages/TemplatesPage';
import TemplateEditorPage from './pages/TemplateEditorPage';
import SubscribersPage from './pages/SubscribersPage';
import AnalyticsPage from './pages/AnalyticsPage';
import AutomationPage from './pages/AutomationPage';
import AutomationBuilderPage from './pages/AutomationBuilderPage';
import SettingsPage from './pages/SettingsPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAppSelector((state) => state.auth);
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function GuestRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAppSelector((state) => state.auth);
  if (token) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      {/* Auth routes */}
      <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />
      <Route path="/register" element={<GuestRoute><RegisterPage /></GuestRoute>} />

      {/* Protected routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="campaigns" element={<CampaignsPage />} />
        <Route path="campaigns/new" element={<CampaignBuilderPage />} />
        <Route path="campaigns/:id/edit" element={<CampaignBuilderPage />} />
        <Route path="templates" element={<TemplatesPage />} />
        <Route path="templates/:id/edit" element={<TemplateEditorPage />} />
        <Route path="subscribers" element={<SubscribersPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="automation" element={<AutomationPage />} />
        <Route path="automation/new" element={<AutomationBuilderPage />} />
        <Route path="automation/:id/edit" element={<AutomationBuilderPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
