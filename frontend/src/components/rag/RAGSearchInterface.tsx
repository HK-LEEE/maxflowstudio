/**
 * RAG Search Interface Component
 * RAG 검색 기능을 제공하는 인터페이스
 * 2025 트렌디 심플 디자인
 */

import React, { useState } from 'react';
import {
  Row,
  Col,
  Input,
  Button,
  Card,
  Typography,
  Space,
  List,
  Tag,
  Spin,
  Alert,
  Collapse,
  Progress,
  Tooltip,
  message,
  Avatar,
  Divider,
  Modal
} from 'antd';
import {
  SearchOutlined,
  SendOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  StarOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  ThunderboltOutlined,
  BulbOutlined,
  DownOutlined,
  UpOutlined,
  EyeOutlined,
  ExpandOutlined
} from '@ant-design/icons';
import { ragService } from '../../services/rag';
import type { RAGCollection, RAGSearchResponse, RAGSearchDocument, RAGSearchStep } from '../../services/rag';

const { Text, Paragraph, Title } = Typography;
const { Panel } = Collapse;

interface RAGSearchInterfaceProps {
  collection: RAGCollection;
  workspaceId: string;
}

const RAGSearchInterface: React.FC<RAGSearchInterfaceProps> = ({
  collection,
  workspaceId
}) => {
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<RAGSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedDocs, setExpandedDocs] = useState<Set<number>>(new Set());
  const [selectedDocument, setSelectedDocument] = useState<RAGSearchDocument | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  const handleSearch = async () => {
    if (!query.trim()) {
      message.warning('검색어를 입력해주세요');
      return;
    }

    if (collection.status !== 'active') {
      message.error('활성 상태의 컬렉션에서만 검색할 수 있습니다');
      return;
    }

    if (collection.document_count === 0) {
      message.error('문서가 없는 컬렉션에서는 검색할 수 없습니다');
      return;
    }

    setSearching(true);
    setError(null);
    setExpandedDocs(new Set());
    setExpandedSteps(new Set());
    setSelectedDocument(null);

    try {
      // 검색 진행 중 메시지 표시
      const hideLoadingMessage = message.loading('RAG 검색 중... 벡터 검색 및 답변 생성을 진행하고 있습니다. 최대 2분 정도 소요될 수 있습니다.', 0);
      
      const result = await ragService.search(collection.id, {
        query: query.trim(),
        include_metadata: true
      });
      
      hideLoadingMessage(); // 로딩 메시지 숨기기
      
      // 디버깅: 응답 데이터 구조 확인
      console.log('RAG Search Result:', result);
      console.log('Response field:', result?.result?.response);
      console.log('Response type:', typeof result?.result?.response);
      console.log('Response length:', result?.result?.response?.length);
      
      setSearchResult(result);
      message.success('검색이 완료되었습니다');
    } catch (error: any) {
      console.error('Search failed:', error);
      const errorMessage = error.response?.data?.detail || error.message || '검색에 실패했습니다';
      setError(errorMessage);
      
      // 타임아웃 오류인 경우 특별한 메시지 표시
      if (error.code === 'ECONNABORTED') {
        message.error('검색 시간이 초과되었습니다. 더 간단한 질문으로 다시 시도해보세요.');
      } else {
        message.error(errorMessage);
      }
    } finally {
      setSearching(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  const toggleDocExpansion = (docIndex: number) => {
    const newExpandedDocs = new Set(expandedDocs);
    if (newExpandedDocs.has(docIndex)) {
      newExpandedDocs.delete(docIndex);
    } else {
      newExpandedDocs.add(docIndex);
    }
    setExpandedDocs(newExpandedDocs);
  };

  const toggleStepExpansion = (stepIndex: number) => {
    const newExpandedSteps = new Set(expandedSteps);
    if (newExpandedSteps.has(stepIndex)) {
      newExpandedSteps.delete(stepIndex);
    } else {
      newExpandedSteps.add(stepIndex);
    }
    setExpandedSteps(newExpandedSteps);
  };

  const getStepIcon = (stepName: string) => {
    switch (stepName) {
      case 'retrieve':
        return <SearchOutlined style={{ color: '#1890ff' }} />;
      case 'rerank':
        return <StarOutlined style={{ color: '#722ed1' }} />;
      case 'generate':
        return <BulbOutlined style={{ color: '#52c41a' }} />;
      case 'transform_query':
        return <ThunderboltOutlined style={{ color: '#fa8c16' }} />;
      default:
        return <InfoCircleOutlined style={{ color: '#666666' }} />;
    }
  };

  const formatExecutionTime = (seconds: number) => {
    if (seconds < 1) {
      return `${Math.round(seconds * 1000)}ms`;
    }
    return `${seconds.toFixed(2)}s`;
  };

  return (
    <div style={{ padding: '24px', minHeight: '500px' }}>
      {/* Search Input */}
      <Card
        style={{
          marginBottom: '24px',
          borderRadius: '12px',
          border: '1px solid #f0f0f0',
          background: '#ffffff'
        }}
        bodyStyle={{ padding: '20px' }}
      >
        <Row gutter={[16, 16]} align="middle">
          <Col flex="auto">
            <Input.TextArea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="질문을 입력하세요. 예: 제품의 보증 기간은 얼마나 되나요?"
              autoSize={{ minRows: 2, maxRows: 4 }}
              style={{
                borderRadius: '8px',
                border: '1px solid #e8e8e8',
                fontSize: '14px'
              }}
              disabled={collection.status !== 'active' || collection.document_count === 0}
            />
          </Col>
          <Col>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSearch}
              loading={searching}
              disabled={collection.status !== 'active' || collection.document_count === 0}
              style={{
                background: '#000000',
                borderColor: '#000000',
                borderRadius: '8px',
                height: '40px',
                paddingLeft: '20px',
                paddingRight: '20px'
              }}
            >
              검색
            </Button>
          </Col>
        </Row>

        {/* Collection Status Warning */}
        {collection.status !== 'active' && (
          <Alert
            message="컬렉션이 비활성 상태입니다"
            description="활성 상태의 컬렉션에서만 검색할 수 있습니다."
            type="warning"
            showIcon
            style={{ marginTop: '16px', borderRadius: '8px' }}
          />
        )}

        {collection.document_count === 0 && collection.status === 'active' && (
          <Alert
            message="문서가 없습니다"
            description="먼저 학습할 문서를 업로드해주세요."
            type="info"
            showIcon
            style={{ marginTop: '16px', borderRadius: '8px' }}
          />
        )}
      </Card>

      {/* Error Display */}
      {error && (
        <Alert
          message="검색 오류"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: '24px', borderRadius: '8px' }}
        />
      )}

      {/* Search Results */}
      {searchResult && (
        <div>
          {/* Main Response */}
          <Card
            title={
              <Space>
                <BulbOutlined style={{ color: '#52c41a' }} />
                <Text style={{ fontWeight: 600, fontSize: '16px' }}>AI 응답</Text>
                <Tag color="green">
                  {formatExecutionTime(searchResult.result.total_execution_time)}
                </Tag>
              </Space>
            }
            style={{
              marginBottom: '24px',
              borderRadius: '12px',
              border: '1px solid #f0f0f0'
            }}
            bodyStyle={{ padding: '24px' }}
          >
            <Paragraph
              style={{
                fontSize: '15px',
                lineHeight: '1.7',
                color: '#000000',
                margin: 0,
                whiteSpace: 'pre-wrap'
              }}
            >
              {(() => {
                const response = searchResult?.result?.response;
                console.log('Rendering response:', response);
                
                if (!response || response.trim() === '') {
                  return '응답을 생성하지 못했습니다. 다른 질문으로 다시 시도해보세요.';
                }
                return response;
              })()}
            </Paragraph>
          </Card>

          <Row gutter={24}>
            {/* Retrieved Documents */}
            <Col xs={24} lg={12}>
              <Card
                title={
                  <Space>
                    <FileTextOutlined style={{ color: '#1890ff' }} />
                    <Text style={{ fontWeight: 600 }}>참조 문서</Text>
                    <Tag>{searchResult.result.retrieved_documents.length}개</Tag>
                  </Space>
                }
                style={{
                  marginBottom: '24px',
                  borderRadius: '12px',
                  border: '1px solid #f0f0f0'
                }}
                bodyStyle={{ padding: '16px' }}
              >
                <List
                  dataSource={searchResult.result.retrieved_documents}
                  renderItem={(doc: RAGSearchDocument, index) => {
                    const isExpanded = expandedDocs.has(index);
                    const contentPreview = doc.content.length > 200 ? doc.content.substring(0, 200) + '...' : doc.content;
                    
                    return (
                      <List.Item
                        style={{
                          padding: '12px',
                          margin: '0 0 8px 0',
                          background: '#fafafa',
                          borderRadius: '8px',
                          border: '1px solid #f0f0f0'
                        }}
                      >
                        <List.Item.Meta
                          avatar={
                            <Avatar
                              style={{
                                background: '#1890ff',
                                color: '#ffffff',
                                fontSize: '12px',
                                fontWeight: 600
                              }}
                            >
                              {index + 1}
                            </Avatar>
                          }
                          title={
                            <div style={{ 
                              marginBottom: '4px', 
                              display: 'flex', 
                              alignItems: 'center', 
                              justifyContent: 'space-between',
                              gap: '8px'
                            }}>
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <Text
                                  style={{
                                    fontSize: '13px',
                                    fontWeight: 500,
                                    color: '#000000'
                                  }}
                                  ellipsis
                                >
                                  {doc.filename}
                                </Text>
                                <Tag
                                  color="blue"
                                  style={{
                                    marginLeft: '8px',
                                    fontSize: '10px'
                                  }}
                                >
                                  {(doc.score * 100).toFixed(1)}%
                                </Tag>
                              </div>
                              <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
                                <Tooltip title="상세보기">
                                  <Button
                                    type="text"
                                    size="small"
                                    icon={<EyeOutlined />}
                                    onClick={() => setSelectedDocument(doc)}
                                    style={{ 
                                      padding: '2px 4px',
                                      height: '20px',
                                      width: '20px',
                                      minWidth: '20px'
                                    }}
                                  />
                                </Tooltip>
                                {doc.content.length > 200 && (
                                  <Tooltip title={isExpanded ? '접기' : '더보기'}>
                                    <Button
                                      type="text"
                                      size="small"
                                      icon={isExpanded ? <UpOutlined /> : <DownOutlined />}
                                      onClick={() => toggleDocExpansion(index)}
                                      style={{ 
                                        padding: '2px 4px',
                                        height: '20px',
                                        width: '20px',
                                        minWidth: '20px'
                                      }}
                                    />
                                  </Tooltip>
                                )}
                              </div>
                            </div>
                          }
                          description={
                            <div
                              style={{
                                fontSize: '12px',
                                color: '#666666',
                                margin: 0,
                                whiteSpace: 'pre-wrap'
                              }}
                            >
                              {isExpanded ? doc.content : contentPreview}
                            </div>
                          }
                        />
                      </List.Item>
                    );
                  }}
                />
              </Card>
            </Col>

            {/* Search Steps */}
            <Col xs={24} lg={12}>
              <Card
                title={
                  <Space>
                    <ClockCircleOutlined style={{ color: '#722ed1' }} />
                    <Text style={{ fontWeight: 600 }}>검색 단계</Text>
                  </Space>
                }
                style={{
                  marginBottom: '24px',
                  borderRadius: '12px',
                  border: '1px solid #f0f0f0'
                }}
                bodyStyle={{ padding: '16px' }}
              >
                <Collapse
                  size="small"
                  style={{ background: 'transparent' }}
                  items={searchResult.result.search_steps.map((step: RAGSearchStep, index) => ({
                    key: index,
                    label: (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        {getStepIcon(step.step_name)}
                        <Text style={{ fontSize: '13px', fontWeight: 500 }}>
                          {step.description}
                        </Text>
                        <Tag size="small">
                          {formatExecutionTime(step.execution_time)}
                        </Tag>
                        <Tag 
                          color={step.status === 'completed' ? 'green' : 'orange'}
                          size="small"
                        >
                          {step.status}
                        </Tag>
                      </div>
                    ),
                    children: (
                      <div style={{ padding: '8px 0' }}>
                        <Space direction="vertical" style={{ width: '100%' }} size="small">
                          {step.input_data && Object.keys(step.input_data).length > 0 && (
                            <div>
                              <Text strong style={{ fontSize: '12px', color: '#1890ff' }}>
                                입력 데이터:
                              </Text>
                              <pre style={{ 
                                fontSize: '11px', 
                                color: '#666666', 
                                background: '#f8f8f8',
                                padding: '8px',
                                borderRadius: '4px',
                                margin: '4px 0 0 0',
                                overflow: 'auto',
                                maxHeight: '150px'
                              }}>
                                {JSON.stringify(step.input_data, null, 2)}
                              </pre>
                            </div>
                          )}
                          {step.output_data && Object.keys(step.output_data).length > 0 && (
                            <div>
                              <Text strong style={{ fontSize: '12px', color: '#52c41a' }}>
                                출력 데이터:
                              </Text>
                              <pre style={{ 
                                fontSize: '11px', 
                                color: '#666666', 
                                background: '#f8f8f8',
                                padding: '8px',
                                borderRadius: '4px',
                                margin: '4px 0 0 0',
                                overflow: 'auto',
                                maxHeight: '150px'
                              }}>
                                {JSON.stringify(step.output_data, null, 2)}
                              </pre>
                            </div>
                          )}
                          <div style={{ fontSize: '11px', color: '#999999' }}>
                            실행 시간: {formatExecutionTime(step.execution_time)} · 
                            상태: {step.status}
                          </div>
                        </Space>
                      </div>
                    )
                  }))}
                />
              </Card>
            </Col>
          </Row>
        </div>
      )}

      {/* Loading State */}
      {searching && (
        <Card
          style={{
            borderRadius: '12px',
            border: '1px solid #f0f0f0',
            textAlign: 'center'
          }}
          bodyStyle={{ padding: '60px' }}
        >
          <Spin size="large" />
          <div style={{ marginTop: '16px' }}>
            <Text style={{ color: '#666666', fontSize: '14px' }}>
              AI가 답변을 생성하고 있습니다...
            </Text>
          </div>
        </Card>
      )}

      {/* Empty State */}
      {!searchResult && !searching && !error && (
        <Card
          style={{
            borderRadius: '12px',
            border: '1px solid #f0f0f0',
            textAlign: 'center'
          }}
          bodyStyle={{ padding: '60px' }}
        >
          <SearchOutlined 
            style={{ 
              fontSize: '48px', 
              color: '#e8e8e8', 
              marginBottom: '16px' 
            }} 
          />
          <Title level={4} style={{ color: '#666666', marginBottom: '8px' }}>
            질문을 입력해보세요
          </Title>
          <Text style={{ color: '#999999', fontSize: '14px' }}>
            업로드된 문서를 기반으로 정확한 답변을 제공해드립니다
          </Text>
        </Card>
      )}

      {/* Document Detail Modal */}
      <Modal
        title={
          <Space>
            <FileTextOutlined style={{ color: '#1890ff' }} />
            <span>참조 문서 상세보기</span>
          </Space>
        }
        open={!!selectedDocument}
        onCancel={() => setSelectedDocument(null)}
        footer={[
          <Button key="close" onClick={() => setSelectedDocument(null)}>
            닫기
          </Button>
        ]}
        width={800}
        style={{ top: 20 }}
      >
        {selectedDocument && (
          <div>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {/* Document Info */}
              <Card size="small" style={{ background: '#f8f9fa' }}>
                <Row gutter={16}>
                  <Col span={12}>
                    <Text strong>파일명:</Text>
                    <br />
                    <Text copyable>{selectedDocument.filename}</Text>
                  </Col>
                  <Col span={12}>
                    <Text strong>관련성 점수:</Text>
                    <br />
                    <Tag color="blue" style={{ fontSize: '14px' }}>
                      {(selectedDocument.score * 100).toFixed(1)}%
                    </Tag>
                  </Col>
                </Row>
                
                {selectedDocument.metadata && Object.keys(selectedDocument.metadata).length > 0 && (
                  <div style={{ marginTop: '12px' }}>
                    <Text strong>메타데이터:</Text>
                    <div style={{ marginTop: '8px' }}>
                      {selectedDocument.metadata.page && (
                        <Tag icon={<InfoCircleOutlined />} color="green">
                          페이지 {selectedDocument.metadata.page}
                        </Tag>
                      )}
                      {selectedDocument.metadata.total_pages && (
                        <Tag color="default">
                          전체 {selectedDocument.metadata.total_pages}페이지
                        </Tag>
                      )}
                      {selectedDocument.metadata.chunk_id && (
                        <Tag color="purple">
                          청크 ID: {selectedDocument.metadata.chunk_id.substring(0, 8)}...
                        </Tag>
                      )}
                    </div>
                  </div>
                )}
              </Card>

              {/* Document Content */}
              <Card size="small" title="문서 내용">
                <div
                  style={{
                    maxHeight: '400px',
                    overflow: 'auto',
                    padding: '16px',
                    background: '#fafafa',
                    borderRadius: '6px',
                    fontSize: '14px',
                    lineHeight: '1.6',
                    whiteSpace: 'pre-wrap',
                    border: '1px solid #f0f0f0'
                  }}
                >
                  {selectedDocument.content}
                </div>
              </Card>

              {/* Full Metadata (if available) */}
              {selectedDocument.metadata && Object.keys(selectedDocument.metadata).length > 0 && (
                <Card size="small" title="전체 메타데이터">
                  <pre style={{
                    fontSize: '12px',
                    color: '#666666',
                    background: '#f8f8f8',
                    padding: '12px',
                    borderRadius: '4px',
                    margin: 0,
                    overflow: 'auto',
                    maxHeight: '200px'
                  }}>
                    {JSON.stringify(selectedDocument.metadata, null, 2)}
                  </pre>
                </Card>
              )}
            </Space>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default RAGSearchInterface;