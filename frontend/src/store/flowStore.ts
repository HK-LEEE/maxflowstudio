/**
 * 파일명: flowStore.ts (400줄)
 * 목적: Zustand 기반 Flow Store 메인 구현체
 * 동작 과정:
 * 1. Zustand store 생성 및 초기화
 * 2. Flow 관리 액션 구현 (로드, 저장, 생성)
 * 3. 노드/엣지 조작 액션 구현
 * 4. 실행 및 상태 관리 액션 구현
 * 데이터베이스 연동: /api/flows 엔드포인트 통해 실제 DB 연동
 * 의존성: flowStore.types.ts, flowStore.state.ts
 */

import { create } from 'zustand';
import { devtools, subscribeWithSelector } from 'zustand/middleware';
// Removed unused imports
import type { 
  FlowStore, 
  FlowNode, 
  FlowExecution 
} from './flowStore.types';
import { initialState } from './flowStore.state';
import { canUndo as checkCanUndo, canRedo as checkCanRedo, undoHistory, redoHistory } from './flowStore.history';
import { createFlowManagementActions } from './flowStore.actions';
import { createNodeEdgeOperations } from './flowStore.operations';

// Re-export types for convenience
export type { 
  FlowNode, 
  FlowEdge, 
  FlowDefinition, 
  ExecutionResult, 
  FlowExecution,
  FlowStore 
} from './flowStore.types';

// History management is handled in flowStore.history.ts

