/**
 * 파일명: DeploymentForm.tsx (120줄)
 * 목적: API 배포 생성/수정 폼 컴포넌트
 * 동작 과정:
 * 1. Flow 선택 및 배포 설정 입력
 * 2. 인증 방식 및 레이트 제한 설정
 * 3. 배포 생성/업데이트 API 호출
 * 데이터베이스 연동: api_deployments 테이블에 직접 저장
 * 의존성: 없음 (독립적 폼 컴포넌트)
 */

import React from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  Switch,
  InputNumber,
  message,
} from 'antd';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../services/api';

const { TextArea } = Input;

interface DeploymentFormProps {
  visible: boolean;
  onCancel: () => void;
  deployment?: any;
  flows: any[];
}

export const DeploymentForm: React.FC<DeploymentFormProps> = ({
  visible,
  onCancel,
  deployment,
  flows,
}) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/api/deployments', data),
    onSuccess: () => {
      message.success('Deployment created successfully');
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      form.resetFields();
      onCancel();
    },
    onError: () => {
      message.error('Failed to create deployment');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      apiClient.put(`/api/deployments/${id}`, data),
    onSuccess: () => {
      message.success('Deployment updated successfully');
      queryClient.invalidateQueries({ queryKey: ['deployments'] });
      form.resetFields();
      onCancel();
    },
    onError: () => {
      message.error('Failed to update deployment');
    },
  });

  const handleSubmit = (values: any) => {
    if (deployment) {
      updateMutation.mutate({ id: deployment.id, data: values });
    } else {
      createMutation.mutate(values);
    }
  };

  return (
    <Modal
      title={deployment ? 'Edit Deployment' : 'Create New Deployment'}
      open={visible}
      onCancel={onCancel}
      onOk={() => form.submit()}
      confirmLoading={createMutation.isPending || updateMutation.isPending}
      destroyOnHidden
      width={600}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={deployment}
      >
        <Form.Item
          name="flow_id"
          label="Flow"
          rules={[{ required: true, message: 'Please select a flow' }]}
        >
          <Select placeholder="Select a flow">
            {flows.map((flow) => (
              <Select.Option key={flow.id} value={flow.id}>
                {flow.name}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="name"
          label="Deployment Name"
          rules={[{ required: true, message: 'Please enter a name' }]}
        >
          <Input placeholder="Enter deployment name" />
        </Form.Item>

        <Form.Item name="description" label="Description">
          <TextArea rows={3} placeholder="Enter description" />
        </Form.Item>

        <Form.Item
          name="endpoint_path"
          label="Endpoint Path"
          rules={[{ required: true, message: 'Please enter endpoint path' }]}
        >
          <Input
            addonBefore="/api/deployed/"
            placeholder="my-flow"
            style={{ width: '100%' }}
          />
        </Form.Item>

        <Form.Item name="version" label="Version" initialValue="1.0.0">
          <Input placeholder="1.0.0" />
        </Form.Item>

        <Form.Item
          name="rate_limit"
          label="Rate Limit (requests per minute)"
          initialValue={100}
        >
          <InputNumber min={1} max={10000} style={{ width: '100%' }} />
        </Form.Item>

        <Form.Item name="is_public" label="Public Access" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
};