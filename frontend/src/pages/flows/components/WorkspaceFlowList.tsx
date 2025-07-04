/**
 * 파일명: WorkspaceFlowList.tsx (150줄)
 * 목적: 워크스페이스별 Flow 목록 표시 컴포넌트
 * 동작 과정:
 * 1. 워크스페이스별로 그룹화된 Flow 목록 표시
 * 2. Flow 카드 형태로 정보 표시 (이름, 상태, 실행 버튼 등)
 * 3. Flow 삭제, 편집 등 액션 제공
 * 데이터베이스 연동: flows 테이블에서 워크스페이스별 Flow 조회
 * 의존성: 없음 (독립적 목록 컴포넌트)
 */

import React from 'react';
import {
  List,
  Card,
  Avatar,
  Tag,
  Button,
  Typography,
  Tooltip,
  Popconfirm,
  message,
  Empty,
} from 'antd';
import {
  PlayCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  PartitionOutlined,
} from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../../services/api';

const { Text } = Typography;

interface WorkspaceFlowListProps {
  flows: any[];
  workspaceName: string;
  loading?: boolean;
}

export const WorkspaceFlowList: React.FC<WorkspaceFlowListProps> = ({
  flows,
  workspaceName,
  loading = false,
}) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/api/flows/${id}`),
    onSuccess: () => {
      message.success('Flow deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['flows'] });
    },
    onError: () => {
      message.error('Failed to delete flow');
    },
  });

  const executeMutation = useMutation({
    mutationFn: (id: string) => apiClient.post(`/api/flows/${id}/execute`),
    onSuccess: () => {
      message.success('Flow execution started');
    },
    onError: () => {
      message.error('Failed to start flow execution');
    },
  });

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id);
  };

  const handleExecute = (id: string) => {
    executeMutation.mutate(id);
  };

  const handleEdit = (id: string) => {
    navigate(`/flows/${id}`);
  };

  const handleView = (id: string) => {
    navigate(`/flows/${id}/view`);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'draft':
        return 'default';
      case 'running':
        return 'processing';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (flows.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={`No flows in ${workspaceName}`}
      />
    );
  }

  return (
    <List
      grid={{ gutter: 16, xs: 1, sm: 2, md: 2, lg: 3, xl: 3, xxl: 4 }}
      dataSource={flows}
      loading={loading}
      renderItem={(flow) => (
        <List.Item>
          <Card
            hoverable
            actions={[
              <Tooltip title="View Flow">
                <Button
                  type="text"
                  icon={<EyeOutlined />}
                  onClick={() => handleView(flow.id)}
                />
              </Tooltip>,
              <Tooltip title="Edit Flow">
                <Button
                  type="text"
                  icon={<EditOutlined />}
                  onClick={() => handleEdit(flow.id)}
                />
              </Tooltip>,
              <Tooltip title="Execute Flow">
                <Button
                  type="text"
                  icon={<PlayCircleOutlined />}
                  onClick={() => handleExecute(flow.id)}
                  loading={executeMutation.isPending}
                />
              </Tooltip>,
              <Popconfirm
                title="Are you sure you want to delete this flow?"
                onConfirm={() => handleDelete(flow.id)}
                okText="Yes"
                cancelText="No"
              >
                <Tooltip title="Delete Flow">
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    loading={deleteMutation.isPending}
                  />
                </Tooltip>
              </Popconfirm>,
            ]}
          >
            <Card.Meta
              avatar={<Avatar icon={<PartitionOutlined />} />}
              title={
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{flow.name}</span>
                  <Tag color={getStatusColor(flow.status)}>
                    {flow.status.toUpperCase()}
                  </Tag>
                </div>
              }
              description={
                <div>
                  <Text type="secondary" style={{ fontSize: '12px' }}>
                    {flow.description || 'No description'}
                  </Text>
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary" style={{ fontSize: '11px' }}>
                      Created: {formatDate(flow.created_at)}
                    </Text>
                  </div>
                  <div style={{ marginTop: 4 }}>
                    <Text type="secondary" style={{ fontSize: '11px' }}>
                      Updated: {formatDate(flow.updated_at)}
                    </Text>
                  </div>
                </div>
              }
            />
          </Card>
        </List.Item>
      )}
    />
  );
};