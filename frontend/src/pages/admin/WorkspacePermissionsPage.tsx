/**
 * 워크스페이스 권한 관리 페이지 (관리자 전용)
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Select,
  Space,
  Typography,
  message,
  Modal,
  Form,
  Input,
  Tag,
  Tooltip,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Tabs,
  Result
} from 'antd';
import {
  UserAddOutlined,
  TeamOutlined,
  SettingOutlined,
  DeleteOutlined,
  ReloadOutlined,
  SearchOutlined,
  SafetyOutlined
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../services/api';

const { Title, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  group_id?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

interface Group {
  id: string;
  name: string;
  description?: string;
  is_active: boolean;
  is_system_group: boolean;
  member_count: number;
  workspace_count: number;
  created_at: string;
  updated_at: string;
  created_by?: string;
}

interface Workspace {
  id: string;
  name: string;
  description?: string;
  type: 'user' | 'group';
  creator_user_id: string;
  group_id?: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  flow_count: number;
}

interface WorkspacePermission {
  mapping_id: string;
  user_id?: string;
  username?: string;
  email?: string;
  group_id?: string;
  group_name?: string;
  permission_level: 'owner' | 'admin' | 'member' | 'viewer';
  assigned_at?: string;
  assigned_by?: string;
}

interface WorkspacePermissions {
  workspace_id: string;
  user_permissions: WorkspacePermission[];
  group_permissions: WorkspacePermission[];
}

export const WorkspacePermissionsPage: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>('');
  const [workspacePermissions, setWorkspacePermissions] = useState<WorkspacePermissions | null>(null);
  const [assignModalVisible, setAssignModalVisible] = useState(false);
  const [assignForm] = Form.useForm();
  const [stats, setStats] = useState<any>(null);

  // 관리자 권한 확인
  if (!user?.is_superuser) {
    return (
      <Card>
        <Result
          status="403"
          title="403"
          subTitle="이 페이지에 접근할 권한이 없습니다."
          extra={<Button type="primary" href="/dashboard">대시보드로 돌아가기</Button>}
        />
      </Card>
    );
  }

  // 데이터 로드
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        loadWorkspaces(),
        loadUsers(),
        loadGroups(),
        loadStats()
      ]);
    } catch (error) {
      message.error('데이터 로드 실패');
    } finally {
      setLoading(false);
    }
  };

  const loadWorkspaces = async () => {
    try {
      console.log('🔍 DEBUG - Loading workspaces via apiClient');
      
      const response = await api.workspaces.list();
      console.log('🔍 DEBUG - Workspaces API response:', response);
      
      if (response.data) {
        console.log('🔍 DEBUG - Workspaces data received:', response.data);
        setWorkspaces(response.data);
      }
    } catch (error: any) {
      console.error('워크스페이스 로드 실패:', error);
      if (error.response) {
        console.error('🔍 DEBUG - Workspaces API error response:', {
          status: error.response.status,
          statusText: error.response.statusText,
          data: error.response.data
        });
      }
    }
  };

  const loadUsers = async () => {
    try {
      console.log('🔍 DEBUG - Loading users via apiClient');
      
      const response = await api.admin.users();
      console.log('🔍 DEBUG - Users API response:', response);
      
      if (response.data) {
        console.log('🔍 DEBUG - Users data received:', response.data);
        setUsers(response.data);
      }
    } catch (error: any) {
      console.error('사용자 로드 실패:', error);
      if (error.response) {
        console.error('🔍 DEBUG - Users API error response:', {
          status: error.response.status,
          statusText: error.response.statusText,
          data: error.response.data
        });
        message.error(`사용자 목록 로드 실패: ${error.response.status} ${error.response.statusText}`);
      } else {
        message.error('사용자 목록 로드 중 네트워크 오류가 발생했습니다.');
      }
    }
  };

  const loadGroups = async () => {
    try {
      console.log('🔍 DEBUG - Loading groups via apiClient');
      
      const response = await api.admin.groups();
      console.log('🔍 DEBUG - Groups API response:', response);
      
      if (response.data) {
        console.log('🔍 DEBUG - Groups data received:', response.data);
        setGroups(response.data);
      }
    } catch (error: any) {
      console.error('그룹 로드 실패:', error);
      if (error.response) {
        console.error('🔍 DEBUG - Groups API error response:', {
          status: error.response.status,
          statusText: error.response.statusText,
          data: error.response.data
        });
        message.error(`그룹 목록 로드 실패: ${error.response.status} ${error.response.statusText}`);
      } else {
        message.error('그룹 목록 로드 중 네트워크 오류가 발생했습니다.');
      }
    }
  };

  const loadStats = async () => {
    try {
      console.log('🔍 DEBUG - Loading stats via apiClient');
      
      const response = await api.admin.stats();
      console.log('🔍 DEBUG - Stats API response:', response);
      
      if (response.data) {
        console.log('🔍 DEBUG - Stats data received:', response.data);
        setStats(response.data);
      }
    } catch (error: any) {
      console.error('통계 로드 실패:', error);
      if (error.response) {
        console.error('🔍 DEBUG - Stats API error response:', {
          status: error.response.status,
          statusText: error.response.statusText,
          data: error.response.data
        });
      }
    }
  };

  const loadWorkspacePermissions = async (workspaceId: string) => {
    try {
      console.log('🔍 DEBUG - Loading workspace permissions via apiClient', workspaceId);
      
      const response = await api.workspaces.permissions.get(workspaceId);
      console.log('🔍 DEBUG - Workspace permissions API response:', response);
      
      if (response.data) {
        console.log('🔍 DEBUG - Workspace permissions data received:', response.data);
        setWorkspacePermissions(response.data);
      }
    } catch (error: any) {
      console.error('워크스페이스 권한 로드 실패:', error);
      if (error.response) {
        console.error('🔍 DEBUG - Workspace permissions API error response:', {
          status: error.response.status,
          statusText: error.response.statusText,
          data: error.response.data
        });
      }
      message.error('워크스페이스 권한 로드 실패');
    }
  };

  const handleWorkspaceChange = (workspaceId: string) => {
    setSelectedWorkspace(workspaceId);
    if (workspaceId) {
      loadWorkspacePermissions(workspaceId);
    } else {
      setWorkspacePermissions(null);
    }
  };

  const handleAssignPermission = async (values: any) => {
    try {
      console.log('🔍 DEBUG - Assigning permission via apiClient', values);
      
      const response = await api.workspaces.permissions.assign(selectedWorkspace, values);
      console.log('🔍 DEBUG - Assign permission API response:', response);

      message.success('권한이 성공적으로 할당되었습니다.');
      setAssignModalVisible(false);
      assignForm.resetFields();
      loadWorkspacePermissions(selectedWorkspace);
    } catch (error: any) {
      console.error('권한 할당 실패:', error);
      if (error.response) {
        console.error('🔍 DEBUG - Assign permission API error response:', {
          status: error.response.status,
          statusText: error.response.statusText,
          data: error.response.data
        });
        message.error(error.response.data?.detail || '권한 할당 실패');
      } else {
        message.error('네트워크 오류');
      }
    }
  };

  const handleRemovePermission = async (mappingType: string, mappingId: string) => {
    try {
      console.log('🔍 DEBUG - Removing permission via apiClient', { mappingType, mappingId });
      
      const response = await api.workspaces.permissions.remove(selectedWorkspace, mappingType, mappingId);
      console.log('🔍 DEBUG - Remove permission API response:', response);

      message.success('권한이 성공적으로 제거되었습니다.');
      loadWorkspacePermissions(selectedWorkspace);
    } catch (error: any) {
      console.error('권한 제거 실패:', error);
      if (error.response) {
        console.error('🔍 DEBUG - Remove permission API error response:', {
          status: error.response.status,
          statusText: error.response.statusText,
          data: error.response.data
        });
        message.error(error.response.data?.detail || '권한 제거 실패');
      } else {
        message.error('네트워크 오류');
      }
    }
  };

  const getPermissionColor = (level: string) => {
    const colors = {
      owner: 'red',
      admin: 'orange',
      member: 'blue',
      viewer: 'green',
    };
    return colors[level as keyof typeof colors] || 'default';
  };

  const userPermissionColumns = [
    {
      title: '사용자',
      key: 'user',
      render: (record: WorkspacePermission) => (
        <Space>
          <Text strong>{record.username}</Text>
          <Text type="secondary">({record.email})</Text>
        </Space>
      ),
    },
    {
      title: '권한 레벨',
      dataIndex: 'permission_level',
      key: 'permission_level',
      render: (level: string) => (
        <Tag color={getPermissionColor(level)}>
          {level.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: '할당일시',
      dataIndex: 'assigned_at',
      key: 'assigned_at',
      render: (date: string) => date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: '작업',
      key: 'actions',
      render: (record: WorkspacePermission) => (
        <Popconfirm
          title="권한을 제거하시겠습니까?"
          onConfirm={() => handleRemovePermission('user', record.mapping_id)}
          okText="제거"
          cancelText="취소"
        >
          <Button type="text" icon={<DeleteOutlined />} danger size="small" />
        </Popconfirm>
      ),
    },
  ];

  const groupPermissionColumns = [
    {
      title: '그룹',
      key: 'group',
      render: (record: WorkspacePermission) => (
        <Space>
          <TeamOutlined />
          <Text strong>{record.group_name}</Text>
        </Space>
      ),
    },
    {
      title: '권한 레벨',
      dataIndex: 'permission_level',
      key: 'permission_level',
      render: (level: string) => (
        <Tag color={getPermissionColor(level)}>
          {level.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: '할당일시',
      dataIndex: 'assigned_at',
      key: 'assigned_at',
      render: (date: string) => date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: '작업',
      key: 'actions',
      render: (record: WorkspacePermission) => (
        <Popconfirm
          title="권한을 제거하시겠습니까?"
          onConfirm={() => handleRemovePermission('group', record.mapping_id)}
          okText="제거"
          cancelText="취소"
        >
          <Button type="text" icon={<DeleteOutlined />} danger size="small" />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <Space align="center" style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <SafetyOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
                <Title level={2} style={{ margin: 0 }}>
                  워크스페이스 권한 관리
                </Title>
              </Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={loadInitialData}
                loading={loading}
              >
                새로고침
              </Button>
            </Space>
          </Card>
        </Col>

        {/* 통계 카드 */}
        {stats && (
          <Col span={24}>
            <Row gutter={16}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="전체 사용자"
                    value={stats.users?.total || 0}
                    prefix={<UserAddOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="전체 그룹"
                    value={stats.groups?.total || 0}
                    prefix={<TeamOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="전체 워크스페이스"
                    value={stats.workspaces?.total || 0}
                    prefix={<SettingOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="활성 워크스페이스"
                    value={stats.workspaces?.active || 0}
                    prefix={<SettingOutlined />}
                  />
                </Card>
              </Col>
            </Row>
          </Col>
        )}

        {/* 워크스페이스 선택 */}
        <Col span={24}>
          <Card title="워크스페이스 선택">
            <Row gutter={16} align="middle">
              <Col span={12}>
                <Select
                  placeholder="권한을 관리할 워크스페이스를 선택하세요"
                  style={{ width: '100%' }}
                  value={selectedWorkspace}
                  onChange={handleWorkspaceChange}
                  showSearch
                  optionFilterProp="children"
                >
                  {workspaces.map((workspace) => (
                    <Option key={workspace.id} value={workspace.id}>
                      <Space>
                        <Text strong>{workspace.name}</Text>
                        <Tag color={workspace.type === 'group' ? 'blue' : 'green'}>
                          {workspace.type === 'group' ? '그룹' : '개인'}
                        </Tag>
                        <Text type="secondary">({workspace.flow_count}개 플로우)</Text>
                      </Space>
                    </Option>
                  ))}
                </Select>
              </Col>
              <Col span={6}>
                <Button
                  type="primary"
                  icon={<UserAddOutlined />}
                  onClick={() => setAssignModalVisible(true)}
                  disabled={!selectedWorkspace}
                >
                  권한 할당
                </Button>
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 권한 목록 */}
        {workspacePermissions && (
          <Col span={24}>
            <Card title="워크스페이스 권한 목록">
              <Tabs defaultActiveKey="users">
                <TabPane 
                  tab={<span><UserAddOutlined />사용자 권한 ({workspacePermissions.user_permissions.length})</span>} 
                  key="users"
                >
                  <Table
                    columns={userPermissionColumns}
                    dataSource={workspacePermissions.user_permissions}
                    rowKey="mapping_id"
                    pagination={{ pageSize: 10 }}
                    locale={{ emptyText: '할당된 사용자 권한이 없습니다.' }}
                  />
                </TabPane>
                <TabPane 
                  tab={<span><TeamOutlined />그룹 권한 ({workspacePermissions.group_permissions.length})</span>} 
                  key="groups"
                >
                  <Table
                    columns={groupPermissionColumns}
                    dataSource={workspacePermissions.group_permissions}
                    rowKey="mapping_id"
                    pagination={{ pageSize: 10 }}
                    locale={{ emptyText: '할당된 그룹 권한이 없습니다.' }}
                  />
                </TabPane>
              </Tabs>
            </Card>
          </Col>
        )}
      </Row>

      {/* 권한 할당 모달 */}
      <Modal
        title="권한 할당"
        open={assignModalVisible}
        onCancel={() => {
          setAssignModalVisible(false);
          assignForm.resetFields();
        }}
        onOk={() => assignForm.submit()}
        okText="할당"
        cancelText="취소"
      >
        <Form
          form={assignForm}
          layout="vertical"
          onFinish={handleAssignPermission}
        >
          <Form.Item
            name="assignment_type"
            label="할당 유형"
            rules={[{ required: true, message: '할당 유형을 선택하세요' }]}
            initialValue="user"
          >
            <Select onChange={() => assignForm.resetFields(['target_id'])}>
              <Option value="user">사용자</Option>
              <Option value="group">그룹</Option>
            </Select>
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.assignment_type !== curr.assignment_type}>
            {({ getFieldValue }) => {
              const assignmentType = getFieldValue('assignment_type');
              return (
                <Form.Item
                  name={assignmentType === 'user' ? 'user_id' : 'group_id'}
                  label={assignmentType === 'user' ? '사용자 선택' : '그룹 선택'}
                  rules={[{ required: true, message: `${assignmentType === 'user' ? '사용자' : '그룹'}을 선택하세요` }]}
                >
                  <Select
                    placeholder={`${assignmentType === 'user' ? '사용자' : '그룹'}을 선택하세요`}
                    showSearch
                    optionFilterProp="children"
                  >
                    {assignmentType === 'user'
                      ? users.map((user) => (
                          <Option key={user.id} value={user.id}>
                            <Space>
                              <Text>{user.username}</Text>
                              <Text type="secondary">({user.email})</Text>
                            </Space>
                          </Option>
                        ))
                      : groups.map((group) => (
                          <Option key={group.id} value={group.id}>
                            <Space>
                              <TeamOutlined />
                              <Text>{group.name}</Text>
                              <Text type="secondary">({group.member_count}명)</Text>
                            </Space>
                          </Option>
                        ))
                    }
                  </Select>
                </Form.Item>
              );
            }}
          </Form.Item>

          <Form.Item
            name="permission_level"
            label="권한 레벨"
            rules={[{ required: true, message: '권한 레벨을 선택하세요' }]}
          >
            <Select placeholder="권한 레벨을 선택하세요">
              <Option value="viewer">
                <Tag color="green">VIEWER</Tag>
                <Text> - 읽기 전용</Text>
              </Option>
              <Option value="member">
                <Tag color="blue">MEMBER</Tag>
                <Text> - 플로우 생성/편집</Text>
              </Option>
              <Option value="admin">
                <Tag color="orange">ADMIN</Tag>
                <Text> - 멤버 관리</Text>
              </Option>
              <Option value="owner">
                <Tag color="red">OWNER</Tag>
                <Text> - 모든 권한</Text>
              </Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};