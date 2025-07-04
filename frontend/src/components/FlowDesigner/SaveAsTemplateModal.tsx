/**
 * Save As Template Modal Component
 * 관리자용 템플릿 저장 기능을 위한 모달
 */

import React, { useState } from 'react';
import { Modal, Form, Input, Select, Switch, message } from 'antd';
import { CloudUploadOutlined } from '@ant-design/icons';

const { Option } = Select;
const { TextArea } = Input;

interface SaveAsTemplateModalProps {
  visible: boolean;
  onCancel: () => void;
  onSave: (data: {
    name: string;
    description?: string;
    category?: string;
    is_public: boolean;
    thumbnail?: string;
  }) => Promise<void>;
  currentFlowName?: string;
  loading?: boolean;
}

const SaveAsTemplateModal: React.FC<SaveAsTemplateModalProps> = ({
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
      
      await onSave({
        name: values.name,
        description: values.description,
        category: values.category || 'General',
        is_public: values.is_public ?? true,
        thumbnail: values.thumbnail
      });
      
      form.resetFields();
      setSaving(false);
      message.success('템플릿이 성공적으로 저장되었습니다!');
    } catch (error: any) {
      setSaving(false);
      if (error.errorFields) {
        // Form validation errors - already handled by form
        return;
      }
      
      // API errors
      console.error('Save template error:', error);
      message.error(error.message || '템플릿 저장 중 오류가 발생했습니다');
    }
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  const categoryOptions = [
    'General',
    'Data Processing',
    'AI/ML',
    'Automation',
    'Analysis',
    'Integration',
    'Workflow',
    'API Integration',
    'Data Transformation',
    'Reporting'
  ];

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <CloudUploadOutlined />
          템플릿으로 저장
        </div>
      }
      open={visible}
      onOk={handleSave}
      onCancel={handleCancel}
      confirmLoading={saving || loading}
      okText="템플릿 저장"
      cancelText="취소"
      width={600}
      destroyOnClose
    >
      <div style={{ marginBottom: 16 }}>
        <p style={{ color: '#666', margin: 0 }}>
          현재 Flow를 다른 사용자들이 사용할 수 있는 템플릿으로 저장합니다.
        </p>
        {currentFlowName && (
          <p style={{ color: '#888', margin: '8px 0 0 0', fontSize: '14px' }}>
            원본 Flow: {currentFlowName}
          </p>
        )}
      </div>

      <Form
        form={form}
        layout="vertical"
        initialValues={{
          name: currentFlowName ? `${currentFlowName} 템플릿` : '',
          description: '',
          category: 'General',
          is_public: true,
          thumbnail: ''
        }}
      >
        <Form.Item
          label="템플릿 이름"
          name="name"
          rules={[
            { required: true, message: '템플릿 이름을 입력해주세요' },
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
            placeholder="템플릿 이름을 입력하세요"
            maxLength={255}
            showCount
          />
        </Form.Item>

        <Form.Item
          label="설명"
          name="description"
          rules={[
            { max: 1000, message: '설명은 1000글자를 초과할 수 없습니다' }
          ]}
        >
          <TextArea
            placeholder="템플릿에 대한 설명을 입력하세요 (사용자들이 이해하기 쉽게 작성)"
            rows={3}
            maxLength={1000}
            showCount
          />
        </Form.Item>

        <Form.Item
          label="카테고리"
          name="category"
          rules={[
            { required: true, message: '카테고리를 선택해주세요' }
          ]}
        >
          <Select placeholder="템플릿 카테고리를 선택하세요">
            {categoryOptions.map(category => (
              <Option key={category} value={category}>
                {category}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          label="썸네일 이미지 URL (선택사항)"
          name="thumbnail"
          rules={[
            {
              type: 'url',
              message: '올바른 URL 형식을 입력해주세요'
            }
          ]}
        >
          <Input
            placeholder="https://example.com/image.png"
          />
        </Form.Item>

        <Form.Item
          label="공개 설정"
          name="is_public"
          valuePropName="checked"
        >
          <Switch 
            checkedChildren="공개" 
            unCheckedChildren="비공개"
            defaultChecked={true}
          />
        </Form.Item>
      </Form>

      <div style={{ 
        background: '#f0f6ff', 
        padding: '12px', 
        borderRadius: '6px',
        marginTop: '16px',
        fontSize: '13px',
        color: '#0958d9',
        border: '1px solid #d6e4ff'
      }}>
        <strong>관리자 권한:</strong>
        <ul style={{ margin: '4px 0 0 0', paddingLeft: '20px' }}>
          <li>저장된 템플릿은 모든 사용자에게 제공됩니다</li>
          <li>공개 템플릿은 누구나 사용할 수 있습니다</li>
          <li>비공개 템플릿은 관리자만 관리할 수 있습니다</li>
          <li>템플릿은 나중에 수정하거나 삭제할 수 있습니다</li>
        </ul>
      </div>
    </Modal>
  );
};

export default SaveAsTemplateModal;