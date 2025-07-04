/**
 * Workspace-centric Sidebar Component
 * Shows workspaces as collapsible tree structure with flows underneath
 * Updated with improved design and reordered menu structure
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  Tree, 
  Spin, 
  Button, 
  Typography, 
  Space,
  Dropdown,
  Badge
} from 'antd';
import {
  FolderOutlined,
  FolderOpenOutlined,
  PartitionOutlined,
  TeamOutlined,
  PlusOutlined,
  MoreOutlined,
  PlayCircleOutlined,
  EditOutlined,
  DashboardOutlined,
  SettingOutlined,
  ApiOutlined,
  SafetyOutlined,
  HistoryOutlined,
  FileTextOutlined,
  BookOutlined
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { workspaceService } from '../services/workspace';
import type { Workspace, WorkspaceTypeType } from '../types';
import { WorkspaceType, PermissionType } from '../types';
import { apiClient } from '../services/api';

const { Text } = Typography;

interface Flow {
  id: string;
  name: string;
  workspace_id?: string;
  current_version: number;
}

interface TreeNode {
  key: string;
  title: React.ReactNode;
  icon?: React.ReactNode;
  children?: TreeNode[];
  isLeaf?: boolean;
  data?: {
    type: 'menu' | 'workspace' | 'flow';
    workspace?: Workspace;
    flow?: Flow;
  };
  selectable?: boolean;
}

interface WorkspaceSidebarProps {
  collapsed: boolean;
}

export const WorkspaceSidebar: React.FC<WorkspaceSidebarProps> = ({ collapsed }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [expandedKeys, setExpandedKeys] = useState<string[]>([]);
  const [selectedKeys, setSelectedKeys] = useState<string[]>([]);

  // Fetch user's workspaces (automatic loading based on user/group membership)
  const { data: workspaces, isLoading: workspacesLoading } = useQuery({
    queryKey: ['user-workspaces'],
    queryFn: workspaceService.getUserWorkspaces,
    enabled: !!user,
  });

  // Fetch flows
  const { data: flows, isLoading: flowsLoading } = useQuery({
    queryKey: ['flows'],
    queryFn: async () => {
      const response = await apiClient.get('/api/flows');
      return response.data;
    },
    enabled: !!user,
  });

  useEffect(() => {
    const path = location.pathname;
    setSelectedKeys([path]);

    // Auto-expand workspace if we're in a flow
    if (path.startsWith('/flows/') && flows) {
      const flowId = path.split('/flows/')[1];
      const flow = flows.find((f: Flow) => f.id === flowId);
      if (flow?.workspace_id) {
        const workspaceKey = `workspace-${flow.workspace_id}`;
        if (!expandedKeys.includes(workspaceKey)) {
          setExpandedKeys(prev => [...prev, workspaceKey]);
        }
        setSelectedKeys([`flow-${flowId}`]);
      }
    }
  }, [location.pathname, flows, expandedKeys]);

  const getFlowActions = (flow: Flow, workspace: Workspace) => {
    const canEdit = workspace.user_permission && 
      [PermissionType.OWNER, PermissionType.ADMIN, PermissionType.WRITE].includes(workspace.user_permission);

    const items = [
      {
        key: 'run',
        icon: <PlayCircleOutlined />,
        label: '플로우 실행',
        onClick: () => {
          apiClient.post('/api/executions', { 
            flow_id: flow.id, 
            inputs: {} 
          }).then(() => {
            navigate('/executions');
          });
        }
      }
    ];

    if (canEdit) {
      items.push({
        key: 'edit',
        icon: <EditOutlined />,
        label: '플로우 편집',
        onClick: () => navigate(`/flows/${flow.id}`)
      });
    }

    return items;
  };

  const buildTreeData = (): TreeNode[] => {
    const treeData: TreeNode[] = [];

    // Add workspaces section first (when not collapsed)
    if (!collapsed && workspaces && workspaces.length > 0) {
      treeData.push({
        key: 'separator-workspaces',
        title: (
          <div style={{ 
            margin: '0 0 12px 0',
            paddingBottom: '8px'
          }}>
            <Text style={{ 
              fontSize: '13px', 
              color: '#666666', 
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              워크스페이스
            </Text>
          </div>
        ),
        selectable: false,
        data: { type: 'menu' as const }
      });

      // Add workspace nodes
      workspaces.forEach(workspace => {
        const workspaceFlows = (Array.isArray(flows) ? flows.filter(flow => flow.workspace_id === workspace.id) : []) || [];
        const isExpanded = expandedKeys.includes(`workspace-${workspace.id}`);
        
        const workspaceNode: TreeNode = {
          key: `workspace-${workspace.id}`,
          title: (
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              width: '100%',
              padding: '4px 0',
              gap: '8px'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                flex: 1,
                minWidth: 0
              }}>
                <span style={{ 
                  fontSize: '14px', 
                  fontWeight: 500, 
                  color: '#000000',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {workspace.name}
                </span>
                {workspace.user_permission && (
                  <Badge 
                    count={workspace.user_permission.toUpperCase()} 
                    style={{ 
                      backgroundColor: workspace.user_permission === PermissionType.OWNER ? '#ff4d4f' : '#1890ff',
                      fontSize: '10px',
                      height: '16px',
                      lineHeight: '14px',
                      minWidth: '16px',
                      paddingInline: '4px'
                    }}
                  />
                )}
                {workspaceFlows.length > 0 && (
                  <Badge 
                    count={workspaceFlows.length}
                    style={{ 
                      backgroundColor: '#f0f0f0',
                      color: '#666666',
                      fontSize: '10px',
                      fontWeight: 500,
                      height: '16px',
                      lineHeight: '14px',
                      minWidth: '16px',
                      paddingInline: '4px',
                      border: '1px solid #e8e8e8'
                    }}
                  />
                )}
              </div>
              <Button
                type="text"
                size="small"
                icon={<PlusOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  console.log('Create new flow in workspace:', workspace.id);
                }}
                style={{
                  border: 'none',
                  boxShadow: 'none',
                  width: '24px',
                  height: '24px',
                  minWidth: '24px',
                  padding: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  opacity: 0.7
                }}
                className="opacity-70 hover:opacity-100"
              />
            </div>
          ),
          icon: workspace.type === WorkspaceType.TEAM ? <TeamOutlined style={{ color: '#1890ff' }} /> : <FolderOutlined style={{ color: '#666666' }} />,
          children: isExpanded ? [
            // 플로우들
            ...workspaceFlows.map(flow => ({
              key: `flow-${flow.id}`,
              title: (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
                  <span style={{ 
                    fontSize: '13px', 
                    color: '#666666',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                    flex: 1
                  }}>
                    {flow.name}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span style={{ 
                      fontSize: '10px', 
                      color: '#999999',
                      fontWeight: 400
                    }}>
                      v{flow.current_version}
                    </span>
                    <Dropdown
                      menu={{ 
                        items: getFlowActions(flow, workspace),
                        onClick: (e) => e.domEvent.stopPropagation()
                      }}
                      trigger={['click']}
                      placement="bottomRight"
                    >
                      <Button
                        type="text"
                        size="small"
                        icon={<MoreOutlined />}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          border: 'none',
                          boxShadow: 'none',
                          width: '20px',
                          height: '20px',
                          minWidth: '20px',
                          padding: 0,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          opacity: 0.5
                        }}
                        className="opacity-50 hover:opacity-100"
                      />
                    </Dropdown>
                  </div>
                </div>
              ),
              icon: <PartitionOutlined style={{ color: '#722ed1', fontSize: '12px' }} />,
              isLeaf: true,
              data: { type: 'flow', flow, workspace }
            })),
            // RAG 학습 메뉴 추가
            {
              key: `rag-${workspace.id}`,
              title: (
                <span style={{ 
                  fontSize: '13px', 
                  color: '#000000',
                  fontWeight: 500
                }}>
                  RAG 학습
                </span>
              ),
              icon: <BookOutlined style={{ color: '#13c2c2', fontSize: '12px' }} />,
              isLeaf: true,
              data: { type: 'rag', workspace }
            }
          ] : [],
          data: { type: 'workspace', workspace }
        };

        treeData.push(workspaceNode);
      });
    }

    // Add main menu items at bottom with separator (only for admin users)
    if (!collapsed && user?.is_superuser) {
      treeData.push({
        key: 'separator-main-menu',
        title: (
          <div style={{ 
            borderTop: '1px solid #f0f0f0', 
            margin: '16px 0 12px 0',
            paddingTop: '16px'
          }}>
            <Text style={{ 
              fontSize: '13px', 
              color: '#666666', 
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              관리자 메뉴
            </Text>
          </div>
        ),
        selectable: false,
        data: { type: 'menu' as const }
      });
    }

    // Main menu items (only visible to admin users)
    console.log('🔍 DEBUG WorkspaceSidebar - user:', user);
    console.log('🔍 DEBUG WorkspaceSidebar - user?.is_superuser:', user?.is_superuser);
    console.log('🔍 DEBUG WorkspaceSidebar - Admin check result:', !!user?.is_superuser);
    
    if (user?.is_superuser) {
      const mainMenuItems = [
        {
          key: '/dashboard',
          title: collapsed ? '' : '대시보드',
          icon: <DashboardOutlined style={{ color: '#000000', fontSize: '16px' }} />,
          data: { type: 'menu' as const }
        },
        {
          key: '/workspaces',
          title: collapsed ? '' : '워크스페이스 관리',
          icon: <SettingOutlined style={{ color: '#000000', fontSize: '16px' }} />,
          data: { type: 'menu' as const }
        },
        {
          key: '/executions',
          title: collapsed ? '' : '실행 기록',
          icon: <HistoryOutlined style={{ color: '#000000', fontSize: '16px' }} />,
          data: { type: 'menu' as const }
        },
        {
          key: '/api-deployments',
          title: collapsed ? '' : 'API 배포',
          icon: <ApiOutlined style={{ color: '#000000', fontSize: '16px' }} />,
          data: { type: 'menu' as const }
        },
        {
          key: '/admin/workspace-permissions',
          title: collapsed ? '' : '워크스페이스 권한',
          icon: <SafetyOutlined style={{ color: '#ff4d4f', fontSize: '16px' }} />,
          data: { type: 'menu' as const }
        },
        {
          key: '/admin/template-management',
          title: collapsed ? '' : '템플릿 관리',
          icon: <FileTextOutlined style={{ color: '#722ed1', fontSize: '16px' }} />,
          data: { type: 'menu' as const }
        }
      ];

      treeData.push(...mainMenuItems);
    }

    return treeData;
  };

  const handleSelect = (selectedKeys: React.Key[], info: any) => {
    const key = selectedKeys[0] as string;
    const nodeData = info.node.data;

    if (nodeData?.type === 'flow') {
      navigate(`/flows/${nodeData.flow.id}`);
    } else if (nodeData?.type === 'workspace') {
      // Toggle expand/collapse
      const workspaceKey = key;
      if (expandedKeys.includes(workspaceKey)) {
        setExpandedKeys(expandedKeys.filter(k => k !== workspaceKey));
      } else {
        setExpandedKeys([...expandedKeys, workspaceKey]);
      }
    } else if (nodeData?.type === 'rag') {
      // RAG 학습 페이지로 이동
      navigate(`/workspaces/${nodeData.workspace.id}/rag`);
    } else if (nodeData?.type === 'menu') {
      navigate(key);
    }
  };

  const handleExpand = (expandedKeys: React.Key[]) => {
    setExpandedKeys(expandedKeys as string[]);
  };

  if (workspacesLoading || flowsLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '200px' 
      }}>
        <Spin size="small" />
      </div>
    );
  }

  return (
    <div style={{ 
      padding: '16px 12px',
      height: '100%',
      background: 'transparent'
    }}>
      <Tree
        treeData={buildTreeData()}
        selectedKeys={selectedKeys}
        expandedKeys={expandedKeys}
        onSelect={handleSelect}
        onExpand={handleExpand}
        showIcon
        blockNode
        style={{
          background: 'transparent',
          fontSize: '14px'
        }}
      />
    </div>
  );
};