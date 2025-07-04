/**
 * 파일명: DeploymentTable.tsx (180줄)
 * 목적: API 배포 목록 테이블 컴포넌트
 * 동작 과정:
 * 1. 배포 목록을 테이블 형태로 표시
 * 2. 상태 변경, 삭제 등 액션 버튼 제공
 * 3. 배포 상세 정보 및 엔드포인트 복사 기능
 * 데이터베이스 연동: api_deployments 테이블에서 데이터 조회/수정
 * 의존성: 없음 (독립적 테이블 컴포넌트)
 */

import React, { useState } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Popconfirm,
  message,
  Typography,
  Modal,
  Tabs,
  Alert,
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
  CopyOutlined,
  SettingOutlined,
  CheckOutlined,
  CloseOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../services/api';

const { Text } = Typography;

interface DeploymentTableProps {
  deployments: any[];
  loading: boolean;
  onEdit: (deployment: any) => void;
}

export const DeploymentTable: React.FC<DeploymentTableProps> = ({
  deployments,
  loading,
  onEdit,
}) => {
  const queryClient = useQueryClient();
  const [usageModalVisible, setUsageModalVisible] = useState(false);
  const [selectedDeployment, setSelectedDeployment] = useState<any>(null);

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      apiClient.put(`/api/deployments/${id}/status`, { status }),
    onSuccess: () => {
      message.success('Deployment status updated');
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
    },
    onError: () => {
      message.error('Failed to update deployment status');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/api/deployments/${id}`),
    onSuccess: () => {
      message.success('Deployment deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
    },
    onError: () => {
      message.error('Failed to delete deployment');
    },
  });

  const handleStatusToggle = (deployment: any) => {
    const newStatus = deployment.status === 'active' ? 'inactive' : 'active';
    updateStatusMutation.mutate({ id: deployment.id, status: newStatus });
  };

  const handleApprove = (deployment: any) => {
    updateStatusMutation.mutate({ 
      id: deployment.id, 
      status: 'active' 
    });
    message.success(`Deployment "${deployment.name}" approved and activated!`);
  };

  const handleReject = (deployment: any) => {
    updateStatusMutation.mutate({ 
      id: deployment.id, 
      status: 'inactive' 
    });
    message.warning(`Deployment "${deployment.name}" rejected.`);
  };

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id);
  };

  const handleCopyFullUrl = (deployment: any) => {
    const fullUrl = `http://localhost:8005/api/deployed${deployment.endpoint_path}`;
    navigator.clipboard.writeText(fullUrl);
    message.success('전체 URL이 클립보드에 복사되었습니다');
  };

  const handleCopyRelativePath = (deployment: any) => {
    const relativePath = `/api/deployed${deployment.endpoint_path}`;
    navigator.clipboard.writeText(relativePath);
    message.success('상대 경로가 클립보드에 복사되었습니다');
  };

  const handleShowUsage = (deployment: any) => {
    setSelectedDeployment(deployment);
    setUsageModalVisible(true);
  };

  const generateCurlExample = (deployment: any) => {
    const endpoint = `http://localhost:8005/api/deployed${deployment.endpoint_path}`;
    const authHeader = deployment.requires_auth ? `  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\` : '';
    
    return `curl -X POST ${endpoint} \\${authHeader}
  -H "Content-Type: application/json" \\
  -d '{
    "field1": "value1",
    "field2": "value2"
  }'`;
  };

  const generatePythonExample = (deployment: any) => {
    const endpoint = `http://localhost:8005/api/deployed${deployment.endpoint_path}`;
    const authHeader = deployment.requires_auth ? `    "Authorization": "Bearer YOUR_JWT_TOKEN",` : '';
    
    return `import requests

url = "${endpoint}"
headers = {${authHeader}
    "Content-Type": "application/json"
}
data = {
    "field1": "value1",
    "field2": "value2"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())`;
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'inactive':
        return 'default';
      case 'pending':
        return 'processing';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          {record.description && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.description}
            </Text>
          )}
        </div>
      ),
    },
    {
      title: 'Endpoint',
      dataIndex: 'endpoint_path',
      key: 'endpoint_path',
      width: 350,
      render: (path: string, record: any) => (
        <div style={{ fontSize: '12px' }}>
          <div style={{ marginBottom: '4px' }}>
            <Text strong style={{ fontSize: '11px', color: '#666666' }}>전체 URL:</Text>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
              <Text 
                code 
                style={{ 
                  fontSize: '11px', 
                  padding: '2px 6px',
                  backgroundColor: '#f5f5f5',
                  border: '1px solid #e8e8e8',
                  borderRadius: '4px',
                  flex: 1,
                  wordBreak: 'break-all'
                }}
              >
                http://localhost:8005/api/deployed{path}
              </Text>
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  handleCopyFullUrl(record);
                }}
                style={{ 
                  minWidth: '24px', 
                  height: '24px', 
                  padding: '0',
                  fontSize: '10px'
                }}
                title="전체 URL 복사"
              />
            </div>
          </div>
          <div>
            <Text strong style={{ fontSize: '11px', color: '#666666' }}>상대 경로:</Text>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
              <Text 
                code 
                style={{ 
                  fontSize: '11px', 
                  padding: '2px 6px',
                  backgroundColor: '#f9f9f9',
                  border: '1px solid #e8e8e8',
                  borderRadius: '4px',
                  flex: 1,
                  wordBreak: 'break-all'
                }}
              >
                /api/deployed{path}
              </Text>
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  handleCopyRelativePath(record);
                }}
                style={{ 
                  minWidth: '24px', 
                  height: '24px', 
                  padding: '0',
                  fontSize: '10px'
                }}
                title="상대 경로 복사"
              />
            </div>
          </div>
        </div>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Type',
      key: 'type',
      render: (record: any) => (
        <Space direction="vertical" size="small">
          <Tag color={record.flow_id ? 'blue' : 'green'}>
            {record.flow_id ? 'Flow' : 'API'}
          </Tag>
          {record.version && <Tag>{record.version}</Tag>}
        </Space>
      ),
    },
    {
      title: 'Requests',
      dataIndex: 'total_requests',
      key: 'total_requests',
      render: (count: number) => count.toLocaleString(),
    },
    {
      title: 'Last Request',
      dataIndex: 'last_request_at',
      key: 'last_request_at',
      render: (date: string) => date ? formatDate(date) : 'Never',
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => formatDate(date),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: any) => (
        <Space size="small">
          {/* 승인 대기 상태일 때 승인/거부 버튼 표시 */}
          {record.status === 'pending' && (
            <>
              <Button
                type="text"
                icon={<CheckOutlined />}
                onClick={() => handleApprove(record)}
                loading={updateStatusMutation.isPending}
                title="승인하여 활성화"
                style={{ color: '#52c41a' }}
              />
              <Button
                type="text"
                icon={<CloseOutlined />}
                onClick={() => handleReject(record)}
                loading={updateStatusMutation.isPending}
                title="승인 거부"
                style={{ color: '#ff4d4f' }}
              />
            </>
          )}
          
          {/* 일반 상태 토글 버튼 */}
          {record.status !== 'pending' && (
            <Button
              type="text"
              icon={record.status === 'active' ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              onClick={() => handleStatusToggle(record)}
              loading={updateStatusMutation.isPending}
              title={record.status === 'active' ? 'Pause' : 'Activate'}
            />
          )}
          
          <Button
            type="text"
            icon={<QuestionCircleOutlined />}
            onClick={() => handleShowUsage(record)}
            title="API 사용법 보기"
            style={{ color: '#1890ff' }}
          />
          
          
          <Button
            type="text"
            icon={<SettingOutlined />}
            onClick={() => onEdit(record)}
            title="Edit deployment"
          />
          
          <Popconfirm
            title="Are you sure you want to delete this deployment?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              loading={deleteMutation.isPending}
              title="Delete deployment"
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Table
        columns={columns}
        dataSource={deployments}
        loading={loading}
        rowKey="id"
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `Total ${total} deployments`,
        }}
      />
      
      {/* API Usage Guide Modal */}
      <Modal
        title={`API 사용법: ${selectedDeployment?.name}`}
        open={usageModalVisible}
        onCancel={() => setUsageModalVisible(false)}
        width={900}
        footer={null}
      >
        {selectedDeployment && (
          <Tabs
            defaultActiveKey="1"
            items={[
              {
                key: '1',
                label: '빠른 시작',
                children: (
                  <div>
                    <Alert
                      message="API 엔드포인트 정보"
                      description={
                        <div style={{ fontSize: '14px' }}>
                          <div style={{ marginBottom: '12px' }}>
                            <strong>전체 URL:</strong>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                              <code style={{ 
                                backgroundColor: '#f5f5f5', 
                                padding: '4px 8px', 
                                borderRadius: '4px',
                                flex: 1,
                                wordBreak: 'break-all'
                              }}>
                                http://localhost:8005/api/deployed{selectedDeployment.endpoint_path}
                              </code>
                              <Button
                                size="small"
                                icon={<CopyOutlined />}
                                onClick={() => handleCopyFullUrl(selectedDeployment)}
                                title="전체 URL 복사"
                              />
                            </div>
                          </div>
                          <div style={{ marginBottom: '12px' }}>
                            <strong>상대 경로:</strong>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
                              <code style={{ 
                                backgroundColor: '#f5f5f5', 
                                padding: '4px 8px', 
                                borderRadius: '4px',
                                flex: 1,
                                wordBreak: 'break-all'
                              }}>
                                /api/deployed{selectedDeployment.endpoint_path}
                              </code>
                              <Button
                                size="small"
                                icon={<CopyOutlined />}
                                onClick={() => handleCopyRelativePath(selectedDeployment)}
                                title="상대 경로 복사"
                              />
                            </div>
                          </div>
                          <p><strong>HTTP 메소드:</strong> POST</p>
                          <p><strong>인증:</strong> {selectedDeployment.requires_auth ? '필수 (JWT 토큰)' : '불필요'}</p>
                          <p><strong>요청 제한:</strong> {selectedDeployment.rate_limit || '제한 없음'} 요청/분</p>
                          <p><strong>상태:</strong> <Tag color={getStatusColor(selectedDeployment.status)}>{selectedDeployment.status.toUpperCase()}</Tag></p>
                        </div>
                      }
                      type="info"
                      style={{ marginBottom: 16 }}
                    />
                    
                    {selectedDeployment.requires_auth && (
                      <Alert
                        message="JWT 토큰 받기"
                        description={
                          <div style={{ fontSize: '14px' }}>
                            <p>1. FlowStudio에 로그인: <code>http://localhost:3005</code></p>
                            <p>2. 브라우저 개발자 도구 열기 (F12)</p>
                            <p>3. Application/Storage → Local Storage 이동</p>
                            <p>4. <code>accessToken</code> 값 복사</p>
                            <p style={{ color: '#666', fontSize: '12px', marginTop: '8px' }}>
                              팁: 토큰을 Authorization 헤더에 "Bearer YOUR_TOKEN" 형식으로 추가하세요.
                            </p>
                          </div>
                        }
                        type="warning"
                        style={{ marginBottom: 16 }}
                      />
                    )}
                  </div>
                )
              },
              {
                key: '2',
                label: 'cURL 예제',
                children: (
                  <div>
                    <Typography.Title level={5}>이 명령어를 복사하세요:</Typography.Title>
                    <pre style={{ 
                      background: '#f6f8fa', 
                      padding: '16px', 
                      border: '1px solid #e1e4e8',
                      borderRadius: '6px',
                      overflow: 'auto'
                    }}>
                      {generateCurlExample(selectedDeployment)}
                    </pre>
                    <Button 
                      type="primary" 
                      icon={<CopyOutlined />}
                      onClick={() => {
                        navigator.clipboard.writeText(generateCurlExample(selectedDeployment));
                        message.success('cURL 명령어가 클립보드에 복사되었습니다');
                      }}
                      style={{ marginTop: '8px' }}
                    >
                      클립보드에 복사
                    </Button>
                  </div>
                )
              },
              {
                key: '3',
                label: 'Python 예제',
                children: (
                  <div>
                    <Typography.Title level={5}>이 코드를 복사하세요:</Typography.Title>
                    <pre style={{ 
                      background: '#f6f8fa', 
                      padding: '16px', 
                      border: '1px solid #e1e4e8',
                      borderRadius: '6px',
                      overflow: 'auto'
                    }}>
                      {generatePythonExample(selectedDeployment)}
                    </pre>
                    <Button 
                      type="primary" 
                      icon={<CopyOutlined />}
                      onClick={() => {
                        navigator.clipboard.writeText(generatePythonExample(selectedDeployment));
                        message.success('Python 코드가 클립보드에 복사되었습니다');
                      }}
                      style={{ marginTop: '8px' }}
                    >
                      클립보드에 복사
                    </Button>
                  </div>
                )
              },
              {
                key: '4',
                label: 'Schema',
                children: (
                  <div>
                    <Typography.Title level={5}>Input Schema:</Typography.Title>
                    <pre style={{ 
                      background: '#f6f8fa', 
                      padding: '16px', 
                      border: '1px solid #e1e4e8',
                      borderRadius: '6px',
                      overflow: 'auto'
                    }}>
                      {JSON.stringify(selectedDeployment.input_schema || {
                        type: "object",
                        properties: {
                          field1: { type: "string", description: "Example field" },
                          field2: { type: "string", description: "Another example field" }
                        }
                      }, null, 2)}
                    </pre>
                    
                    <Typography.Title level={5} style={{ marginTop: 16 }}>Output Schema:</Typography.Title>
                    <pre style={{ 
                      background: '#f6f8fa', 
                      padding: '16px', 
                      border: '1px solid #e1e4e8',
                      borderRadius: '6px',
                      overflow: 'auto'
                    }}>
                      {JSON.stringify(selectedDeployment.output_schema || {
                        type: "object",
                        properties: {
                          result: { type: "string", description: "Processing result" }
                        }
                      }, null, 2)}
                    </pre>
                  </div>
                )
              }
            ]}
          />
        )}
      </Modal>
    </>
  );
};