/**
 * 파일명: workspace.ts (100줄)
 * 목적: 워크스페이스 및 권한 관련 타입 정의
 * 동작 과정:
 * 1. 워크스페이스 구조 및 멤버십 타입
 * 2. 권한 시스템 및 역할 정의
 * 3. 워크스페이스 설정 및 리소스 타입
 * 데이터베이스 연동: workspaces, workspace_members 테이블과 매핑
 * 의존성: base.ts
 */

import type { UUID, DateTime, JSONObject } from './base';

// Workspace Types
export const WorkspaceType = {
  PERSONAL: 'user',     // Backend uses 'user' for personal workspaces
  TEAM: 'group',        // Backend uses 'group' for team workspaces
  ORGANIZATION: 'organization',
  ENTERPRISE: 'enterprise',
  USER: 'user',
  GROUP: 'group',
} as const;

export type WorkspaceTypeType = typeof WorkspaceType[keyof typeof WorkspaceType];

// Permission Types
export const PermissionType = {
  READ: 'read',
  WRITE: 'write',
  EXECUTE: 'execute',
  ADMIN: 'admin',
  OWNER: 'owner',
  MEMBER: 'member',
  VIEWER: 'viewer',
} as const;

export type PermissionTypeType = typeof PermissionType[keyof typeof PermissionType];

// Workspace Definition
export interface Workspace {
  id: UUID;
  name: string;
  description: string;
  type: WorkspaceTypeType;
  
  // Ownership
  ownerId: UUID;
  
  // Settings
  settings: WorkspaceSettings;
  
  // Status
  isActive: boolean;
  
  // Limits
  limits: WorkspaceLimits;
  
  // User permissions (for current user)
  user_permission?: PermissionTypeType;
  permissions?: PermissionTypeType[];
  
  // Statistics
  flow_count?: number;
  
  // Group info
  group_id?: UUID;
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
}

// Workspace Settings
export interface WorkspaceSettings {
  // General
  isPublic: boolean;
  allowGuestAccess: boolean;
  
  // Features
  enabledFeatures: string[];
  disabledFeatures: string[];
  
  // Integrations
  integrations: WorkspaceIntegration[];
  
  // Branding
  logo?: string;
  theme?: JSONObject;
  
  // Notifications
  notifications: WorkspaceNotificationSettings;
}

// Workspace Limits
export interface WorkspaceLimits {
  maxMembers: number;
  maxFlows: number;
  maxExecutionsPerMonth: number;
  maxStorageGB: number;
  
  // Feature limits
  maxComponentsPerFlow: number;
  maxScheduledFlows: number;
  
  // Current usage
  currentMembers: number;
  currentFlows: number;
  currentExecutions: number;
  currentStorageGB: number;
}

// Workspace Member
export interface WorkspaceMember {
  id: UUID;
  workspaceId: UUID;
  userId: UUID;
  
  // Role and permissions
  role: WorkspaceRole;
  permissions: PermissionTypeType[];
  
  // Status
  status: 'active' | 'invited' | 'suspended';
  joinedAt?: DateTime;
  invitedAt: DateTime;
  invitedBy: UUID;
  
  // Activity
  lastActiveAt?: DateTime;
}

// Workspace Roles
export interface WorkspaceRole {
  id: UUID;
  name: string;
  description: string;
  permissions: PermissionTypeType[];
  isDefault: boolean;
  isSystemRole: boolean;
}

// Workspace Integration
export interface WorkspaceIntegration {
  id: UUID;
  type: string; // 'slack', 'teams', 'webhook', etc.
  name: string;
  config: JSONObject;
  isEnabled: boolean;
  createdAt: DateTime;
  updatedAt: DateTime;
}

// Workspace Notification Settings
export interface WorkspaceNotificationSettings {
  email: {
    enabled: boolean;
    events: string[];
  };
  inApp: {
    enabled: boolean;
    events: string[];
  };
  webhook: {
    enabled: boolean;
    url?: string;
    events: string[];
  };
}

// Workspace Invitation
export interface WorkspaceInvitation {
  id: UUID;
  workspaceId: UUID;
  email: string;
  role: string;
  invitedBy: UUID;
  
  // Status
  status: 'pending' | 'accepted' | 'declined' | 'expired';
  
  // Timing
  expiresAt: DateTime;
  acceptedAt?: DateTime;
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
}

// Workspace create/update requests
export interface CreateWorkspaceRequest {
  name: string;
  description?: string;
  type: WorkspaceTypeType;
  group_id?: string;
}

export interface UpdateWorkspaceRequest {
  name?: string;
  description?: string;
  settings?: Partial<WorkspaceSettings>;
}