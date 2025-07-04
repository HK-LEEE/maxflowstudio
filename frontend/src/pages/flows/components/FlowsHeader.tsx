/**
 * 파일명: FlowsHeader.tsx (70줄)
 * 목적: Flows 페이지 헤더 및 통계 컴포넌트
 * 동작 과정:
 * 1. 페이지 제목 및 새 Flow 생성 버튼 표시
 * 2. Flow 통계 정보 표시 (총 개수, 활성화된 Flow 등)
 * 3. 검색 및 필터 기능 제공
 * 데이터베이스 연동: flows 테이블에서 집계 데이터 조회
 * 의존성: 없음 (독립적 헤더 컴포넌트)
 */

import React from 'react';
import {
  Row,
  Col,
  Typography,
  Button,
  Space,
  Statistic,
  Card,
} from 'antd';
import {
  PlusOutlined,
  PartitionOutlined,
  PlayCircleOutlined,
  TeamOutlined,
} from '@ant-design/icons';

const { Title } = Typography;

interface FlowsHeaderProps {
  onCreateFlow: () => void;
  totalFlows: number;
  activeFlows: number;
  totalWorkspaces: number;
}

export const FlowsHeader: React.FC<FlowsHeaderProps> = ({
  onCreateFlow,
  totalFlows,
  activeFlows,
  totalWorkspaces,
}) => {
  return (
    <div style={{ marginBottom: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={2} style={{ margin: 0 }}>
          Flows
        </Title>
        <Space>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={onCreateFlow}
          >
            Create Flow
          </Button>
        </Space>
      </div>

      <Row gutter={16}>
        <Col span={8}>
          <Card>
            <Statistic
              title="Total Flows"
              value={totalFlows}
              prefix={<PartitionOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Active Flows"
              value={activeFlows}
              prefix={<PlayCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="Workspaces"
              value={totalWorkspaces}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};