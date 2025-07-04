/**
 * 파일명: components.ts (120줄)
 * 목적: Flow 컴포넌트 관련 타입 정의
 * 동작 과정:
 * 1. Flow 컴포넌트 인터페이스 정의
 * 2. 입출력 포트 및 연결 정보 타입
 * 3. 컴포넌트 실행 및 상태 관리 타입
 * 데이터베이스 연동: components 테이블과 매핑
 * 의존성: base.ts
 */

import type { 
  UUID, 
  DateTime, 
  JSONObject, 
  ComponentStatusType, 
  InputTypeType, 
  OutputTypeType, 
  ValidationRule 
} from './base';

// Component Input/Output Port Types
export interface InputPort {
  id: UUID;
  name: string;
  type: InputTypeType;
  required: boolean;
  description?: string;
  defaultValue?: any;
  validation?: ValidationRule[];
}

export interface OutputPort {
  id: UUID;
  name: string;
  type: OutputTypeType;
  description?: string;
}

// Component Configuration
export interface ComponentConfig {
  [key: string]: any;
}

// Component Definition
export interface ComponentDefinition {
  id: UUID;
  name: string;
  type: string;
  category: string;
  description: string;
  version: string;
  author?: string;
  
  // Component interface
  inputs: InputPort[];
  outputs: OutputPort[];
  
  // Configuration schema
  configSchema?: JSONObject;
  defaultConfig?: ComponentConfig;
  
  // Metadata
  tags: string[];
  documentation?: string;
  examples?: JSONObject[];
  
  // UI properties
  icon?: string;
  color?: string;
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
}

// Runtime Component Instance
export interface ComponentInstance {
  id: UUID;
  definitionId: UUID;
  flowId: UUID;
  
  // Current state
  status: ComponentStatusType;
  config: ComponentConfig;
  
  // Runtime data
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  
  // Execution info
  executionTime?: number;
  error?: string;
  lastExecuted?: DateTime;
  
  // Position in flow
  position: {
    x: number;
    y: number;
  };
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
}

// Component Connection (Edge)
export interface ComponentConnection {
  id: UUID;
  flowId: UUID;
  
  // Connection endpoints
  sourceComponentId: UUID;
  sourcePortId: UUID;
  targetComponentId: UUID;
  targetPortId: UUID;
  
  // Connection metadata
  label?: string;
  dataType?: string;
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
}

// Component Execution Result
export interface ComponentExecutionResult {
  componentId: UUID;
  status: ComponentStatusType;
  outputs: Record<string, any>;
  executionTime: number;
  error?: string;
  logs?: string[];
  metadata?: JSONObject;
}

// Component Library
export interface ComponentLibrary {
  id: UUID;
  name: string;
  description: string;
  version: string;
  author: string;
  
  // Components in this library
  components: ComponentDefinition[];
  
  // Library metadata
  tags: string[];
  isPublic: boolean;
  downloadCount: number;
  
  // Timestamps
  createdAt: DateTime;
  updatedAt: DateTime;
}