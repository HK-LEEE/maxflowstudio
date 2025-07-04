/**
 * System Status Page
 * Shows system health and monitoring information
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Card, 
  Row, 
  Col, 
  Statistic, 
  Progress, 
  Tag, 
  Button,
  Space,
  Typography,
  Alert,
  Spin,
  Descriptions,
  Tabs,
  Divider
} from 'antd';
import { 
  ReloadOutlined, 
  CheckCircleOutlined, 
  CloseCircleOutlined,
  DashboardOutlined,
  SettingOutlined,
  MonitorOutlined,
  PartitionOutlined,
  PlayCircleOutlined,
  LoadingOutlined,
  ApiOutlined
} from '@ant-design/icons';
import { apiClient } from '../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface HealthStatus {
  status: string;
  healthy: boolean;
  services: Record<string, boolean>;
  issues: string[];
  timestamp: string;
  uptime_seconds: number;
}

interface SystemMetrics {
  timestamp: string;
  system: {
    cpu_percent: number;
    memory_percent: number;
    memory_used_bytes: number;
    memory_total_bytes: number;
    disk_percent: number;
    disk_used_bytes: number;
    disk_total_bytes: number;
    active_connections: number;
    uptime_seconds: number;
  };
  application: {
    total_flows: number;
    active_flows: number;
    total_executions: number;
    running_executions: number;
    completed_executions: number;
    failed_executions: number;
    total_deployments: number;
    active_deployments: number;
    queue_size: number;
    worker_count: number;
  };
}

interface DetailedHealth {
  status: string;
  healthy: boolean;
  version: string;
  services: Record<string, boolean>;
  system: {
    cpu_percent: number;
    memory_percent: number;
    disk_percent: number;
    uptime_seconds: number;
    active_connections: number;
  };
  application: {
    total_flows: number;
    total_executions: number;
    running_executions: number;
    total_deployments: number;
    active_deployments: number;
    queue_size: number;
  };
  database: any;
  system_info: any;
  last_check: string;
}

export const SystemStatusPage: React.FC = () => {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  // Fetch health status
  const { 
    data: healthStatus, 
    isLoading: healthLoading, 
    refetch: refetchHealth,
    error: healthError 
  } = useQuery<HealthStatus>({
    queryKey: ['system-health'],
    queryFn: () => apiClient.get('/api/system/health/'),
    refetchInterval: autoRefresh ? 5000 : false,
  });

  // Fetch current metrics
  const { 
    data: currentMetrics, 
    isLoading: metricsLoading,
    refetch: refetchMetrics 
  } = useQuery<SystemMetrics>({
    queryKey: ['current-metrics'],
    queryFn: () => apiClient.get('/api/system/metrics/current/'),
    refetchInterval: autoRefresh ? 10000 : false,
    retry: false,
  });

  // Fetch detailed health
  const { 
    data: detailedHealth, 
    isLoading: detailedLoading,
    refetch: refetchDetailed 
  } = useQuery<DetailedHealth>({
    queryKey: ['detailed-health'],
    queryFn: () => apiClient.get('/api/system/health/detailed/'),
    refetchInterval: autoRefresh ? 30000 : false,
  });

  const handleRefresh = () => {
    refetchHealth();
    refetchMetrics();
    refetchDetailed();
  };

  const getStatusIcon = (status: string | boolean) => {
    const isHealthy = typeof status === 'boolean' ? status : 
                     status.toLowerCase() === 'healthy' || status.toLowerCase() === 'connected';
    
    if (isHealthy) {
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    } else {
      return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
    }
  };

  const getStatusColor = (status: string | boolean) => {
    const isHealthy = typeof status === 'boolean' ? status : 
                     status.toLowerCase() === 'healthy' || status.toLowerCase() === 'connected';
    return isHealthy ? 'success' : 'error';
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  };

  if (healthError) {
    return (
      <Alert
        message="Failed to load system status"
        description="You may not have sufficient permissions or the system is unavailable."
        type="error"
        showIcon
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Title level={2}>System Status</Title>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={healthLoading || metricsLoading}
          >
            Refresh
          </Button>
          <Button
            type={autoRefresh ? 'primary' : 'default'}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            Auto Refresh: {autoRefresh ? 'ON' : 'OFF'}
          </Button>
        </Space>
      </div>

      {/* Overall Health Status */}
      {healthStatus && (
        <Alert
          message={`System Status: ${healthStatus.status.toUpperCase()}`}
          description={
            healthStatus.issues.length > 0 ? (
              <div>
                <div>Issues detected:</div>
                <ul className="mt-2">
                  {healthStatus.issues.map((issue, index) => (
                    <li key={index}>{issue}</li>
                  ))}
                </ul>
              </div>
            ) : (
              'All systems operational'
            )
          }
          type={healthStatus.healthy ? 'success' : 'error'}
          showIcon
        />
      )}

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane
          tab={
            <span>
              <DashboardOutlined />
              Overview
            </span>
          }
          key="overview"
        >
          {healthLoading ? (
            <div className="flex justify-center items-center h-64">
              <Spin size="large" />
            </div>
          ) : (
            <div className="space-y-6">
              {/* Service Status Cards */}
              <Row gutter={[16, 16]}>
                {healthStatus?.services && Object.entries(healthStatus.services).map(([service, status]) => (
                  <Col xs={24} sm={12} lg={6} key={service}>
                    <Card>
                      <Statistic
                        title={service.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        value={status ? 'Healthy' : 'Unhealthy'}
                        prefix={getStatusIcon(status)}
                        valueStyle={{ 
                          color: status ? '#3f8600' : '#cf1322',
                          fontSize: '16px'
                        }}
                      />
                    </Card>
                  </Col>
                ))}
              </Row>

              {/* Application Metrics */}
              {currentMetrics?.application && (
                <>
                  <Divider>Application Statistics</Divider>
                  <Row gutter={[16, 16]}>
                    <Col xs={24} sm={12} lg={6}>
                      <Card>
                        <Statistic
                          title="Total Flows"
                          value={currentMetrics.application.total_flows}
                          prefix={<PartitionOutlined />}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Card>
                        <Statistic
                          title="Total Executions"
                          value={currentMetrics.application.total_executions}
                          prefix={<PlayCircleOutlined />}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Card>
                        <Statistic
                          title="Running Executions"
                          value={currentMetrics.application.running_executions}
                          prefix={<LoadingOutlined />}
                          valueStyle={{ color: '#1890ff' }}
                        />
                      </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                      <Card>
                        <Statistic
                          title="Active Deployments"
                          value={currentMetrics.application.active_deployments}
                          prefix={<ApiOutlined />}
                          valueStyle={{ color: '#52c41a' }}
                        />
                      </Card>
                    </Col>
                  </Row>
                </>
              )}
            </div>
          )}
        </TabPane>

        <TabPane
          tab={
            <span>
              <MonitorOutlined />
              System Metrics
            </span>
          }
          key="metrics"
        >
          {metricsLoading ? (
            <div className="flex justify-center items-center h-64">
              <Spin size="large" />
            </div>
          ) : currentMetrics ? (
            <div className="space-y-6">
              {/* System Resource Usage */}
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={8}>
                  <Card title="CPU Usage">
                    <Progress
                      type="circle"
                      percent={Math.round(currentMetrics.system.cpu_percent)}
                      status={currentMetrics.system.cpu_percent > 80 ? 'exception' : 'normal'}
                    />
                  </Card>
                </Col>
                <Col xs={24} lg={8}>
                  <Card title="Memory Usage">
                    <Progress
                      type="circle"
                      percent={Math.round(currentMetrics.system.memory_percent)}
                      status={currentMetrics.system.memory_percent > 85 ? 'exception' : 'normal'}
                    />
                    <div className="mt-4 text-center">
                      <Text type="secondary">
                        {formatBytes(currentMetrics.system.memory_used_bytes)} / {formatBytes(currentMetrics.system.memory_total_bytes)}
                      </Text>
                    </div>
                  </Card>
                </Col>
                <Col xs={24} lg={8}>
                  <Card title="Disk Usage">
                    <Progress
                      type="circle"
                      percent={Math.round(currentMetrics.system.disk_percent)}
                      status={currentMetrics.system.disk_percent > 90 ? 'exception' : 'normal'}
                    />
                    <div className="mt-4 text-center">
                      <Text type="secondary">
                        {formatBytes(currentMetrics.system.disk_used_bytes)} / {formatBytes(currentMetrics.system.disk_total_bytes)}
                      </Text>
                    </div>
                  </Card>
                </Col>
              </Row>

              {/* System Information */}
              <Card title="System Information">
                <Row gutter={[16, 16]}>
                  <Col xs={24} sm={12}>
                    <Statistic
                      title="Uptime"
                      value={formatUptime(currentMetrics.system.uptime_seconds)}
                    />
                  </Col>
                  <Col xs={24} sm={12}>
                    <Statistic
                      title="Active Connections"
                      value={currentMetrics.system.active_connections}
                    />
                  </Col>
                </Row>
              </Card>
            </div>
          ) : (
            <Alert message="Metrics not available" type="warning" />
          )}
        </TabPane>

        <TabPane
          tab={
            <span>
              <SettingOutlined />
              Detailed Status
            </span>
          }
          key="detailed"
        >
          {detailedLoading ? (
            <div className="flex justify-center items-center h-64">
              <Spin size="large" />
            </div>
          ) : detailedHealth ? (
            <div className="space-y-6">
              <Descriptions title="System Details" bordered column={2}>
                <Descriptions.Item label="Status">
                  <Tag color={getStatusColor(detailedHealth.healthy)}>
                    {getStatusIcon(detailedHealth.healthy)} {detailedHealth.status.toUpperCase()}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Version">
                  <Tag color="blue">{detailedHealth.version}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="Last Check">
                  {new Date(detailedHealth.last_check).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label="Uptime">
                  {formatUptime(detailedHealth.system.uptime_seconds)}
                </Descriptions.Item>
              </Descriptions>

              {detailedHealth.database && (
                <Card title="Database Statistics">
                  <Descriptions bordered column={2}>
                    <Descriptions.Item label="Total Flows">
                      {detailedHealth.database.total_flows}
                    </Descriptions.Item>
                    <Descriptions.Item label="Total Executions">
                      {detailedHealth.database.total_executions}
                    </Descriptions.Item>
                    <Descriptions.Item label="Total Deployments">
                      {detailedHealth.database.total_deployments}
                    </Descriptions.Item>
                    <Descriptions.Item label="Recent Executions (24h)">
                      {detailedHealth.database.recent_executions_24h}
                    </Descriptions.Item>
                  </Descriptions>
                </Card>
              )}
            </div>
          ) : (
            <Alert message="Detailed status not available" type="warning" />
          )}
        </TabPane>
      </Tabs>
    </div>
  );
};