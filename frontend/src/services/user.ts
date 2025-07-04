/**
 * User API Service
 * Handles user management operations and search
 */

import { authApiClient, apiClient } from './api';

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  group_id?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserListParams {
  page?: number;
  limit?: number;
  search?: string;
  group_id?: string;
  is_active?: boolean;
}

export interface UserListResponse {
  users: User[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export const userService = {
  /**
   * List all users with search and pagination
   */
  list: async (params: UserListParams = {}): Promise<UserListResponse> => {
    const queryParams = new URLSearchParams();
    
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.search) queryParams.append('search', params.search);
    if (params.group_id) queryParams.append('group_id', params.group_id);
    if (params.is_active !== undefined) queryParams.append('is_active', params.is_active.toString());

    const response = await authApiClient.get(`/admin/users?${queryParams.toString()}`);
    return response.data;
  },

  /**
   * Search users by query string
   */
  search: async (query: string, limit: number = 20): Promise<User[]> => {
    try {
      console.log('👤 Searching users with query:', query);
      console.log('🌐 Request URL:', `http://localhost:8000/admin/users`);
      
      const response = await authApiClient.get('/admin/users', {
        params: {
          search: encodeURIComponent(query),
          limit,
          is_active: true, // Only search active users
        },
      });
      
      console.log('✅ User search response:', response.data);
      
      // Handle different response formats
      let users = [];
      if (Array.isArray(response.data)) {
        users = response.data;
      } else if (response.data.users && Array.isArray(response.data.users)) {
        users = response.data.users;
      } else if (response.data && typeof response.data === 'object') {
        users = [response.data];
      }
      
      // Map auth server fields to expected format
      const mappedUsers = users.map((user: any) => ({
        id: String(user.id), // Ensure ID is always a string
        username: user.display_name || user.email.split('@')[0],
        email: user.email,
        full_name: user.real_name || user.display_name || user.email,
        group_id: user.group?.id,
        is_active: user.is_active,
        is_superuser: user.is_admin || false,
        created_at: user.created_at,
        updated_at: user.updated_at,
      }));
      
      console.log('📦 Processed users:', mappedUsers);
      return mappedUsers;
    } catch (error: any) {
      console.error('❌ User search failed:', error);
      console.error('📋 Error details:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        url: error.config?.url,
        params: error.config?.params,
      });
      return [];
    }
  },

  /**
   * Get user by ID
   */
  getById: async (userId: string): Promise<User> => {
    const response = await authApiClient.get(`/admin/users/${userId}`);
    return response.data;
  },

  /**
   * Get current user information via OAuth userinfo
   */
  getCurrentUser: async (): Promise<User> => {
    try {
      // Try OAuth userinfo endpoint first
      const response = await authApiClient.get('/api/oauth/userinfo');
      const userInfo = response.data;
      
      // Map OAuth userinfo response to User format
      return {
        id: userInfo.sub || userInfo.id,
        username: userInfo.display_name || userInfo.username,
        email: userInfo.email,
        full_name: userInfo.real_name || userInfo.full_name || userInfo.display_name,
        group_id: userInfo.groups?.[0]?.id,
        is_active: userInfo.is_active !== false,
        is_superuser: userInfo.is_admin || userInfo.is_superuser || false,
        created_at: userInfo.created_at || new Date().toISOString(),
        updated_at: userInfo.updated_at || new Date().toISOString(),
      };
    } catch (error) {
      // Fallback to legacy endpoint
      console.warn('OAuth userinfo failed, using legacy endpoint:', error);
      const response = await apiClient.get('/api/auth/me');
      return response.data;
    }
  },

  /**
   * Get users by IDs (batch fetch) - fallback to individual requests
   */
  getByIds: async (userIds: string[]): Promise<User[]> => {
    try {
      // Try batch endpoint first if available
      const response = await authApiClient.post('/admin/users/batch', {
        user_ids: userIds,
      });
      return response.data;
    } catch {
      // Fallback to individual requests
      const users: User[] = [];
      for (const userId of userIds) {
        try {
          const user = await userService.getById(userId);
          users.push(user);
        } catch (err) {
          console.warn(`Failed to fetch user ${userId}:`, err);
        }
      }
      return users;
    }
  },
};