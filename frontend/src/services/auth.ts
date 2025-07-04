/**
 * Authentication Service
 * OAuth 2.0 integration with MAX Platform auth server
 * OAuth-only authentication for FlowStudio
 */

import axios from 'axios';
import type { User } from '../types';
import { oauthClient } from './oauth';
import { PopupOAuthLogin, getUserInfo } from '../utils/popupOAuth';
import { attemptSilentLogin } from '../utils/silentAuth';

const AUTH_SERVER_URL = import.meta.env.VITE_AUTH_SERVER_URL || 'http://localhost:8000';

// Create separate axios instance for auth server
const authClient = axios.create({
  baseURL: AUTH_SERVER_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to auth server requests
authClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);


export const authService = {
  /**
   * Attempt silent SSO login (for automatic login)
   */
  attemptSilentLogin: async (): Promise<User | null> => {
    try {
      console.log('🔇 Attempting silent SSO login...');
      
      const silentResult = await attemptSilentLogin();
      
      if (silentResult.success && silentResult.token) {
        // Get user information
        const userInfo = await getUserInfo(silentResult.token);
        
        // Store authentication data
        localStorage.setItem('accessToken', silentResult.token);
        if (silentResult.tokenData) {
          localStorage.setItem('tokenType', silentResult.tokenData.token_type || 'Bearer');
          localStorage.setItem('expiresIn', (silentResult.tokenData.expires_in || 3600).toString());
          localStorage.setItem('scope', silentResult.tokenData.scope || 'read:profile read:groups manage:workflows');
        }
        
        // Map OAuth userinfo to User format
        const user: User = {
          id: userInfo.sub,
          email: userInfo.email,
          username: userInfo.display_name,
          full_name: userInfo.real_name,
          is_active: true,
          is_superuser: userInfo.is_admin,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          group_id: userInfo.groups?.[0]?.id
        };
        
        localStorage.setItem('user', JSON.stringify(user));
        console.log('✅ Silent SSO login successful');
        return user;
      } else {
        console.log('ℹ️ Silent SSO login failed:', silentResult.error);
        return null;
      }
      
    } catch (error: any) {
      console.error('Silent SSO login error:', error);
      return null;
    }
  },

  /**
   * Start popup-based OAuth 2.0 login flow
   */
  loginWithPopupOAuth: async (): Promise<User> => {
    const oauthInstance = new PopupOAuthLogin();
    
    try {
      console.log('🔐 Starting popup OAuth login...');
      
      // Start popup OAuth flow
      const tokenResponse = await oauthInstance.startAuth();
      
      console.log('✅ Popup OAuth successful, getting user info...');
      
      // Get user information
      const userInfo = await getUserInfo(tokenResponse.access_token);
      
      // Store authentication data
      localStorage.setItem('accessToken', tokenResponse.access_token);
      localStorage.setItem('tokenType', tokenResponse.token_type);
      localStorage.setItem('expiresIn', tokenResponse.expires_in.toString());
      localStorage.setItem('scope', tokenResponse.scope);
      
      // Fallback: Check if email contains 'admin' since OAuth doesn't provide is_admin field
      const isAdmin = userInfo.is_admin ?? userInfo.email?.includes('admin') ?? false;
      
      // Map OAuth userinfo to User format
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
      
      localStorage.setItem('user', JSON.stringify(user));
      
      return user;
      
    } catch (error: any) {
      console.error('Popup OAuth login error:', error);
      
      // Provide specific error messages for different scenarios
      if (error.message?.includes('blocked')) {
        throw new Error('Popup was blocked. Please allow popups for this site and try again.');
      } else if (error.message?.includes('cancelled')) {
        throw new Error('Login was cancelled by the user.');
      } else if (error.message?.includes('login_required')) {
        throw new Error('Please log in to MAX Platform first, then try OAuth login again.');
      } else if (error.message?.includes('No token')) {
        throw new Error('Authentication completed but no token received. Please try again.');
      } else if (error.message?.includes('untrusted origin')) {
        throw new Error('Security error: Invalid origin detected. Please contact support.');
      } else {
        // Log the actual error for debugging while showing user-friendly message
        console.error('Detailed OAuth error:', error);
        throw new Error('OAuth login failed. Please try again or contact support if the problem persists.');
      }
    } finally {
      oauthInstance.forceCleanup();
    }
  },

  /**
   * Start OAuth 2.0 login flow (with fallback to legacy login)
   */
  loginWithOAuth: async (): Promise<void> => {
    try {
      await oauthClient.startAuth();
    } catch (error: any) {
      console.warn('OAuth 2.0 login initiation failed:', error);
      
      // Provide specific error messages for different scenarios
      if (error.message?.includes('not available')) {
        throw new Error('OAuth 2.0 is not currently available. Please use email/password login.');
      } else if (error.message?.includes('login_required')) {
        throw new Error('Please log in to MAX Platform first, then try OAuth login again.');
      } else {
        throw new Error('Failed to start OAuth login. Please try again or use email/password login.');
      }
    }
  },

  /**
   * Handle OAuth callback and complete login
   */
  handleOAuthCallback: async (): Promise<User> => {
    const tokenResponse = await oauthClient.handleCallback();
    const userInfo = await oauthClient.getUserInfo(tokenResponse.access_token);
    
    // Store tokens and user info
    localStorage.setItem('accessToken', tokenResponse.access_token);
    localStorage.setItem('tokenType', tokenResponse.token_type);
    localStorage.setItem('expiresIn', tokenResponse.expires_in.toString());
    localStorage.setItem('scope', tokenResponse.scope);
    
    // Fallback: Check if email contains 'admin' since OAuth doesn't provide is_admin field
    const isAdmin = userInfo.is_admin ?? userInfo.email?.includes('admin') ?? false;
    
    // Map OAuth userinfo to User type
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
    
    localStorage.setItem('user', JSON.stringify(user));
    
    return user;
  },

  
  /**
   * Refresh access token using refresh token
   */
  refreshToken: async (): Promise<{ access_token: string }> => {
    console.log('🔄 authService.refreshToken: Starting token refresh');
    const refreshToken = localStorage.getItem('refreshToken');
    
    if (!refreshToken) {
      console.error('❌ authService.refreshToken: No refresh token available');
      throw new Error('No refresh token available');
    }

    try {
      console.log('🔄 authService.refreshToken: Calling OAuth refresh endpoint');
      const response = await oauthClient.refreshToken(refreshToken);
      
      // Store new tokens
      localStorage.setItem('accessToken', response.access_token);
      if (response.refresh_token) {
        localStorage.setItem('refreshToken', response.refresh_token);
      }
      if (response.expires_in) {
        localStorage.setItem('expiresIn', response.expires_in.toString());
      }
      
      console.log('✅ authService.refreshToken: Token refreshed successfully');
      return { access_token: response.access_token };
    } catch (error) {
      console.error('❌ authService.refreshToken: Refresh failed:', error);
      // Clear all tokens on refresh failure
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('tokenType');
      localStorage.removeItem('expiresIn');
      localStorage.removeItem('scope');
      localStorage.removeItem('user');
      throw error;
    }
  },

  /**
   * Logout and clear tokens
   */
  logout: async (): Promise<void> => {
    try {
      const accessToken = localStorage.getItem('accessToken');
      if (accessToken) {
        // Try to revoke OAuth token first
        await oauthClient.revokeToken(accessToken);
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear all stored data
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('tokenType');
      localStorage.removeItem('expiresIn');
      localStorage.removeItem('scope');
      localStorage.removeItem('user');
    }
  },
  
  /**
   * Get current user info using OAuth userinfo endpoint
   */
  getCurrentUser: async (): Promise<User> => {
    const accessToken = localStorage.getItem('accessToken');
    if (!accessToken) {
      throw new Error('No access token available');
    }

    // Use OAuth userinfo endpoint only
    const userInfo = await oauthClient.getUserInfo(accessToken);
    
    // Fallback: Check if email contains 'admin' since OAuth doesn't provide is_admin field
    const isAdmin = userInfo.is_admin ?? userInfo.email?.includes('admin') ?? false;
    console.log('🔍 DEBUG authService.getCurrentUser - Admin detection:', {
      'userInfo.is_admin': userInfo.is_admin,
      'email': userInfo.email,
      'email.includes("admin")': userInfo.email?.includes('admin'),
      'final isAdmin': isAdmin
    });
    
    // Map OAuth userinfo to User type
    const user = {
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
    
    console.log('🔍 DEBUG authService.getCurrentUser - Final user object:', user);
    return user;
  },
  
  /**
   * Check if user is authenticated
   */
  isAuthenticated: (): boolean => {
    return !!localStorage.getItem('accessToken');
  },
  
  /**
   * Get stored user info
   */
  getStoredUser: (): User | null => {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },
  

  /**
   * Redirect to MAXplatform for signup
   */
  redirectToSignup: (): void => {
    // According to the requirements, redirect to MAXplatform for signup
    window.location.href = 'http://localhost:3000/signup?redirect=' + 
      encodeURIComponent(window.location.origin);
  },
};