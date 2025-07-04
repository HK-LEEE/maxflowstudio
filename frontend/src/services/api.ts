/**
 * API Client Configuration
 * Flow: axios instance -> request interceptor -> response interceptor
 */

import axios, { AxiosError } from 'axios';
import { authService } from './auth';
import { getAccessToken, ensureValidToken } from '../utils/auth';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8005';
const AUTH_API_URL = import.meta.env.VITE_AUTH_API_URL || 'http://localhost:8000';

// Create axios instance for main API
export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Create axios instance for Auth Server
export const authApiClient = axios.create({
  baseURL: AUTH_API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  async (config) => {
    const token = await ensureValidToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Track if we're currently refreshing to avoid multiple simultaneous refresh attempts
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: any) => void;
  reject: (error?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  
  failedQueue = [];
};

// Response interceptor to handle errors and token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // If already refreshing, queue this request
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(token => {
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${token}`;
          }
          return apiClient(originalRequest);
        }).catch(err => {
          return Promise.reject(err);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshResponse = await authService.refreshToken();
        const newToken = refreshResponse.access_token;
        
        // Update the authorization header for the original request
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
        }
        
        processQueue(null, newToken);
        
        // Retry the original request with new token
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        console.error('Token refresh failed in API interceptor:', refreshError);
        processQueue(refreshError, null);
        
        // Clear all auth data
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        
        // Redirect to login page
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    
    return Promise.reject(error);
  }
);

// Add the same interceptors to authApiClient
authApiClient.interceptors.request.use(
  async (config) => {
    const token = await ensureValidToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

authApiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as any;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => {
          return authApiClient(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await authService.refreshToken();
        processQueue(null);
        return authApiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError);
        authService.logout();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// API endpoints
export const api = {
  // Health
  health: () => apiClient.get('/api/health'),
  
  // Auth
  auth: {
    login: (credentials: { email: string; password: string }) =>
      apiClient.post('/api/auth/login', credentials),
    logout: () => apiClient.post('/api/auth/logout'),
    me: () => apiClient.get('/api/auth/me'),
  },
  
  // Flows
  flows: {
    list: () => apiClient.get('/api/flows/'),
    get: (id: string) => apiClient.get(`/api/flows/${id}`),
    create: (data: any) => apiClient.post('/api/flows/', data),
    update: (id: string, data: any) => apiClient.put(`/api/flows/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/flows/${id}`),
  },
  
  // Executions
  executions: {
    list: (flowId?: string) => 
      apiClient.get('/api/executions/', { params: { flowId } }),
    get: (id: string) => apiClient.get(`/api/executions/${id}`),
    start: (flowId: string, inputs?: any) =>
      apiClient.post(`/api/executions/start`, { flowId, inputs }),
  },
  
  // Nodes
  nodes: {
    list: () => apiClient.get('/api/nodes/'),
    get: (id: string) => apiClient.get(`/api/nodes/${id}`),
  },
  
  // API Keys
  apiKeys: {
    list: () => apiClient.get('/api/api-keys/'),
    create: (name: string) => apiClient.post('/api/api-keys/', { name }),
    delete: (id: string) => apiClient.delete(`/api/api-keys/${id}`),
  },

  // Admin APIs
  admin: {
    users: () => apiClient.get('/api/admin/users'),
    groups: () => apiClient.get('/api/admin/groups'),
    stats: () => apiClient.get('/api/admin/stats'),
  },

  // Workspaces
  workspaces: {
    list: () => apiClient.get('/api/workspaces/'),
    permissions: {
      get: (workspaceId: string) => apiClient.get(`/api/workspaces/${workspaceId}/permissions`),
      assign: (workspaceId: string, data: any) => apiClient.post(`/api/workspaces/${workspaceId}/permissions`, data),
      remove: (workspaceId: string, mappingType: string, mappingId: string) => 
        apiClient.delete(`/api/workspaces/${workspaceId}/permissions/${mappingType}/${mappingId}`),
    },
  },
};