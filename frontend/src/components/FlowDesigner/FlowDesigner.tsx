/**
 * Flow Designer Component
 * Main visual workflow editor using React Flow
 */

import React, { useCallback, useRef, useState, useEffect, useMemo } from 'react';
import ReactFlow, {
  addEdge,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  ReactFlowProvider,
} from 'reactflow';
import 'reactflow/dist/style.css';
import type {
  Node,
  Edge,
  Connection,
  ReactFlowInstance,
} from 'reactflow';
import { Button, Space, message, Input, Modal, Typography, Drawer, List, Tag, Tooltip, Badge } from 'antd';
import { useLayout } from '../../contexts/LayoutContext';
import { 
  SaveOutlined, 
  EditOutlined,
  BugOutlined,
  RocketOutlined,
  HistoryOutlined,
  CloseOutlined,
  DeleteOutlined,
  DoubleLeftOutlined,
  DoubleRightOutlined,
  SettingOutlined,
  CloudOutlined,
  ApiOutlined,
  CopyOutlined,
  FileTextOutlined,
  CloudUploadOutlined
} from '@ant-design/icons';

import { NodePalette } from './NodePalette';
import { NodePropertiesPanel } from './NodePropertiesPanel';
import { CustomNode } from './CustomNode';
import { ChatPanel } from './ChatPanel';
import SaveAsModal from './SaveAsModal';
import TemplateLoaderModal from './TemplateLoaderModal';
import SaveAsTemplateModal from './SaveAsTemplateModal';
import './FlowDesigner.css';

// Custom node types - defined outside component to prevent recreation
const nodeTypes = {
  custom: CustomNode,
} as const;

const initialNodes: Node[] = [
  {
    id: '1',
    type: 'custom',
    position: { x: 250, y: 250 },
    data: {
      type: 'input',
      label: 'Input',
      description: 'Flow input node',
    },
  },
];

const initialEdges: Edge[] = [];

interface FlowDesignerProps {
  flowId?: string;
  flowName?: string;
  flowDefinition?: any;
  onSave?: (flowData: any) => void;
  onRun?: () => void;
  onUpdateFlowName?: (newName: string) => void;
}

interface FlowVersion {
  id: string;
  version_number: number;
  version_name?: string;
  description?: string;
  change_summary?: string;
  created_at: string;
  created_by: string;
  is_published: boolean;
}

