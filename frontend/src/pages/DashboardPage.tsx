/**
 * Dashboard Page - Workspace-aware Overview
 */

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Card, 
  Row, 
  Col, 
  Statistic, 
  Table, 
  Tag, 
  Button, 
  Space, 
  Typography, 
  List,
  Avatar,
  Divider
} from 'antd';
import { 
  PartitionOutlined, 
  PlayCircleOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined, 
  ClockCircleOutlined,
  FolderOutlined,
  TeamOutlined,
  UserOutlined,
  ApiOutlined,
  TrophyOutlined,
  RocketOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../services/api';
import { workspaceService } from '../services/workspace';
import type { Workspace, WorkspaceTypeType } from '../types';
import { WorkspaceType, PermissionType } from '../types';

const { Title, Text, Paragraph } = Typography;


interface Flow {
  id: string;
  name: string;
  workspace_id?: string;
  workspace_name?: string;
  current_version: number;
  created_at: string;
}

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Fetch workspaces
  const { data: workspaces, isLoading: workspacesLoading } = useQuery<Workspace[]>({
    queryKey: ['workspaces'],
    queryFn: workspaceService.list,
  });

  // Fetch flows
  const { data: flows, isLoading: flowsLoading } = useQuery<Flow[]>({
    queryKey: ['flows'],
    queryFn: async () => {
      const response = await apiClient.get('/api/flows/');
      return response.data;
    },
  });

  // Fetch executions
  const { data: executions, isLoading: executionsLoading } = useQuery<any[]>({
    queryKey: ['executions'],
    queryFn: async () => {
      const response = await apiClient.get('/api/executions/');
      return response.data;
    },
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'running':
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'processing';
      default:
        return 'default';
    }
  };

  const getWorkspaceIcon = (type: WorkspaceTypeType) => {
    return type === WorkspaceType.GROUP ? <TeamOutlined /> : <UserOutlined />;
  };

  // Calculate statistics
  const totalFlows = flows?.length || 0;
  const totalExecutions = executions?.length || 0;
  const totalWorkspaces = workspaces?.length || 0;
  const recentExecutions = executions?.slice(0, 5) || [];
  
  // Success rate calculation
  const completedExecutions = executions?.filter(e => e.status === 'completed').length || 0;
  const successRate = totalExecutions > 0 ? (completedExecutions / totalExecutions) * 100 : 0;

  // Workspace breakdown
  const userWorkspaces = workspaces?.filter(w => w.type === WorkspaceType.USER).length || 0;
  const groupWorkspaces = workspaces?.filter(w => w.type === WorkspaceType.GROUP).length || 0;

  // User's role summary
  const ownedWorkspaces = workspaces?.filter(w => w.user_permission === PermissionType.OWNER).length || 0;
  const adminWorkspaces = workspaces?.filter(w => w.user_permission === PermissionType.ADMIN).length || 0;

  const executionColumns = [
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag icon={getStatusIcon(status)} color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Flow',
      dataIndex: 'flow_id',
      key: 'flow_id',
      render: (flowId: string) => {
        const flow = flows?.find(f => f.id === flowId);
        return flow ? flow.name : `${flowId.substring(0, 8)}...`;
      },
    },
    {
      title: 'Workspace',
      dataIndex: 'flow_id',
      key: 'workspace',
      render: (flowId: string) => {
        const flow = flows?.find(f => f.id === flowId);
        return flow?.workspace_name ? (
          <Tag>{flow.workspace_name}</Tag>
        ) : (
          <Text type="secondary">-</Text>
        );
      },
    },
    {
      title: 'Started',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
  ];

  const isLoading = workspacesLoading || flowsLoading || executionsLoading;

  return (
    <div className="p-6 space-y-6">
        <div>
          <Title level={2} style={{ color: '#111827', marginBottom: '8px' }}>
            Welcome back, {user?.username}! 
            {user?.is_superuser && <Tag color="red" style={{ marginLeft: 8 }}>ADMIN</Tag>}
          </Title>
          <Paragraph style={{ color: '#6b7280', fontSize: '16px' }}>
            Here's an overview of your workflows and workspaces.
          </Paragraph>
        </div>
      
      {/* Main Stats Cards */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Flows"
              value={totalFlows}
              prefix={<PartitionOutlined />}
              loading={isLoading}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Workspaces"
              value={totalWorkspaces}
              prefix={<FolderOutlined />}
              loading={isLoading}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Executions"
              value={totalExecutions}
              prefix={<PlayCircleOutlined />}
              loading={isLoading}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Success Rate"
              value={Math.round(successRate)}
              suffix="%"
              prefix={<TrophyOutlined />}
              loading={isLoading}
              valueStyle={{ 
                color: successRate >= 80 ? '#52c41a' : successRate >= 60 ? '#faad14' : '#ff4d4f' 
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* Workspace Overview */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Workspace Overview" loading={isLoading}>
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="Personal"
                  value={userWorkspaces}
                  prefix={<UserOutlined />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Group"
                  value={groupWorkspaces}
                  prefix={<TeamOutlined />}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Col>
            </Row>
            <Divider />
            <Row gutter={[16, 16]}>
              <Col span={12}>
                <Statistic
                  title="Owned"
                  value={ownedWorkspaces}
                  prefix={<TrophyOutlined />}
                  valueStyle={{ color: '#cf1322' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Admin"
                  value={adminWorkspaces}
                  prefix={<RocketOutlined />}
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Top Workspaces" loading={isLoading}>
            <List
              dataSource={workspaces?.slice(0, 4)}
              renderItem={(workspace) => (
                <List.Item
                  actions={[
                    <Button 
                      type="link" 
                      size="small"
                      onClick={() => navigate('/workspaces')}
                    >
                      View
                    </Button>
                  ]}
                >
                  <List.Item.Meta
                    avatar={
                      <Avatar
                        icon={getWorkspaceIcon(workspace.type)}
                        size="small"
                        style={{
                          backgroundColor: workspace.type === WorkspaceType.GROUP ? '#1890ff' : '#52c41a',
                        }}
                      />
                    }
                    title={
                      <Space>
                        <span>{workspace.name}</span>
                        {workspace.user_permission && (
                          <Tag 
                            color={workspace.user_permission === PermissionType.OWNER ? 'red' : 'blue'}
                          >
                            {workspace.user_permission.toUpperCase()}
                          </Tag>
                        )}
                      </Space>
                    }
                    description={`${workspace.flow_count} flows`}
                  />
                </List.Item>
              )}
              locale={{ emptyText: 'No workspaces available' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Recent Activity */}
      <Card 
        title="Recent Executions" 
        extra={
          <Button type="link" onClick={() => navigate('/executions')}>
            View All
          </Button>
        }
        loading={isLoading}
      >
        <Table
          columns={executionColumns}
          dataSource={recentExecutions}
          rowKey="id"
          pagination={false}
          size="small"
          locale={{ emptyText: 'No recent executions' }}
        />
      </Card>

      {/* Quick Actions */}
      <Card title="Quick Actions">
        <Space wrap>
          <Button 
            type="primary" 
            icon={<PartitionOutlined />}
            onClick={() => navigate('/flows')}
          >
            Create Flow
          </Button>
          <Button 
            icon={<FolderOutlined />}
            onClick={() => navigate('/workspaces')}
          >
            Manage Workspaces
          </Button>
          <Button 
            icon={<PlayCircleOutlined />}
            onClick={() => navigate('/executions')}
          >
            View Executions
          </Button>
          <Button 
            icon={<ApiOutlined />}
            onClick={() => navigate('/api-deployments')}
          >
            API Deployments
          </Button>
          {user?.is_superuser && (
            <Button 
              icon={<RocketOutlined />}
              onClick={() => navigate('/system')}
            >
              System Status
            </Button>
          )}
        </Space>
      </Card>
    </div>
  );
};