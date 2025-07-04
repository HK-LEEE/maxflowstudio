/**
 * 파일명: flowStore.history.ts (60줄)
 * 목적: Flow Store의 Undo/Redo 히스토리 관리
 * 동작 과정:
 * 1. 상태 변경 시 히스토리에 저장
 * 2. Undo/Redo 시 히스토리에서 상태 복원
 * 3. 최대 히스토리 크기 관리
 * 데이터베이스 연동: 메모리에서만 관리, 영구 저장하지 않음
 * 의존성: flowStore.types.ts
 */

import type { FlowNode, FlowEdge } from './flowStore.types';
import type { HistoryState } from './flowStore.state';

// 히스토리 설정
const MAX_HISTORY_SIZE = 50;
let history: HistoryState[] = [];
let historyIndex = -1;

// 히스토리에 현재 상태 저장
export const saveToHistory = (nodes: FlowNode[], edges: FlowEdge[]): void => {
  // Remove future history if we're not at the end
  if (historyIndex < history.length - 1) {
    history = history.slice(0, historyIndex + 1);
  }
  
  // Add new state (deep copy to prevent reference issues)
  history.push({ 
    nodes: JSON.parse(JSON.stringify(nodes)), 
    edges: JSON.parse(JSON.stringify(edges)) 
  });
  
  // Limit history size
  if (history.length > MAX_HISTORY_SIZE) {
    history = history.slice(-MAX_HISTORY_SIZE);
  }
  
  historyIndex = history.length - 1;
};

// Undo 가능 여부 확인
export const canUndo = (): boolean => {
  return historyIndex > 0;
};

// Redo 가능 여부 확인
export const canRedo = (): boolean => {
  return historyIndex < history.length - 1;
};

// Undo 실행
export const undoHistory = (): HistoryState | null => {
  if (!canUndo()) return null;
  
  historyIndex--;
  return history[historyIndex];
};

// Redo 실행
export const redoHistory = (): HistoryState | null => {
  if (!canRedo()) return null;
  
  historyIndex++;
  return history[historyIndex];
};

// 히스토리 초기화
export const clearHistory = (): void => {
  history = [];
  historyIndex = -1;
};