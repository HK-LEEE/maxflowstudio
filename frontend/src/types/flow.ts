/**
 * 파일명: flow.ts (120줄)
 * 목적: Flow 관련 타입 정의
 * 동작 과정:
 * 1. Flow 정의 및 메타데이터 타입
 * 2. Flow 실행 및 스케줄링 타입
 * 3. Flow 버전 관리 및 배포 타입
 * 데이터베이스 연동: flows, flow_executions 테이블과 매핑
 * 의존성: base.ts, components.ts
 */

import type { 
  UUID, 
  DateTime, 
  JSONObject 
} from './base';
import type { ComponentInstance, ComponentConnection, ComponentExecutionResult } from './components';

// Flow Definition
export interface FlowDefinition {
  id: UUID;
  name: string;
  description: string;
  version: string;
  
  // Flow structure
  components: ComponentInstance[];
  connections: ComponentConnection[];
  
  // Flow metadata
  tags: string[];
  category?: string;
  author: UUID; // User ID
  
  // Configuration
  globalVariables: Record<string, any>;
  settings: FlowSettings;
  
  // Status
  isPublic: boolean;
  isActive: boolean;
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
  publishedAt?: DateTime;
}

// Flow Settings
export interface FlowSettings {
  timeout?: number; // seconds
  retryCount?: number;
  parallelExecution?: boolean;
  errorHandling: 'stop' | 'continue' | 'retry';
  
  // Scheduling
  schedule?: FlowSchedule;
  
  // Notifications
  notifications?: FlowNotification[];
}

// Flow Scheduling
export interface FlowSchedule {
  enabled: boolean;
  type: 'cron' | 'interval' | 'manual';
  expression?: string; // cron expression
  interval?: number; // milliseconds
  timezone?: string;
  nextRun?: DateTime;
}

// Flow Notifications
export interface FlowNotification {
  type: 'email' | 'webhook' | 'slack';
  target: string;
  events: ('start' | 'success' | 'failure' | 'complete')[];
  enabled: boolean;
}

// Flow Execution
export interface FlowExecution {
  id: UUID;
  flowId: UUID;
  flowVersion: string;
  
  // Execution state
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0-100
  
  // Timing
  startTime: DateTime;
  endTime?: DateTime;
  duration?: number; // milliseconds
  
  // Results
  componentResults: ComponentExecutionResult[];
  globalInputs: Record<string, any>;
  finalOutputs: Record<string, any>;
  
  // Error info
  error?: string;
  failedComponentId?: UUID;
  
  // Execution context
  triggeredBy: 'manual' | 'schedule' | 'api' | 'webhook';
  triggeredByUser?: UUID;
  
  // Metadata
  logs: ExecutionLog[];
  metrics: ExecutionMetrics;
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
}

// Execution Logging
export interface ExecutionLog {
  timestamp: DateTime;
  level: 'debug' | 'info' | 'warn' | 'error';
  componentId?: UUID;
  message: string;
  data?: JSONObject;
}

// Execution Metrics
export interface ExecutionMetrics {
  totalComponents: number;
  completedComponents: number;
  failedComponents: number;
  
  // Performance
  averageComponentTime: number;
  slowestComponent?: {
    componentId: UUID;
    executionTime: number;
  };
  
  // Resource usage
  memoryUsage?: number;
  cpuUsage?: number;
}

// Flow Template
export interface FlowTemplate {
  id: UUID;
  name: string;
  description: string;
  category: string;
  
  // Template data
  flowDefinition: Omit<FlowDefinition, 'id' | 'author' | 'createdAt' | 'updatedAt'>;
  
  // Template metadata
  tags: string[];
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  estimatedTime?: number; // minutes
  
  // Usage stats
  useCount: number;
  rating: number;
  
  // Ownership
  author: UUID;
  isPublic: boolean;
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
}