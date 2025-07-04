/**
 * Environment Variable Manager Component
 * 환경변수 관리를 위한 컴포넌트
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Modal,
  Table,
  Button,
  Form,
  Input,
  Select,
  Switch,
  Space,
  Tooltip,
  Typography,
  Alert,
  message,
  Popconfirm,
  Badge,
  Tag
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  LockOutlined,
  UnlockOutlined,
  GlobalOutlined,
  FolderOutlined,
  InfoCircleOutlined,
  SafetyOutlined
} from '@ant-design/icons';
import { SecureInput } from './SecureInput';
import './EnvironmentVariableManager.css';

const { Title, Text } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface EnvironmentVariable {
  id: string;
  key: string;
  value: string;
  description?: string;
  var_type: 'string' | 'secret' | 'url' | 'number' | 'boolean';
  category: 'database' | 'authentication' | 'llm_api' | 'infrastructure' | 'application' | 'custom';
  scope: 'system' | 'user' | 'workspace';
  is_secret: boolean;
  is_encrypted: boolean;
  is_system_managed: boolean;
  user_id: string;
  workspace_id?: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
  category_display_name?: string;
  scope_display_name?: string;
}

interface EnvironmentVariableManagerProps {
  visible: boolean;
  onClose: () => void;
  workspaceId?: string;
  onVariablesChange?: (variables: Record<string, string>) => void;
}

interface EnvironmentVariableForm {
  key: string;
  value: string;
  description?: string;
  var_type: 'string' | 'secret' | 'url' | 'number' | 'boolean';
  category: 'database' | 'authentication' | 'llm_api' | 'infrastructure' | 'application' | 'custom';
  scope: 'system' | 'user' | 'workspace';
  is_secret: boolean;
  workspace_id?: string;
}

export const EnvironmentVariableManager: React.FC<EnvironmentVariableManagerProps> = ({
  visible,
  onClose,
  workspaceId,
  onVariablesChange
}) => {
  const [variables, setVariables] = useState<EnvironmentVariable[]>([]);
  const [loading, setLoading] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [editingVariable, setEditingVariable] = useState<EnvironmentVariable | null>(null);
  const [form] = Form.useForm<EnvironmentVariableForm>();
  const [showValues, setShowValues] = useState<Record<string, boolean>>({});
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [categories, setCategories] = useState<any[]>([]);

  // 카테고리 목록 로드
  const loadCategories = useCallback(async () => {
    try {
      const response = await fetch('/api/environment-variables/categories/list', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setCategories(data.categories || []);
      }
    } catch {
      console.warn('카테고리 목록 로드 실패');
    }
  }, []);

  // 환경변수 목록 로드
  const loadVariables = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (workspaceId) {
        params.append('workspace_id', workspaceId);
      }
      params.append('include_global', 'true');
      
      if (selectedCategory !== 'all') {
        params.append('category', selectedCategory);
      }

      const response = await fetch(`/api/environment-variables?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setVariables(data);
        
        // Notify parent component of resolved variables
        if (onVariablesChange) {
          const resolvedVars: Record<string, string> = {};
          data.forEach((envVar: EnvironmentVariable) => {
            resolvedVars[envVar.key] = envVar.value;
          });
          onVariablesChange(resolvedVars);
        }
      } else {
        message.error('환경변수 목록을 불러오는데 실패했습니다.');
      }
    } catch {
      message.error('네트워크 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }, [workspaceId, onVariablesChange, selectedCategory]);

  useEffect(() => {
    if (visible) {
      loadCategories();
      loadVariables();
    }
  }, [visible, loadCategories, loadVariables]);

  // 환경변수 생성/수정
  const handleSaveVariable = async (values: EnvironmentVariableForm) => {
    try {
      const url = editingVariable
        ? `/api/environment-variables/${editingVariable.id}`
        : '/api/environment-variables';
      
      const method = editingVariable ? 'PUT' : 'POST';
      
      const payload = {
        ...values,
        workspace_id: values.workspace_id || workspaceId || null,
      };

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        message.success(
          editingVariable ? '환경변수가 수정되었습니다.' : '환경변수가 생성되었습니다.'
        );
        setEditModalVisible(false);
        setEditingVariable(null);
        form.resetFields();
        loadVariables();
      } else {
        const errorData = await response.json();
        message.error(errorData.detail || '환경변수 저장에 실패했습니다.');
      }
    } catch {
      message.error('네트워크 오류가 발생했습니다.');
    }
  };

  // 환경변수 삭제
  const handleDeleteVariable = async (id: string) => {
    try {
      const response = await fetch(`/api/environment-variables/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (response.ok) {
        message.success('환경변수가 삭제되었습니다.');
        loadVariables();
      } else {
        message.error('환경변수 삭제에 실패했습니다.');
      }
    } catch {
      message.error('네트워크 오류가 발생했습니다.');
    }
  };

  // 새 환경변수 추가
  const handleAddVariable = () => {
    setEditingVariable(null);
    form.resetFields();
    form.setFieldsValue({
      var_type: 'string',
      category: 'custom',
      scope: workspaceId ? 'workspace' : 'user',
      is_secret: false,
      workspace_id: workspaceId,
    });
    setEditModalVisible(true);
  };

  // 환경변수 수정
  const handleEditVariable = (variable: EnvironmentVariable) => {
    setEditingVariable(variable);
    form.setFieldsValue({
      key: variable.key,
      value: variable.is_secret ? '' : variable.value, // Don't pre-fill secret values
      description: variable.description,
      var_type: variable.var_type,
      category: variable.category,
      scope: variable.scope,
      is_secret: variable.is_secret,
      workspace_id: variable.workspace_id,
    });
    setEditModalVisible(true);
  };

  // 값 표시/숨김 토글
  const toggleValueVisibility = (id: string) => {
    setShowValues(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  // 테이블 컬럼 정의
  const columns = [
    {
      title: '키',
      dataIndex: 'key',
      key: 'key',
      render: (key: string, record: EnvironmentVariable) => (
        <Space>
          <Text strong>{key}</Text>
          {record.scope === 'workspace' ? (
            <Tooltip title="워크스페이스 환경변수">
              <FolderOutlined style={{ color: '#1890ff' }} />
            </Tooltip>
          ) : record.scope === 'system' ? (
            <Tooltip title="시스템 환경변수">
              <SafetyOutlined style={{ color: '#ff7a00' }} />
            </Tooltip>
          ) : (
            <Tooltip title="사용자 환경변수">
              <GlobalOutlined style={{ color: '#52c41a' }} />
            </Tooltip>
          )}
        </Space>
      ),
    },
    {
      title: '값',
      dataIndex: 'value',
      key: 'value',
      render: (value: string, record: EnvironmentVariable) => (
        <Space>
          {record.is_secret ? (
            <Space>
              <Text code style={{ fontFamily: 'monospace' }}>
                {showValues[record.id] ? value : '••••••••••••••••'}
              </Text>
              <Button
                type="text"
                size="small"
                icon={showValues[record.id] ? <EyeInvisibleOutlined /> : <EyeOutlined />}
                onClick={() => toggleValueVisibility(record.id)}
              />
            </Space>
          ) : (
            <Text code style={{ fontFamily: 'monospace', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {value}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: '타입',
      dataIndex: 'var_type',
      key: 'var_type',
      render: (type: string) => {
        const typeColors: Record<string, string> = {
          string: 'default',
          secret: 'red',
          url: 'blue',
          number: 'green',
          boolean: 'orange',
        };
        return <Tag color={typeColors[type]}>{type.toUpperCase()}</Tag>;
      },
    },
    {
      title: '보안',
      dataIndex: 'is_secret',
      key: 'is_secret',
      render: (isSecret: boolean) => (
        <Badge
          status={isSecret ? 'error' : 'default'}
          text={isSecret ? '보안' : '일반'}
        />
      ),
    },
    {
      title: '카테고리',
      dataIndex: 'category_display_name',
      key: 'category',
      render: (categoryName: string, record: EnvironmentVariable) => {
        const categoryColors: Record<string, string> = {
          database: 'blue',
          authentication: 'green',
          llm_api: 'purple',
          infrastructure: 'orange',
          application: 'cyan',
          custom: 'default',
        };
        return (
          <Tag color={categoryColors[record.category]}>
            {categoryName || record.category}
          </Tag>
        );
      },
    },
    {
      title: '설명',
      dataIndex: 'description',
      key: 'description',
      render: (description: string) => (
        <Text type="secondary" style={{ maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {description || '-'}
        </Text>
      ),
    },
    {
      title: '작업',
      key: 'actions',
      render: (_: any, record: EnvironmentVariable) => (
        <Space>
          <Tooltip title="수정">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEditVariable(record)}
              disabled={record.is_system_managed && record.scope === 'system'}
            />
          </Tooltip>
          <Popconfirm
            title="환경변수를 삭제하시겠습니까?"
            description="이 작업은 되돌릴 수 없습니다."
            onConfirm={() => handleDeleteVariable(record.id)}
            okText="삭제"
            cancelText="취소"
          >
            <Tooltip title="삭제">
              <Button
                type="text"
                size="small"
                icon={<DeleteOutlined />}
                danger
                disabled={record.is_system_managed && record.scope === 'system'}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Modal
        title={
          <Space>
            <LockOutlined />
            환경변수 관리
            {workspaceId && <Tag color="blue">워크스페이스</Tag>}
          </Space>
        }
        open={visible}
        onCancel={onClose}
        width={1000}
        footer={[
          <Button key="close" onClick={onClose}>
            닫기
          </Button>,
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Alert
            message="환경변수 정보"
            description={
              <ul style={{ margin: 0, paddingLeft: '16px' }}>
                <li>전역 환경변수는 모든 워크스페이스에서 사용할 수 있습니다</li>
                <li>워크스페이스 환경변수는 해당 워크스페이스에서만 사용할 수 있습니다</li>
                <li>같은 키의 환경변수가 있을 경우 워크스페이스 &gt; 전역 순으로 우선됩니다</li>
                <li>보안 환경변수는 암호화되어 저장되며 마스킹 처리됩니다</li>
              </ul>
            }
            type="info"
            showIcon
            style={{ marginBottom: '16px' }}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <Space>
              <Title level={5} style={{ margin: 0 }}>
                환경변수 목록 ({variables.length}개)
              </Title>
              <Select
                value={selectedCategory}
                onChange={setSelectedCategory}
                style={{ width: '180px' }}
                placeholder="카테고리 선택"
              >
                <Option value="all">전체 카테고리</Option>
                {categories.map((category) => (
                  <Option key={category.value} value={category.value}>
                    {category.label}
                  </Option>
                ))}
              </Select>
            </Space>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAddVariable}
            >
              환경변수 추가
            </Button>
          </div>

          <Table
            columns={columns}
            dataSource={variables}
            rowKey="id"
            loading={loading}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showTotal: (total) => `총 ${total}개`,
            }}
            scroll={{ x: 800 }}
          />
        </Space>
      </Modal>

      {/* 환경변수 추가/수정 모달 */}
      <Modal
        title={editingVariable ? '환경변수 수정' : '환경변수 추가'}
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          setEditingVariable(null);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        okText={editingVariable ? '수정' : '생성'}
        cancelText="취소"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSaveVariable}
        >
          <Form.Item
            name="key"
            label="키"
            rules={[
              { required: true, message: '키를 입력하세요' },
              { pattern: /^[A-Z][A-Z0-9_]*$/, message: '키는 대문자와 숫자, 언더스코어만 사용 가능합니다' }
            ]}
          >
            <Input placeholder="EXAMPLE_ENV_VAR" />
          </Form.Item>

          <Form.Item noStyle shouldUpdate={(prev, curr) => prev.is_secret !== curr.is_secret}>
            {({ getFieldValue }) => {
              const isSecret = getFieldValue('is_secret');
              return (
                <Form.Item
                  name="value"
                  label="값"
                  rules={[{ required: true, message: '값을 입력하세요' }]}
                >
                  {isSecret ? (
                    <SecureInput
                      placeholder="환경변수 값"
                      type="password"
                    />
                  ) : (
                    <Input placeholder="환경변수 값" />
                  )}
                </Form.Item>
              );
            }}
          </Form.Item>

          <Form.Item
            name="description"
            label="설명"
          >
            <TextArea
              rows={2}
              placeholder="환경변수에 대한 설명을 입력하세요"
            />
          </Form.Item>

          <Form.Item
            name="var_type"
            label="타입"
            rules={[{ required: true, message: '타입을 선택하세요' }]}
          >
            <Select placeholder="타입 선택">
              <Option value="string">문자열</Option>
              <Option value="secret">보안 문자열</Option>
              <Option value="url">URL</Option>
              <Option value="number">숫자</Option>
              <Option value="boolean">불린</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="category"
            label="카테고리"
            rules={[{ required: true, message: '카테고리를 선택하세요' }]}
          >
            <Select placeholder="카테고리 선택">
              {categories.map((category) => (
                <Option key={category.value} value={category.value}>
                  {category.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="scope"
            label="범위"
            rules={[{ required: true, message: '범위를 선택하세요' }]}
          >
            <Select placeholder="범위 선택">
              <Option value="user">사용자</Option>
              <Option value="workspace">워크스페이스</Option>
              <Option value="system" disabled>시스템 (관리자 전용)</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="is_secret"
            label={
              <Space>
                보안 환경변수
                <Tooltip title="보안 환경변수는 암호화되어 저장되며, 값이 마스킹 처리됩니다">
                  <InfoCircleOutlined />
                </Tooltip>
              </Space>
            }
            valuePropName="checked"
          >
            <Switch checkedChildren={<LockOutlined />} unCheckedChildren={<UnlockOutlined />} />
          </Form.Item>

        </Form>
      </Modal>
    </>
  );
};