export const FlowDesigner: React.FC<FlowDesignerProps> = ({
  flowId,
  flowName,
  flowDefinition,
  onSave,
  onRun,
  onUpdateFlowName,
}) => {
  const { sidebarCollapsed } = useLayout();
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);
  
  // Initialize nodes and edges from flowDefinition or use defaults
  const getInitialNodes = () => {
    if (flowDefinition?.nodes && flowDefinition.nodes.length > 0) {
      return flowDefinition.nodes.map((node: any) => ({
        ...node,
        type: 'custom', // Ensure all nodes use custom type
      }));
    }
    return initialNodes;
  };

  const getInitialEdges = () => {
    if (flowDefinition?.edges) {
      return flowDefinition.edges;
    }
    return initialEdges;
  };

  const [nodes, setNodes, onNodesChange] = useNodesState(getInitialNodes());
  const [edges, setEdges, onEdgesChange] = useEdgesState(getInitialEdges());
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null);
  const [highlightedNodes, setHighlightedNodes] = useState<Set<string>>(new Set());
  const [highlightedEdges, setHighlightedEdges] = useState<Set<string>>(new Set());
  const [connectingNode, setConnectingNode] = useState<string | null>(null);
  const [editingFlowName, setEditingFlowName] = useState(false);
  const [tempFlowName, setTempFlowName] = useState(flowName || 'Untitled Flow');
  const [versionsDrawerVisible, setVersionsDrawerVisible] = useState(false);
  const [versions, setVersions] = useState<FlowVersion[]>([]);
  const [chatPanelVisible, setChatPanelVisible] = useState(false);
  const [saveAsModalVisible, setSaveAsModalVisible] = useState(false);
  const [templateLoaderVisible, setTemplateLoaderVisible] = useState(false);
  const [saveAsTemplateModalVisible, setSaveAsTemplateModalVisible] = useState(false);
  const [executingNodes, setExecutingNodes] = useState<Set<string>>(new Set());
  const [completedNodes, setCompletedNodes] = useState<Set<string>>(new Set());
  const [errorNodes, setErrorNodes] = useState<Set<string>>(new Set());
  const [copiedNode, setCopiedNode] = useState<Node | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  // 3단계 패널 상태: 0=닫기, 1=좁게(320px), 2=넓게(640px)
  const [propertiesPanelState, setPropertiesPanelState] = useState<number>(() => {
    const saved = localStorage.getItem('flowDesigner.propertiesPanelState');
    return saved ? parseInt(saved, 10) : 1; // 기본값: 좁게
  });
  
  // Canvas bounds for movement limitation
  const [canvasBounds, setCanvasBounds] = useState({ 
    minX: -1000, maxX: 1000, minY: -1000, maxY: 1000 
  });
  
  // Deployment state
  const [deployments, setDeployments] = useState<any[]>([]);
  const [deploymentsDrawerVisible, setDeploymentsDrawerVisible] = useState(false);

  const getPanelWidth = (state: number) => {
    switch (state) {
      case 0: return 0; // 닫기
      case 1: return 320; // 좁게
      case 2: return 640; // 넓게
      default: return 320;
    }
  };

  // Calculate canvas bounds based on node positions
  const calculateCanvasBounds = useCallback(() => {
    if (nodes.length === 0) {
      // No nodes - allow reasonable movement for initial setup
      setCanvasBounds({ minX: -2000, maxX: 2000, minY: -2000, maxY: 2000 });
      return;
    }

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    
    nodes.forEach(node => {
      const x = node.position.x;
      const y = node.position.y;
      const nodeWidth = 250; // Approximate node width with some margin
      const nodeHeight = 150; // Approximate node height with some margin
      
      minX = Math.min(minX, x - nodeWidth / 2);
      maxX = Math.max(maxX, x + nodeWidth / 2);
      minY = Math.min(minY, y - nodeHeight / 2);
      maxY = Math.max(maxY, y + nodeHeight / 2);
    });
    
    // Add generous padding for comfortable panning
    // This allows users to pan beyond nodes to center them in viewport
    const padding = 1000;
    
    setCanvasBounds({
      minX: minX - padding,
      maxX: maxX + padding,
      minY: minY - padding,
      maxY: maxY + padding
    });
  }, [nodes]);

  // Update canvas bounds when nodes change
  useEffect(() => {
    calculateCanvasBounds();
  }, [nodes, calculateCanvasBounds]);

  // Update nodes and edges when flowDefinition changes
  useEffect(() => {
    if (flowDefinition) {
      if (flowDefinition.nodes && flowDefinition.nodes.length > 0) {
        const updatedNodes = flowDefinition.nodes.map((node: any) => ({
          ...node,
          // Keep the original node type in data for backend processing
          // but use 'custom' as the ReactFlow type for UI rendering
          type: 'custom',
          data: {
            ...node.data,
            // Ensure the actual node type is preserved in data.type
            type: node.data?.type || node.type || 'unknown'
          }
        }));
        setNodes(updatedNodes);
      }
      if (flowDefinition.edges) {
        setEdges(flowDefinition.edges);
      }
    }
  }, [flowDefinition, setNodes, setEdges]);

  // Update flow name when it changes
  useEffect(() => {
    setTempFlowName(flowName || 'Untitled Flow');
  }, [flowName]);

  // Check if current user is admin
  useEffect(() => {
    const checkAdminStatus = async () => {
      try {
        const { authService } = await import('../../services/auth');
        const user = authService.getStoredUser();
        setIsAdmin(user?.is_superuser === true);
      } catch (error) {
        console.error('Failed to check admin status:', error);
        setIsAdmin(false);
      }
    };

    checkAdminStatus();
  }, []);

  const fetchVersions = async () => {
    if (!flowId || flowId === 'new') return;
    
    try {
      const response = await fetch(`/api/flows/${flowId}/versions`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });
      
      if (response.ok) {
        const versionsData = await response.json();
        setVersions(versionsData);
      }
    } catch (error) {
      console.error('Failed to fetch versions:', error);
    }
  };

  const fetchDeployments = async () => {
    if (!flowId || flowId === 'new') return;
    
    try {
      // Use trailing slash to avoid 307 redirect and import auth utility
      const { ensureValidToken } = await import('../../utils/auth');
      const token = await ensureValidToken();
      
      if (!token) {
        console.error('🚫 No valid token available for deployment fetch');
        message.error('Authentication required to fetch deployments');
        return;
      }

      console.log(`🔍 Fetching deployments for flow: ${flowId}`);
      const response = await fetch(`/api/deployments/?flow_id=${flowId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const deploymentsData = await response.json();
        console.log(`📦 Found ${deploymentsData.length} deployments for flow ${flowId}:`, deploymentsData);
        setDeployments(deploymentsData);
      } else {
        const errorText = await response.text();
        console.error('❌ Failed to fetch deployments:', {
          status: response.status,
          statusText: response.statusText,
          error: errorText,
          flowId
        });
        message.error(`Failed to fetch deployments (${response.status})`);
      }
    } catch (error) {
      console.error('❌ Failed to fetch deployments:', error);
      message.error('Network error while fetching deployments');
    }
  };

  // Fetch versions and deployments when flowId changes
  useEffect(() => {
    if (flowId && flowId !== 'new') {
      fetchVersions();
      fetchDeployments();
    }
  }, [flowId]);

  const handleLoadVersion = async (versionNumber: number) => {
    if (!flowId || flowId === 'new') return;
    
    try {
      const response = await fetch(`/api/flows/${flowId}/versions/${versionNumber}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });
      
      if (response.ok) {
        const versionData = await response.json();
        if (versionData.definition) {
          // Update nodes and edges with the version definition
          if (versionData.definition.nodes) {
            const updatedNodes = versionData.definition.nodes.map((node: any) => ({
              ...node,
              type: 'custom',
            }));
            setNodes(updatedNodes);
          }
          if (versionData.definition.edges) {
            setEdges(versionData.definition.edges);
          }
        }
        setVersionsDrawerVisible(false);
        message.success(`Loaded version ${versionNumber}`);
      }
    } catch (error) {
      console.error('Failed to load version:', error);
      message.error('Failed to load version');
    }
  };

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) => addEdge({
        ...params,
        animated: true,
        style: { stroke: '#3b82f6', strokeWidth: 2 },
        type: 'smoothstep',
      }, eds));
      setConnectingNode(null);
      message.success('Nodes connected successfully');
    },
    [setEdges]
  );

  const onConnectStart = useCallback((_: any, { nodeId }: { nodeId: string }) => {
    setConnectingNode(nodeId);
  }, []);

  const onConnectEnd = useCallback(() => {
    setConnectingNode(null);
  }, []);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      const type = event.dataTransfer.getData('application/reactflow');
      const label = event.dataTransfer.getData('application/reactflow-label');

      if (typeof type === 'undefined' || !type) {
        return;
      }

      if (reactFlowWrapper.current && reactFlowInstance) {
        const position = reactFlowInstance.screenToFlowPosition({
          x: event.clientX,
          y: event.clientY,
        });

        // Default config for template nodes
        const defaultConfig = type === 'template' ? {
          template: '안녕하세요 {Variable1}님, 오늘의 주제는 {Variable2}입니다.',
          template_mode: 'simple',
          undefined_behavior: 'empty',
          strip_whitespace: false
        } : {};

        const newNode: Node = {
          id: `${Date.now()}`,
          type: 'custom',
          position,
          data: {
            type,
            label,
            description: `${label} node`,
            config: defaultConfig,
          },
        };

        setNodes((nds) => nds.concat(newNode));
      }
    },
    [reactFlowInstance, setNodes]
  );

  // Find connected nodes and edges for a given node
  const findConnectedElements = useCallback((nodeId: string) => {
    const connectedNodes = new Set<string>();
    const connectedEdges = new Set<string>();
    
    connectedNodes.add(nodeId); // Include the clicked node itself
    
    edges.forEach(edge => {
      if (edge.source === nodeId || edge.target === nodeId) {
        connectedEdges.add(edge.id);
        connectedNodes.add(edge.source);
        connectedNodes.add(edge.target);
      }
    });
    
    return { connectedNodes, connectedEdges };
  }, [edges]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
    setSelectedEdgeId(null);
    
    // Highlight connected elements
    const { connectedNodes, connectedEdges } = findConnectedElements(node.id);
    setHighlightedNodes(connectedNodes);
    setHighlightedEdges(connectedEdges);
  }, [findConnectedElements]);

  const handleDeleteEdge = useCallback((edgeId: string) => {
    setEdges((edges) => edges.filter((edge) => edge.id !== edgeId));
    setSelectedEdgeId(null);
    setHighlightedNodes(new Set());
    setHighlightedEdges(new Set());
    message.success('연결이 삭제되었습니다');
  }, [setEdges]);

  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setSelectedEdgeId(edge.id);
    setSelectedNodeId(null);
    
    // Highlight connected nodes and the clicked edge
    const connectedNodes = new Set([edge.source, edge.target]);
    const connectedEdges = new Set([edge.id]);
    
    setHighlightedNodes(connectedNodes);
    setHighlightedEdges(connectedEdges);
  }, []);

  const onEdgeDoubleClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    handleDeleteEdge(edge.id);
  }, [handleDeleteEdge]);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedEdgeId(null);
    setHighlightedNodes(new Set());
    setHighlightedEdges(new Set());
  }, []);

  const handleDeleteNode = useCallback((nodeId: string) => {
    setNodes((nds) => nds.filter((node) => node.id !== nodeId));
    setEdges((eds) => eds.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
    setSelectedNodeId(null);
    setHighlightedNodes(new Set());
    setHighlightedEdges(new Set());
    message.success('노드가 삭제되었습니다');
  }, [setNodes, setEdges]);

  const handleDuplicateNode = useCallback((nodeId: string) => {
    const nodeToDuplicate = nodes.find(n => n.id === nodeId);
    if (nodeToDuplicate) {
      const newNode: Node = {
        ...nodeToDuplicate,
        id: `${Date.now()}`,
        position: {
          x: nodeToDuplicate.position.x + 50,
          y: nodeToDuplicate.position.y + 50,
        },
        data: {
          ...nodeToDuplicate.data,
          label: `${nodeToDuplicate.data.label} Copy`,
        },
      };
      setNodes((nds) => [...nds, newNode]);
      message.success('노드가 복제되었습니다');
    }
  }, [nodes, setNodes]);

  const handleOpenNodeProperties = useCallback((nodeId: string) => {
    setSelectedNodeId(nodeId);
    // Properties panel will automatically show when selectedNodeId changes
  }, []);

  const handleCopyNode = useCallback(() => {
    if (selectedNodeId) {
      const nodeToCopy = nodes.find(n => n.id === selectedNodeId);
      if (nodeToCopy) {
        setCopiedNode(nodeToCopy);
        message.success('노드가 복사되었습니다');
      }
    }
  }, [selectedNodeId, nodes]);

  const handlePasteNode = useCallback(() => {
    if (copiedNode && reactFlowInstance) {
      const viewport = reactFlowInstance.getViewport();
      const centerX = -viewport.x / viewport.zoom + 200;
      const centerY = -viewport.y / viewport.zoom + 200;
      
      const newNode: Node = {
        ...copiedNode,
        id: `${Date.now()}`,
        position: { x: centerX, y: centerY },
        data: {
          ...copiedNode.data,
          label: `${copiedNode.data.label} Copy`,
        },
      };
      
      setNodes((nds) => [...nds, newNode]);
      setSelectedNodeId(newNode.id);
      message.success('노드가 붙여넣기되었습니다');
    }
  }, [copiedNode, reactFlowInstance, setNodes]);

  const updateNodeData = useCallback((nodeId: string, newData: any) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId
          ? { ...node, data: newData }
          : node
      )
    );
  }, [setNodes]);

  const handleSave = useCallback(() => {
    const flowData = {
      nodes: nodes.map(node => ({
        id: node.id,
        type: 'custom', // React Flow node type remains 'custom'
        position: { ...node.position }, // Ensure position is cloned
        data: {
          ...node.data,
          position: node.position, // Also store position in data for backup
        },
      })),
      edges: edges.map(edge => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle,
        targetHandle: edge.targetHandle,
      })),
    };

    if (onSave) {
      onSave(flowData);
      // Refresh versions after save
      setTimeout(() => {
        if (flowId && flowId !== 'new') {
          fetchVersions();
        }
      }, 1000);
    } else {
      message.success('Flow saved successfully!');
      console.log('Flow data:', flowData);
    }
  }, [nodes, edges, onSave, flowId]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check if user is typing in input fields
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.contentEditable === 'true') {
        return;
      }

      // Ctrl+S: Save
      if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        handleSave();
        return;
      }

      // Ctrl+C: Copy node
      if (e.ctrlKey && e.key === 'c' && selectedNodeId) {
        e.preventDefault();
        handleCopyNode();
        return;
      }

      // Ctrl+V: Paste node
      if (e.ctrlKey && e.key === 'v' && copiedNode) {
        e.preventDefault();
        handlePasteNode();
        return;
      }

      // Note: Delete key functionality removed - use floating delete button instead
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedNodeId, selectedEdgeId, copiedNode, handleSave, handleCopyNode, handlePasteNode, handleDeleteNode, handleDeleteEdge]);


  const handleFlowNameEdit = () => {
    setEditingFlowName(true);
    setTempFlowName(flowName || 'Untitled Flow');
  };

  const handleFlowNameSave = () => {
    if (onUpdateFlowName && tempFlowName.trim()) {
      onUpdateFlowName(tempFlowName.trim());
    }
    setEditingFlowName(false);
  };

  const handleFlowNameCancel = () => {
    setTempFlowName(flowName || 'Untitled Flow');
    setEditingFlowName(false);
  };

  const handleTest = () => {
    if (flowId && flowId !== 'new') {
      setChatPanelVisible(true);
    } else {
      message.warning('Please save the flow first before testing');
    }
  };

  const handleSaveAs = async (name: string, description?: string) => {
    if (!flowId || flowId === 'new') {
      throw new Error('원본 Flow가 저장되지 않았습니다. 먼저 Flow를 저장해주세요.');
    }

    try {
      // Get token
      const { ensureValidToken } = await import('../../utils/auth');
      const token = await ensureValidToken();
      
      if (!token) {
        throw new Error('인증 토큰이 없습니다');
      }

      // Call save as API
      const response = await fetch(`/api/flows/${flowId}/save-as`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: name.trim(),
          description: description?.trim() || null
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage;
        try {
          const errorObj = JSON.parse(errorText);
          errorMessage = errorObj.detail || errorObj.message;
        } catch {
          errorMessage = errorText;
        }
        throw new Error(errorMessage || 'Flow 복제에 실패했습니다');
      }

      const newFlow = await response.json();
      
      // Close modal
      setSaveAsModalVisible(false);
      
      // Redirect to the new flow
      const currentPath = window.location.pathname;
      const newPath = currentPath.replace(/\/[^\/]*$/, `/${newFlow.id}`);
      window.location.href = newPath;
      
    } catch (error: any) {
      console.error('Save as error:', error);
      throw error; // Re-throw to be handled by the modal
    }
  };

  const handleLoadTemplate = async (templateId: string) => {
    try {
      // Get token
      const { ensureValidToken } = await import('../../utils/auth');
      const token = await ensureValidToken();
      
      if (!token) {
        throw new Error('인증 토큰이 없습니다');
      }

      // Call template load API
      const response = await fetch(`/api/templates/${templateId}/load`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          template_id: templateId,
          increment_usage: true
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage;
        try {
          const errorObj = JSON.parse(errorText);
          errorMessage = errorObj.detail || errorObj.message;
        } catch {
          errorMessage = errorText;
        }
        throw new Error(errorMessage || '템플릿 로드에 실패했습니다');
      }

      const result = await response.json();
      const template = result.template;
      
      if (!template.definition) {
        throw new Error('템플릿 정의가 없습니다');
      }

      // Load template definition into current flow
      const templateDefinition = template.definition;
      
      // Update nodes and edges
      if (templateDefinition.nodes) {
        const loadedNodes = templateDefinition.nodes.map((node: any) => ({
          ...node,
          type: 'custom', // Ensure all nodes use custom type
        }));
        setNodes(loadedNodes);
      }
      
      if (templateDefinition.edges) {
        setEdges(templateDefinition.edges);
      }

      // Clear selection and highlights
      setSelectedNodeId(null);
      setSelectedEdgeId(null);
      setHighlightedNodes(new Set());
      setHighlightedEdges(new Set());
      
      // Close modal
      setTemplateLoaderVisible(false);
      
    } catch (error: any) {
      console.error('Load template error:', error);
      throw error; // Re-throw to be handled by the modal
    }
  };

  const handleSaveAsTemplate = async (templateData: {
    name: string;
    description?: string;
    category?: string;
    is_public: boolean;
    thumbnail?: string;
  }) => {
    if (!flowId || flowId === 'new') {
      throw new Error('원본 Flow가 저장되지 않았습니다. 먼저 Flow를 저장해주세요.');
    }

    try {
      // Get token
      const { ensureValidToken } = await import('../../utils/auth');
      const token = await ensureValidToken();
      
      if (!token) {
        throw new Error('인증 토큰이 없습니다');
      }

      // Call save as template API
      const response = await fetch(`/api/templates/save-from-flow/${flowId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(templateData),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage;
        try {
          const errorObj = JSON.parse(errorText);
          errorMessage = errorObj.detail || errorObj.message;
        } catch {
          errorMessage = errorText;
        }
        throw new Error(errorMessage || '템플릿 저장에 실패했습니다');
      }

      const savedTemplate = await response.json();
      
      // Close modal
      setSaveAsTemplateModalVisible(false);
      
      console.log('Template saved successfully:', savedTemplate);
      
    } catch (error: any) {
      console.error('Save as template error:', error);
      throw error; // Re-throw to be handled by the modal
    }
  };

  const handlePublish = async () => {
    if (!flowId || flowId === 'new') {
      message.warning('Please save the flow first before publishing');
      return;
    }

    try {
      message.loading('Publishing flow...', 0);

      // Get token first
      const { ensureValidToken } = await import('../../utils/auth');
      const token = await ensureValidToken();
      
      if (!token) {
        throw new Error('No valid token available');
      }

      // First, save the current flow to create a new version and get the new version data
      let newVersionData = null;
      
      try {
        const flowData = {
          nodes: nodes.map(node => ({
            id: node.id,
            type: 'custom',
            position: { ...node.position },
            data: {
              ...node.data,
              position: node.position,
            },
          })),
          edges: edges.map(edge => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            sourceHandle: edge.sourceHandle,
            targetHandle: edge.targetHandle,
          })),
        };

        // Save the flow and get the response
        const saveResponse = await fetch(`/api/flows/${flowId}`, {
          method: 'PUT',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            definition: flowData,
            change_summary: 'Updated for publish',
          }),
        });

        if (saveResponse.ok) {
          const saveData = await saveResponse.json();
          console.log('Save response:', saveData);
          
          // Wait a moment for the save to complete
          await new Promise(resolve => setTimeout(resolve, 500));
          
          // Now get the latest version that was just created
          const versionsResponse2 = await fetch(`/api/flows/${flowId}/versions`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
          
          if (versionsResponse2.ok) {
            const versionsData2 = await versionsResponse2.json();
            // Get the most recently created version
            newVersionData = versionsData2.reduce((latest: any, current: any) => {
              const latestDate = new Date(latest.created_at);
              const currentDate = new Date(current.created_at);
              return currentDate > latestDate ? current : latest;
            });
            console.log('Newly created version:', newVersionData);
          }
        } else {
          // Fallback to the old method if direct save fails
          if (onSave) {
            onSave(flowData);
            await new Promise(resolve => setTimeout(resolve, 1000));
          }
        }
      } catch (saveError) {
        console.error('Save error, falling back to old method:', saveError);
        // Fallback to the old method
        const flowData = {
          nodes: nodes.map(node => ({
            id: node.id,
            type: 'custom',
            position: { ...node.position },
            data: {
              ...node.data,
              position: node.position,
            },
          })),
          edges: edges.map(edge => ({
            id: edge.id,
            source: edge.source,
            target: edge.target,
            sourceHandle: edge.sourceHandle,
            targetHandle: edge.targetHandle,
          })),
        };

        if (onSave) {
          onSave(flowData);
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      }

      // Use the newly created version or fallback to fetching latest version
      let latestVersion = newVersionData;
      
      if (!latestVersion) {
        console.log('No new version data, fetching latest version...');
        const versionsResponse = await fetch(`/api/flows/${flowId}/versions`, {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!versionsResponse.ok) {
          throw new Error('Failed to fetch versions');
        }

        const versionsData = await versionsResponse.json();
        if (!versionsData || versionsData.length === 0) {
          throw new Error('No versions found to publish');
        }

        console.log('Available versions:', versionsData.map((v: any) => ({ 
          id: v.id, 
          version_number: v.version_number,
          created_at: v.created_at 
        })));

        // Get the latest version (most recent created_at)
        latestVersion = versionsData.reduce((latest: any, current: any) => {
          const latestDate = new Date(latest.created_at);
          const currentDate = new Date(current.created_at);
          return currentDate > latestDate ? current : latest;
        });
      }

      console.log('Selected latest version:', {
        id: latestVersion.id,
        version_number: latestVersion.version_number,
        created_at: latestVersion.created_at
      });

      // Publish the latest version using the version ID (more reliable than version_number)
      console.log(`Publishing version ID: ${latestVersion.id}, version number: ${latestVersion.version_number}`);
      
      const publishResponse = await fetch(
        `/api/flows/${flowId}/versions/${latestVersion.id}/publish`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            publish_notes: `Published version ${latestVersion.version_number}`,
          }),
        }
      );

      message.destroy(); // Clear loading message

      if (publishResponse.ok) {
        const publishData = await publishResponse.json();
        
        // Create or update deployment automatically after successful publish
        try {
          const endpoint_path = `/flow-${flowId}-v${publishData.version_number}`;
          const deployment_name = `${flowName || 'Untitled Flow'} - v${publishData.version_number}`;
          
          // First, check if deployment with this endpoint already exists
          console.log('🔍 Checking for existing deployment...');
          const existingDeploymentResponse = await fetch(`/api/deployments/?flow_id=${flowId}`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });
          
          let existingDeployment = null;
          if (existingDeploymentResponse.ok) {
            const deployments = await existingDeploymentResponse.json();
            existingDeployment = deployments.find((d: any) => d.endpoint_path === endpoint_path);
          }
          
          let deploymentResponse;
          
          if (existingDeployment) {
            // Update existing deployment
            console.log('🔄 Updating existing deployment:', existingDeployment.id);
            deploymentResponse = await fetch(`/api/deployments/${existingDeployment.id}`, {
              method: 'PUT',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                name: deployment_name,
                description: `Updated deployment for flow "${flowName}" version ${publishData.version_number}`,
                flow_id: flowId,
                endpoint_path: endpoint_path,
                is_public: false,
                requires_auth: true,
                rate_limit: 1000,
                deployment_config: {
                  flow_version: publishData.version_number,
                  timeout: 300,
                  memory_limit: 512,
                  auto_scale: true,
                  min_instances: 1,
                  max_instances: 5
                }
              }),
            });
          } else {
            // Create new deployment
            console.log('🚀 Creating new deployment with data:', {
              name: deployment_name,
              flow_id: flowId,
              flow_version: publishData.version_number,
              endpoint_path: endpoint_path,
              status: 'pending'
            });

            deploymentResponse = await fetch('/api/deployments/', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                name: deployment_name,
                description: `Automated deployment for flow "${flowName}" version ${publishData.version_number}`,
                flow_id: flowId,
                endpoint_path: endpoint_path,
                is_public: false,
                requires_auth: true,
                rate_limit: 1000,
                deployment_config: {
                  flow_version: publishData.version_number,
                  timeout: 300,
                  memory_limit: 512,
                  auto_scale: true,
                  min_instances: 1,
                  max_instances: 5
                }
              }),
            });
          }

          if (deploymentResponse.ok) {
            const deploymentData = await deploymentResponse.json();
            const actionText = existingDeployment ? 'updated' : 'created';
            console.log(`✅ Deployment ${actionText} successfully:`, deploymentData);
            
            message.success(
              `Flow published successfully! (Version ${publishData.version_number})\n` +
              `Deployment ${actionText} and awaiting approval.`
            );
            
            // Show deployment info in a more user-friendly way
            setTimeout(() => {
              message.info(
                `📋 Deployment ${existingDeployment ? 'Updated' : 'Draft Created'}!\n` +
                `• Name: ${deploymentData.name}\n` +
                `• Status: ${deploymentData.status} (승인 대기중)\n` +
                `• Endpoint: /api/deployed${deploymentData.endpoint_path}\n` +
                `• 승인하기: http://localhost:3005/api-deployments`,
                10 // Show for 10 seconds
              );
            }, 2000);
          } else {
            // Read response body once and handle both JSON and text formats
            let errorData;
            try {
              const responseText = await deploymentResponse.text();
              try {
                errorData = JSON.parse(responseText);
              } catch {
                errorData = responseText;
              }
            } catch {
              errorData = 'Failed to read error response';
            }
            
            const actionText = existingDeployment ? 'update' : 'creation';
            console.error(`❌ Deployment ${actionText} failed:`, {
              status: deploymentResponse.status,
              statusText: deploymentResponse.statusText,
              error: errorData,
              requestData: {
                name: deployment_name,
                flow_id: flowId,
                endpoint_path: endpoint_path
              }
            });
            
            message.success(`Flow published successfully! (Version ${publishData.version_number})`);
            
            // 더 상세한 오류 메시지 제공
            const deploymentActionText = existingDeployment ? 'update' : 'creation';
            if (deploymentResponse.status === 422) {
              message.error(`Deployment ${deploymentActionText} failed: Invalid data format. Check console for details.`);
            } else if (deploymentResponse.status === 409) {
              message.error(`Deployment ${deploymentActionText} failed: Endpoint path conflict.`);
            } else {
              message.warning(`Deployment ${deploymentActionText} failed (${deploymentResponse.status}). Please ${existingDeployment ? 'update' : 'create'} manually in API Deployments.`);
            }
          }
        } catch (deployError) {
          console.error('❌ Deployment creation error:', deployError);
          message.success(`Flow published successfully! (Version ${publishData.version_number})`);
          message.error('Deployment creation failed: Network or server error. Please check console and try again.');
        }
        
        // Refresh versions and deployments to show published status
        if (flowId && flowId !== 'new') {
          fetchVersions();
          fetchDeployments();
          
          // API Deployments 페이지의 캐시도 무효화 (새로 생성된 deployment 반영)
          setTimeout(() => {
            if (window.location.href.includes('api-deployments')) {
              window.location.reload();
            } else {
              // 다른 창에서 API Deployments가 열려있다면 강제 새로고침 시그널 보내기
              localStorage.setItem('deployment-cache-invalidate', Date.now().toString());
              // 브라우저 이벤트도 트리거
              window.dispatchEvent(new StorageEvent('storage', {
                key: 'deployment-cache-invalidate',
                newValue: Date.now().toString()
              }));
            }
          }, 1000); // deployment 생성 완료 후 1초 대기
        }
      } else {
        const errorData = await publishResponse.json();
        throw new Error(errorData.detail || 'Failed to publish flow');
      }
    } catch (error) {
      message.destroy(); // Clear loading message
      console.error('Publish error:', error);
      message.error(error instanceof Error ? error.message : 'Failed to publish flow');
    }
  };

  const handleVersions = () => {
    if (flowId && flowId !== 'new') {
      setVersionsDrawerVisible(true);
      fetchVersions();
    } else {
      message.info('Save the flow first to view version history');
    }
  };

  const handleDeployments = () => {
    if (flowId && flowId !== 'new') {
      setDeploymentsDrawerVisible(true);
      fetchDeployments();
    } else {
      message.info('Save the flow first to view deployments');
    }
  };

  const handleStopDeployment = async (deploymentId: string) => {
    try {
      const { ensureValidToken } = await import('../../utils/auth');
      const token = await ensureValidToken();
      
      if (!token) {
        message.error('Authentication required');
        return;
      }

      const response = await fetch(`/api/deployments/${deploymentId}/stop/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        message.success('Deployment stopped successfully');
        fetchDeployments(); // Refresh deployment list
      } else {
        message.error('Failed to stop deployment');
      }
    } catch (error) {
      console.error('Stop deployment error:', error);
      message.error('Failed to stop deployment');
    }
  };

  const handleStartDeployment = async (deploymentId: string) => {
    try {
      const { ensureValidToken } = await import('../../utils/auth');
      const token = await ensureValidToken();
      
      if (!token) {
        message.error('Authentication required');
        return;
      }

      const response = await fetch(`/api/deployments/${deploymentId}/start/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        message.success('Deployment started successfully');
        fetchDeployments(); // Refresh deployment list
      } else {
        message.error('Failed to start deployment');
      }
    } catch (error) {
      console.error('Start deployment error:', error);
      message.error('Failed to start deployment');
    }
  };

  const handleNodeExecutionUpdate = (nodeId: string, status: 'executing' | 'completed' | 'error' | 'reset') => {
    if (status === 'reset' || nodeId === 'all') {
      setExecutingNodes(new Set());
      setCompletedNodes(new Set());
      setErrorNodes(new Set());
      return;
    }

    switch (status) {
      case 'executing':
        setExecutingNodes(prev => new Set(prev).add(nodeId));
        setCompletedNodes(prev => {
          const newSet = new Set(prev);
          newSet.delete(nodeId);
          return newSet;
        });
        setErrorNodes(prev => {
          const newSet = new Set(prev);
          newSet.delete(nodeId);
          return newSet;
        });
        break;
      case 'completed':
        setExecutingNodes(prev => {
          const newSet = new Set(prev);
          newSet.delete(nodeId);
          return newSet;
        });
        setCompletedNodes(prev => new Set(prev).add(nodeId));
        setErrorNodes(prev => {
          const newSet = new Set(prev);
          newSet.delete(nodeId);
          return newSet;
        });
        break;
      case 'error':
        setExecutingNodes(prev => {
          const newSet = new Set(prev);
          newSet.delete(nodeId);
          return newSet;
        });
        setCompletedNodes(prev => {
          const newSet = new Set(prev);
          newSet.delete(nodeId);
          return newSet;
        });
        setErrorNodes(prev => new Set(prev).add(nodeId));
        break;
    }
  };

  const handleNodeHighlight = (nodeId: string) => {
    // Highlight the specific node
    const connectedNodes = new Set([nodeId]);
    const connectedEdges = new Set<string>();
    
    // Find connected edges
    edges.forEach(edge => {
      if (edge.source === nodeId || edge.target === nodeId) {
        connectedEdges.add(edge.id);
      }
    });
    
    setHighlightedNodes(connectedNodes);
    setHighlightedEdges(connectedEdges);
    
    // Auto-clear highlight after 3 seconds
    setTimeout(() => {
      setHighlightedNodes(new Set());
      setHighlightedEdges(new Set());
    }, 3000);
  };

  // Properties Panel Toggle
  const togglePropertiesPanel = useCallback(() => {
    const nextState = (propertiesPanelState + 1) % 3; // 0 → 1 → 2 → 0
    setPropertiesPanelState(nextState);
    localStorage.setItem('flowDesigner.propertiesPanelState', nextState.toString());
  }, [propertiesPanelState]);


  const selectedNode = selectedNodeId ? nodes.find(n => n.id === selectedNodeId) : null;

  // Calculate responsive widths based on sidebar state
  const nodePaletteWidth = sidebarCollapsed ? '18%' : '12%';
  const nodePaletteMinWidth = sidebarCollapsed ? '280px' : '240px';

  // Apply highlighting styles to nodes and edges  
  const styledNodes = nodes.map(node => {
    const isHighlighted = highlightedNodes.has(node.id);
    const isConnecting = connectingNode === node.id;
    const isDimmed = highlightedNodes.size > 0 && !isHighlighted;
    const isExecuting = executingNodes.has(node.id);
    const isCompleted = completedNodes.has(node.id);
    const hasError = errorNodes.has(node.id);
    
    let borderColor = '#d9d9d9';
    let borderWidth = 1;
    let boxShadow = 'none';
    
    if (isExecuting) {
      borderColor = '#1890ff';
      borderWidth = 3;
      boxShadow = '0 0 0 3px rgba(24, 144, 255, 0.2)';
    } else if (isCompleted) {
      borderColor = '#52c41a';
      borderWidth = 2;
    } else if (hasError) {
      borderColor = '#ff4d4f';
      borderWidth = 2;
      boxShadow = '0 0 0 2px rgba(255, 77, 79, 0.2)';
    } else if (isHighlighted) {
      borderColor = '#722ed1';
      borderWidth = 2;
    }
    
    return {
      ...node,
      data: {
        ...node.data,
        isHighlighted,
        isConnecting,
        isDimmed,
        isExecuting,
        isCompleted,
        hasError,
        onDelete: handleDeleteNode,
        onDuplicate: handleDuplicateNode,
        onOpenProperties: handleOpenNodeProperties,
      },
      style: {
        ...node.style,
        opacity: isDimmed ? 0.3 : 1,
        border: `${borderWidth}px solid ${borderColor}`,
        boxShadow,
      }
    };
  });

  const styledEdges = edges.map(edge => ({
    ...edge,
    style: {
      ...edge.style,
      opacity: highlightedEdges.size > 0 ? (highlightedEdges.has(edge.id) ? 1 : 0.3) : 1,
      strokeWidth: highlightedEdges.has(edge.id) ? 3 : 2,
      stroke: highlightedEdges.has(edge.id) ? '#3b82f6' : '#94a3b8',
    },
    animated: highlightedEdges.has(edge.id),
    className: highlightedEdges.has(edge.id) ? 'highlighted-edge' : undefined,
  }));

  return (
    <div className="h-full flex flex-col">
      
      {/* Flow Editor Toolbar */}
      <div 
        style={{
          height: '56px',
          borderBottom: '1px solid #f0f0f0',
          backgroundColor: '#fafafa',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: 'linear-gradient(90deg, #ffffff 0%, #fafafa 100%)'
        }}
      >
        {/* Left - Flow Name with Edit */}
        <div 
          style={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            padding: '8px 12px',
            borderRadius: '8px',
            transition: 'background-color 0.2s ease',
            backgroundColor: 'rgba(0, 0, 0, 0.02)'
          }}
          onClick={handleFlowNameEdit}
          className="hover:bg-gray-100"
        >
          <Typography.Title 
            level={4} 
            style={{ 
              margin: 0, 
              color: '#000000',
              fontSize: '16px',
              fontWeight: 600
            }}
          >
            {flowName || 'Untitled Flow'}
          </Typography.Title>
          <EditOutlined 
            style={{ 
              marginLeft: '8px', 
              color: '#666666',
              fontSize: '14px'
            }} 
          />
        </div>

        {/* Right - Action Buttons */}
        <Space size="small">
          <Button 
            icon={<SaveOutlined />} 
            onClick={handleSave}
            size="small"
            style={{
              borderColor: '#000000',
              color: '#000000',
              height: '32px'
            }}
          >
            저장
          </Button>
          <Button 
            icon={<CopyOutlined />} 
            onClick={() => setSaveAsModalVisible(true)}
            size="small"
            disabled={!flowId || flowId === 'new'}
            style={{
              borderColor: '#595959',
              color: '#595959',
              height: '32px'
            }}
            title={!flowId || flowId === 'new' ? '먼저 Flow를 저장해주세요' : '다른 이름으로 저장'}
          >
            다른 이름으로 저장
          </Button>
          <Button 
            icon={<FileTextOutlined />} 
            onClick={() => setTemplateLoaderVisible(true)}
            size="small"
            style={{
              borderColor: '#722ed1',
              color: '#722ed1',
              height: '32px'
            }}
            title="템플릿 가져오기"
          >
            템플릿 가져오기
          </Button>
          {isAdmin && (
            <Button 
              icon={<CloudUploadOutlined />} 
              onClick={() => setSaveAsTemplateModalVisible(true)}
              size="small"
              disabled={!flowId || flowId === 'new'}
              style={{
                borderColor: '#fa8c16',
                color: '#fa8c16',
                height: '32px'
              }}
              title={!flowId || flowId === 'new' ? '먼저 Flow를 저장해주세요' : '템플릿으로 저장 (관리자 전용)'}
            >
              템플릿으로 저장
            </Button>
          )}
          <Button 
            icon={<BugOutlined />} 
            onClick={handleTest}
            size="small"
            style={{
              borderColor: '#52c41a',
              color: '#52c41a',
              height: '32px'
            }}
          >
            테스트
          </Button>
          <Button 
            icon={<RocketOutlined />} 
            onClick={handlePublish}
            type="primary"
            size="small"
            style={{
              backgroundColor: '#000000',
              borderColor: '#000000',
              height: '32px'
            }}
          >
            발행
          </Button>
          <Badge count={deployments.length} size="small">
            <Button 
              icon={<CloudOutlined />} 
              onClick={handleDeployments}
              size="small"
              style={{
                borderColor: '#1890ff',
                color: '#1890ff',
                height: '32px'
              }}
            >
              배포
            </Button>
          </Badge>
          <Button 
            icon={<HistoryOutlined />} 
            onClick={handleVersions}
            size="small"
            style={{
              borderColor: '#722ed1',
              color: '#722ed1',
              height: '32px'
            }}
          >
            버전
          </Button>
        </Space>
      </div>

      {/* Main Content Area with 3 Columns */}
      <div className="flex-1 flex">
        {/* Node Palette - Responsive Width */}
        <div 
          style={{
            width: nodePaletteWidth,
            minWidth: nodePaletteMinWidth,
            borderRight: '1px solid #e8e8e8',
            backgroundColor: '#f9f9f9',
            padding: '16px',
            transition: 'width 0.3s ease, min-width 0.3s ease'
          }}
        >
          <NodePalette />
        </div>

        {/* Main Flow Editor - Flexible Width */}
        <div className="flex-1 relative" style={{ overflow: 'hidden' }}>

          {/* React Flow Canvas */}
          <div ref={reactFlowWrapper} className="h-full" style={{ overflow: 'hidden' }}>
            <ReactFlowProvider>
              <ReactFlow
                nodes={styledNodes}
                edges={styledEdges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onConnectStart={onConnectStart}
                onConnectEnd={onConnectEnd}
                onInit={setReactFlowInstance}
                onDrop={onDrop}
                onDragOver={onDragOver}
                onNodeClick={onNodeClick}
                onEdgeClick={onEdgeClick}
                onEdgeDoubleClick={onEdgeDoubleClick}
                onPaneClick={onPaneClick}
                nodeTypes={nodeTypes}
                nodesDraggable={true}
                nodesConnectable={true}
                elementsSelectable={true}
                panOnDrag={true}
                panOnScroll={false}
                panOnScrollMode="vertical"
                zoomOnScroll={true}
                zoomOnPinch={true}
                zoomOnDoubleClick={true}
                preventScrolling={false}
                selectionOnDrag={false}
                selectNodesOnDrag={false}
                multiSelectionKeyCode="Meta"
                deleteKeyCode={null}
                connectOnClick={false}
                onlyRenderVisibleElements={true}
                snapToGrid={true}
                snapGrid={[16, 16]}
                minZoom={0.2}
                maxZoom={2}
                translateExtent={[[canvasBounds.minX, canvasBounds.minY], [canvasBounds.maxX, canvasBounds.maxY]]}
                nodeExtent={[[canvasBounds.minX + 100, canvasBounds.minY + 100], [canvasBounds.maxX - 100, canvasBounds.maxY - 100]]}
                defaultViewport={{ x: 0, y: 0, zoom: 1 }}
                fitView
                fitViewOptions={{ padding: 0.2 }}
              >
                <Controls />
                <MiniMap />
                <Background gap={12} size={1} />
              </ReactFlow>
            </ReactFlowProvider>
          </div>

          {/* Floating Delete Button */}
          {selectedNodeId && (
            <div
              style={{
                position: 'fixed',
                bottom: '80px',
                left: '50%',
                transform: 'translateX(-50%)',
                zIndex: 1000,
                animation: 'fadeIn 0.3s ease-in-out',
                pointerEvents: 'none'
              }}
            >
              <Button
                type="primary"
                danger
                size="large"
                icon={<DeleteOutlined />}
                onClick={() => handleDeleteNode(selectedNodeId)}
                style={{
                  boxShadow: '0 8px 25px rgba(255, 77, 79, 0.3), 0 4px 12px rgba(0, 0, 0, 0.15)',
                  borderRadius: '12px',
                  height: '52px',
                  paddingLeft: '20px',
                  paddingRight: '20px',
                  fontSize: '16px',
                  fontWeight: 600,
                  pointerEvents: 'auto',
                  border: 'none',
                  background: 'linear-gradient(135deg, #ff4757 0%, #ff3742 100%)',
                  backdropFilter: 'blur(10px)'
                }}
              >
                Delete Node
              </Button>
            </div>
          )}

        </div>

        {/* Properties Panel - 3-Stage Toggle */}
        {propertiesPanelState > 0 && (
          <div 
            style={{
              width: `${getPanelWidth(propertiesPanelState)}px`,
              borderLeft: '1px solid #e8e8e8',
              backgroundColor: '#f9f9f9',
              position: 'relative',
              transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
            }}
          >
            {/* Panel Toggle Button */}
            <div
              style={{
                position: 'absolute',
                left: -16,
                top: '50%',
                transform: 'translateY(-50%)',
                zIndex: 10
              }}
            >
              <Button
                type="text"
                onClick={togglePropertiesPanel}
                style={{
                  width: '32px',
                  height: '80px',
                  padding: 0,
                  borderRadius: '16px 0 0 16px',
                  backgroundColor: 'rgba(255, 255, 255, 0.95)',
                  backdropFilter: 'blur(8px)',
                  border: '1px solid rgba(226, 232, 240, 0.8)',
                  borderRight: 'none',
                  boxShadow: '-4px 0 12px rgba(0, 0, 0, 0.08)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '18px',
                  color: '#64748b',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 1)';
                  e.currentTarget.style.boxShadow = '-6px 0 20px rgba(0, 0, 0, 0.12)';
                  e.currentTarget.style.color = '#1e293b';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
                  e.currentTarget.style.boxShadow = '-4px 0 12px rgba(0, 0, 0, 0.08)';
                  e.currentTarget.style.color = '#64748b';
                }}
                title={
                  propertiesPanelState === 1 ? '패널 넓게 (640px)' : 
                  propertiesPanelState === 2 ? '패널 닫기' : '패널 열기'
                }
              >
                {propertiesPanelState === 1 ? <DoubleRightOutlined /> : 
                 propertiesPanelState === 2 ? <DoubleLeftOutlined /> : <DoubleRightOutlined />}
              </Button>
            </div>
            
            <NodePropertiesPanel
              selectedNodeId={selectedNodeId}
              nodes={nodes}
              edges={edges}
              onUpdateNode={updateNodeData}
            />
          </div>
        )}

        {/* Panel Toggle Button (when closed) */}
        {propertiesPanelState === 0 && (
          <div
            style={{
              position: 'fixed',
              right: 0,
              top: '50%',
              transform: 'translateY(-50%)',
              zIndex: 1000
            }}
          >
            <Button
              type="text"
              onClick={togglePropertiesPanel}
              style={{
                width: '32px',
                height: '80px',
                padding: 0,
                borderRadius: '16px 0 0 16px',
                backgroundColor: 'rgba(59, 130, 246, 0.95)',
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                borderRight: 'none',
                boxShadow: '-4px 0 12px rgba(59, 130, 246, 0.25)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '18px',
                color: 'white',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                animation: 'pulseGlow 2s ease-in-out infinite'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 1)';
                e.currentTarget.style.boxShadow = '-6px 0 20px rgba(59, 130, 246, 0.4)';
                e.currentTarget.style.width = '40px';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(59, 130, 246, 0.95)';
                e.currentTarget.style.boxShadow = '-4px 0 12px rgba(59, 130, 246, 0.25)';
                e.currentTarget.style.width = '32px';
              }}
              title="노드 설정창 열기"
            >
              <SettingOutlined style={{ fontSize: '20px' }} />
            </Button>
          </div>
        )}
      </div>

      {/* Flow Name Edit Modal */}
      <Modal
        title="Edit Flow Name"
        open={editingFlowName}
        onOk={handleFlowNameSave}
        onCancel={handleFlowNameCancel}
        okText="Save"
        cancelText="Cancel"
        width={400}
      >
        <Input
          value={tempFlowName}
          onChange={(e) => setTempFlowName(e.target.value)}
          placeholder="Enter flow name"
          maxLength={100}
          onPressEnter={handleFlowNameSave}
          autoFocus
        />
      </Modal>

      {/* Version History Drawer */}
      <Drawer
        title="Version History"
        placement="right"
        onClose={() => setVersionsDrawerVisible(false)}
        open={versionsDrawerVisible}
        width={400}
      >
        <List
          dataSource={versions}
          renderItem={(version) => (
            <List.Item
              actions={[
                <Button 
                  type="link" 
                  size="small"
                  onClick={() => handleLoadVersion(version.version_number)}
                >
                  Load
                </Button>
              ]}
            >
              <List.Item.Meta
                title={
                  <Space>
                    <span>v{version.version_number}</span>
                    {version.version_name && (
                      <span style={{ fontWeight: 'normal' }}>- {version.version_name}</span>
                    )}
                    {version.is_published && (
                      <Tag color="green" size="small">Published</Tag>
                    )}
                  </Space>
                }
                description={
                  <div>
                    {version.change_summary && (
                      <div style={{ marginBottom: 4 }}>{version.change_summary}</div>
                    )}
                    <div style={{ fontSize: 12, color: '#666' }}>
                      {new Date(version.created_at).toLocaleString()}
                    </div>
                  </div>
                }
              />
            </List.Item>
          )}
          locale={{ emptyText: 'No versions found' }}
        />
      </Drawer>

      {/* Deployments Drawer */}
      <Drawer
        title={
          <Space>
            <CloudOutlined />
            Deployments
            <Badge count={deployments.length} size="small" />
          </Space>
        }
        placement="right"
        onClose={() => setDeploymentsDrawerVisible(false)}
        open={deploymentsDrawerVisible}
        width={500}
      >
        {deployments.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
            <CloudOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
            <div>No deployments found</div>
            <div style={{ fontSize: '12px', marginTop: '8px' }}>
              Publish your flow to create a deployment
            </div>
          </div>
        ) : (
          <List
            dataSource={deployments}
            renderItem={(deployment) => (
              <List.Item
                actions={[
                  <Button 
                    type="link" 
                    size="small"
                    icon={<ApiOutlined />}
                    onClick={() => {
                      navigator.clipboard.writeText(`/api/deployments/${deployment.id}/execute`);
                      message.success('API endpoint copied to clipboard');
                    }}
                  >
                    Copy API
                  </Button>,
                  deployment.status === 'running' ? (
                    <Button 
                      type="link" 
                      size="small"
                      danger
                      onClick={() => handleStopDeployment(deployment.id)}
                    >
                      Stop
                    </Button>
                  ) : (
                    <Button 
                      type="link" 
                      size="small"
                      onClick={() => handleStartDeployment(deployment.id)}
                    >
                      Start
                    </Button>
                  ),
                  <Button 
                    type="link" 
                    size="small"
                    onClick={() => window.open('http://localhost:3005/api-deployments', '_blank')}
                  >
                    View Details
                  </Button>
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <span>{deployment.name}</span>
                      <Tag 
                        color={
                          deployment.status === 'running' ? 'green' :
                          deployment.status === 'stopped' ? 'red' :
                          deployment.status === 'pending' ? 'orange' : 'default'
                        }
                        size="small"
                      >
                        {deployment.status}
                      </Tag>
                    </Space>
                  }
                  description={
                    <div>
                      <div style={{ marginBottom: 4 }}>
                        <strong>Version:</strong> {deployment.flow_version || 'Latest'}
                      </div>
                      <div style={{ marginBottom: 4 }}>
                        <strong>API:</strong> 
                        <Tag style={{ marginLeft: 4, fontSize: '11px' }}>
                          /api/deployments/{deployment.id}/execute
                        </Tag>
                      </div>
                      <div style={{ fontSize: 12, color: '#666' }}>
                        Created: {new Date(deployment.created_at).toLocaleString()}
                      </div>
                    </div>
                  }
                />
              </List.Item>
            )}
          />
        )}
      </Drawer>

      {/* Chat Panel for Interactive Testing */}
      <ChatPanel
        visible={chatPanelVisible}
        flowId={flowId || ''}
        flowName={flowName || 'Untitled Flow'}
        onClose={() => setChatPanelVisible(false)}
        onNodeExecutionUpdate={handleNodeExecutionUpdate}
      />

      {/* Save As Modal */}
      <SaveAsModal
        visible={saveAsModalVisible}
        onCancel={() => setSaveAsModalVisible(false)}
        onSave={handleSaveAs}
        currentFlowName={flowName}
      />

      {/* Template Loader Modal */}
      <TemplateLoaderModal
        visible={templateLoaderVisible}
        onCancel={() => setTemplateLoaderVisible(false)}
        onLoad={handleLoadTemplate}
      />

      {/* Save As Template Modal (Admin Only) */}
      {isAdmin && (
        <SaveAsTemplateModal
          visible={saveAsTemplateModalVisible}
          onCancel={() => setSaveAsTemplateModalVisible(false)}
          onSave={handleSaveAsTemplate}
          currentFlowName={flowName}
        />
      )}
    </div>
  );
};