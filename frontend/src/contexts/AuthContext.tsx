/**
 * Authentication Context
 * Manages authentication state and provides auth methods with SSO auto-login
 */

import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { App } from 'antd';
import { authService } from '../services/auth';
import { attemptSilentLogin } from '../utils/silentAuth';
import { getUserInfo } from '../utils/popupOAuth';
import type { User } from '../types';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAttemptingSilentLogin: boolean;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAttemptingSilentLogin, setIsAttemptingSilentLogin] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { message } = App.useApp();

  const checkAuthWithAutoLogin = useCallback(async () => {
    try {
      // First check if we already have a valid token
      if (authService.isAuthenticated()) {
        console.log('🔍 DEBUG - Using existing token, getting current user...');
        const currentUser = await authService.getCurrentUser();
        console.log('🔍 DEBUG - Current user from authService:', currentUser);
        setUser(currentUser);
        localStorage.setItem('user', JSON.stringify(currentUser));
        setIsLoading(false);
        return;
      }

      // No token - attempt silent SSO login
      console.log('🔄 No token found, attempting silent SSO login...');
      setIsAttemptingSilentLogin(true);
      
      const silentResult = await attemptSilentLogin();
      
      if (silentResult.success && silentResult.token) {
        console.log('✅ Silent SSO login successful');
        
        // Get user info and store tokens
        const userInfo = await getUserInfo(silentResult.token);
        console.log('🔍 DEBUG - Full userInfo:', userInfo);
        console.log('🔍 DEBUG - userInfo.is_admin:', userInfo.is_admin);
        
        // Store authentication data
        localStorage.setItem('accessToken', silentResult.token);
        if (silentResult.tokenData) {
          localStorage.setItem('tokenType', silentResult.tokenData.token_type || 'Bearer');
          localStorage.setItem('expiresIn', (silentResult.tokenData.expires_in || 3600).toString());
          localStorage.setItem('scope', silentResult.tokenData.scope || 'read:profile read:groups manage:workflows');
        }
        
        // Map OAuth userinfo to User format
        // Fallback: Check if email contains 'admin' since OAuth doesn't provide is_admin field
        const isAdmin = userInfo.is_admin ?? userInfo.email?.includes('admin') ?? false;
        console.log('🔍 DEBUG - Admin detection:', {
          'userInfo.is_admin': userInfo.is_admin,
          'email': userInfo.email,
          'email.includes("admin")': userInfo.email?.includes('admin'),
          'final isAdmin': isAdmin
        });
        
        const user: User = {
          id: userInfo.sub,
          email: userInfo.email,
          username: userInfo.display_name || userInfo.email?.split('@')[0],
          full_name: userInfo.real_name,
          is_active: true,
          is_superuser: isAdmin,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          group_id: userInfo.groups?.[0]?.id
        };
        
        console.log('🔍 DEBUG - Created user object:', user);
        console.log('🔍 DEBUG - user.is_superuser:', user.is_superuser);
        
        localStorage.setItem('user', JSON.stringify(user));
        setUser(user);
        
        // Show success message
        message.success(`자동 로그인되었습니다. 환영합니다, ${user.full_name || user.username}!`);
        
      } else {
        // Silent login failed - user needs to manually log in
        console.log('ℹ️ Silent SSO login failed, manual login required:', silentResult.error);
        
        // Only redirect to login if not already on login page
        if (location.pathname !== '/login') {
          // Show a brief message that we're redirecting to manual login
          if (silentResult.error === 'silent_auth_timeout' || silentResult.error === 'login_required') {
            // Common cases - don't show error, just redirect
            navigate('/login');
          } else {
            // Unexpected error - show message
            message.info('로그인이 필요합니다. 로그인 페이지로 이동합니다.');
            setTimeout(() => navigate('/login'), 1000);
          }
        }
      }
      
    } catch (error) {
      console.error('Auto-login error:', error);
      
      // Clear all auth data on error
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
      setUser(null);
      
      // Redirect to login page only if not already on login page
      if (location.pathname !== '/login') {
        navigate('/login');
      }
    } finally {
      setIsAttemptingSilentLogin(false);
      setIsLoading(false);
    }
  }, [navigate, location.pathname, message]);

  // Check authentication on mount with SSO auto-login support
  useEffect(() => {
    // Skip authentication check completely on login and OAuth callback pages
    const isOAuthCallback = location.pathname === '/oauth/callback';
    const isLoginPage = location.pathname === '/login';
    
    if (!isOAuthCallback && !isLoginPage) {
      checkAuthWithAutoLogin();
    } else {
      // Just set loading to false for login/callback pages
      setIsLoading(false);
    }
  }, [location.pathname, checkAuthWithAutoLogin]);

  const checkAuth = async () => {
    try {

      if (authService.isAuthenticated()) {
        const currentUser = await authService.getCurrentUser();
        setUser(currentUser);
        localStorage.setItem('user', JSON.stringify(currentUser));
      } else {
        // No token available, redirect to login only if not already on login page
        if (location.pathname !== '/login') {
          console.log('🚫 No authentication token, redirecting to login');
          navigate('/login');
        }
      }
    } catch (error) {
      console.error('Auth check failed:', error);
      
      // Clear all auth data
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
      setUser(null);
      
      // Redirect to login page only if not already on login page
      if (location.pathname !== '/login') {
        navigate('/login');
      }
    } finally {
      setIsLoading(false);
    }
  };


  const logout = async () => {
    try {
      await authService.logout();
      setUser(null);
      message.success('Logged out successfully');
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
      // Still logout locally even if server request fails
      setUser(null);
      navigate('/login');
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAttemptingSilentLogin,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};