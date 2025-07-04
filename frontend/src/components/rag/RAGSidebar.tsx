/**
 * RAG Sidebar Component
 * 컬렉션 목록과 생성 기능을 제공하는 사이드바
 * 2025 트렌디 심플 디자인
 */

import React, { useState } from 'react';
import {
  List,
  Button,
  Typography,
  Space,
  Badge,
  Modal,
  Form,
  Input,
  message,
  Spin,
  Empty,
  Tooltip,
  Divider
} from 'antd';
import {
  PlusOutlined,
  BookOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  StopOutlined
} from '@ant-design/icons';
import { ragService, RAGCollectionStatus } from '../../services/rag';
import type { RAGCollection, CreateCollectionRequest } from '../../services/rag';

const { Text, Title } = Typography;

interface RAGSidebarProps {
  workspaceId: string;
  collections: RAGCollection[];
  selectedCollection: RAGCollection | null;
  onCollectionSelect: (collection: RAGCollection) => void;
  onCollectionCreated: () => void;
  loading: boolean;
}

const RAGSidebar: React.FC<RAGSidebarProps> = ({
  workspaceId,
  collections,
  selectedCollection,
  onCollectionSelect,
  onCollectionCreated,
  loading
}) => {
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [createForm] = Form.useForm();
  const [creating, setCreating] = useState(false);

  const getStatusIcon = (status: RAGCollectionStatus) => {
    switch (status) {
      case RAGCollectionStatus.ACTIVE:
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case RAGCollectionStatus.LEARNING:
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      case RAGCollectionStatus.ERROR:
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      case RAGCollectionStatus.INACTIVE:
        return <StopOutlined style={{ color: '#d9d9d9' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const getStatusText = (status: RAGCollectionStatus) => {
    switch (status) {
      case RAGCollectionStatus.ACTIVE:
        return '활성';
      case RAGCollectionStatus.LEARNING:
        return '학습 중';
      case RAGCollectionStatus.ERROR:
        return '오류';
      case RAGCollectionStatus.INACTIVE:
        return '비활성';
      default:
        return '알 수 없음';
    }
  };

  const handleCreateCollection = async (values: CreateCollectionRequest) => {
    setCreating(true);
    try {
      await ragService.createCollection(workspaceId, values);
      message.success('컬렉션이 성공적으로 생성되었습니다');
      setCreateModalVisible(false);
      createForm.resetFields();
      onCollectionCreated();
    } catch (error: any) {
      console.error('Failed to create collection:', error);
      message.error(error.response?.data?.detail || '컬렉션 생성에 실패했습니다');
    } finally {
      setCreating(false);
    }
  };

  const handleCreateCancel = () => {
    setCreateModalVisible(false);
    createForm.resetFields();
  };

  return (
    <div style={{ 
      padding: '20px 16px',
      height: '100%',
      background: '#ffffff'
    }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          marginBottom: '8px'
        }}>
          <Title 
            level={5} 
            style={{ 
              margin: 0, 
              color: '#000000',
              fontWeight: 600,
              fontSize: '16px'
            }}
          >
            컬렉션
          </Title>
          <Button
            type="text"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
            style={{
              color: '#000000',
              border: 'none',
              boxShadow: 'none',
              borderRadius: '6px',
              width: '32px',
              height: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            className="hover:bg-gray-100"
          />
        </div>
        <Text style={{ fontSize: '13px', color: '#666666' }}>
          {collections.length}개의 학습 컬렉션
        </Text>
      </div>

      <Divider style={{ margin: '0 0 20px 0', borderColor: '#f0f0f0' }} />

      {/* Collection List */}
      {loading ? (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          height: '200px' 
        }}>
          <Spin size="small" />
        </div>
      ) : collections.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Text style={{ color: '#666666', fontSize: '14px' }}>
              아직 생성된 컬렉션이 없습니다
            </Text>
          }
          style={{ padding: '40px 0' }}
        >
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
            style={{
              background: '#000000',
              borderColor: '#000000',
              borderRadius: '6px'
            }}
          >
            첫 컬렉션 만들기
          </Button>
        </Empty>
      ) : (
        <List
          dataSource={collections}
          renderItem={(collection) => (
            <List.Item
              style={{
                padding: '12px 16px',
                margin: '0 0 8px 0',
                border: selectedCollection?.id === collection.id ? '2px solid #000000' : '1px solid #f0f0f0',
                borderRadius: '8px',
                background: selectedCollection?.id === collection.id ? '#f9f9f9' : '#ffffff',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
              className="hover:shadow-sm"
              onClick={() => onCollectionSelect(collection)}
            >
              <List.Item.Meta
                avatar={
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '8px',
                    background: '#f0f0f0',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <BookOutlined style={{ color: '#666666', fontSize: '18px' }} />
                  </div>
                }
                title={
                  <div style={{ marginBottom: '4px' }}>
                    <Text 
                      style={{ 
                        color: '#000000', 
                        fontWeight: 500,
                        fontSize: '14px'
                      }}
                      ellipsis
                    >
                      {collection.name}
                    </Text>
                  </div>
                }
                description={
                  <div>
                    <div style={{ marginBottom: '6px' }}>
                      <Space size={4} align="center">
                        {getStatusIcon(collection.status)}
                        <Text style={{ fontSize: '12px', color: '#666666' }}>
                          {getStatusText(collection.status)}
                        </Text>
                      </Space>
                    </div>
                    <div>
                      <Space size={12}>
                        <Tooltip title="문서 수">
                          <Space size={4} align="center">
                            <FileTextOutlined style={{ fontSize: '11px', color: '#999999' }} />
                            <Text style={{ fontSize: '11px', color: '#999999' }}>
                              {collection.document_count}
                            </Text>
                          </Space>
                        </Tooltip>
                        <Tooltip title="벡터 수">
                          <Badge 
                            count={collection.vector_count} 
                            style={{ 
                              backgroundColor: '#f0f0f0',
                              color: '#666666',
                              fontSize: '10px',
                              fontWeight: 400,
                              border: '1px solid #e8e8e8'
                            }}
                          />
                        </Tooltip>
                      </Space>
                    </div>
                    {collection.description && (
                      <Text 
                        style={{ 
                          fontSize: '11px', 
                          color: '#999999',
                          marginTop: '4px',
                          display: 'block'
                        }}
                        ellipsis
                      >
                        {collection.description}
                      </Text>
                    )}
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}

      {/* Create Collection Modal */}
      <Modal
        title={
          <Space>
            <BookOutlined />
            <span>새 컬렉션 만들기</span>
          </Space>
        }
        open={createModalVisible}
        onCancel={handleCreateCancel}
        footer={null}
        width={480}
        styles={{
          header: {
            borderBottom: '1px solid #f0f0f0',
            paddingBottom: '16px'
          }
        }}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateCollection}
          style={{ paddingTop: '20px' }}
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
              placeholder="예: 제품 매뉴얼, 회사 정책 등"
              style={{ 
                borderRadius: '6px',
                padding: '8px 12px'
              }}
            />
          </Form.Item>

          <Form.Item
            name="description"
            label={<Text style={{ fontWeight: 500 }}>설명 (선택사항)</Text>}
          >
            <Input.TextArea
              placeholder="컬렉션에 대한 간단한 설명을 입력해주세요"
              rows={3}
              style={{ 
                borderRadius: '6px',
                padding: '8px 12px'
              }}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, marginTop: '24px' }}>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button 
                onClick={handleCreateCancel}
                style={{ borderRadius: '6px' }}
              >
                취소
              </Button>
              <Button 
                type="primary" 
                htmlType="submit" 
                loading={creating}
                style={{
                  background: '#000000',
                  borderColor: '#000000',
                  borderRadius: '6px'
                }}
              >
                생성하기
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default RAGSidebar;