/**
 * 파일명: ApiDeploymentsPage.tsx (120줄)
 * 목적: API 배포 관리 페이지 메인 컴포넌트
 * 동작 과정:
 * 1. API 배포 목록 조회 및 표시
 * 2. 새 배포 생성 및 기존 배포 수정
 * 3. 배포 통계 및 모니터링 정보 표시
 * 데이터베이스 연동: api_deployments 테이블과 직접 연동
 * 의존성: DeploymentForm, DeploymentStats, DeploymentTable
 */

import React, { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Typography,
  Space,
  Layout,
  Badge,
  Alert,
  Select,
} from 'antd';
import {
  PlusOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { apiClient } from '../services/api';
import { DeploymentForm } from './api-deployments/components/DeploymentForm';
import { DeploymentStats } from './api-deployments/components/DeploymentStats';
import { DeploymentTable } from './api-deployments/components/DeploymentTable';
import { DocumentationViewer } from '../components/DocumentationViewer';

const { Title } = Typography;
const { Content } = Layout;

const ApiDeploymentsPage: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingDeployment, setEditingDeployment] = useState<any>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [docsVisible, setDocsVisible] = useState(false);
  const queryClient = useQueryClient();

  // Canvas에서 새 deployment 생성 시 자동 새로고침
  useEffect(() => {
    const handleStorageChange = () => {
      const invalidateSignal = localStorage.getItem('deployment-cache-invalidate');
      if (invalidateSignal) {
        console.log('🔄 API Deployments: Cache invalidation signal received, refreshing...');
        queryClient.invalidateQueries({ queryKey: ['deployments'] });
        localStorage.removeItem('deployment-cache-invalidate');
      }
    };

    window.addEventListener('storage', handleStorageChange);
    // 페이지 로드 시에도 체크
    handleStorageChange();

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [queryClient]);

  // Fetch deployments
  const { data: deployments = [], isLoading: deploymentsLoading, error: deploymentsError } = useQuery({
    queryKey: ['deployments'],
    queryFn: async () => {
      console.log('🔍 API Deployments: Fetching deployments from /api/deployments/');
      
      try {
        // 관리자 권한으로 모든 deployment 조회 (include_all=true 파라미터 추가)
        const response = await apiClient.get('/api/deployments/', {
          params: {
            include_all: true,  // 관리자 권한으로 모든 deployment 조회
            include_flows: true, // flow 기반 deployment 포함
          }
        });
        
        console.log('📦 API Deployments: Received data:', response.data);
        console.log('📊 API Deployments: Total deployments:', response.data.length);
        console.log('📊 API Deployments: Flow deployments found:', 
          response.data.filter((d: any) => d.flow_id).length
        );
        console.log('📊 API Deployments: Pending deployments found:', 
          response.data.filter((d: any) => d.status === 'pending').length
        );
        console.log('📊 API Deployments: Sample deployment:', response.data[0]);
        
        return response.data;
      } catch (error: any) {
        console.error('❌ API Deployments: Failed to fetch deployments:', error);
        if (error.response?.status === 401) {
          console.error('❌ API Deployments: Unauthorized - token may be expired');
        }
        throw error;
      }
    },
    retry: (failureCount, error: any) => {
      // Don't retry on auth errors
      if (error?.response?.status === 401) {
        return false;
      }
      return failureCount < 3;
    },
  });

  // Fetch flows for deployment creation
  const { data: flows = [] } = useQuery({
    queryKey: ['flows'],
    queryFn: () => apiClient.get('/api/flows/').then(res => res.data),
  });

  // Fetch deployment statistics
  const { data: stats } = useQuery({
    queryKey: ['deployment-stats'],
    queryFn: () => apiClient.get('/api/deployments/stats/').then(res => res.data),
  });

  // Filter deployments based on status
  const filteredDeployments = deployments.filter((d: any) => {
    if (statusFilter === 'all') return true;
    return d.status === statusFilter;
  });

  const pendingDeployments = deployments.filter((d: any) => d.status === 'pending');
  const flowDeployments = deployments.filter((d: any) => d.flow_id);

  const deploymentStats = {
    totalDeployments: deployments.length,
    activeDeployments: deployments.filter((d: any) => d.status === 'active').length,
    pendingDeployments: pendingDeployments.length,
    flowDeployments: flowDeployments.length,
    totalRequests: stats?.total_requests || 0,
    averageResponseTime: stats?.average_response_time || 0,
  };

  const handleCreateNew = () => {
    setEditingDeployment(null);
    setIsModalVisible(true);
  };

  const handleEdit = (deployment: any) => {
    setEditingDeployment(deployment);
    setIsModalVisible(true);
  };

  const handleModalClose = () => {
    setIsModalVisible(false);
    setEditingDeployment(null);
  };

  const handleRefresh = () => {
    console.log('🔄 Manual refresh triggered');
    queryClient.invalidateQueries({ queryKey: ['deployments'] });
    queryClient.invalidateQueries({ queryKey: ['deployment-stats'] });
  };

  return (
    <Content style={{ padding: '24px' }}>
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={2} style={{ margin: 0 }}>
            API Deployments
            {pendingDeployments.length > 0 && (
              <Badge 
                count={pendingDeployments.length} 
                style={{ marginLeft: 8 }}
                title={`${pendingDeployments.length} pending approvals`}
              />
            )}
          </Title>
          <Space>
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 150 }}
              options={[
                { label: 'All Status', value: 'all' },
                { label: 'Active', value: 'active' },
                { label: 'Pending', value: 'pending' },
                { label: 'Inactive', value: 'inactive' },
              ]}
            />
            <Button
              icon={<QuestionCircleOutlined />}
              onClick={() => setDocsVisible(true)}
              title="API Usage Documentation"
            >
              API Guide
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              loading={deploymentsLoading}
              title="Refresh deployments"
            >
              Refresh
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateNew}
            >
              New Deployment
            </Button>
          </Space>
        </div>

        {/* Authentication Error Alert */}
        {deploymentsError && (deploymentsError as any)?.response?.status === 401 && (
          <Alert
            message="Authentication Error"
            description="Your session may have expired. Please refresh the page or log in again."
            type="error"
            style={{ marginBottom: 16 }}
            showIcon
            action={
              <Button size="small" onClick={() => window.location.reload()}>
                Refresh Page
              </Button>
            }
          />
        )}

        {/* Other Errors Alert */}
        {deploymentsError && (deploymentsError as any)?.response?.status !== 401 && (
          <Alert
            message="Failed to Load Deployments"
            description={`Error: ${(deploymentsError as any)?.message || 'Unknown error occurred'}`}
            type="error"
            style={{ marginBottom: 16 }}
            showIcon
            action={
              <Button size="small" onClick={handleRefresh}>
                Retry
              </Button>
            }
          />
        )}

        {/* Pending Approvals Alert */}
        {pendingDeployments.length > 0 && (
          <Alert
            message={`${pendingDeployments.length} deployments awaiting approval`}
            description={
              <Space direction="vertical" size="small">
                <div>The following deployments require your approval:</div>
                {pendingDeployments.slice(0, 3).map((deployment: any) => (
                  <div key={deployment.id}>
                    • {deployment.name} ({deployment.flow_id ? 'Flow' : 'API'})
                  </div>
                ))}
                {pendingDeployments.length > 3 && (
                  <div>... and {pendingDeployments.length - 3} more</div>
                )}
              </Space>
            }
            type="warning"
            icon={<CheckCircleOutlined />}
            showIcon
            style={{ marginBottom: 16 }}
            action={
              <Button 
                size="small" 
                onClick={() => setStatusFilter('pending')}
              >
                Review All
              </Button>
            }
          />
        )}
        
        <DeploymentStats deploymentStats={deploymentStats} />
      </div>

      <DeploymentTable
        deployments={filteredDeployments}
        loading={deploymentsLoading}
        onEdit={handleEdit}
      />

      <DeploymentForm
        visible={isModalVisible}
        onCancel={handleModalClose}
        deployment={editingDeployment}
        flows={flows}
      />

      <DocumentationViewer
        visible={docsVisible}
        onClose={() => setDocsVisible(false)}
      />
    </Content>
  );
};

export default ApiDeploymentsPage;