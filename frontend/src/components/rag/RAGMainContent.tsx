/**
 * RAG Main Content Component
 * 컬렉션 정보, 검색, 파일 관리를 제공하는 메인 콘텐츠 영역
 * 2025 트렌디 심플 디자인
 */

import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Typography,
  Space,
  Button,
  Empty,
  Tabs,
  Badge,
  Statistic,
  Progress,
  Tooltip,
  App
} from 'antd';
import {
  SearchOutlined,
  FileTextOutlined,
  HistoryOutlined,
  BarChartOutlined,
  SettingOutlined,
  BookOutlined,
  UploadOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import type { RAGCollection } from '../../services/rag';
import type { Workspace } from '../../types';
import RAGSearchInterface from './RAGSearchInterface';
import RAGFileManager from './RAGFileManager';
import RAGSearchHistory from './RAGSearchHistory';
import RAGCollectionSettings from './RAGCollectionSettings';

const { Title, Text } = Typography;

interface RAGMainContentProps {
  workspaceId: string;
  workspace?: Workspace;
  selectedCollection: RAGCollection | null;
  onCollectionUpdated: () => void;
  onCollectionDeleted: () => void;
}

const RAGMainContent: React.FC<RAGMainContentProps> = ({
  workspaceId,
  workspace,
  selectedCollection,
  onCollectionUpdated,
  onCollectionDeleted
}) => {
  const [activeTab, setActiveTab] = useState('search');

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

  const getProcessingProgress = (collection: RAGCollection) => {
    if (collection.status === 'active') return 100;
    if (collection.status === 'learning') return 50;
    if (collection.status === 'error') return 0;
    return 0;
  };

  // 컬렉션이 선택되지 않았을 때
  if (!selectedCollection) {
    return (
      <div style={{ 
        padding: '80px 40px',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100%',
        background: '#fafafa'
      }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <div style={{ textAlign: 'center' }}>
              <Title level={4} style={{ color: '#666666', marginBottom: '8px' }}>
                컬렉션을 선택해주세요
              </Title>
              <Text style={{ color: '#999999', fontSize: '14px' }}>
                왼쪽 사이드바에서 학습할 컬렉션을 선택하거나 새로 만들어보세요
              </Text>
            </div>
          }
          style={{ padding: '60px 0' }}
        >
          <BookOutlined style={{ fontSize: '48px', color: '#e8e8e8', marginBottom: '20px' }} />
        </Empty>
      </div>
    );
  }

  const tabItems = [
    {
      key: 'search',
      label: (
        <Space>
          <SearchOutlined />
          <span>검색</span>
        </Space>
      ),
      children: (
        <RAGSearchInterface
          collection={selectedCollection}
          workspaceId={workspaceId}
        />
      )
    },
    {
      key: 'files',
      label: (
        <Space>
          <FileTextOutlined />
          <span>파일 관리</span>
          {selectedCollection.document_count > 0 && (
            <Badge 
              count={selectedCollection.document_count} 
              style={{ 
                backgroundColor: '#f0f0f0',
                color: '#666666',
                fontSize: '10px'
              }}
            />
          )}
        </Space>
      ),
      children: (
        <App>
          <RAGFileManager
            collection={selectedCollection}
            onFileUploaded={onCollectionUpdated}
          />
        </App>
      )
    },
    {
      key: 'history',
      label: (
        <Space>
          <HistoryOutlined />
          <span>검색 기록</span>
        </Space>
      ),
      children: (
        <RAGSearchHistory
          collection={selectedCollection}
        />
      )
    },
    {
      key: 'settings',
      label: (
        <Space>
          <SettingOutlined />
          <span>설정</span>
        </Space>
      ),
      children: (
        <RAGCollectionSettings
          collection={selectedCollection}
          onCollectionUpdated={onCollectionUpdated}
          onCollectionDeleted={onCollectionDeleted}
        />
      )
    }
  ];

  return (
    <div style={{ 
      padding: '24px',
      background: '#fafafa',
      minHeight: '100%'
    }}>
      {/* Collection Header */}
      <Card
        style={{
          marginBottom: '24px',
          borderRadius: '12px',
          border: '1px solid #f0f0f0',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.02)'
        }}
        bodyStyle={{ padding: '24px' }}
      >
        <Row gutter={[24, 16]} align="middle">
          {/* Collection Info */}
          <Col flex="auto">
            <Space direction="vertical" size={4}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Title 
                  level={3} 
                  style={{ 
                    margin: 0, 
                    color: '#000000',
                    fontWeight: 600,
                    fontSize: '20px'
                  }}
                >
                  {selectedCollection.name}
                </Title>
                <div style={{
                  padding: '2px 8px',
                  borderRadius: '12px',
                  background: getStatusColor(selectedCollection.status),
                  color: '#ffffff',
                  fontSize: '11px',
                  fontWeight: 500,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  {selectedCollection.status}
                </div>
              </div>
              
              {selectedCollection.description && (
                <Text style={{ color: '#666666', fontSize: '14px' }}>
                  {selectedCollection.description}
                </Text>
              )}

              {selectedCollection.status === 'learning' && (
                <div style={{ marginTop: '8px', maxWidth: '300px' }}>
                  <Text style={{ fontSize: '12px', color: '#666666', marginBottom: '4px' }}>
                    컬렉션 학습 중...
                  </Text>
                  <Progress 
                    percent={getProcessingProgress(selectedCollection)} 
                    size="small"
                    showInfo={false}
                    strokeColor="#1890ff"
                  />
                </div>
              )}
            </Space>
          </Col>

          {/* Statistics */}
          <Col>
            <Row gutter={16}>
              <Col>
                <Statistic
                  title={<Text style={{ fontSize: '12px', color: '#999999' }}>문서</Text>}
                  value={selectedCollection.document_count}
                  suffix={<Text style={{ fontSize: '12px', color: '#666666' }}>개</Text>}
                  valueStyle={{ fontSize: '18px', fontWeight: 600, color: '#000000' }}
                />
              </Col>
              <Col>
                <Statistic
                  title={<Text style={{ fontSize: '12px', color: '#999999' }}>벡터</Text>}
                  value={selectedCollection.vector_count.toLocaleString()}
                  valueStyle={{ fontSize: '18px', fontWeight: 600, color: '#000000' }}
                />
              </Col>
            </Row>
          </Col>

          {/* Quick Actions */}
          <Col>
            <Space>
              <Tooltip title="파일 업로드">
                <Button
                  icon={<UploadOutlined />}
                  onClick={() => setActiveTab('files')}
                  style={{
                    borderRadius: '8px',
                    border: '1px solid #f0f0f0'
                  }}
                >
                  업로드
                </Button>
              </Tooltip>
              <Tooltip title="통계 보기">
                <Button
                  icon={<BarChartOutlined />}
                  onClick={() => setActiveTab('settings')}
                  style={{
                    borderRadius: '8px',
                    border: '1px solid #f0f0f0'
                  }}
                >
                  통계
                </Button>
              </Tooltip>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Main Content Tabs */}
      <Card
        style={{
          borderRadius: '12px',
          border: '1px solid #f0f0f0',
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.02)',
          minHeight: 'calc(100vh - 280px)'
        }}
        bodyStyle={{ padding: 0 }}
      >
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          style={{
            height: '100%'
          }}
          tabBarStyle={{
            margin: 0,
            padding: '0 24px',
            borderBottom: '1px solid #f0f0f0',
            background: '#fafafa'
          }}
          tabBarGutter={32}
        />
      </Card>
    </div>
  );
};

export default RAGMainContent;