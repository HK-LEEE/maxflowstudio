/**
 * Main Layout Component
 * Provides the main application layout with workspace-centric sidebar navigation
 */

import React from 'react';
import { Outlet } from 'react-router-dom';
import { Layout } from 'antd';
import { useLayout } from '../contexts/LayoutContext';
import { WorkspaceSidebar } from '../components/WorkspaceSidebar';
import { Header } from '../components/Layout/Header';

const { Sider, Content } = Layout;

export const MainLayout: React.FC = () => {
  const { sidebarCollapsed, setSidebarCollapsed, isFlowEditor } = useLayout();

  return (
    <Layout className="h-screen">
      {/* Header - Full width at the top */}
      <Header />
      
      {/* Main Layout - Sidebar + Content */}
      <Layout style={{ height: 'calc(100vh - 64px)' }}>
        <Sider
          collapsible
          collapsed={sidebarCollapsed}
          onCollapse={setSidebarCollapsed}
          theme="light"
          style={{ 
            backgroundColor: '#fafafa',
            borderRight: '1px solid #e8e8e8',
            transition: 'all 0.2s ease',
            background: 'linear-gradient(180deg, #ffffff 0%, #fafafa 100%)',
            height: '100%'
          }}
          width={280}
          collapsedWidth={80}
        >
          <WorkspaceSidebar collapsed={sidebarCollapsed} />
        </Sider>
        
        <Content 
          style={{
            margin: '0',
            padding: '0',
            backgroundColor: '#f9fafb',
            overflow: 'auto'
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};