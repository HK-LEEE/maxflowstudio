/**
 * RAG Learning Page
 * 워크스페이스별 RAG 학습 시스템 메인 페이지
 * 2025 트렌디 심플 디자인 (화이트 95%, 블랙 5%)
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  Layout, 
  Typography, 
  Spin, 
  Alert,
  Button,
  Space
} from 'antd';
import { 
  ArrowLeftOutlined,
  PlusOutlined 
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { workspaceService } from '../services/workspace';
import { ragService } from '../services/rag';
import type { RAGCollection } from '../services/rag';
import RAGSidebar from '../components/rag/RAGSidebar';
import RAGMainContent from '../components/rag/RAGMainContent';

const { Content, Sider } = Layout;
const { Title } = Typography;

interface RAGPageProps {}

export const RAGPage: React.FC<RAGPageProps> = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [selectedCollection, setSelectedCollection] = useState<RAGCollection | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // 워크스페이스 정보 조회
  const { data: workspace, isLoading: workspaceLoading, error: workspaceError } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => workspaceService.getById(workspaceId!),
    enabled: !!workspaceId,
  });

  // RAG 컬렉션 목록 조회
  const { data: collectionsData, isLoading: collectionsLoading, refetch: refetchCollections } = useQuery({
    queryKey: ['rag-collections', workspaceId],
    queryFn: () => ragService.getCollections(workspaceId!, { limit: 100 }),
    enabled: !!workspaceId,
  });

  // 워크스페이스 RAG 통계 조회
  const { data: workspaceStats, error: statsError } = useQuery({
    queryKey: ['rag-workspace-stats', workspaceId],
    queryFn: () => ragService.getWorkspaceStats(workspaceId!),
    enabled: !!workspaceId,
    retry: false,
    refetchOnWindowFocus: false,
  });

  // 첫 번째 컬렉션 자동 선택
  useEffect(() => {
    if (collectionsData?.collections && collectionsData.collections.length > 0 && !selectedCollection) {
      setSelectedCollection(collectionsData.collections[0]);
    }
  }, [collectionsData, selectedCollection]);

  const handleGoBack = () => {
    navigate('/dashboard');
  };

  const handleCollectionSelect = (collection: RAGCollection) => {
    setSelectedCollection(collection);
  };

  const handleCollectionCreated = () => {
    refetchCollections();
  };

  const handleCollectionUpdated = () => {
    refetchCollections();
  };

  const handleCollectionDeleted = () => {
    setSelectedCollection(null);
    refetchCollections();
  };

  if (workspaceLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        background: '#fafafa'
      }}>
        <Spin size="large" />
      </div>
    );
  }

  if (workspaceError) {
    return (
      <div style={{ padding: '24px', background: '#fafafa', minHeight: '100vh' }}>
        <Alert
          message="워크스페이스를 찾을 수 없습니다"
          description="존재하지 않거나 접근 권한이 없는 워크스페이스입니다."
          type="error"
          showIcon
          action={
            <Button size="small" onClick={handleGoBack}>
              돌아가기
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div style={{ 
      background: '#fafafa', 
      minHeight: '100vh'
    }}>
      {/* Header */}
      <div style={{
        background: '#ffffff',
        borderBottom: '1px solid #f0f0f0',
        padding: '16px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Space>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={handleGoBack}
            style={{
              color: '#000000',
              border: 'none',
              boxShadow: 'none'
            }}
          />
          <div>
            <Title 
              level={3} 
              style={{ 
                margin: 0, 
                color: '#000000',
                fontWeight: 600,
                fontSize: '20px'
              }}
            >
              RAG 학습
            </Title>
            <Typography.Text 
              style={{ 
                color: '#666666',
                fontSize: '14px'
              }}
            >
              {workspace?.name} 워크스페이스
            </Typography.Text>
          </div>
        </Space>

        {workspaceStats && (
          <Space>
            <div style={{ textAlign: 'right' }}>
              <Typography.Text 
                style={{ 
                  fontSize: '12px', 
                  color: '#999999',
                  display: 'block'
                }}
              >
                컬렉션 {workspaceStats.collection_stats.total_collections}개 ·{' '}
                문서 {workspaceStats.collection_stats.total_documents}개 ·{' '}
                {workspaceStats.collection_stats.total_file_size_mb}MB
              </Typography.Text>
              <Typography.Text 
                style={{ 
                  fontSize: '12px', 
                  color: '#666666'
                }}
              >
                최근 7일 검색 {workspaceStats.recent_searches}회
              </Typography.Text>
            </div>
          </Space>
        )}
      </div>

      {/* Main Layout */}
      <Layout style={{ background: 'transparent' }}>
        {/* Sidebar */}
        <Sider
          width={280}
          collapsed={sidebarCollapsed}
          collapsedWidth={0}
          style={{
            background: '#ffffff',
            borderRight: '1px solid #f0f0f0',
            height: 'calc(100vh - 73px)',
            overflow: 'auto'
          }}
          breakpoint="md"
          onBreakpoint={(broken) => {
            setSidebarCollapsed(broken);
          }}
        >
          <RAGSidebar
            workspaceId={workspaceId!}
            collections={collectionsData?.collections || []}
            selectedCollection={selectedCollection}
            onCollectionSelect={handleCollectionSelect}
            onCollectionCreated={handleCollectionCreated}
            loading={collectionsLoading}
          />
        </Sider>

        {/* Main Content */}
        <Content style={{ 
          background: '#fafafa',
          minHeight: 'calc(100vh - 73px)'
        }}>
          <RAGMainContent
            workspaceId={workspaceId!}
            workspace={workspace}
            selectedCollection={selectedCollection}
            onCollectionUpdated={handleCollectionUpdated}
            onCollectionDeleted={handleCollectionDeleted}
          />
        </Content>
      </Layout>

      {/* Mobile Sidebar Toggle (when collapsed) */}
      {sidebarCollapsed && (
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setSidebarCollapsed(false)}
          style={{
            position: 'fixed',
            top: '90px',
            left: '16px',
            zIndex: 1000,
            borderRadius: '50%',
            width: '48px',
            height: '48px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
            background: '#000000',
            borderColor: '#000000'
          }}
        />
      )}
    </div>
  );
};

export default RAGPage;