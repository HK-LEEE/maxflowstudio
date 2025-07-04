/**
 * 파일명: DeploymentStats.tsx (80줄)
 * 목적: API 배포 통계 및 메트릭 표시 컴포넌트
 * 동작 과정:
 * 1. 배포별 요청 수, 응답 시간 등 통계 표시
 * 2. 최근 활동 및 상태 모니터링
 * 3. 실시간 메트릭 업데이트
 * 데이터베이스 연동: api_request_logs 테이블에서 통계 조회
 * 의존성: 없음 (독립적 통계 컴포넌트)
 */

import React from 'react';
import { Card, Statistic, Row, Col, Tag } from 'antd';
import {
  ApiOutlined,
  BarChartOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';

interface DeploymentStatsProps {
  deploymentStats: {
    totalDeployments: number;
    activeDeployments: number;
    totalRequests: number;
    averageResponseTime: number;
  };
}

export const DeploymentStats: React.FC<DeploymentStatsProps> = ({
  deploymentStats,
}) => {
  const formatResponseTime = (time: number) => {
    if (time < 1000) {
      return `${time.toFixed(0)}ms`;
    }
    return `${(time / 1000).toFixed(1)}s`;
  };

  const getStatusColor = (activeCount: number, totalCount: number) => {
    const ratio = activeCount / totalCount;
    if (ratio >= 0.8) return 'success';
    if (ratio >= 0.5) return 'warning';
    return 'error';
  };

  return (
    <Row gutter={16} style={{ marginBottom: 24 }}>
      <Col span={6}>
        <Card>
          <Statistic
            title="Total Deployments"
            value={deploymentStats.totalDeployments}
            prefix={<ApiOutlined />}
            valueStyle={{ color: '#1890ff' }}
          />
        </Card>
      </Col>
      
      <Col span={6}>
        <Card>
          <Statistic
            title="Active Deployments"
            value={deploymentStats.activeDeployments}
            prefix={<CheckCircleOutlined />}
            valueStyle={{ 
              color: getStatusColor(
                deploymentStats.activeDeployments, 
                deploymentStats.totalDeployments
              ) === 'success' ? '#52c41a' : '#faad14'
            }}
            suffix={
              <Tag color={getStatusColor(
                deploymentStats.activeDeployments, 
                deploymentStats.totalDeployments
              )}>
                {deploymentStats.totalDeployments > 0 
                  ? Math.round((deploymentStats.activeDeployments / deploymentStats.totalDeployments) * 100)
                  : 0}%
              </Tag>
            }
          />
        </Card>
      </Col>
      
      <Col span={6}>
        <Card>
          <Statistic
            title="Total Requests"
            value={deploymentStats.totalRequests}
            prefix={<BarChartOutlined />}
            valueStyle={{ color: '#722ed1' }}
          />
        </Card>
      </Col>
      
      <Col span={6}>
        <Card>
          <Statistic
            title="Avg Response Time"
            value={formatResponseTime(deploymentStats.averageResponseTime)}
            prefix={<ClockCircleOutlined />}
            valueStyle={{ 
              color: deploymentStats.averageResponseTime < 500 ? '#52c41a' : '#faad14'
            }}
          />
        </Card>
      </Col>
    </Row>
  );
};