/**
 * RAG File Manager Component
 * 파일 업로드 및 문서 관리 기능을 제공하는 컴포넌트
 * 2025 트렌디 심플 디자인
 */

import React, { useState, useEffect } from 'react';
import {
  Row,
  Col,
  Card,
  Typography,
  Space,
  Upload,
  Button,
  List,
  Tag,
  Progress,
  Alert,
  message,
  Modal,
  Tooltip,
  Badge,
  Divider,
  Empty,
  Spin,
  App
} from 'antd';
import {
  UploadOutlined,
  InboxOutlined,
  FileTextOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  EyeOutlined,
  WarningOutlined,
  CopyOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { ragService, RAGDocumentStatus } from '../../services/rag';
import type { RAGCollection, RAGDocument } from '../../services/rag';
import type { UploadFile, UploadProps } from 'antd/es/upload';

const { Text, Title, Paragraph } = Typography;
const { Dragger } = Upload;

interface RAGFileManagerProps {
  collection: RAGCollection;
  onFileUploaded: () => void;
}

const RAGFileManager: React.FC<RAGFileManagerProps> = ({
  collection,
  onFileUploaded
}) => {
  const [uploading, setUploading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [deleting, setDeleting] = useState<string | null>(null);
  
  // Use Ant Design's modal hooks for better context support
  const { modal } = App.useApp();

  // 문서 목록 조회
  const { data: documentsData, isLoading: documentsLoading, refetch: refetchDocuments } = useQuery({
    queryKey: ['rag-documents', collection.id],
    queryFn: () => ragService.getDocuments(collection.id, { limit: 100 }),
    refetchInterval: 5000, // 5초마다 자동 새로고침 (처리 상태 업데이트용)
  });

  const getStatusIcon = (status: RAGDocumentStatus) => {
    switch (status) {
      case RAGDocumentStatus.COMPLETED:
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case RAGDocumentStatus.PROCESSING:
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      case RAGDocumentStatus.PENDING:
        return <ClockCircleOutlined style={{ color: '#fa8c16' }} />;
      case RAGDocumentStatus.ERROR:
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <InfoCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const getStatusText = (status: RAGDocumentStatus) => {
    switch (status) {
      case RAGDocumentStatus.COMPLETED:
        return '완료';
      case RAGDocumentStatus.PROCESSING:
        return '처리 중';
      case RAGDocumentStatus.PENDING:
        return '대기 중';
      case RAGDocumentStatus.ERROR:
        return '오류';
      default:
        return '알 수 없음';
    }
  };

  const getStatusColor = (status: RAGDocumentStatus) => {
    switch (status) {
      case RAGDocumentStatus.COMPLETED:
        return 'green';
      case RAGDocumentStatus.PROCESSING:
        return 'blue';
      case RAGDocumentStatus.PENDING:
        return 'orange';
      case RAGDocumentStatus.ERROR:
        return 'red';
      default:
        return 'default';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: true,
    accept: '.pdf,.docx,.txt,.md,.html',
    fileList,
    beforeUpload: (file) => {
      const isValidType = [
        'application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/markdown',
        'text/html'
      ].includes(file.type);

      if (!isValidType) {
        message.error(`${file.name}은(는) 지원하지 않는 파일 형식입니다.`);
        return false;
      }

      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        message.error('파일 크기는 10MB를 초과할 수 없습니다.');
        return false;
      }

      return false; // Prevent automatic upload
    },
    onChange: (info) => {
      setFileList(info.fileList);
    },
    onDrop: (e) => {
      console.log('Dropped files', e.dataTransfer.files);
    },
  };

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('업로드할 파일을 선택해주세요');
      return;
    }

    setUploading(true);

    try {
      for (const fileWrapper of fileList) {
        if (fileWrapper.originFileObj) {
          await ragService.uploadDocument(collection.id, fileWrapper.originFileObj);
        }
      }

      message.success(`${fileList.length}개 파일이 업로드되었습니다`);
      setFileList([]);
      onFileUploaded();
      refetchDocuments();
    } catch (error: any) {
      console.error('Upload failed:', error);
      message.error(error.response?.data?.detail || '파일 업로드에 실패했습니다');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDocument = async (document: RAGDocument) => {
    modal.confirm({
      title: '문서 삭제',
      icon: <WarningOutlined />,
      content: (
        <div>
          <p>다음 문서를 삭제하시겠습니까?</p>
          <Text strong>{document.original_filename}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            삭제된 문서는 복구할 수 없으며, 벡터 데이터와 파일도 함께 삭제됩니다.
          </Text>
        </div>
      ),
      okText: '삭제',
      okType: 'danger',
      cancelText: '취소',
      onOk: async () => {
        try {
          setDeleting(document.id);
          await ragService.deleteDocument(collection.id, document.id);
          message.success('문서가 성공적으로 삭제되었습니다');
          refetchDocuments();
          onFileUploaded(); // 컬렉션 통계 업데이트용
        } catch (error: any) {
          console.error('Delete failed:', error);
          message.error(error.response?.data?.detail || '문서 삭제에 실패했습니다');
        } finally {
          setDeleting(null);
        }
      },
    });
  };

  const showErrorDetails = (document: RAGDocument) => {
    const copyToClipboard = (text: string) => {
      navigator.clipboard.writeText(text).then(() => {
        message.success('클립보드에 복사되었습니다');
      });
    };

    modal.error({
      title: `오류 상세 정보: ${document.original_filename}`,
      width: 700,
      content: (
        <div style={{ marginTop: '16px' }}>
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Alert
              message="문서 처리 중 오류가 발생했습니다"
              description="아래 오류 내용을 확인하고 문제를 해결한 후 다시 업로드해주세요."
              type="error"
              showIcon
            />
            
            <div>
              <Text strong>오류 메시지:</Text>
              <div
                style={{
                  marginTop: '8px',
                  padding: '12px',
                  backgroundColor: '#fff2f0',
                  border: '1px solid #ffccc7',
                  borderRadius: '6px',
                  fontFamily: 'monospace',
                  fontSize: '13px',
                  maxHeight: '200px',
                  overflow: 'auto'
                }}
              >
                <Text type="danger">{document.error_message}</Text>
              </div>
              <Button
                size="small"
                icon={<CopyOutlined />}
                onClick={() => copyToClipboard(document.error_message || '')}
                style={{ marginTop: '8px' }}
              >
                오류 메시지 복사
              </Button>
            </div>

            <Divider />

            <Row gutter={16}>
              <Col span={8}><Text strong>파일명:</Text></Col>
              <Col span={16}><Text>{document.original_filename}</Text></Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}><Text strong>파일 크기:</Text></Col>
              <Col span={16}><Text>{formatFileSize(document.file_size)}</Text></Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}><Text strong>업로드 시간:</Text></Col>
              <Col span={16}><Text>{formatDate(document.uploaded_at)}</Text></Col>
            </Row>
          </Space>
        </div>
      ),
    });
  };

  const showDocumentDetails = (document: RAGDocument) => {
    modal.info({
      title: `문서 상세 정보: ${document.original_filename}`,
      width: 600,
      content: (
        <div style={{ marginTop: '16px' }}>
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            <Row gutter={16}>
              <Col span={8}><Text strong>파일명:</Text></Col>
              <Col span={16}><Text>{document.original_filename}</Text></Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}><Text strong>파일 크기:</Text></Col>
              <Col span={16}><Text>{formatFileSize(document.file_size)}</Text></Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}><Text strong>파일 형식:</Text></Col>
              <Col span={16}><Tag>{document.file_type.toUpperCase()}</Tag></Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}><Text strong>상태:</Text></Col>
              <Col span={16}>
                <Space>
                  {getStatusIcon(document.status)}
                  <Tag color={getStatusColor(document.status)}>
                    {getStatusText(document.status)}
                  </Tag>
                </Space>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}><Text strong>청크 수:</Text></Col>
              <Col span={16}><Text>{document.chunk_count.toLocaleString()}</Text></Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}><Text strong>벡터 수:</Text></Col>
              <Col span={16}><Text>{document.vector_count.toLocaleString()}</Text></Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}><Text strong>업로드 일시:</Text></Col>
              <Col span={16}><Text>{formatDate(document.uploaded_at)}</Text></Col>
            </Row>
            {document.processed_at && (
              <Row gutter={16}>
                <Col span={8}><Text strong>처리 완료:</Text></Col>
                <Col span={16}><Text>{formatDate(document.processed_at)}</Text></Col>
              </Row>
            )}
            {document.error_message && (
              <Row gutter={16}>
                <Col span={8}><Text strong>오류 메시지:</Text></Col>
                <Col span={16}>
                  <Text type="danger">{document.error_message}</Text>
                </Col>
              </Row>
            )}
          </Space>
        </div>
      ),
    });
  };

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={24}>
        {/* File Upload Section */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <UploadOutlined />
                <Text style={{ fontWeight: 600 }}>파일 업로드</Text>
              </Space>
            }
            style={{
              marginBottom: '24px',
              borderRadius: '12px',
              border: '1px solid #f0f0f0'
            }}
            bodyStyle={{ padding: '20px' }}
          >
            <Dragger
              {...uploadProps}
              style={{
                borderRadius: '8px',
                border: '2px dashed #e8e8e8',
                background: '#fafafa'
              }}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined style={{ color: '#666666' }} />
              </p>
              <p className="ant-upload-text" style={{ color: '#000000', fontWeight: 500 }}>
                파일을 드래그하거나 클릭하여 업로드
              </p>
              <p className="ant-upload-hint" style={{ color: '#666666' }}>
                지원 형식: PDF, DOCX, TXT, MD, HTML (최대 10MB)
              </p>
            </Dragger>

            {fileList.length > 0 && (
              <div style={{ marginTop: '16px' }}>
                <Text style={{ fontWeight: 500, marginBottom: '8px', display: 'block' }}>
                  선택된 파일 ({fileList.length}개)
                </Text>
                <List
                  size="small"
                  dataSource={fileList}
                  renderItem={(file) => (
                    <List.Item>
                      <Text ellipsis style={{ flex: 1 }}>
                        {file.name}
                      </Text>
                      <Text style={{ color: '#666666', fontSize: '12px' }}>
                        {formatFileSize(file.size || 0)}
                      </Text>
                    </List.Item>
                  )}
                />
                <Button
                  type="primary"
                  onClick={handleUpload}
                  loading={uploading}
                  style={{
                    marginTop: '12px',
                    background: '#000000',
                    borderColor: '#000000',
                    borderRadius: '6px'
                  }}
                  block
                >
                  {uploading ? '업로드 중...' : `${fileList.length}개 파일 업로드`}
                </Button>
              </div>
            )}

            <Alert
              message="지원 파일 형식"
              description="PDF, Word 문서(DOCX), 텍스트 파일(TXT), 마크다운(MD), HTML 파일을 업로드할 수 있습니다."
              type="info"
              showIcon
              style={{ marginTop: '16px', borderRadius: '6px' }}
            />
          </Card>
        </Col>

        {/* Document List Section */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <FileTextOutlined />
                <Text style={{ fontWeight: 600 }}>업로드된 문서</Text>
                {documentsData && (
                  <Badge count={documentsData.total} style={{ backgroundColor: '#f0f0f0', color: '#666666' }} />
                )}
              </Space>
            }
            extra={
              documentsData && documentsData.total > 0 && (
                <Button 
                  size="small" 
                  onClick={() => refetchDocuments()}
                  style={{ borderRadius: '6px' }}
                >
                  새로고침
                </Button>
              )
            }
            style={{
              marginBottom: '24px',
              borderRadius: '12px',
              border: '1px solid #f0f0f0'
            }}
            bodyStyle={{ padding: '16px', maxHeight: '500px', overflow: 'auto' }}
          >
            {documentsLoading ? (
              <div style={{ textAlign: 'center', padding: '40px' }}>
                <Spin size="small" />
              </div>
            ) : !documentsData?.documents || documentsData.documents.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <Text style={{ color: '#666666', fontSize: '14px' }}>
                    업로드된 문서가 없습니다
                  </Text>
                }
                style={{ padding: '20px 0' }}
              />
            ) : (
              <List
                dataSource={documentsData.documents}
                renderItem={(document: RAGDocument) => (
                  <List.Item
                    style={{
                      padding: '12px',
                      margin: '0 0 8px 0',
                      background: '#fafafa',
                      borderRadius: '8px',
                      border: '1px solid #f0f0f0'
                    }}
                    actions={[
                      document.status === RAGDocumentStatus.ERROR && (
                        <Tooltip title="오류 상세 보기" key="error-details">
                          <Button
                            type="text"
                            icon={<WarningOutlined />}
                            size="small"
                            onClick={() => showErrorDetails(document)}
                            style={{ color: '#ff4d4f' }}
                          />
                        </Tooltip>
                      ),
                      <Tooltip title="상세 정보" key="details">
                        <Button
                          type="text"
                          icon={<EyeOutlined />}
                          size="small"
                          onClick={() => showDocumentDetails(document)}
                          style={{ color: '#666666' }}
                        />
                      </Tooltip>,
                      <Tooltip title="문서 삭제" key="delete">
                        <Button
                          type="text"
                          icon={<DeleteOutlined />}
                          size="small"
                          loading={deleting === document.id}
                          onClick={() => handleDeleteDocument(document)}
                          style={{ color: '#ff4d4f' }}
                          disabled={deleting === document.id}
                        />
                      </Tooltip>
                    ].filter(Boolean)}
                  >
                    <List.Item.Meta
                      avatar={getStatusIcon(document.status)}
                      title={
                        <div style={{ marginBottom: '4px' }}>
                          <Text
                            style={{
                              fontSize: '13px',
                              fontWeight: 500,
                              color: '#000000'
                            }}
                            ellipsis
                          >
                            {document.original_filename}
                          </Text>
                        </div>
                      }
                      description={
                        <div>
                          <Space size={8}>
                            <Tag color={getStatusColor(document.status)} size="small">
                              {getStatusText(document.status)}
                            </Tag>
                            <Text style={{ fontSize: '11px', color: '#999999' }}>
                              {formatFileSize(document.file_size)}
                            </Text>
                            {document.status === RAGDocumentStatus.COMPLETED && (
                              <Text style={{ fontSize: '11px', color: '#999999' }}>
                                청크 {document.chunk_count}개
                              </Text>
                            )}
                          </Space>
                          {document.status === RAGDocumentStatus.PROCESSING && (
                            <div style={{ marginTop: '4px' }}>
                              <Progress 
                                percent={50} 
                                size="small" 
                                showInfo={false}
                                strokeColor="#1890ff"
                              />
                            </div>
                          )}
                          {document.error_message && (
                            <Text 
                              style={{ 
                                fontSize: '11px', 
                                color: '#ff4d4f',
                                display: 'block',
                                marginTop: '4px',
                                cursor: 'pointer'
                              }}
                              ellipsis
                              onClick={() => showErrorDetails(document)}
                            >
                              {document.error_message} (클릭하여 자세히 보기)
                            </Text>
                          )}
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default RAGFileManager;