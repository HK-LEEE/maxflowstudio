/**
 * 파일명: index.ts (60줄)
 * 목적: 전체 타입 시스템의 진입점 및 재내보내기
 * 동작 과정:
 * 1. 모든 하위 타입 모듈에서 타입 가져오기
 * 2. 통합된 타입 네임스페이스 제공
 * 3. 타입 재내보내기로 일관된 import 경로 제공
 * 데이터베이스 연동: 모든 테이블 타입의 통합 진입점
 * 의존성: base.ts, components.ts, flow.ts, workspace.ts, user.ts, api.ts
 */

// Re-export all types from sub-modules
export * from './base';
export * from './components';
export * from './flow';
export * from './workspace';
export * from './user';
export * from './api';
export * from './auth';

// Re-export constants for value usage (values, not types)
export { ComponentStatus, InputType, OutputType } from './base';
export { WorkspaceType, PermissionType } from './workspace';

// Re-export type definitions (types only)
export type { 
  UUID, 
  DateTime, 
  JSONValue, 
  JSONObject, 
  JSONArray,
  ComponentStatusType,
  InputTypeType,
  OutputTypeType
} from './base';

export type {
  ComponentDefinition,
  ComponentInstance,
  ComponentConnection,
  ComponentExecutionResult
} from './components';

export type {
  FlowDefinition,
  FlowExecution,
  FlowTemplate
} from './flow';

export type {
  Workspace,
  WorkspaceMember,
  WorkspaceTypeType,
  PermissionTypeType
} from './workspace';

export type {
  User,
  UserSession,
  UserActivity
} from './user';

export type {
  ApiDeployment,
  ApiKey,
  ApiRequestLog
} from './api';