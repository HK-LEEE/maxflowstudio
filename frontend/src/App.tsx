import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntdApp } from 'antd';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LayoutProvider } from './contexts/LayoutContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { MainLayout } from './layouts/MainLayout';
import { SilentLoginLoader } from './components/SilentLoginLoader';
import { LoginPage } from './pages/LoginPage';
import { OAuthCallback } from './pages/OAuthCallback';
import { DashboardPage } from './pages/DashboardPage';
import FlowsPage from './pages/FlowsPage';
import { FlowEditorPage } from './pages/FlowEditorPage';
import { ExecutionsPage } from './pages/ExecutionsPage';
import { ApiKeysPage } from './pages/ApiKeysPage';
import ApiDeploymentsPage from './pages/ApiDeploymentsPage';
import { WorkspacesPage } from './pages/WorkspacesPage';
import { SystemStatusPage } from './pages/SystemStatusPage';
import { WorkspacePermissionsPage } from './pages/admin/WorkspacePermissionsPage';
import { TemplateManagementPage } from './pages/admin/TemplateManagementPage';
import { RAGPage } from './pages/RAGPage';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Ant Design theme configuration - 2025 Modern Design System
const theme = {
  token: {
    // Primary colors - Black/White with subtle variations
    colorPrimary: '#000000',
    colorInfo: '#000000',
    colorSuccess: '#00c851',
    colorWarning: '#ff9500',
    colorError: '#ff4757',
    
    // Border radius - Modern rounded corners
    borderRadius: 8,
    borderRadiusLG: 12,
    borderRadiusXS: 4,
    
    // Borders - Softer and more subtle
    colorBorder: '#f0f0f0',
    colorBorderSecondary: '#f5f5f5',
    
    // Background colors
    colorFill: '#fafafa',
    colorBgContainer: '#ffffff',
    colorBgElevated: '#ffffff',
    colorBgLayout: '#ffffff',
    colorBgMask: 'rgba(0, 0, 0, 0.45)',
    
    // Typography
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "SF Pro Display", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontSize: 14,
    fontSizeLG: 16,
    fontSizeXL: 20,
    lineHeight: 1.5714,
    
    // Spacing
    padding: 16,
    paddingLG: 24,
    paddingXL: 32,
    
    // Shadows - Modern depth system
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
    boxShadowSecondary: '0 4px 16px rgba(0, 0, 0, 0.08)',
    boxShadowTertiary: '0 6px 24px rgba(0, 0, 0, 0.12)',
  },
  components: {
    Button: {
      // Modern button styling
      primaryShadow: 'none',
      defaultShadow: 'none',
      borderRadius: 8,
      fontWeight: 500,
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.08)',
    },
    Card: {
      // Enhanced card design
      borderRadiusLG: 16,
      boxShadowTertiary: '0 8px 32px rgba(0, 0, 0, 0.08)',
      paddingLG: 32,
    },
    Layout: {
      headerBg: '#ffffff',
      siderBg: 'linear-gradient(180deg, #ffffff 0%, #fafafa 100%)',
      bodyBg: '#ffffff',
      headerHeight: 64,
      headerPadding: '0 24px',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: 'rgba(0, 0, 0, 0.06)',
      itemHoverBg: 'rgba(0, 0, 0, 0.04)',
      itemActiveBg: 'rgba(0, 0, 0, 0.08)',
      borderRadius: 8,
      itemMarginInline: 4,
    },
    Tree: {
      // Tree component styling for sidebar
      nodeSelectedBg: 'rgba(0, 0, 0, 0.06)',
      nodeHoverBg: 'rgba(0, 0, 0, 0.04)',
      borderRadius: 8,
    },
    Input: {
      // Modern input styling
      borderRadius: 8,
      paddingInline: 12,
      fontSize: 14,
    },
    Table: {
      // Enhanced table design
      borderRadiusLG: 12,
      headerBg: '#fafafa',
      headerSplitColor: '#f0f0f0',
      rowHoverBg: '#fafafa',
    },
    Typography: {
      // Typography enhancements
      titleMarginTop: 0,
      titleMarginBottom: 16,
    },
    Drawer: {
      borderRadiusLG: 16,
    },
    Modal: {
      borderRadiusLG: 16,
      paddingLG: 32,
    },
    Badge: {
      borderRadiusSM: 12,
      fontSizeSM: 11,
      fontWeight: 500,
    },
    Tag: {
      borderRadiusSM: 6,
      fontSizeSM: 12,
      fontWeight: 500,
    }
  },
};

// App content component to access auth context
const AppContent: React.FC = () => {
  const { isAttemptingSilentLogin } = useAuth();

  return (
    <>
      <SilentLoginLoader isVisible={isAttemptingSilentLogin} />
      <LayoutProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/oauth/callback" element={<OAuthCallback />} />
          
          {/* Protected routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="workspaces" element={<WorkspacesPage />} />
            <Route path="flows" element={<FlowsPage />} />
            <Route path="flows/:id" element={<FlowEditorPage />} />
            <Route path="executions" element={<ExecutionsPage />} />
            <Route path="api-keys" element={<ApiKeysPage />} />
            <Route path="api-deployments" element={<ApiDeploymentsPage />} />
            <Route path="system" element={<SystemStatusPage />} />
            <Route path="workspaces/:workspaceId/rag" element={<RAGPage />} />
            <Route path="admin/workspace-permissions" element={<WorkspacePermissionsPage />} />
            <Route path="admin/template-management" element={<TemplateManagementPage />} />
          </Route>
        </Routes>
      </LayoutProvider>
    </>
  );
};

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider theme={theme}>
        <AntdApp>
          <Router>
            <AuthProvider>
              <AppContent />
            </AuthProvider>
          </Router>
        </AntdApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;