/**
 * 파일명: api.ts (90줄)
 * 목적: API 관련 타입 정의
 * 동작 과정:
 * 1. API 엔드포인트 및 배포 관련 타입
 * 2. API 키 및 인증 타입
 * 3. API 사용량 및 통계 타입
 * 데이터베이스 연동: api_deployments, api_keys 테이블과 매핑
 * 의존성: base.ts, flow.ts
 */

import type { UUID, DateTime, JSONObject } from './base';

// API Deployment
export interface ApiDeployment {
  id: UUID;
  flowId: UUID;
  name: string;
  description?: string;
  
  // Deployment config
  version: string;
  endpoint: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  
  // Authentication
  authType: 'none' | 'api_key' | 'jwt' | 'oauth';
  authConfig?: JSONObject;
  
  // Rate limiting
  rateLimit?: {
    requests: number;
    per: 'second' | 'minute' | 'hour' | 'day';
  };
  
  // Status
  status: 'draft' | 'deployed' | 'paused' | 'deprecated';
  isPublic: boolean;
  
  // Deployment info
  deployedAt?: DateTime;
  deployedBy?: UUID;
  
  // Usage
  totalRequests: number;
  lastRequestAt?: DateTime;
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
}

// API Key
export interface ApiKey {
  id: UUID;
  name: string;
  description?: string;
  
  // Key details
  key: string; // Hashed in database
  prefix: string; // First few chars for identification
  
  // Scope
  workspaceId?: UUID;
  userId: UUID;
  scopes: ApiScope[];
  
  // Restrictions
  allowedIPs?: string[];
  allowedDomains?: string[];
  
  // Rate limiting
  rateLimit?: {
    requests: number;
    per: 'second' | 'minute' | 'hour' | 'day';
  };
  
  // Status
  isActive: boolean;
  expiresAt?: DateTime;
  
  // Usage
  totalRequests: number;
  lastUsedAt?: DateTime;
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
}

// API Scopes
export interface ApiScope {
  resource: string; // 'flows', 'executions', 'workspaces', etc.
  actions: string[]; // 'read', 'write', 'execute', 'delete'
}

// API Request Log
export interface ApiRequestLog {
  id: UUID;
  
  // Request details
  method: string;
  path: string;
  query?: JSONObject;
  headers?: JSONObject;
  body?: JSONObject;
  
  // Response details
  statusCode: number;
  responseTime: number; // milliseconds
  responseSize: number; // bytes
  
  // Authentication
  apiKeyId?: UUID;
  userId?: UUID;
  
  // Client info
  userAgent?: string;
  ipAddress: string;
  
  // Error info
  error?: string;
  
  // Timestamp
  createdAt: DateTime;
}

// API Usage Statistics
export interface ApiUsageStats {
  period: 'hour' | 'day' | 'week' | 'month';
  startDate: DateTime;
  endDate: DateTime;
  
  // Request stats
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  
  // Performance stats
  averageResponseTime: number;
  p95ResponseTime: number;
  p99ResponseTime: number;
  
  // Top endpoints
  topEndpoints: Array<{
    endpoint: string;
    requests: number;
    averageResponseTime: number;
  }>;
  
  // Error breakdown
  errorBreakdown: Array<{
    statusCode: number;
    count: number;
  }>;
}