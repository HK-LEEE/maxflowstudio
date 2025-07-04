/**
 * 파일명: FlowsPage.tsx (120줄)
 * 목적: Flows 관리 페이지 메인 컴포넌트
 * 동작 과정:
 * 1. 워크스페이스별로 Flow 목록 조회 및 표시
 * 2. Flow 생성, 편집, 삭제 등 관리 기능
 * 3. 접기/펼치기 가능한 워크스페이스 섹션 제공
 * 데이터베이스 연동: flows, workspaces 테이블 조인 조회
 * 의존성: FlowCreateModal, WorkspaceFlowList, FlowsHeader
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Collapse,
  Space,
  Typography,
  Empty,
  Spin,
  Layout,
  Tag,
} from 'antd';
import {
  FolderOutlined,
  TeamOutlined,
  UserOutlined,
  CaretRightOutlined,
} from '@ant-design/icons';
// import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../services/api';
import { workspaceService } from '../services/workspace';
import { FlowCreateModal } from './flows/components/FlowCreateModal';
import { WorkspaceFlowList } from './flows/components/WorkspaceFlowList';
import { FlowsHeader } from './flows/components/FlowsHeader';
import type { WorkspaceTypeType } from '../types';

const { Text } = Typography;
const { Panel } = Collapse;
const { Content } = Layout;

const FlowsPage: React.FC = () => {
  // const { user } = useAuth();
  const [createModalVisible, setCreateModalVisible] = useState(false);

  // Fetch user workspaces
  const { data: workspaces = [], isLoading: workspacesLoading } = useQuery({
    queryKey: ['user-workspaces'],
    queryFn: () => workspaceService.getUserWorkspaces(),
  });

  // Fetch flows
  const { data: flows = [], isLoading: flowsLoading } = useQuery({
    queryKey: ['flows'],
    queryFn: () => apiClient.get('/api/flows/').then(res => res.data),
  });

  const getWorkspaceTypeIcon = (type: WorkspaceTypeType) => {
    switch (type) {
      case 'personal':
        return <UserOutlined />;
      case 'team':
        return <TeamOutlined />;
      case 'organization':
        return <FolderOutlined />;
      default:
        return <FolderOutlined />;
    }
  };

  const getWorkspaceTypeColor = (type: WorkspaceTypeType) => {
    switch (type) {
      case 'personal':
        return 'blue';
      case 'team':
        return 'green';
      case 'organization':
        return 'purple';
      default:
        return 'default';
    }
  };

  // const hasPermission = (permission: PermissionTypeType, workspaceId: string) => {
  //   const workspace = workspaces.find(w => w.id === workspaceId);
  //   return workspace?.permissions?.includes(permission) || false;
  // };

  // Group flows by workspace
  const flowsByWorkspace = workspaces.map(workspace => {
    const workspaceFlows = flows.filter((flow: any) => flow.workspace_id === workspace.id);
    return {
      ...workspace,
      flows: workspaceFlows,
    };
  });

  const totalFlows = flows.length;
  const activeFlows = flows.filter((flow: any) => flow.status === 'active').length;

  if (workspacesLoading || flowsLoading) {
    return (
      <Content style={{ padding: '24px', textAlign: 'center' }}>
        <Spin size="large" />
      </Content>
    );
  }

  return (
    <Content style={{ padding: '24px' }}>
      <FlowsHeader
        onCreateFlow={() => setCreateModalVisible(true)}
        totalFlows={totalFlows}
        activeFlows={activeFlows}
        totalWorkspaces={workspaces.length}
      />

      {flowsByWorkspace.length === 0 ? (
        <Empty description="No workspaces available" />
      ) : (
        <Collapse
          expandIcon={({ isActive }) => <CaretRightOutlined rotate={isActive ? 90 : 0} />}
          ghost
        >
          {flowsByWorkspace.map(workspace => (
            <Panel
              header={
                <Space>
                  {getWorkspaceTypeIcon(workspace.type)}
                  <Text strong>{workspace.name}</Text>
                  <Tag color={getWorkspaceTypeColor(workspace.type)}>
                    {workspace.type.toUpperCase()}
                  </Tag>
                  <Text type="secondary">({workspace.flows.length} flows)</Text>
                </Space>
              }
              key={workspace.id}
            >
              <WorkspaceFlowList
                flows={workspace.flows}
                workspaceName={workspace.name}
              />
            </Panel>
          ))}
        </Collapse>
      )}

      <FlowCreateModal
        visible={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        workspaces={workspaces}
      />
    </Content>
  );
};

export default FlowsPage;