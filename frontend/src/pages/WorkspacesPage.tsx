/**
 * Workspaces Page
 * Manage workspaces and organize flows
 */

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Typography,
  Card,
  Statistic,
  Row,
  Col,
  Tooltip,
  List,
  Avatar,
} from 'antd';
import {
  PlusOutlined,
  TeamOutlined,
  UserOutlined,
  DeleteOutlined,
  SettingOutlined,
  FolderOutlined,
  PartitionOutlined,
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import '../utils/debug-auth'; // Load debug utilities
import { workspaceService } from '../services/workspace';
import type { Workspace, WorkspaceTypeType, PermissionTypeType, CreateWorkspaceRequest } from '../types';
import { WorkspaceType, PermissionType } from '../types';
import { UserSelector } from '../components/workspace/UserSelector';
import { GroupSelector } from '../components/workspace/GroupSelector';
import type { UserPermission } from '../components/workspace/UserSelector';
import type { GroupPermission } from '../components/workspace/GroupSelector';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface CreateWorkspaceForm {
  name: string;
  description?: string;
  type: WorkspaceTypeType;
  group_id?: string;
}

export const WorkspacesPage: React.FC = () => {
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editingWorkspace, setEditingWorkspace] = useState<Workspace | null>(null);
  const [form] = Form.useForm<CreateWorkspaceForm>();
  const [editForm] = Form.useForm();
  const [selectedUsers, setSelectedUsers] = useState<UserPermission[]>([]);
  const [selectedGroups, setSelectedGroups] = useState<GroupPermission[]>([]);
  const queryClient = useQueryClient();
  const { user } = useAuth();

  // Fetch workspaces
  const { data: workspaces, isLoading } = useQuery<Workspace[]>({
    queryKey: ['workspaces'],
    queryFn: workspaceService.list,
  });

  // Create workspace mutation with permissions
  const createWorkspaceMutation = useMutation({
    mutationFn: async (data: {
      workspace: CreateWorkspaceRequest;
      userPermissions: Array<{ user_id: string; permission: PermissionTypeType }>;
      groupPermissions: Array<{ group_id: string; permission: PermissionTypeType }>;
    }) => {
      return workspaceService.createWithPermissions(
        data.workspace,
        data.userPermissions,
        data.groupPermissions
      );
    },
    onSuccess: () => {
      message.success('Workspace created successfully with permissions');
      handleModalClose();
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
    onError: (error: any) => {
      console.error('💥 Workspace creation error:', error);
      console.error('📋 Error response:', error.response);
      console.error('📋 Error status:', error.response?.status);
      console.error('📋 Error data:', error.response?.data);
      
      // Log detailed error information if it's an array
      if (error.response?.data?.detail && Array.isArray(error.response.data.detail)) {
        console.error('📋 Detailed validation errors:', error.response.data.detail);
        error.response.data.detail.forEach((err: any, index: number) => {
          console.error(`❌ Validation Error ${index + 1}:`, err);
        });
      }
      
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to create workspace';
      const statusCode = error.response?.status;
      
      // Provide more specific error messages based on the error
      if (statusCode === 400) {
        message.error('Invalid workspace data. Please check your input and try again.');
      } else if (statusCode === 422) {
        message.error('Workspace validation failed. Please check required fields.');
      } else if (statusCode === 500) {
        message.error('Server error occurred while creating workspace. Please try again or contact support.');
      } else if (errorMessage.includes('permission') || errorMessage.includes('unauthorized')) {
        message.error('You do not have permission to create workspaces or assign permissions');
      } else if (errorMessage.includes('user') && errorMessage.includes('not found')) {
        message.error('One or more selected users could not be found');
      } else if (errorMessage.includes('group') && errorMessage.includes('not found')) {
        message.error('One or more selected groups could not be found');
      } else if (errorMessage.includes('limit') || errorMessage.includes('quota')) {
        message.error('Workspace creation limit reached');
      } else {
        message.error(`Workspace creation failed: ${errorMessage}`);
      }
    },
  });

  // Update workspace mutation
  const updateWorkspaceMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => 
      workspaceService.update(id, data),
    onSuccess: () => {
      message.success('Workspace updated successfully');
      setEditingWorkspace(null);
      editForm.resetFields();
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || 'Failed to update workspace');
    },
  });

  // Delete workspace mutation
  const deleteWorkspaceMutation = useMutation({
    mutationFn: (workspaceId: string) => workspaceService.delete(workspaceId),
    onSuccess: () => {
      message.success('Workspace deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['workspaces'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || 'Failed to delete workspace');
    },
  });

  const handleCreateWorkspace = (values: CreateWorkspaceForm) => {
    // For group workspaces, validate that at least one group is selected
    if (values.type === WorkspaceType.TEAM && selectedGroups.length === 0) {
      message.error('Group workspace requires at least one group to be selected');
      return;
    }

    // For group workspaces, use the first selected group as the primary group
    let groupId = values.group_id;
    if (values.type === WorkspaceType.TEAM && selectedGroups.length > 0) {
      groupId = String(selectedGroups[0].groupId); // Ensure it's a string
      console.log('🏢 Using first selected group as primary group:', groupId, 'type:', typeof groupId);
    }

    const workspaceData: CreateWorkspaceRequest = {
      name: values.name,
      description: values.description,
      type: values.type as WorkspaceTypeType, // Ensure proper typing
      group_id: groupId,
    };
    
    console.log('🔍 Workspace data before sending:', {
      ...workspaceData,
      typeValue: values.type,
      typeIsString: typeof values.type === 'string',
      groupIdValue: groupId,
      groupIdIsString: typeof groupId === 'string',
    });
    
    const userPermissions = selectedUsers.map(up => ({
      user_id: up.userId,
      permission: up.permission,
    }));
    
    const groupPermissions = selectedGroups.map(gp => ({
      group_id: gp.groupId,
      permission: gp.permission,
    }));

    console.log('🎯 Creating workspace with permissions:', {
      workspace: workspaceData,
      userPermissions,
      groupPermissions,
      hasPermissions: userPermissions.length > 0 || groupPermissions.length > 0,
      isGroupWorkspace: values.type === WorkspaceType.TEAM,
      primaryGroupId: groupId,
    });

    createWorkspaceMutation.mutate({
      workspace: workspaceData,
      userPermissions,
      groupPermissions,
    });
  };

  const handleModalClose = () => {
    setCreateModalVisible(false);
    form.resetFields();
    setSelectedUsers([]);
    setSelectedGroups([]);
  };

  const handleUpdateWorkspace = (values: any) => {
    if (!editingWorkspace) return;
    
    updateWorkspaceMutation.mutate({
      id: editingWorkspace.id,
      data: values,
    });
  };

  const handleDeleteWorkspace = (workspaceId: string) => {
    deleteWorkspaceMutation.mutate(workspaceId);
  };

  const getWorkspaceTypeIcon = (type: WorkspaceTypeType) => {
    return type === WorkspaceType.TEAM ? <TeamOutlined /> : <UserOutlined />;
  };

  const getPermissionColor = (permission?: PermissionTypeType) => {
    switch (permission) {
      case PermissionType.OWNER:
        return 'red';
      case PermissionType.ADMIN:
        return 'orange';
      case PermissionType.MEMBER:
        return 'blue';
      case PermissionType.VIEWER:
        return 'default';
      default:
        return 'default';
    }
  };

  const canModifyWorkspace = (workspace: Workspace) => {
    return user?.is_superuser || 
           workspace.user_permission === PermissionType.OWNER ||
           workspace.user_permission === PermissionType.ADMIN;
  };

  const canDeleteWorkspace = (workspace: Workspace) => {
    return user?.is_superuser || workspace.user_permission === PermissionType.OWNER;
  };

  // Group workspaces by type
  console.log('📊 All workspaces:', workspaces);
  console.log('🔧 WorkspaceType constants:', { PERSONAL: WorkspaceType.PERSONAL, TEAM: WorkspaceType.TEAM });
  
  const userWorkspaces = workspaces?.filter(w => {
    console.log(`🔍 Workspace ${w.name}: type="${w.type}", matches PERSONAL: ${w.type === WorkspaceType.PERSONAL}`);
    return w.type === WorkspaceType.PERSONAL;
  }) || [];
  
  const groupWorkspaces = workspaces?.filter(w => {
    console.log(`🔍 Workspace ${w.name}: type="${w.type}", matches TEAM: ${w.type === WorkspaceType.TEAM}`);
    return w.type === WorkspaceType.TEAM;
  }) || [];

  console.log('👤 Personal workspaces:', userWorkspaces);
  console.log('🏢 Team workspaces:', groupWorkspaces);

  const renderWorkspaceList = (workspaces: Workspace[], title: string, icon: React.ReactNode) => {
    return (
      <Card
        title={
          <Space>
            {icon}
            <span>{title}</span>
            <Tag color="blue">{workspaces.length}</Tag>
          </Space>
        }
        size="small"
      >
        <List
          dataSource={workspaces}
          renderItem={(workspace) => (
            <List.Item
              actions={[
                <Tooltip title="Settings">
                  <Button
                    type="text"
                    size="small"
                    icon={<SettingOutlined />}
                    onClick={() => {
                      setEditingWorkspace(workspace);
                      editForm.setFieldsValue({
                        name: workspace.name,
                        description: workspace.description,
                      });
                    }}
                    disabled={!canModifyWorkspace(workspace)}
                  />
                </Tooltip>,
                <Popconfirm
                  title="Delete workspace"
                  description="Are you sure you want to delete this workspace? All flows will be moved to your default workspace."
                  onConfirm={() => handleDeleteWorkspace(workspace.id)}
                  okText="Yes"
                  cancelText="No"
                  disabled={!canDeleteWorkspace(workspace)}
                >
                  <Tooltip title="Delete">
                    <Button
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      disabled={!canDeleteWorkspace(workspace)}
                    />
                  </Tooltip>
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                avatar={
                  <Avatar
                    icon={getWorkspaceTypeIcon(workspace.type)}
                    style={{
                      backgroundColor: workspace.type === WorkspaceType.TEAM ? '#1890ff' : '#52c41a',
                    }}
                  />
                }
                title={
                  <Space>
                    <span>{workspace.name}</span>
                    {workspace.user_permission && (
                      <Tag color={getPermissionColor(workspace.user_permission)}>
                        {workspace.user_permission.toUpperCase()}
                      </Tag>
                    )}
                  </Space>
                }
                description={
                  <Space direction="vertical" size="small">
                    {workspace.description && <Text type="secondary">{workspace.description}</Text>}
                    <Space>
                      <Tag icon={<PartitionOutlined />} color="default">
                        {workspace.flow_count} flows
                      </Tag>
                      {workspace.group_id && (
                        <Tag color="blue">Group: {workspace.group_id}</Tag>
                      )}
                    </Space>
                  </Space>
                }
              />
            </List.Item>
          )}
          locale={{ emptyText: `No ${title.toLowerCase()} yet` }}
        />
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <Title level={2}>Workspaces</Title>
          <Paragraph>
            Organize your flows into workspaces for better collaboration and access control.
          </Paragraph>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateModalVisible(true)}
        >
          Create Workspace
        </Button>
      </div>

      {/* Summary Statistics */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Total Workspaces"
              value={workspaces?.length || 0}
              prefix={<FolderOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Personal Workspaces"
              value={userWorkspaces.length}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Team Workspaces"
              value={groupWorkspaces.length}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {isLoading ? (
        <Card loading />
      ) : (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            {renderWorkspaceList(userWorkspaces, 'Personal Workspaces', <UserOutlined />)}
          </Col>
          <Col xs={24} lg={12}>
            {renderWorkspaceList(groupWorkspaces, 'Team Workspaces', <TeamOutlined />)}
          </Col>
        </Row>
      )}

      {/* Create Workspace Modal */}
      <Modal
        title="Create Workspace"
        open={createModalVisible}
        onCancel={handleModalClose}
        footer={null}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreateWorkspace}
          initialValues={{
            type: WorkspaceType.PERSONAL,
          }}
        >
          <Form.Item
            name="name"
            label="Workspace Name"
            rules={[
              { required: true, message: 'Please enter a workspace name' },
              { max: 255, message: 'Name must be less than 255 characters' },
            ]}
          >
            <Input placeholder="e.g., My Data Science Projects" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
          >
            <TextArea
              rows={3}
              placeholder="Optional description of this workspace"
            />
          </Form.Item>

          <Form.Item
            name="type"
            label="Workspace Type"
            rules={[{ required: true, message: 'Please select workspace type' }]}
          >
            <Select>
              <Select.Option value={WorkspaceType.PERSONAL}>
                <Space>
                  <UserOutlined />
                  Personal Workspace
                </Space>
              </Select.Option>
              <Select.Option value={WorkspaceType.TEAM}>
                <Space>
                  <TeamOutlined />
                  Team Workspace
                </Space>
              </Select.Option>
            </Select>
          </Form.Item>

          {/* Permission Assignment Section */}
          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.type !== currentValues.type
            }
          >
            {({ getFieldValue }) => {
              const workspaceType = getFieldValue('type');
              
              if (workspaceType === WorkspaceType.PERSONAL) {
                return (
                  <Form.Item
                    label={
                      <Space>
                        <UserOutlined />
                        <span>Collaborate with Users</span>
                      </Space>
                    }
                  >
                    <UserSelector
                      value={selectedUsers}
                      onChange={setSelectedUsers}
                      placeholder="Search and add users to this workspace..."
                      maxUsers={20}
                      defaultPermission={PermissionType.MEMBER}
                      excludeUserIds={[]}
                    />
                  </Form.Item>
                );
              } else if (workspaceType === WorkspaceType.TEAM) {
                return (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Form.Item
                      label={
                        <Space>
                          <TeamOutlined />
                          <span>Primary Groups</span>
                        </Space>
                      }
                    >
                      <GroupSelector
                        value={selectedGroups}
                        onChange={setSelectedGroups}
                        placeholder="Search and add groups to this workspace..."
                        maxGroups={10}
                        defaultPermission={PermissionType.MEMBER}
                        includeSystemGroups={true}
                      />
                    </Form.Item>
                    
                    <Form.Item
                      label={
                        <Space>
                          <UserOutlined />
                          <span>Additional Users</span>
                        </Space>
                      }
                    >
                      <UserSelector
                        value={selectedUsers}
                        onChange={setSelectedUsers}
                        placeholder="Search and add individual users..."
                        maxUsers={50}
                        defaultPermission={PermissionType.VIEWER}
                        excludeUserIds={[]}
                      />
                    </Form.Item>
                  </Space>
                );
              }
              
              return null;
            }}
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={createWorkspaceMutation.isPending}
              >
                Create Workspace
              </Button>
              <Button onClick={handleModalClose}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit Workspace Modal */}
      <Modal
        title="Edit Workspace"
        open={!!editingWorkspace}
        onCancel={() => setEditingWorkspace(null)}
        footer={null}
        width={600}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleUpdateWorkspace}
        >
          <Form.Item
            name="name"
            label="Workspace Name"
            rules={[
              { required: true, message: 'Please enter a workspace name' },
              { max: 255, message: 'Name must be less than 255 characters' },
            ]}
          >
            <Input placeholder="e.g., My Data Science Projects" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
          >
            <TextArea
              rows={3}
              placeholder="Optional description of this workspace"
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={updateWorkspaceMutation.isPending}
              >
                Update Workspace
              </Button>
              <Button onClick={() => setEditingWorkspace(null)}>
                Cancel
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};