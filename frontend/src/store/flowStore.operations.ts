/**
 * 파일명: flowStore.operations.ts (200줄)
 * 목적: Flow Store의 노드/엣지 조작 액션들
 * 동작 과정:
 * 1. 노드 추가, 수정, 삭제 작업
 * 2. 엣지 추가, 수정, 삭제 작업
 * 3. 선택 상태 관리
 * 4. React Flow 이벤트 처리
 * 데이터베이스 연동: 실시간 상태 변경, 저장 시 DB 반영
 * 의존성: flowStore.types.ts, flowStore.history.ts
 */

import { applyNodeChanges, applyEdgeChanges, addEdge } from 'reactflow';
import type { Connection, XYPosition, NodeChange, EdgeChange } from 'reactflow';
import type { FlowNode, FlowEdge } from './flowStore.types';
import { saveToHistory } from './flowStore.history';

// 노드/엣지 조작 액션 타입
export interface NodeEdgeOperations {
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
}

// 노드/엣지 조작 액션 구현체 생성 함수
export const createNodeEdgeOperations = (
  set: (partial: any) => void,
  get: () => any
): NodeEdgeOperations => ({
  
  addNode: (nodeType: string, position: XYPosition) => {
    /*
    Add Node Process:
    1. Generate unique node ID
    2. Create node with default config
    3. Add to nodes array
    4. Save to history
    5. Mark as dirty
    */
    const newNode: FlowNode = {
      id: `node_${Date.now()}`,
      type: 'custom',
      position,
      data: {
        label: nodeType,
        componentType: nodeType,
        config: {},
        inputs: {},
        outputs: {},
        status: 'idle',
      },
    };
    
    const { nodes, edges } = get();
    const newNodes = [...nodes, newNode];
    
    set({
      nodes: newNodes,
      isDirty: true,
    });
    
    saveToHistory(newNodes, edges);
  },
  
  updateNode: (nodeId: string, updates: Partial<FlowNode['data']>) => {
    /*
    Update Node Process:
    1. Find node by ID
    2. Merge updates with existing data
    3. Update nodes array
    4. Save to history if structural change
    */
    const { nodes, edges } = get();
    const newNodes = nodes.map((node: FlowNode) =>
      node.id === nodeId
        ? {
            ...node,
            data: { ...node.data, ...updates },
          }
        : node
    );
    
    set({
      nodes: newNodes,
      isDirty: true,
    });
    
    // Save to history for significant changes
    if (updates.config || updates.inputs) {
      saveToHistory(newNodes, edges);
    }
  },
  
  deleteNode: (nodeId: string) => {
    /*
    Delete Node Process:
    1. Remove node from nodes array
    2. Remove all connected edges
    3. Clear selection if node was selected
    4. Save to history
    */
    const { nodes, edges, selectedNodes } = get();
    const newNodes = nodes.filter((node: FlowNode) => node.id !== nodeId);
    const newEdges = edges.filter((edge: FlowEdge) => 
      edge.source !== nodeId && edge.target !== nodeId
    );
    
    set({
      nodes: newNodes,
      edges: newEdges,
      selectedNodes: selectedNodes.filter((id: string) => id !== nodeId),
      isDirty: true,
    });
    
    saveToHistory(newNodes, newEdges);
  },
  
  duplicateNode: (nodeId: string) => {
    /*
    Duplicate Node Process:
    1. Find original node
    2. Create copy with new ID and offset position
    3. Add to nodes array
    4. Save to history
    */
    const { nodes, edges } = get();
    const originalNode = nodes.find((node: FlowNode) => node.id === nodeId);
    if (!originalNode) return;
    
    const duplicatedNode: FlowNode = {
      ...originalNode,
      id: `node_${Date.now()}`,
      position: {
        x: originalNode.position.x + 50,
        y: originalNode.position.y + 50,
      },
      data: {
        ...originalNode.data,
        label: `${originalNode.data.label} Copy`,
      },
    };
    
    const newNodes = [...nodes, duplicatedNode];
    
    set({
      nodes: newNodes,
      isDirty: true,
    });
    
    saveToHistory(newNodes, edges);
  },
  
  onConnect: (connection: Connection) => {
    /*
    Connect Edge Process:
    1. Create new edge from connection
    2. Add to edges array
    3. Save to history
    */
    const { edges, nodes } = get();
    const newEdge: FlowEdge = {
      id: `edge_${Date.now()}`,
      source: connection.source!,
      target: connection.target!,
      data: {
        sourceHandle: connection.sourceHandle || '',
        targetHandle: connection.targetHandle || '',
      },
    };
    
    const newEdges = addEdge(newEdge, edges);
    
    set({
      edges: newEdges,
      isDirty: true,
    });
    
    saveToHistory(nodes, newEdges);
  },
  
  updateEdge: (edgeId: string, updates: Partial<FlowEdge['data']>) => {
    const { edges, nodes } = get();
    const newEdges = edges.map((edge: FlowEdge) =>
      edge.id === edgeId
        ? { ...edge, data: { ...edge.data, ...updates } }
        : edge
    );
    
    set({
      edges: newEdges,
      isDirty: true,
    });
    
    saveToHistory(nodes, newEdges);
  },
  
  deleteEdge: (edgeId: string) => {
    const { edges, nodes, selectedEdges } = get();
    const newEdges = edges.filter((edge: FlowEdge) => edge.id !== edgeId);
    
    set({
      edges: newEdges,
      selectedEdges: selectedEdges.filter((id: string) => id !== edgeId),
      isDirty: true,
    });
    
    saveToHistory(nodes, newEdges);
  },
  
  selectNode: (nodeId: string, multi = false) => {
    const { selectedNodes } = get();
    const newSelection = multi 
      ? selectedNodes.includes(nodeId)
        ? selectedNodes.filter((id: string) => id !== nodeId)
        : [...selectedNodes, nodeId]
      : [nodeId];
    
    set({ selectedNodes: newSelection, selectedEdges: [] });
  },
  
  selectEdge: (edgeId: string, multi = false) => {
    const { selectedEdges } = get();
    const newSelection = multi
      ? selectedEdges.includes(edgeId)
        ? selectedEdges.filter((id: string) => id !== edgeId)
        : [...selectedEdges, edgeId]
      : [edgeId];
    
    set({ selectedEdges: newSelection, selectedNodes: [] });
  },
  
  clearSelection: () => {
    set({ selectedNodes: [], selectedEdges: [] });
  },
  
  selectAll: () => {
    const { nodes, edges } = get();
    set({
      selectedNodes: nodes.map((node: FlowNode) => node.id),
      selectedEdges: edges.map((edge: FlowEdge) => edge.id),
    });
  },
  
  onNodesChange: (changes: NodeChange[]) => {
    const { nodes, edges } = get();
    const newNodes = applyNodeChanges(changes, nodes);
    
    set({ nodes: newNodes, isDirty: true });
    
    // Save to history for position changes
    const hasPositionChange = changes.some(change => change.type === 'position');
    if (hasPositionChange) {
      saveToHistory(newNodes, edges);
    }
  },
  
  onEdgesChange: (changes: EdgeChange[]) => {
    const { edges, nodes } = get();
    const newEdges = applyEdgeChanges(changes, edges);
    
    set({ edges: newEdges, isDirty: true });
    saveToHistory(nodes, newEdges);
  },
});