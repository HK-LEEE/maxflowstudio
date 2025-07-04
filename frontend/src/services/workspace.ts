/**
 * Workspace API Service
 * Handles workspace management operations
 */

import { apiClient } from './api';
import type { 
  PermissionTypeType, 
  Workspace,
  CreateWorkspaceRequest,
  UpdateWorkspaceRequest
} from '../types';

export interface AddFlowToWorkspaceRequest {
  flow_id: string;
  workspace_id: string;
}

export interface WorkspacePermission {
  workspace_id: string;
  user_id: string;
  permission: PermissionTypeType;
  is_admin: boolean;
}

export interface AssignPermissionRequest {
  user_id?: string;
  group_id?: string;
  permission_level: PermissionTypeType;
}

export const workspaceService = {
  /**
   * Create a new workspace
   */
  create: async (data: CreateWorkspaceRequest): Promise<Workspace> => {
    // Clean the data by removing undefined values
    const cleanData: CreateWorkspaceRequest = {
      name: data.name,
      type: data.type,
      ...(data.description && { description: data.description }),
      ...(data.group_id && { group_id: data.group_id }),
    };
    
    console.log('🚀 Creating workspace with data:', data);
    console.log('🧹 Cleaned data:', cleanData);
    console.log('🔍 Data types:', {
      name: typeof cleanData.name,
      type: typeof cleanData.type,
      description: typeof cleanData.description,
      group_id: typeof cleanData.group_id,
    });
    console.log('📦 JSON stringified:', JSON.stringify(cleanData));
    
    try {
      const response = await apiClient.post('/api/workspaces/', cleanData);
      console.log('✅ Workspace creation response:', response.data);
      return response.data;
    } catch (error: any) {
      console.error('❌ Workspace creation request failed:', error);
      console.error('📋 Original data:', data);
      console.error('📋 Cleaned data:', cleanData);
      console.error('📋 Error details:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        data: error.response?.data,
        url: error.config?.url,
      });
      
      // Log full error message if truncated
      if (error.response?.data?.detail) {
        console.error('📋 Full error message:', error.response.data.detail);
      }
      throw error;
    }
  },

  /**
   * List all accessible workspaces
   */
  list: async (): Promise<Workspace[]> => {
    const response = await apiClient.get('/api/workspaces/');
    return response.data;
  },

  /**
   * Get workspace by ID
   */
  getById: async (workspaceId: string): Promise<Workspace> => {
    const response = await apiClient.get(`/api/workspaces/${workspaceId}`);
    return response.data;
  },

  /**
   * Update workspace
   */
  update: async (workspaceId: string, data: UpdateWorkspaceRequest): Promise<Workspace> => {
    const response = await apiClient.put(`/api/workspaces/${workspaceId}`, data);
    return response.data;
  },

  /**
   * Delete workspace
   */
  delete: async (workspaceId: string): Promise<void> => {
    await apiClient.delete(`/api/workspaces/${workspaceId}`);
  },

  /**
   * Add flow to workspace
   */
  addFlow: async (data: AddFlowToWorkspaceRequest): Promise<void> => {
    await apiClient.post('/api/workspaces/flows/assign', data);
  },

  /**
   * Get flows in workspace
   */
  getFlows: async (workspaceId: string): Promise<any[]> => {
    const response = await apiClient.get(`/api/workspaces/${workspaceId}/flows`);
    return response.data;
  },

  /**
   * Get user permission for workspace
   */
  getUserPermission: async (workspaceId: string): Promise<WorkspacePermission> => {
    const response = await apiClient.get(`/api/workspaces/${workspaceId}/permission`);
    return response.data;
  },

  /**
   * Get user's workspaces
   */
  getUserWorkspaces: async (): Promise<Workspace[]> => {
    const response = await apiClient.get('/api/workspaces/');
    return response.data;
  },

  /**
   * Assign permission to workspace (user or group)
   */
  assignPermission: async (workspaceId: string, data: AssignPermissionRequest): Promise<void> => {
    console.log('🔗 Assigning permission:', data);
    await apiClient.post(`/api/workspaces/${workspaceId}/permissions`, data);
  },

  /**
   * Create workspace with permissions (two-step process)
   */
  createWithPermissions: async (
    workspaceData: Omit<CreateWorkspaceRequest, 'user_permissions' | 'group_permissions'>,
    userPermissions: Array<{ user_id: string; permission: PermissionTypeType }> = [],
    groupPermissions: Array<{ group_id: string; permission: PermissionTypeType }> = []
  ): Promise<Workspace> => {
    console.log('🏗️ Creating workspace with data:', workspaceData);
    console.log('👥 User permissions:', userPermissions);
    console.log('🏢 Group permissions:', groupPermissions);
    
    try {
      // Step 1: Create workspace
      const workspace = await workspaceService.create(workspaceData);
      console.log('✅ Workspace created successfully:', workspace);
      
      // Step 2: Assign permissions
      const permissionPromises: Promise<void>[] = [];
      
      // Add user permissions
      userPermissions.forEach(up => {
        console.log('➕ Adding user permission:', up);
        permissionPromises.push(
          workspaceService.assignPermission(workspace.id, {
            user_id: up.user_id,
            permission_level: up.permission,
          })
        );
      });
      
      // Add group permissions
      groupPermissions.forEach(gp => {
        console.log('➕ Adding group permission:', gp);
        permissionPromises.push(
          workspaceService.assignPermission(workspace.id, {
            group_id: gp.group_id,
            permission_level: gp.permission,
          })
        );
      });
      
      // Wait for all permissions to be assigned
      if (permissionPromises.length > 0) {
        console.log(`⏳ Assigning ${permissionPromises.length} permissions...`);
        await Promise.all(permissionPromises);
        console.log('✅ All permissions assigned successfully');
      }
      
      return workspace;
    } catch (error: any) {
      console.error('❌ Workspace creation failed:', error);
      
      // Enhance error messages for better user feedback
      if (error?.response?.status === 404 && error?.response?.data?.detail?.includes('Group not found')) {
        const enhancedError: any = new Error(
          'Workspace 생성은 성공했지만 그룹 권한 할당에 실패했습니다. ' +
          '선택한 그룹이 시스템에 존재하지 않거나 접근 권한이 없을 수 있습니다. ' +
          '관리자에게 문의하거나 다른 그룹을 선택해 주세요.'
        );
        enhancedError.originalError = error;
        throw enhancedError;
      }
      
      if (error?.response?.status === 403) {
        const enhancedError: any = new Error(
          '권한이 부족합니다. 이 작업을 수행하려면 관리자 권한이 필요합니다.'
        );
        enhancedError.originalError = error;
        throw enhancedError;
      }
      
      if (error?.response?.status === 500) {
        const enhancedError: any = new Error(
          '서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.'
        );
        enhancedError.originalError = error;
        throw enhancedError;
      }
      
      throw error;
    }
  },
};