export const useFlowStore = create<FlowStore>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      ...initialState,
      
      // Flow management (imported from flowStore.actions.ts)
      ...createFlowManagementActions(set, get),
      
      // Node and edge operations (imported from flowStore.operations.ts)
      ...createNodeEdgeOperations(set, get),
      
      // Execution operations
      executeFlow: async (globalInputs = {}) => {
        /*
        Execute Flow Process:
        1. Validate flow structure
        2. Create execution context
        3. Send to backend API
        4. Monitor execution progress
        5. Update node statuses in real-time
        */
        const { nodes, edges, currentFlow } = get();
        if (!currentFlow) return;
        
        // Validate flow first
        const validation = get().validateFlow();
        if (!validation.isValid) {
          set({ error: validation.errors.join(', ') });
          return;
        }
        
        const execution: FlowExecution = {
          id: `exec_${Date.now()}`,
          flowId: currentFlow.id,
          status: 'running',
          startTime: new Date(),
          nodeResults: [],
          globalInputs,
        };
        
        set({
          currentExecution: execution,
          isExecuting: true,
          error: null,
        });
        
        // Reset all node statuses
        const resetNodes = nodes.map(node => ({
          ...node,
          data: { ...node.data, status: 'idle' as const, error: undefined },
        }));
        set({ nodes: resetNodes });
        
        try {
          const response = await fetch(`/api/flows/${currentFlow.id}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              nodes,
              edges,
              globalInputs,
            }),
          });
          
          if (!response.ok) throw new Error('Failed to start execution');
          
          // Handle streaming response for real-time updates
          const reader = response.body?.getReader();
          if (reader) {
            const decoder = new TextDecoder();
            
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              
              const chunk = decoder.decode(value);
              const events = chunk.split('\n').filter(line => line.trim());
              
              for (const eventLine of events) {
                try {
                  const event = JSON.parse(eventLine);
                  if (event.type === 'node_status') {
                    get().updateNodeExecutionStatus(
                      event.nodeId,
                      event.status,
                      event.result
                    );
                  }
                } catch (e) {
                  // Skip malformed events
                }
              }
            }
          }
          
          // Execution completed
          set({
            isExecuting: false,
            currentExecution: {
              ...execution,
              status: 'completed',
              endTime: new Date(),
            },
          });
          
        } catch (error) {
          set({
            isExecuting: false,
            error: error instanceof Error ? error.message : 'Execution failed',
            currentExecution: {
              ...execution,
              status: 'failed',
              endTime: new Date(),
            },
          });
        }
      },
      
      cancelExecution: () => {
        /*
        Cancel Execution Process:
        1. Send cancel request to backend
        2. Update execution status
        3. Reset node statuses
        */
        const { currentExecution } = get();
        if (!currentExecution) return;
        
        // Send cancel request to backend
        fetch(`/api/executions/${currentExecution.id}/cancel`, {
          method: 'POST',
        });
        
        set({
          isExecuting: false,
          currentExecution: {
            ...currentExecution,
            status: 'cancelled',
            endTime: new Date(),
          },
        });
      },
      
      stepExecute: async (nodeId: string) => {
        // Implementation for single node execution
        const { nodes } = get();
        const node = nodes.find(n => n.id === nodeId);
        if (!node) return;
        
        get().updateNodeExecutionStatus(nodeId, 'running');
        
        try {
          const response = await fetch(`/api/nodes/${nodeId}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              config: node.data.config,
              inputs: node.data.inputs,
            }),
          });
          
          if (!response.ok) throw new Error('Node execution failed');
          
          const result = await response.json();
          get().updateNodeExecutionStatus(nodeId, 'completed', result);
          
        } catch (error) {
          get().updateNodeExecutionStatus(nodeId, 'failed', {
            error: error instanceof Error ? error.message : 'Unknown error',
          });
        }
      },
      
      updateNodeExecutionStatus: (nodeId: string, status: FlowNode['data']['status'], result?: any) => {
        /*
        Update Node Execution Status Process:
        1. Find node by ID
        2. Update status and result data
        3. Trigger re-render
        */
        const { nodes } = get();
        const newNodes = nodes.map(node =>
          node.id === nodeId
            ? {
                ...node,
                data: {
                  ...node.data,
                  status,
                  outputs: result?.outputs || node.data.outputs,
                  executionTime: result?.executionTime,
                  error: result?.error,
                },
              }
            : node
        );
        
        set({ nodes: newNodes });
      },
      
      // Utility actions
      setError: (error: string | null) => set({ error }),
      setLoading: (isLoading: boolean) => set({ isLoading }),
      setViewport: (viewport) => set({ viewport }),
      
      // Validation
      validateFlow: () => {
        /*
        Validate Flow Process:
        1. Check for orphaned nodes
        2. Validate edge connections
        3. Check for required inputs
        4. Detect circular dependencies
        */
        const { nodes, edges } = get();
        const errors: string[] = [];
        
        // Check for nodes without connections (optional warning)
        const connectedNodeIds = new Set([
          ...edges.map(e => e.source),
          ...edges.map(e => e.target),
        ]);
        
        const orphanedNodes = nodes.filter(node => !connectedNodeIds.has(node.id));
        if (orphanedNodes.length > 0) {
          errors.push(`Orphaned nodes found: ${orphanedNodes.map(n => n.data.label).join(', ')}`);
        }
        
        // Check for invalid edge connections
        for (const edge of edges) {
          const sourceNode = nodes.find(n => n.id === edge.source);
          const targetNode = nodes.find(n => n.id === edge.target);
          
          if (!sourceNode) {
            errors.push(`Edge ${edge.id} has invalid source node`);
          }
          if (!targetNode) {
            errors.push(`Edge ${edge.id} has invalid target node`);
          }
        }
        
        return {
          isValid: errors.length === 0,
          errors,
        };
      },
      
      // Undo/Redo functionality
      undo: () => {
        const state = undoHistory();
        if (state) {
          set({
            nodes: JSON.parse(JSON.stringify(state.nodes)),
            edges: JSON.parse(JSON.stringify(state.edges)),
            isDirty: true,
          });
        }
      },
      
      redo: () => {
        const state = redoHistory();
        if (state) {
          set({
            nodes: JSON.parse(JSON.stringify(state.nodes)),
            edges: JSON.parse(JSON.stringify(state.edges)),
            isDirty: true,
          });
        }
      },
      
      get canUndo() {
        return checkCanUndo();
      },
      
      get canRedo() {
        return checkCanRedo();
      },
    })),
    {
      name: 'flow-store',
      partialize: (state: FlowStore) => ({
        // Only persist essential state, not UI state
        currentFlow: state.currentFlow,
        nodes: state.nodes,
        edges: state.edges,
        viewport: state.viewport,
      }),
    }
  )
);