/**
 * 파일명: user.ts (80줄)
 * 목적: 사용자 관련 타입 정의
 * 동작 과정:
 * 1. 사용자 프로필 및 인증 정보 타입
 * 2. 사용자 설정 및 선호도 타입
 * 3. 사용자 활동 및 통계 타입
 * 데이터베이스 연동: users, user_profiles 테이블과 매핑
 * 의존성: base.ts
 */

import type { UUID, DateTime, JSONObject } from './base';

// User Profile
export interface User {
  id: UUID;
  email: string;
  username: string;
  
  // Profile info
  firstName?: string;
  lastName?: string;
  displayName?: string;
  avatar?: string;
  bio?: string;
  
  // Account status
  isActive: boolean;
  isVerified: boolean;
  is_superuser?: boolean; // Admin user flag
  
  // Preferences
  preferences: UserPreferences;
  
  // Activity
  lastLoginAt?: DateTime;
  lastActiveAt?: DateTime;
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
}

// User Preferences
export interface UserPreferences {
  // UI preferences
  theme: 'light' | 'dark' | 'auto';
  language: string;
  timezone: string;
  
  // Notification preferences
  notifications: UserNotificationPreferences;
  
  // Editor preferences
  editor: UserEditorPreferences;
  
  // Privacy preferences
  privacy: UserPrivacyPreferences;
}

// User Notification Preferences
export interface UserNotificationPreferences {
  email: {
    enabled: boolean;
    frequency: 'immediate' | 'daily' | 'weekly' | 'never';
    events: string[];
  };
  push: {
    enabled: boolean;
    events: string[];
  };
  inApp: {
    enabled: boolean;
    events: string[];
  };
}

// User Editor Preferences
export interface UserEditorPreferences {
  // Code editor
  fontSize: number;
  fontFamily: string;
  tabSize: number;
  wordWrap: boolean;
  
  // Flow editor
  snapToGrid: boolean;
  gridSize: number;
  autoSave: boolean;
  autoSaveInterval: number; // seconds
}

// User Privacy Preferences
export interface UserPrivacyPreferences {
  profileVisibility: 'public' | 'workspace' | 'private';
  showOnlineStatus: boolean;
  allowDirectMessages: boolean;
}

// User Session
export interface UserSession {
  id: UUID;
  userId: UUID;
  
  // Session info
  token: string;
  refreshToken?: string;
  expiresAt: DateTime;
  
  // Client info
  userAgent?: string;
  ipAddress?: string;
  device?: string;
  
  // Status
  isActive: boolean;
  
  // Timestamps
  createdAt: DateTime;
  lastUsedAt: DateTime;
}

// User Activity
export interface UserActivity {
  id: UUID;
  userId: UUID;
  
  // Activity details
  type: 'login' | 'logout' | 'flow_created' | 'flow_executed' | 'workspace_joined';
  details: JSONObject;
  
  // Context
  workspaceId?: UUID;
  flowId?: UUID;
  
  // Client info
  userAgent?: string;
  ipAddress?: string;
  
  // Timestamp
  createdAt: DateTime;
}