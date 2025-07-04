/**
 * API Keys Page Component
 */

import React from 'react';
import { Button, Table, Space, Modal, Form, Input } from 'antd';
import { PlusOutlined, CopyOutlined, DeleteOutlined } from '@ant-design/icons';

export const ApiKeysPage: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = React.useState(false);
  const [form] = Form.useForm();

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Key',
      dataIndex: 'key',
      key: 'key',
      render: (key: string) => (
        <span className="font-mono">{key ? `${key.substring(0, 8)}...` : ''}</span>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: () => (
        <Space>
          <Button type="link" icon={<CopyOutlined />}>Copy</Button>
          <Button type="link" danger icon={<DeleteOutlined />}>Delete</Button>
        </Space>
      ),
    },
  ];

  const handleCreateKey = () => {
    setIsModalVisible(true);
  };

  const handleModalOk = () => {
    form.validateFields().then(() => {
      // TODO: Implement API key creation
      setIsModalVisible(false);
      form.resetFields();
    });
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">API Keys</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateKey}>
          Create API Key
        </Button>
      </div>
      
      <Table
        columns={columns}
        dataSource={[]}
        pagination={false}
        locale={{ emptyText: 'No API keys created yet' }}
      />

      <Modal
        title="Create API Key"
        open={isModalVisible}
        onOk={handleModalOk}
        onCancel={() => setIsModalVisible(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Key Name"
            rules={[{ required: true, message: 'Please input the key name!' }]}
          >
            <Input placeholder="Enter key name" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};