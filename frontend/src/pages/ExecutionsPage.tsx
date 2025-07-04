/**
 * Executions Page Component
 */

import React, { useState, useEffect } from 'react';
import { Table, Tag, Space, Button, message, Modal } from 'antd';
import { EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import { api } from '../services/api';

interface Execution {
  id: string;
  flow_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  inputs?: any;
  outputs?: any;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  duration?: number;
}

export const ExecutionsPage: React.FC = () => {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState<Execution | null>(null);
  const [detailsVisible, setDetailsVisible] = useState(false);

  useEffect(() => {
    loadExecutions();
    
    // Auto-refresh every 5 seconds to see status updates
    const interval = setInterval(loadExecutions, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadExecutions = async () => {
    setLoading(true);
    try {
      const response = await api.executions.list();
      setExecutions(response.data);
    } catch (error) {
      message.error('Failed to load executions');
      console.error('Load executions error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetails = (execution: Execution) => {
    setSelectedExecution(execution);
    setDetailsVisible(true);
  };

  const formatDuration = (duration?: number) => {
    if (!duration) return '-';
    if (duration < 60) return `${duration.toFixed(1)}s`;
    return `${Math.floor(duration / 60)}m ${(duration % 60).toFixed(1)}s`;
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'green';
      case 'running': return 'blue';
      case 'pending': return 'orange';
      case 'failed': return 'red';
      case 'cancelled': return 'default';
      default: return 'default';
    }
  };

  const columns = [
    {
      title: 'Execution ID',
      dataIndex: 'id',
      key: 'id',
      render: (id: string) => (
        <span className="font-mono text-sm">{id.slice(0, 8)}...</span>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Started',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (date: string) => 
        date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: 'Completed',
      dataIndex: 'completed_at',
      key: 'completed_at',
      render: (date: string) => 
        date ? new Date(date).toLocaleString() : '-',
    },
    {
      title: 'Duration',
      dataIndex: 'duration',
      key: 'duration',
      render: (duration: number) => formatDuration(duration),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Execution) => (
        <Space>
          <Button 
            type="link" 
            icon={<EyeOutlined />}
            onClick={() => handleViewDetails(record)}
          >
            View
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Executions</h1>
        <Button 
          icon={<ReloadOutlined />} 
          onClick={loadExecutions}
          loading={loading}
        >
          Refresh
        </Button>
      </div>
      
      <Table
        columns={columns}
        dataSource={executions}
        loading={loading}
        rowKey="id"
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
        }}
        locale={{ emptyText: 'No executions yet. Run a flow to see executions here!' }}
      />

      <Modal
        title="Execution Details"
        open={detailsVisible}
        onCancel={() => setDetailsVisible(false)}
        footer={null}
        width={800}
      >
        {selectedExecution && (
          <div className="space-y-4">
            <div>
              <h4 className="font-semibold">Execution ID:</h4>
              <span className="font-mono">{selectedExecution.id}</span>
            </div>
            
            <div>
              <h4 className="font-semibold">Status:</h4>
              <Tag color={getStatusColor(selectedExecution.status)}>
                {selectedExecution.status.toUpperCase()}
              </Tag>
            </div>
            
            {selectedExecution.inputs && (
              <div>
                <h4 className="font-semibold">Inputs:</h4>
                <pre className="bg-gray-100 p-2 rounded text-sm overflow-auto">
                  {JSON.stringify(selectedExecution.inputs, null, 2)}
                </pre>
              </div>
            )}
            
            {selectedExecution.outputs && (
              <div>
                <h4 className="font-semibold">Outputs:</h4>
                <pre className="bg-gray-100 p-2 rounded text-sm overflow-auto max-h-64">
                  {JSON.stringify(selectedExecution.outputs, null, 2)}
                </pre>
              </div>
            )}
            
            {selectedExecution.error_message && (
              <div>
                <h4 className="font-semibold text-red-600">Error:</h4>
                <div className="bg-red-50 border border-red-200 p-2 rounded text-sm">
                  {selectedExecution.error_message}
                </div>
              </div>
            )}
            
            <div>
              <h4 className="font-semibold">Timeline:</h4>
              <div className="text-sm space-y-1">
                <div>Created: {new Date(selectedExecution.created_at).toLocaleString()}</div>
                {selectedExecution.started_at && (
                  <div>Started: {new Date(selectedExecution.started_at).toLocaleString()}</div>
                )}
                {selectedExecution.completed_at && (
                  <div>Completed: {new Date(selectedExecution.completed_at).toLocaleString()}</div>
                )}
                {selectedExecution.duration && (
                  <div>Duration: {formatDuration(selectedExecution.duration)}</div>
                )}
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};