/**
 * Group API Service
 * Handles group management operations and search
 */

import { authApiClient } from './api';

export interface Group {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  is_system_group: boolean;
  member_count: number;
  workspace_count: number;
  created_at?: string;
  updated_at?: string;
  created_by?: string;
}

export interface GroupListParams {
  page?: number;
  limit?: number;
  search?: string;
  is_active?: boolean;
  include_system?: boolean;
}

export interface GroupListResponse {
  groups: Group[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export const groupService = {
  /**
   * List all groups with search and pagination
   */
  list: async (params: GroupListParams = {}): Promise<GroupListResponse> => {
    const queryParams = new URLSearchParams();
    
    if (params.page) queryParams.append('page', params.page.toString());
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.search) queryParams.append('search', params.search);
    if (params.is_active !== undefined) queryParams.append('is_active', params.is_active.toString());
    if (params.include_system !== undefined) queryParams.append('include_system', params.include_system.toString());

    const response = await authApiClient.get(`/admin/groups?${queryParams.toString()}`);
    return response.data;
  },

  /**
   * Search groups by query string
   */
  search: async (query: string, limit: number = 20): Promise<Group[]> => {
    try {
      console.log('🔍 Searching groups with query:', query);
      console.log('🌐 Request URL:', `http://localhost:8000/admin/groups`);
      
      const response = await authApiClient.get('/admin/groups', {
        params: {
          search: encodeURIComponent(query),
          limit,
          is_active: true, // Only search active groups
          include_system: true, // Include system groups in search
        },
      });
      
      console.log('✅ Group search response:', response.data);
      
      // Handle different response formats
      let groups = [];
      if (Array.isArray(response.data)) {
        groups = response.data;
      } else if (response.data.groups && Array.isArray(response.data.groups)) {
        groups = response.data.groups;
      } else if (response.data && typeof response.data === 'object') {
        groups = [response.data];
      }
      
      // Debug: Check raw group ID format from Auth Server
      if (groups.length > 0) {
        console.log('🔍 Raw group ID analysis:', {
          firstGroupId: groups[0].id,
          idType: typeof groups[0].id,
          isUUID: /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(groups[0].id)),
          allGroupIds: groups.map(g => ({ id: g.id, type: typeof g.id }))
        });
      }
      
      // Map auth server fields to expected format
      const mappedGroups = groups.map((group: any) => ({
        id: String(group.id), // Keep as string for now, will optimize based on format
        name: group.name,
        description: group.description,
        is_active: true, // Auth server groups are assumed active if returned
        is_system_group: false, // Can be determined by other logic if needed
        member_count: group.users_count || group.member_count || 0,
        workspace_count: group.workspace_count || 0,
        created_at: group.created_at,
        updated_at: group.updated_at,
        created_by: group.created_by,
      }));
      
      console.log('📦 Processed groups:', mappedGroups);
      return mappedGroups;
    } catch (error: any) {
      console.error('❌ Group search failed:', error);
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
   * Get group by ID
   */
  getById: async (groupId: string): Promise<Group> => {
    const response = await authApiClient.get(`/admin/groups/${groupId}`);
    return response.data;
  },

  /**
   * Get groups by IDs (batch fetch) - fallback to individual requests
   */
  getByIds: async (groupIds: string[]): Promise<Group[]> => {
    try {
      // Try batch endpoint first if available
      const response = await authApiClient.post('/admin/groups/batch', {
        group_ids: groupIds,
      });
      return response.data;
    } catch {
      // Fallback to individual requests
      const groups: Group[] = [];
      for (const groupId of groupIds) {
        try {
          const group = await groupService.getById(groupId);
          groups.push(group);
        } catch (err) {
          console.warn(`Failed to fetch group ${groupId}:`, err);
        }
      }
      return groups;
    }
  },

  /**
   * Create new group
   */
  create: async (data: { name: string; description?: string }): Promise<Group> => {
    const response = await authApiClient.post('/admin/groups', data);
    return response.data;
  },

  /**
   * Update group
   */
  update: async (groupId: string, data: { name?: string; description?: string; is_active?: boolean }): Promise<Group> => {
    const response = await authApiClient.put(`/admin/groups/${groupId}`, data);
    return response.data;
  },

  /**
   * Delete group
   */
  delete: async (groupId: string): Promise<void> => {
    await authApiClient.delete(`/admin/groups/${groupId}`);
  },
};