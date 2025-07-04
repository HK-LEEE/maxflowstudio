/**
 * RAG Search History Component
 * 검색 기록 및 피드백 기능을 제공하는 컴포넌트
 * 2025 트렌디 심플 디자인
 */

import React, { useState } from 'react';
import {
  Card,
  Typography,
  Space,
  List,
  Tag,
  Button,
  Rate,
  Input,
  Modal,
  message,
  Switch,
  Tooltip,
  Pagination,
  Empty,
  Spin,
  Avatar,
  Divider
} from 'antd';
import {
  HistoryOutlined,
  MessageOutlined,
  StarOutlined,
  ClockCircleOutlined,
  UserOutlined,
  SearchOutlined,
  EditOutlined,
  CheckOutlined,
  CloseOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { ragService } from '../../services/rag';
import type { RAGCollection, RAGSearchHistory } from '../../services/rag';

const { Text, Paragraph, Title } = Typography;
const { TextArea } = Input;

interface RAGSearchHistoryProps {
  collection: RAGCollection;
}

const RAGSearchHistoryComponent: React.FC<RAGSearchHistoryProps> = ({
  collection
}) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [userFilterOnly, setUserFilterOnly] = useState(false);
  const [feedbackModalVisible, setFeedbackModalVisible] = useState(false);
  const [selectedHistory, setSelectedHistory] = useState<RAGSearchHistory | null>(null);
  const [feedbackRating, setFeedbackRating] = useState<number>(0);
  const [feedbackText, setFeedbackText] = useState<string>('');
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const pageSize = 10;

  // 검색 기록 조회
  const { data: historyData, isLoading, refetch } = useQuery({
    queryKey: ['rag-search-history', collection.id, currentPage, userFilterOnly],
    queryFn: () => ragService.getSearchHistory(collection.id, {
      page: currentPage,
      limit: pageSize,
      user_filter: userFilterOnly
    }),
  });

  const formatExecutionTime = (seconds?: number) => {
    if (!seconds) return '알 수 없음';
    if (seconds < 1) {
      return `${Math.round(seconds * 1000)}ms`;
    }
    return `${seconds.toFixed(2)}s`;
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

  const handleFeedbackSubmit = async () => {
    if (!selectedHistory) return;

    setSubmittingFeedback(true);
    try {
      await ragService.submitFeedback(selectedHistory.id, {
        rating: feedbackRating || undefined,
        feedback: feedbackText.trim() || undefined
      });

      message.success('피드백이 성공적으로 제출되었습니다');
      setFeedbackModalVisible(false);
      setSelectedHistory(null);
      setFeedbackRating(0);
      setFeedbackText('');
      refetch();
    } catch (error: any) {
      console.error('Failed to submit feedback:', error);
      message.error(error.response?.data?.detail || '피드백 제출에 실패했습니다');
    } finally {
      setSubmittingFeedback(false);
    }
  };

  const openFeedbackModal = (history: RAGSearchHistory) => {
    setSelectedHistory(history);
    setFeedbackRating(history.user_rating || 0);
    setFeedbackText(history.user_feedback || '');
    setFeedbackModalVisible(true);
  };

  const closeFeedbackModal = () => {
    setFeedbackModalVisible(false);
    setSelectedHistory(null);
    setFeedbackRating(0);
    setFeedbackText('');
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* Header Controls */}
      <Card
        style={{
          marginBottom: '24px',
          borderRadius: '12px',
          border: '1px solid #f0f0f0'
        }}
        bodyStyle={{ padding: '16px' }}
      >
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '16px'
        }}>
          <Space>
            <HistoryOutlined style={{ color: '#722ed1' }} />
            <Title level={5} style={{ margin: 0, fontWeight: 600 }}>
              검색 기록
            </Title>
            {historyData && (
              <Tag color="purple">
                총 {historyData.total}개
              </Tag>
            )}
          </Space>

          <Space>
            <Text style={{ fontSize: '13px', color: '#666666' }}>
              내 기록만 보기
            </Text>
            <Switch
              checked={userFilterOnly}
              onChange={setUserFilterOnly}
              size="small"
            />
          </Space>
        </div>
      </Card>

      {/* Search History List */}
      <Card
        style={{
          borderRadius: '12px',
          border: '1px solid #f0f0f0',
          minHeight: '400px'
        }}
        bodyStyle={{ padding: '20px' }}
      >
        {isLoading ? (
          <div style={{ 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center', 
            height: '200px' 
          }}>
            <Spin size="large" />
          </div>
        ) : !historyData?.history || historyData.history.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <div style={{ textAlign: 'center' }}>
                <Text style={{ color: '#666666', fontSize: '14px' }}>
                  {userFilterOnly ? '내 검색 기록이 없습니다' : '검색 기록이 없습니다'}
                </Text>
              </div>
            }
            style={{ padding: '60px 0' }}
          >
            <SearchOutlined style={{ fontSize: '48px', color: '#e8e8e8', marginBottom: '16px' }} />
          </Empty>
        ) : (
          <>
            <List
              dataSource={historyData.history}
              renderItem={(history: RAGSearchHistory) => (
                <List.Item
                  style={{
                    padding: '20px',
                    margin: '0 0 16px 0',
                    background: '#fafafa',
                    borderRadius: '12px',
                    border: '1px solid #f0f0f0'
                  }}
                >
                  <div style={{ width: '100%' }}>
                    {/* Header */}
                    <div style={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'space-between',
                      marginBottom: '12px'
                    }}>
                      <Space>
                        <Avatar 
                          icon={<UserOutlined />} 
                          size="small"
                          style={{ background: '#1890ff' }}
                        />
                        <Text style={{ fontSize: '12px', color: '#666666' }}>
                          {formatDate(history.created_at)}
                        </Text>
                        <Tag icon={<ClockCircleOutlined />} color="blue" size="small">
                          {formatExecutionTime(history.execution_time)}
                        </Tag>
                        {history.retrieved_documents_count && (
                          <Tag size="small">
                            {history.retrieved_documents_count}개 문서 참조
                          </Tag>
                        )}
                      </Space>

                      <Button
                        type="text"
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => openFeedbackModal(history)}
                        style={{ color: '#666666' }}
                      >
                        피드백
                      </Button>
                    </div>

                    {/* Query */}
                    <div style={{ marginBottom: '12px' }}>
                      <Text style={{ 
                        fontSize: '13px', 
                        color: '#999999',
                        fontWeight: 500,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        질문
                      </Text>
                      <Paragraph
                        style={{
                          fontSize: '14px',
                          fontWeight: 500,
                          color: '#000000',
                          margin: '4px 0 0 0',
                          background: '#ffffff',
                          padding: '8px 12px',
                          borderRadius: '6px',
                          border: '1px solid #e8e8e8'
                        }}
                        ellipsis={{ rows: 2, expandable: true, symbol: '더보기' }}
                      >
                        {history.query}
                      </Paragraph>
                    </div>

                    {/* Response */}
                    <div style={{ marginBottom: '12px' }}>
                      <Text style={{ 
                        fontSize: '13px', 
                        color: '#999999',
                        fontWeight: 500,
                        textTransform: 'uppercase',
                        letterSpacing: '0.5px'
                      }}>
                        답변
                      </Text>
                      <Paragraph
                        style={{
                          fontSize: '14px',
                          color: '#333333',
                          margin: '4px 0 0 0',
                          lineHeight: '1.6'
                        }}
                        ellipsis={{ rows: 3, expandable: true, symbol: '더보기' }}
                      >
                        {history.response}
                      </Paragraph>
                    </div>

                    {/* User Feedback */}
                    {(history.user_rating || history.user_feedback) && (
                      <div style={{
                        background: '#ffffff',
                        padding: '12px',
                        borderRadius: '8px',
                        border: '1px solid #e8e8e8',
                        marginTop: '12px'
                      }}>
                        <Space direction="vertical" size={4} style={{ width: '100%' }}>
                          {history.user_rating && (
                            <div>
                              <Text style={{ fontSize: '12px', color: '#666666', marginRight: '8px' }}>
                                평가:
                              </Text>
                              <Rate disabled value={history.user_rating} style={{ fontSize: '14px' }} />
                            </div>
                          )}
                          {history.user_feedback && (
                            <div>
                              <Text style={{ fontSize: '12px', color: '#666666' }}>
                                피드백:
                              </Text>
                              <Text style={{ fontSize: '13px', color: '#333333', marginLeft: '8px' }}>
                                {history.user_feedback}
                              </Text>
                            </div>
                          )}
                        </Space>
                      </div>
                    )}
                  </div>
                </List.Item>
              )}
            />

            {/* Pagination */}
            {historyData.total > pageSize && (
              <div style={{ textAlign: 'center', marginTop: '24px' }}>
                <Pagination
                  current={currentPage}
                  total={historyData.total}
                  pageSize={pageSize}
                  onChange={setCurrentPage}
                  showSizeChanger={false}
                  showQuickJumper
                  showTotal={(total, range) => 
                    `${range[0]}-${range[1]} / 총 ${total}개`
                  }
                />
              </div>
            )}
          </>
        )}
      </Card>

      {/* Feedback Modal */}
      <Modal
        title={
          <Space>
            <MessageOutlined />
            <span>검색 결과 피드백</span>
          </Space>
        }
        open={feedbackModalVisible}
        onCancel={closeFeedbackModal}
        footer={null}
        width={600}
        styles={{
          header: {
            borderBottom: '1px solid #f0f0f0',
            paddingBottom: '16px'
          }
        }}
      >
        {selectedHistory && (
          <div style={{ paddingTop: '20px' }}>
            {/* Original Query */}
            <div style={{ marginBottom: '20px' }}>
              <Text style={{ 
                fontSize: '13px', 
                color: '#999999',
                fontWeight: 500,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                검색한 질문
              </Text>
              <Paragraph
                style={{
                  fontSize: '14px',
                  color: '#000000',
                  margin: '4px 0 0 0',
                  background: '#f5f5f5',
                  padding: '12px',
                  borderRadius: '8px'
                }}
              >
                {selectedHistory.query}
              </Paragraph>
            </div>

            <Divider />

            {/* Rating */}
            <div style={{ marginBottom: '20px' }}>
              <Text style={{ 
                fontSize: '14px', 
                fontWeight: 500,
                marginBottom: '8px',
                display: 'block'
              }}>
                이 답변이 도움이 되었나요?
              </Text>
              <Rate
                value={feedbackRating}
                onChange={setFeedbackRating}
                style={{ fontSize: '20px' }}
              />
            </div>

            {/* Feedback Text */}
            <div style={{ marginBottom: '24px' }}>
              <Text style={{ 
                fontSize: '14px', 
                fontWeight: 500,
                marginBottom: '8px',
                display: 'block'
              }}>
                추가 의견 (선택사항)
              </Text>
              <TextArea
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                placeholder="답변의 정확성, 유용성 등에 대한 의견을 남겨주세요"
                rows={4}
                maxLength={1000}
                showCount
                style={{ borderRadius: '8px' }}
              />
            </div>

            {/* Actions */}
            <div style={{ textAlign: 'right' }}>
              <Space>
                <Button
                  onClick={closeFeedbackModal}
                  style={{ borderRadius: '6px' }}
                  icon={<CloseOutlined />}
                >
                  취소
                </Button>
                <Button
                  type="primary"
                  onClick={handleFeedbackSubmit}
                  loading={submittingFeedback}
                  style={{
                    background: '#000000',
                    borderColor: '#000000',
                    borderRadius: '6px'
                  }}
                  icon={<CheckOutlined />}
                >
                  피드백 제출
                </Button>
              </Space>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default RAGSearchHistoryComponent;