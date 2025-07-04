/**
 * RAG Collection Settings Component
 * 컬렉션 설정 및 통계를 제공하는 컴포넌트
 * 2025 트렌디 심플 디자인
 */

import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Typography,
  Space,
  Form,
  Input,
  Button,
  Switch,
  Modal,
  message,
  Statistic,
  Progress,
  Divider,
  Alert,
  Tooltip,
  Tag
} from 'antd';
import {
  SettingOutlined,
  EditOutlined,
  DeleteOutlined,
  BarChartOutlined,
  FileTextOutlined,
  CloudOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  SaveOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { ragService } from '../../services/rag';
import type { RAGCollection, UpdateCollectionRequest } from '../../services/rag';

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;

interface RAGCollectionSettingsProps {
  collection: RAGCollection;
  onCollectionUpdated: () => void;
  onCollectionDeleted: () => void;
}

const RAGCollectionSettings: React.FC<RAGCollectionSettingsProps> = ({
  collection,
  onCollectionUpdated,
  onCollectionDeleted
}) => {
  const [editForm] = Form.useForm();
  const [editMode, setEditMode] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // 컬렉션 통계 조회
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['rag-collection-stats', collection.id],
    queryFn: () => ragService.getCollectionStats(collection.id),
  });

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return '#52c41a';
      case 'learning':
        return '#1890ff';
      case 'error':
        return '#ff4d4f';
      case 'inactive':
        return '#d9d9d9';
      default:
        return '#d9d9d9';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'active':
        return '활성';
      case 'learning':
        return '학습 중';
      case 'error':
        return '오류';
      case 'inactive':
        return '비활성';
      default:
        return '알 수 없음';
    }
  };

  const handleEditStart = () => {
    editForm.setFieldsValue({
      name: collection.name,
      description: collection.description || '',
      is_active: collection.is_active
    });
    setEditMode(true);
  };

  const handleEditCancel = () => {
    setEditMode(false);
    editForm.resetFields();
  };

  const handleEditSubmit = async (values: UpdateCollectionRequest) => {
    setUpdating(true);
    try {
      await ragService.updateCollection(collection.id, values);
      message.success('컬렉션 정보가 성공적으로 업데이트되었습니다');
      setEditMode(false);
      onCollectionUpdated();
    } catch (error: any) {
      console.error('Failed to update collection:', error);
      message.error(error.response?.data?.detail || '컬렉션 업데이트에 실패했습니다');
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await ragService.deleteCollection(collection.id);
      message.success('컬렉션이 성공적으로 삭제되었습니다');
      setDeleteModalVisible(false);
      onCollectionDeleted();
    } catch (error: any) {
      console.error('Failed to delete collection:', error);
      message.error(error.response?.data?.detail || '컬렉션 삭제에 실패했습니다');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={24}>
        {/* Collection Information */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <EditOutlined />
                <Text style={{ fontWeight: 600 }}>컬렉션 정보</Text>
              </Space>
            }
            extra={
              !editMode && (
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={handleEditStart}
                  style={{ color: '#666666' }}
                >
                  편집
                </Button>
              )
            }
            style={{
              marginBottom: '24px',
              borderRadius: '12px',
              border: '1px solid #f0f0f0'
            }}
            bodyStyle={{ padding: '20px' }}
          >
            {editMode ? (
              <Form
                form={editForm}
                layout="vertical"
                onFinish={handleEditSubmit}
              >
                <Form.Item
                  name="name"
                  label={<Text style={{ fontWeight: 500 }}>컬렉션 이름</Text>}
                  rules={[
                    { required: true, message: '컬렉션 이름을 입력해주세요' },
                    { min: 1, max: 255, message: '1-255자 사이로 입력해주세요' }
                  ]}
                >
                  <Input 
                    style={{ borderRadius: '6px' }}
                    placeholder="컬렉션 이름을 입력하세요"
                  />
                </Form.Item>

                <Form.Item
                  name="description"
                  label={<Text style={{ fontWeight: 500 }}>설명</Text>}
                >
                  <TextArea
                    rows={3}
                    style={{ borderRadius: '6px' }}
                    placeholder="컬렉션에 대한 설명을 입력하세요"
                  />
                </Form.Item>

                <Form.Item
                  name="is_active"
                  label={<Text style={{ fontWeight: 500 }}>활성 상태</Text>}
                  valuePropName="checked"
                >
                  <Switch />
                </Form.Item>

                <Form.Item style={{ marginBottom: 0, marginTop: '20px' }}>
                  <Space>
                    <Button
                      onClick={handleEditCancel}
                      style={{ borderRadius: '6px' }}
                    >
                      취소
                    </Button>
                    <Button
                      type="primary"
                      htmlType="submit"
                      loading={updating}
                      icon={<SaveOutlined />}
                      style={{
                        background: '#000000',
                        borderColor: '#000000',
                        borderRadius: '6px'
                      }}
                    >
                      저장
                    </Button>
                  </Space>
                </Form.Item>
              </Form>
            ) : (
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <div>
                  <Text style={{ 
                    fontSize: '13px', 
                    color: '#999999',
                    fontWeight: 500,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}>
                    이름
                  </Text>
                  <Title level={4} style={{ margin: '4px 0 0 0', color: '#000000' }}>
                    {collection.name}
                  </Title>
                </div>

                {collection.description && (
                  <div>
                    <Text style={{ 
                      fontSize: '13px', 
                      color: '#999999',
                      fontWeight: 500,
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px'
                    }}>
                      설명
                    </Text>
                    <Paragraph style={{ margin: '4px 0 0 0', color: '#666666' }}>
                      {collection.description}
                    </Paragraph>
                  </div>
                )}

                <div>
                  <Text style={{ 
                    fontSize: '13px', 
                    color: '#999999',
                    fontWeight: 500,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                  }}>
                    상태
                  </Text>
                  <div style={{ marginTop: '4px' }}>
                    <Tag
                      color={getStatusColor(collection.status)}
                      style={{ fontSize: '12px', padding: '4px 8px' }}
                    >
                      {getStatusText(collection.status)}
                    </Tag>
                    {collection.is_active ? (
                      <Tag color="green" style={{ fontSize: '12px', padding: '4px 8px' }}>
                        활성화됨
                      </Tag>
                    ) : (
                      <Tag color="default" style={{ fontSize: '12px', padding: '4px 8px' }}>
                        비활성화됨
                      </Tag>
                    )}
                  </div>
                </div>

                <Divider style={{ margin: '16px 0' }} />

                <Row gutter={16}>
                  <Col span={12}>
                    <Text style={{ fontSize: '12px', color: '#666666' }}>생성일</Text>
                    <div style={{ fontSize: '13px', color: '#000000', marginTop: '2px' }}>
                      {formatDate(collection.created_at)}
                    </div>
                  </Col>
                  <Col span={12}>
                    <Text style={{ fontSize: '12px', color: '#666666' }}>수정일</Text>
                    <div style={{ fontSize: '13px', color: '#000000', marginTop: '2px' }}>
                      {formatDate(collection.updated_at)}
                    </div>
                  </Col>
                </Row>
              </Space>
            )}
          </Card>

          {/* Danger Zone */}
          <Card
            title={
              <Space>
                <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
                <Text style={{ fontWeight: 600, color: '#ff4d4f' }}>위험 구역</Text>
              </Space>
            }
            style={{
              borderRadius: '12px',
              border: '1px solid #ffccc7'
            }}
            bodyStyle={{ padding: '20px' }}
          >
            <Alert
              message="컬렉션 삭제"
              description="컬렉션을 삭제하면 모든 문서와 벡터 데이터가 영구적으로 삭제됩니다. 이 작업은 되돌릴 수 없습니다."
              type="warning"
              showIcon
              style={{ marginBottom: '16px', borderRadius: '8px' }}
            />
            <Button
              danger
              icon={<DeleteOutlined />}
              onClick={() => setDeleteModalVisible(true)}
              style={{ borderRadius: '6px' }}
            >
              컬렉션 삭제
            </Button>
          </Card>
        </Col>

        {/* Statistics */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <BarChartOutlined />
                <Text style={{ fontWeight: 600 }}>통계</Text>
              </Space>
            }
            style={{
              marginBottom: '24px',
              borderRadius: '12px',
              border: '1px solid #f0f0f0'
            }}
            bodyStyle={{ padding: '20px' }}
            loading={statsLoading}
          >
            {stats && (
              <Space direction="vertical" size={20} style={{ width: '100%' }}>
                <Row gutter={16}>
                  <Col span={12}>
                    <Statistic
                      title={
                        <Space>
                          <FileTextOutlined style={{ color: '#1890ff' }} />
                          <Text style={{ fontSize: '13px', color: '#666666' }}>문서 수</Text>
                        </Space>
                      }
                      value={stats.total_documents}
                      suffix="개"
                      valueStyle={{ fontSize: '24px', fontWeight: 600, color: '#000000' }}
                    />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title={
                        <Space>
                          <CloudOutlined style={{ color: '#722ed1' }} />
                          <Text style={{ fontSize: '13px', color: '#666666' }}>벡터 수</Text>
                        </Space>
                      }
                      value={stats.total_vectors}
                      valueStyle={{ fontSize: '24px', fontWeight: 600, color: '#000000' }}
                    />
                  </Col>
                </Row>

                <Divider style={{ margin: '8px 0' }} />

                <div>
                  <div style={{ marginBottom: '8px' }}>
                    <Text style={{ fontSize: '13px', color: '#666666' }}>
                      파일 크기
                    </Text>
                    <Text style={{ fontSize: '18px', fontWeight: 600, color: '#000000', float: 'right' }}>
                      {stats.total_file_size_mb} MB
                    </Text>
                  </div>
                  <Progress
                    percent={Math.min((stats.total_file_size_mb / 100) * 100, 100)}
                    showInfo={false}
                    strokeColor="#52c41a"
                    trailColor="#f0f0f0"
                  />
                  <Text style={{ fontSize: '11px', color: '#999999' }}>
                    권장 한도: 100MB
                  </Text>
                </div>

                {stats.average_documents_per_collection > 0 && (
                  <div>
                    <Text style={{ fontSize: '13px', color: '#666666' }}>
                      평균 문서당 청크 수
                    </Text>
                    <div style={{ fontSize: '18px', fontWeight: 600, color: '#000000' }}>
                      {(stats.total_vectors / stats.total_documents || 0).toFixed(1)}개
                    </div>
                  </div>
                )}

                <Alert
                  message={
                    <Space>
                      <InfoCircleOutlined />
                      <Text style={{ fontSize: '12px' }}>
                        통계는 실시간으로 업데이트됩니다
                      </Text>
                    </Space>
                  }
                  type="info"
                  showIcon={false}
                  style={{ 
                    background: '#f6ffed', 
                    border: '1px solid #b7eb8f',
                    borderRadius: '6px'
                  }}
                />
              </Space>
            )}
          </Card>

          {/* Collection ID Info */}
          <Card
            title={
              <Space>
                <InfoCircleOutlined />
                <Text style={{ fontWeight: 600 }}>기술 정보</Text>
              </Space>
            }
            style={{
              borderRadius: '12px',
              border: '1px solid #f0f0f0'
            }}
            bodyStyle={{ padding: '20px' }}
          >
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <div>
                <Text style={{ fontSize: '12px', color: '#666666' }}>컬렉션 ID</Text>
                <Input
                  value={collection.id}
                  readOnly
                  size="small"
                  style={{ 
                    marginTop: '4px',
                    fontFamily: 'monospace',
                    fontSize: '11px',
                    background: '#f5f5f5'
                  }}
                />
              </div>
              <div>
                <Text style={{ fontSize: '12px', color: '#666666' }}>Qdrant 컬렉션명</Text>
                <Input
                  value={collection.qdrant_collection_name}
                  readOnly
                  size="small"
                  style={{ 
                    marginTop: '4px',
                    fontFamily: 'monospace',
                    fontSize: '11px',
                    background: '#f5f5f5'
                  }}
                />
              </div>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Delete Confirmation Modal */}
      <Modal
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />
            <span>컬렉션 삭제 확인</span>
          </Space>
        }
        open={deleteModalVisible}
        onCancel={() => setDeleteModalVisible(false)}
        footer={null}
        width={500}
      >
        <div style={{ paddingTop: '20px' }}>
          <Alert
            message="주의: 이 작업은 되돌릴 수 없습니다"
            description={
              <div style={{ marginTop: '8px' }}>
                <Text>다음 데이터가 영구적으로 삭제됩니다:</Text>
                <ul style={{ marginTop: '8px', marginBottom: '0' }}>
                  <li>컬렉션 '{collection.name}'</li>
                  <li>업로드된 모든 문서 ({collection.document_count}개)</li>
                  <li>모든 벡터 데이터 ({collection.vector_count.toLocaleString()}개)</li>
                  <li>검색 기록 및 사용자 피드백</li>
                </ul>
              </div>
            }
            type="error"
            showIcon
            style={{ marginBottom: '20px' }}
          />

          <div style={{ textAlign: 'right' }}>
            <Space>
              <Button
                onClick={() => setDeleteModalVisible(false)}
                style={{ borderRadius: '6px' }}
              >
                취소
              </Button>
              <Button
                danger
                onClick={handleDelete}
                loading={deleting}
                icon={<DeleteOutlined />}
                style={{ borderRadius: '6px' }}
              >
                영구 삭제
              </Button>
            </Space>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default RAGCollectionSettings;