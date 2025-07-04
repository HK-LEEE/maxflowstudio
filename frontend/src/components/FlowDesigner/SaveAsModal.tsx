/**
 * Save As Modal Component
 * 다른 이름으로 저장 기능을 위한 모달
 */

import React, { useState } from 'react';
import { Modal, Form, Input, message } from 'antd';
import { SaveOutlined } from '@ant-design/icons';

interface SaveAsModalProps {
  visible: boolean;
  onCancel: () => void;
  onSave: (name: string, description?: string) => Promise<void>;
  currentFlowName?: string;
  loading?: boolean;
}

const SaveAsModal: React.FC<SaveAsModalProps> = ({
  visible,
  onCancel,
  onSave,
  currentFlowName,
  loading = false
}) => {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      
      await onSave(values.name, values.description);
      
      form.resetFields();
      setSaving(false);
      message.success('Flow가 성공적으로 복제되었습니다!');
    } catch (error: any) {
      setSaving(false);
      if (error.errorFields) {
        // Form validation errors - already handled by form
        return;
      }
      
      // API errors
      console.error('Save as error:', error);
      message.error(error.message || 'Flow 복제 중 오류가 발생했습니다');
    }
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <SaveOutlined />
          다른 이름으로 저장
        </div>
      }
      open={visible}
      onOk={handleSave}
      onCancel={handleCancel}
      confirmLoading={saving || loading}
      okText="저장"
      cancelText="취소"
      width={500}
      destroyOnClose
    >
      <div style={{ marginBottom: 16 }}>
        <p style={{ color: '#666', margin: 0 }}>
          현재 Flow를 새로운 이름으로 복제합니다. 원본 Flow는 그대로 유지됩니다.
        </p>
        {currentFlowName && (
          <p style={{ color: '#888', margin: '8px 0 0 0', fontSize: '14px' }}>
            원본: {currentFlowName}
          </p>
        )}
      </div>

      <Form
        form={form}
        layout="vertical"
        initialValues={{
          name: currentFlowName ? `${currentFlowName} - 복사본` : '',
          description: ''
        }}
      >
        <Form.Item
          label="새 Flow 이름"
          name="name"
          rules={[
            { required: true, message: 'Flow 이름을 입력해주세요' },
            { min: 1, message: '이름은 최소 1글자 이상이어야 합니다' },
            { max: 255, message: '이름은 255글자를 초과할 수 없습니다' },
            {
              validator: (_, value) => {
                if (value && value.trim() !== value) {
                  return Promise.reject(new Error('이름의 앞뒤 공백은 제거됩니다'));
                }
                return Promise.resolve();
              }
            }
          ]}
        >
          <Input
            placeholder="새로운 Flow 이름을 입력하세요"
            maxLength={255}
            showCount
          />
        </Form.Item>

        <Form.Item
          label="설명 (선택사항)"
          name="description"
          rules={[
            { max: 1000, message: '설명은 1000글자를 초과할 수 없습니다' }
          ]}
        >
          <Input.TextArea
            placeholder="Flow에 대한 설명을 입력하세요"
            rows={3}
            maxLength={1000}
            showCount
          />
        </Form.Item>
      </Form>

      <div style={{ 
        background: '#f5f5f5', 
        padding: '12px', 
        borderRadius: '6px',
        marginTop: '16px',
        fontSize: '13px',
        color: '#666'
      }}>
        <strong>참고:</strong>
        <ul style={{ margin: '4px 0 0 0', paddingLeft: '20px' }}>
          <li>현재 Flow의 모든 노드와 연결이 복제됩니다</li>
          <li>새 Flow는 동일한 워크스페이스에 생성됩니다</li>
          <li>버전 히스토리는 새로 시작됩니다 (v1.0)</li>
        </ul>
      </div>
    </Modal>
  );
};

export default SaveAsModal;