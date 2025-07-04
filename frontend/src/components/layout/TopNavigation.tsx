/**
 * Top Navigation Component for MAX Flowstudio
 * Exact replica of MAX Platform header design (save1.png)
 */

import React, { useState } from 'react';
import { Input, Badge, Dropdown, Avatar } from 'antd';
import { 
  SearchOutlined, 
  BellOutlined, 
  UserOutlined, 
  SettingOutlined,
  LogoutOutlined,
  TeamOutlined,
  KeyOutlined
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';

interface TopNavigationProps {}

export const TopNavigation: React.FC<TopNavigationProps> = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchValue, setSearchValue] = useState('');

  // Get page title based on current route
  const getPageTitle = () => {
    const path = location.pathname;
    if (path.includes('/flows/')) return 'Flow Editor';
    if (path === '/dashboard') return 'Dashboard';
    if (path === '/workspaces') return 'Workspaces';
    if (path === '/flows') return 'Flows';
    if (path === '/executions') return 'Executions';
    if (path === '/api-deployments') return 'API Deployments';
    if (path === '/api-keys') return 'API Keys';
    if (path === '/system') return 'System Status';
    if (path.includes('/admin')) return 'Admin Panel';
    return 'Dashboard';
  };

  const handleLogoClick = () => {
    navigate('/dashboard');
  };

  const handleSearch = (value: string) => {
    console.log('Search:', value);
    // TODO: Implement global search functionality
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '프로필',
      onClick: () => navigate('/profile'),
    },
    {
      key: 'workspaces',
      icon: <TeamOutlined />,
      label: '워크스페이스 관리',
      onClick: () => navigate('/workspaces'),
    },
    {
      key: 'api-keys',
      icon: <KeyOutlined />,
      label: 'API 키',
      onClick: () => navigate('/api-keys'),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '설정',
      onClick: () => navigate('/settings'),
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '로그아웃',
      onClick: handleLogout,
      danger: true,
    },
  ];

  return (
    <header 
      className="bg-white border-b border-gray-200 sticky top-0 z-50"
      style={{ 
        backgroundColor: '#ffffff',
        borderBottomColor: '#e5e7eb',
        height: '64px'
      }}
    >
      <div className="max-w-full px-6">
        <div className="flex items-center justify-between h-16">
          {/* Left Side - Logo and Title (Exact replica of save1.png) */}
          <div 
            className="flex items-center gap-3 cursor-pointer"
            onClick={handleLogoClick}
          >
            {/* M Logo - Exact match to save1.png */}
            <div 
              className="w-10 h-10 bg-gray-800 rounded-lg flex items-center justify-center shadow-sm"
              style={{
                backgroundColor: '#374151',
                borderRadius: '8px',
                width: '40px',
                height: '40px'
              }}
            >
              <span 
                style={{
                  color: '#ffffff',
                  fontSize: '18px',
                  fontWeight: '700',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }}
              >
                M
              </span>
            </div>
            
            {/* Title and Subtitle - Exact match to save1.png */}
            <div className="flex flex-col">
              <h1 
                style={{
                  fontSize: '20px',
                  fontWeight: '600',
                  color: '#111827',
                  margin: 0,
                  lineHeight: '1.2',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }}
              >
                {getPageTitle()}
              </h1>
              <p 
                style={{
                  fontSize: '14px',
                  fontWeight: '400',
                  color: '#6b7280',
                  margin: 0,
                  lineHeight: '1.2',
                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }}
              >
                Manufacturing AI & DX
              </p>
            </div>
          </div>

          {/* Right Side - Search, Notifications, User (Exact replica of save1.png) */}
          <div className="flex items-center gap-4">
            {/* Search - Exact match to save1.png */}
            <div className="hidden md:block">
              <Input
                placeholder="검색..."
                prefix={<SearchOutlined style={{ color: '#9ca3af', fontSize: '16px' }} />}
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                onPressEnter={() => handleSearch(searchValue)}
                style={{
                  width: '280px',
                  height: '40px',
                  backgroundColor: '#f9fafb',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '14px'
                }}
                className="hover:border-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
              />
            </div>

            {/* Notifications - Exact match to save1.png with red dot */}
            <div className="relative">
              <div 
                className="w-10 h-10 bg-gray-50 rounded-lg flex items-center justify-center cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => console.log('Open notifications')}
              >
                <BellOutlined 
                  style={{ 
                    fontSize: '18px', 
                    color: '#6b7280'
                  }} 
                />
              </div>
              {/* Red notification dot */}
              <div 
                className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full"
                style={{
                  backgroundColor: '#ef4444',
                  width: '12px',
                  height: '12px'
                }}
              />
            </div>

            {/* User Menu - Exact match to save1.png */}
            <Dropdown
              menu={{ items: userMenuItems }}
              placement="bottomRight"
              trigger={['click']}
            >
              <div className="flex items-center gap-3 cursor-pointer hover:bg-gray-50 rounded-lg px-3 py-2 transition-colors">
                <Avatar 
                  size={40}
                  style={{ 
                    backgroundColor: '#374151',
                    color: '#ffffff',
                    fontSize: '16px',
                    fontWeight: '600'
                  }}
                  icon={<UserOutlined />}
                />
                <div className="hidden lg:block text-left">
                  <div 
                    style={{ 
                      fontSize: '14px', 
                      fontWeight: '600',
                      color: '#111827',
                      lineHeight: '1.2',
                      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                    }}
                  >
                    {user?.is_superuser ? 'admin' : user?.username || 'admin'}
                  </div>
                  <div 
                    style={{ 
                      fontSize: '12px', 
                      color: '#6b7280',
                      lineHeight: '1.2',
                      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                    }}
                  >
                    {user?.email || 'admin@test.com'}
                  </div>
                </div>
              </div>
            </Dropdown>
          </div>
        </div>
      </div>
    </header>
  );
};

export default TopNavigation;