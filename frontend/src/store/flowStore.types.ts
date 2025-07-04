/**
 * 파일명: flowStore.types.ts (90줄)
 * 목적: Flow Store의 모든 타입 정의
 * 동작 과정:
 * 1. React Flow 타입 확장
 * 2. Flow 시스템 타입 정의
 * 3. Store 상태 및 액션 타입 정의
 * 데이터베이스 연동: flows, flow_nodes, flow_edges 테이블 매핑
 * 의존성: reactflow 라이브러리 타입
 */

import type { Node, Edge, Connection, XYPosition, NodeChange, EdgeChange } from 'reactflow';

// Flow Node 타입 - React Flow Node 확장
export interface FlowNode extends Node {
  data: {
    label: string;
    componentType: string;
    config: Record<string, any>;
    inputs: Record<string, any>;
    outputs: Record<string, any>;
    status: 'idle' | 'running' | 'completed' | 'failed';
    executionTime?: number;
    error?: string;
  };
}

// Flow Edge 타입 - React Flow Edge 확장
export interface FlowEdge extends Omit<Edge, 'id' | 'source' | 'target'> {
  id: string;
  source: string;
  target: string;
  data?: {
    sourceHandle: string;
    targetHandle: string;
    dataType?: string;
  };
}

// 실행 결과 타입
export interface ExecutionResult {
  nodeId: string;
  outputs: Record<string, any>;
  status: 'completed' | 'failed';
  executionTime: number;
  error?: string;
}

// Flow 실행 정보 타입
export interface FlowExecution {
  id: string;
  flowId: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  startTime: Date;
  endTime?: Date;
  nodeResults: ExecutionResult[];
  globalInputs: Record<string, any>;
}

// Flow 정의 타입
export interface FlowDefinition {
  id: string;
  name: string;
  description: string;
  nodes: FlowNode[];
  edges: FlowEdge[];
  globalVariables: Record<string, any>;
  metadata: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
}

// Store 상태 타입
export interface FlowStoreState {
  // Current flow editing state
  currentFlow: FlowDefinition | null;
  nodes: FlowNode[];
  edges: FlowEdge[];
  
  // UI state
  selectedNodes: string[];
  selectedEdges: string[];
  isDirty: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Execution state
  currentExecution: FlowExecution | null;
  isExecuting: boolean;
  executionHistory: FlowExecution[];
  
  // Node palette and types
  availableNodeTypes: Record<string, any>;
  
  // Viewport state
  viewport: { x: number; y: number; zoom: number };
}

// Store 액션 타입
export interface FlowStoreActions {
  // Flow management
  loadFlow: (flowId: string) => Promise<void>;
  saveFlow: () => Promise<void>;
  createNewFlow: (name: string, description?: string) => void;
  updateFlowMetadata: (metadata: Partial<Pick<FlowDefinition, 'name' | 'description' | 'globalVariables'>>) => void;
  
  // Node operations
  addNode: (nodeType: string, position: XYPosition) => void;
  updateNode: (nodeId: string, updates: Partial<FlowNode['data']>) => void;
  deleteNode: (nodeId: string) => void;
  duplicateNode: (nodeId: string) => void;
  
  // Edge operations
  onConnect: (connection: Connection) => void;
  updateEdge: (edgeId: string, updates: Partial<FlowEdge['data']>) => void;
  deleteEdge: (edgeId: string) => void;
  
  // Selection operations
  selectNode: (nodeId: string, multi?: boolean) => void;
  selectEdge: (edgeId: string, multi?: boolean) => void;
  clearSelection: () => void;
  selectAll: () => void;
  
  // React Flow handlers
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  
  // Execution operations
  executeFlow: (globalInputs?: Record<string, any>) => Promise<void>;
  cancelExecution: () => void;
  stepExecute: (nodeId: string) => Promise<void>;
  
  // Real-time updates during execution
  updateNodeExecutionStatus: (nodeId: string, status: FlowNode['data']['status'], result?: any) => void;
  
  // Utility actions
  setError: (error: string | null) => void;
  setLoading: (loading: boolean) => void;
  setViewport: (viewport: { x: number; y: number; zoom: number }) => void;
  
  // Validation
  validateFlow: () => { isValid: boolean; errors: string[] };
  
  // Undo/Redo functionality
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
}

// 전체 Store 타입
export type FlowStore = FlowStoreState & FlowStoreActions;