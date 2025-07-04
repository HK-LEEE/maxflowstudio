/**
 * Header Component - Exact replica of MAX Platform header design
 * Full width header with logo, title, search, notification, and profile
 */

import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigate, useLocation } from 'react-router-dom';
import { Layout } from 'antd';

const { Header: AntHeader } = Layout;

interface HeaderProps {}

export const Header: React.FC<HeaderProps> = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchValue, setSearchValue] = useState('');
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const notificationRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // Dynamic page title based on current route
  const getCurrentPageTitle = () => {
    const path = location.pathname;
    if (path.includes('/flows/')) return 'Flow Editor';
    if (path === '/dashboard') return 'Dashboard';
    if (path === '/workspaces') return 'MAX Flowstudio';
    if (path === '/flows') return 'Flows';
    if (path === '/executions') return 'Executions';
    if (path === '/api-deployments') return 'API Deployments';
    if (path === '/api-keys') return 'API Keys';
    if (path === '/system') return 'System Status';
    if (path.includes('/admin')) return 'Admin Panel';
    return 'Dashboard';
  };

  const handleSearch = (value: string) => {
    console.log('Search:', value);
    // TODO: Implement global search functionality
  };

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
      setShowUserMenu(false);
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const handleMenuItemClick = (path: string) => {
    navigate(path);
    setShowUserMenu(false);
  };

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <AntHeader 
      style={{
        background: '#ffffff',
        borderBottom: '1px solid #f0f0f0',
        padding: '0 24px',
        height: '64px',
        lineHeight: '64px',
        boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'sticky',
        top: 0,
        zIndex: 1000
      }}
    >
      {/* Central Container */}
      <div style={{ 
        width: '100%', 
        maxWidth: '1152px', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between' 
      }}>
        {/* Left Side - Logo + Page Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {/* MF Logo */}
        <div className="relative">
          <div 
            style={{
              width: '36px',
              height: '36px',
              background: 'linear-gradient(to bottom right, #111827, #374151)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer'
            }}
            onClick={() => navigate('/dashboard')}
          >
            <span 
              style={{
                color: '#ffffff',
                fontSize: '13px',
                fontWeight: '700',
                fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
              }}
            >
              MF
            </span>
          </div>
        </div>

        {/* Brand Title - Fixed */}
        <div>
          <h1 
            style={{
              fontSize: '18px',
              fontWeight: '600',
              color: '#111827',
              margin: 0,
              lineHeight: '1.2',
              fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            }}
          >
            MAX Flowstudio
          </h1>
          <p 
            style={{
              fontSize: '12px',
              color: '#6b7280',
              margin: 0,
              lineHeight: '1',
              fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            }}
          >
            Manufacturing AI & DX
          </p>
        </div>
        </div>

        {/* Right Side - Search + Notifications + Profile */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, justifyContent: 'flex-end' }}>
          {/* Search bar - more prominent and centered */}
          <div style={{ position: 'relative', flex: 1, maxWidth: '400px', margin: '0 32px' }}>
            <input
              type="text"
              placeholder="검색..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch(searchValue)}
              style={{
                width: '100%',
                height: '40px',
                padding: '0 16px 0 40px',
                border: '1px solid #d1d5db',
                borderRadius: '10px',
                fontSize: '14px',
                fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                backgroundColor: '#ffffff',
                color: '#111827',
                outline: 'none',
                transition: 'all 0.2s ease'
              }}
            onFocus={(e) => {
              e.target.style.borderColor = '#3b82f6';
              e.target.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.1)';
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#e5e7eb';
              e.target.style.boxShadow = 'none';
            }}
          />
          <svg
            style={{
              position: 'absolute',
              left: '14px',
              top: '50%',
              transform: 'translateY(-50%)',
              width: '16px',
              height: '16px',
              color: '#9ca3af'
            }}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

          {/* Notification button */}
          <div style={{ position: 'relative' }} ref={notificationRef}>
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              style={{
                width: '40px',
                height: '40px',
                border: 'none',
                borderRadius: '50%',
                backgroundColor: 'transparent',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
                transition: 'background-color 0.2s ease'
              }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#e5e7eb';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#f3f4f6';
            }}
          >
            <svg
              style={{
                width: '20px',
                height: '20px',
                color: '#374151'
              }}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
            
            {/* Red notification dot */}
            <div
              style={{
                position: 'absolute',
                top: '6px',
                right: '6px',
                width: '8px',
                height: '8px',
                backgroundColor: '#ef4444',
                borderRadius: '50%'
              }}
            />
          </button>

          {/* Notification dropdown */}
          {showNotifications && (
            <div
              style={{
                position: 'absolute',
                right: '0',
                top: '48px',
                width: '320px',
                backgroundColor: '#ffffff',
                border: '1px solid #e5e7eb',
                borderRadius: '12px',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                zIndex: 1000
              }}
            >
              <div
                style={{
                  padding: '16px',
                  borderBottom: '1px solid #f3f4f6'
                }}
              >
                <h3
                  style={{
                    margin: 0,
                    fontSize: '16px',
                    fontWeight: '600',
                    color: '#111827'
                  }}
                >
                  알림
                </h3>
              </div>
              <div
                style={{
                  padding: '16px',
                  textAlign: 'center',
                  color: '#6b7280',
                  fontSize: '14px'
                }}
              >
                새로운 알림이 없습니다
              </div>
            </div>
          )}
        </div>

          {/* Profile section with user info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {/* User info display */}
            <div style={{ textAlign: 'right' }}>
              <div 
                style={{
                  fontSize: '14px',
                  fontWeight: '600',
                  color: '#111827',
                  lineHeight: '1.2',
                  fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }}
              >
                {user?.displayName || user?.username || 'User'}
              </div>
              <div 
                style={{
                  fontSize: '12px',
                  color: '#6b7280',
                  lineHeight: '1',
                  fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }}
              >
                {user?.email || 'user@example.com'}
              </div>
            </div>
            
            {/* Profile button */}
            <div style={{ position: 'relative' }} ref={userMenuRef}>
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                style={{
                  width: '36px',
                  height: '36px',
                  border: 'none',
                  borderRadius: '8px',
                  backgroundColor: '#374151',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'background-color 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#4b5563';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#374151';
                }}
              >
              <span
                style={{
                  color: '#ffffff',
                  fontSize: '14px',
                  fontWeight: '600',
                  fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                }}
              >
                {user?.username?.charAt(0).toUpperCase() || 'A'}
              </span>
            </button>

          {/* User dropdown menu */}
          {showUserMenu && (
            <div
              style={{
                position: 'absolute',
                right: '0',
                top: '48px',
                width: '200px',
                backgroundColor: '#ffffff',
                border: '1px solid #e5e7eb',
                borderRadius: '12px',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
                zIndex: 1000,
                padding: '8px 0'
              }}
            >
              <button
                onClick={() => handleMenuItemClick('/profile')}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  border: 'none',
                  backgroundColor: 'transparent',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontSize: '14px',
                  color: '#374151',
                  transition: 'background-color 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#f3f4f6';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                프로필
              </button>
              <button
                onClick={() => handleMenuItemClick('/workspaces')}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  border: 'none',
                  backgroundColor: 'transparent',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontSize: '14px',
                  color: '#374151',
                  transition: 'background-color 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#f3f4f6';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                워크스페이스 관리
              </button>
              <button
                onClick={() => handleMenuItemClick('/settings')}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  border: 'none',
                  backgroundColor: 'transparent',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontSize: '14px',
                  color: '#374151',
                  transition: 'background-color 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#f3f4f6';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                설정
              </button>
              <hr style={{ margin: '8px 0', border: 'none', borderTop: '1px solid #f3f4f6' }} />
              <button
                onClick={handleLogout}
                style={{
                  width: '100%',
                  padding: '12px 16px',
                  border: 'none',
                  backgroundColor: 'transparent',
                  textAlign: 'left',
                  cursor: 'pointer',
                  fontSize: '14px',
                  color: '#dc2626',
                  transition: 'background-color 0.2s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#fef2f2';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                로그아웃
              </button>
            </div>
          )}
            </div>
          </div>
        </div>
      </div>
    </AntHeader>
  );
};

export default Header;