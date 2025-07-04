/**
 * 파일명: flowStore.state.ts (30줄)
 * 목적: Flow Store의 초기 상태 정의
 * 동작 과정:
 * 1. Store 초기 상태 설정
 * 2. 기본값 정의
 * 데이터베이스 연동: 빈 상태로 시작, 로드 시 실제 데이터로 채워짐
 * 의존성: flowStore.types.ts
 */

import type { FlowStoreState } from './flowStore.types';

// Flow Store 초기 상태
export const initialState: FlowStoreState = {
  currentFlow: null,
  nodes: [],
  edges: [],
  selectedNodes: [],
  selectedEdges: [],
  isDirty: false,
  isLoading: false,
  error: null,
  currentExecution: null,
  isExecuting: false,
  executionHistory: [],
  availableNodeTypes: {},
  viewport: { x: 0, y: 0, zoom: 1 },
};

// History 관리를 위한 상태 타입
export interface HistoryState {
  nodes: import('./flowStore.types').FlowNode[];
  edges: import('./flowStore.types').FlowEdge[];
}