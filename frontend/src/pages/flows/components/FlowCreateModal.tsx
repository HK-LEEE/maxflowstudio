/**
 * 파일명: FlowCreateModal.tsx (80줄)
 * 목적: 새 Flow 생성 모달 컴포넌트
 * 동작 과정:
 * 1. Flow 이름, 설명 등 기본 정보 입력
 * 2. 워크스페이스 선택 및 권한 확인
 * 3. Flow 생성 API 호출 및 리다이렉션
 * 데이터베이스 연동: flows 테이블에 새 Flow 생성
 * 의존성: 없음 (독립적 모달 컴포넌트)
 */

import React from 'react';
import {
  Modal,
  Form,
  Input,
  Select,
  message,
} from 'antd';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../../services/api';

const { TextArea } = Input;

interface FlowCreateModalProps {
  visible: boolean;
  onCancel: () => void;
  workspaces: any[];
}

export const FlowCreateModal: React.FC<FlowCreateModalProps> = ({
  visible,
  onCancel,
  workspaces,
}) => {
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: any) => apiClient.post('/api/flows', data),
    onSuccess: (response) => {
      message.success('Flow created successfully');
      queryClient.invalidateQueries({ queryKey: ['flows'] });
      form.resetFields();
      onCancel();
      navigate(`/flows/${response.data.id}`);
    },
    onError: () => {
      message.error('Failed to create flow');
    },
  });

  const handleSubmit = (values: any) => {
    createMutation.mutate(values);
  };

  return (
    <Modal
      title="Create New Flow"
      open={visible}
      onCancel={onCancel}
      onOk={() => form.submit()}
      confirmLoading={createMutation.isPending}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        <Form.Item
          name="name"
          label="Flow Name"
          rules={[{ required: true, message: 'Please enter flow name' }]}
        >
          <Input placeholder="Enter flow name" />
        </Form.Item>

        <Form.Item
          name="description"
          label="Description"
        >
          <TextArea rows={3} placeholder="Enter flow description" />
        </Form.Item>

        <Form.Item
          name="workspace_id"
          label="Workspace"
          rules={[{ required: true, message: 'Please select a workspace' }]}
        >
          <Select placeholder="Select workspace">
            {workspaces.map((workspace) => (
              <Select.Option key={workspace.id} value={workspace.id}>
                {workspace.name}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>
      </Form>
    </Modal>
  );
};