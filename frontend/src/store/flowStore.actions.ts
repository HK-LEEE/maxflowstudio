/**
 * 파일명: flowStore.actions.ts (120줄)
 * 목적: Flow Store의 Flow 관리 액션들
 * 동작 과정:
 * 1. Flow 로드, 저장, 생성 액션
 * 2. Flow 메타데이터 업데이트
 * 3. 실제 API 엔드포인트와 연동
 * 데이터베이스 연동: /api/flows 엔드포인트를 통한 실제 DB 연동
 * 의존성: flowStore.types.ts, flowStore.history.ts
 */

import type { FlowDefinition } from './flowStore.types';
import { saveToHistory, clearHistory } from './flowStore.history';

// Flow 관리 액션 타입
export interface FlowManagementActions {
  loadFlow: (flowId: string) => Promise<void>;
  saveFlow: () => Promise<void>;
  createNewFlow: (name: string, description?: string) => void;
  updateFlowMetadata: (metadata: Partial<Pick<FlowDefinition, 'name' | 'description' | 'globalVariables'>>) => void;
}

// Flow 관리 액션 구현체 생성 함수
export const createFlowManagementActions = (
  set: (partial: any) => void,
  get: () => any
): FlowManagementActions => ({
  
  loadFlow: async (flowId: string) => {
    /*
    Load Flow Process:
    1. Set loading state
    2. Fetch flow from API
    3. Parse and validate flow data
    4. Update store state
    5. Initialize history
    */
    set({ isLoading: true, error: null });
    
    try {
      const response = await fetch(`/api/flows/${flowId}`);
      if (!response.ok) throw new Error('Failed to load flow');
      
      const flowData: FlowDefinition = await response.json();
      
      set({
        currentFlow: flowData,
        nodes: flowData.nodes,
        edges: flowData.edges,
        isDirty: false,
        isLoading: false,
      });
      
      // Initialize history
      saveToHistory(flowData.nodes, flowData.edges);
      
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load flow',
        isLoading: false,
      });
    }
  },
  
  saveFlow: async () => {
    /*
    Save Flow Process:
    1. Validate current flow
    2. Prepare flow data
    3. Send to API
    4. Update local state
    */
    const { currentFlow, nodes, edges } = get();
    if (!currentFlow) return;
    
    set({ isLoading: true, error: null });
    
    try {
      const flowData = {
        ...currentFlow,
        nodes,
        edges,
        updatedAt: new Date(),
      };
      
      const response = await fetch(`/api/flows/${currentFlow.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(flowData),
      });
      
      if (!response.ok) throw new Error('Failed to save flow');
      
      const savedFlow = await response.json();
      
      set({
        currentFlow: savedFlow,
        isDirty: false,
        isLoading: false,
      });
      
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to save flow',
        isLoading: false,
      });
    }
  },
  
  createNewFlow: (name: string, description = '') => {
    /*
    Create New Flow Process:
    1. Generate new flow ID
    2. Initialize flow structure
    3. Clear current state
    4. Set up empty history
    */
    const newFlow: FlowDefinition = {
      id: `flow_${Date.now()}`,
      name,
      description,
      nodes: [],
      edges: [],
      globalVariables: {},
      metadata: {},
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    
    set({
      currentFlow: newFlow,
      nodes: [],
      edges: [],
      selectedNodes: [],
      selectedEdges: [],
      isDirty: false,
      error: null,
    });
    
    // Initialize empty history
    clearHistory();
    saveToHistory([], []);
  },
  
  updateFlowMetadata: (metadata: Partial<Pick<FlowDefinition, 'name' | 'description' | 'globalVariables'>>) => {
    const { currentFlow } = get();
    if (!currentFlow) return;
    
    const updatedFlow = {
      ...currentFlow,
      ...metadata,
      updatedAt: new Date(),
    };
    
    set({
      currentFlow: updatedFlow,
      isDirty: true,
    });
  },
});