/**
 * 파일명: base.ts (80줄)
 * 목적: 기본 타입 정의 및 공통 유틸리티 타입
 * 동작 과정:
 * 1. 플랫폼 전체에서 사용하는 기본 타입들
 * 2. UUID, DateTime, JSON 관련 타입
 * 3. 컴포넌트 상태 및 입출력 타입 열거형
 * 데이터베이스 연동: 모든 API 응답 데이터 타입의 기반
 * 의존성: 없음 (독립적 기본 타입)
 */

/*
┌──────────────────────────────────────────────────────────────┐
│                    TypeScript Types Flow                    │
│                                                              │
│  [API] → [Response] → [Type Parse] → [Component] → [Render] │
│    ↓       ↓           ↓             ↓           ↓          │
│  백엔드데이터  타입검증    타입변환      컴포넌트     안전렌더링   │
│                                                              │
│  Type Safety: Backend ↔ Frontend ↔ React Flow              │
│  Validation: Runtime Checks + Compile Time Safety          │
└──────────────────────────────────────────────────────────────┘

TypeScript Type Definitions for MAX Flowstudio
Flow: API response → Type validation → Component props → Render safety
*/

// Base types for the platform
export type UUID = string;
export type DateTime = string; // ISO string format
export type JSONValue = string | number | boolean | null | JSONObject | JSONArray;
export type JSONObject = { [key: string]: JSONValue };
export type JSONArray = JSONValue[];

// Component System Types
export const ComponentStatus = {
  IDLE: 'idle',
  VALIDATING: 'validating',
  EXECUTING: 'executing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
} as const;

export type ComponentStatusType = typeof ComponentStatus[keyof typeof ComponentStatus];

export const InputType = {
  TEXT: 'text',
  NUMBER: 'number',
  BOOLEAN: 'boolean',
  ARRAY: 'array',
  OBJECT: 'object',
  FILE: 'file',
  JSON: 'json',
  ANY: 'any',
} as const;

export type InputTypeType = typeof InputType[keyof typeof InputType];

export const OutputType = {
  TEXT: 'text',
  NUMBER: 'number',
  BOOLEAN: 'boolean',
  ARRAY: 'array',
  OBJECT: 'object',
  FILE: 'file',
  JSON: 'json',
  ANY: 'any',
} as const;

export type OutputTypeType = typeof OutputType[keyof typeof OutputType];

// Validation Types
export interface ValidationRule {
  type: 'required' | 'min' | 'max' | 'pattern' | 'custom';
  value?: any;
  message: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings?: string[];
}

// Error Handling Types
export interface ErrorInfo {
  code: string;
  message: string;
  details?: JSONObject;
  timestamp?: DateTime;
}

// Base Response Types  
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ErrorInfo;
  message?: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
  };
}