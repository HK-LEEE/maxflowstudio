/**
 * 템플릿 관리 페이지 (관리자 전용)
 * Flow 템플릿 생성, 편집, 삭제 및 관리
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Typography,
  message,
  Modal,
  Form,
  Input,
  Select,
  Tag,
  Tooltip,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Switch,
  Upload,
  Image,
  Badge,
  Divider,
  Result
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
  SearchOutlined,
  UploadOutlined,
  FileTextOutlined,
  SettingOutlined,
  FireOutlined,
  CloudUploadOutlined,
  PictureOutlined
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import { ensureValidToken } from '../../utils/auth';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile } from 'antd/es/upload';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface Template {
  id: string;
  name: string;
  description?: string;
  category: string;
  definition: any;
  thumbnail?: string;
  is_public: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
  usage_count: number;
  display_name: string;
}

interface TemplateFormData {
  name: string;
  description?: string;
  category: string;
  is_public: boolean;
  thumbnail?: string;
}

export const TemplateManagementPage: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [filteredTemplates, setFilteredTemplates] = useState<Template[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [categories, setCategories] = useState<string[]>([]);
  const [stats, setStats] = useState<any>(null);
  
  // Modal states
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [viewModalVisible, setViewModalVisible] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  
  // Form
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  
  // File upload
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  // 관리자 권한 확인
  if (!user?.is_superuser) {
    return (
      <Card>
        <Result
          status="403"
          title="403"
          subTitle="이 페이지에 접근할 권한이 없습니다."
          extra={<Button type="primary" href="/dashboard">대시보드로 돌아가기</Button>}
        />
      </Card>
    );
  }

  // Helper function to get auth headers
  const getAuthHeaders = async () => {
    const token = await ensureValidToken();
    if (!token) {
      throw new Error('Authentication token not available');
    }
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  // Load data on mount
  useEffect(() => {
    loadTemplates();
    loadStats();
  }, []);

  // Filter templates when search or category changes
  useEffect(() => {
    let filtered = templates;

    if (selectedCategory !== 'all') {
      filtered = filtered.filter(template => template.category === selectedCategory);
    }

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(template =>
        template.name.toLowerCase().includes(term) ||
        template.description?.toLowerCase().includes(term)
      );
    }

    setFilteredTemplates(filtered);
  }, [templates, searchTerm, selectedCategory]);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const headers = await getAuthHeaders();
      
      const response = await fetch('/api/templates/?page_size=100', {
        headers,
      });

      if (response.ok) {
        const data = await response.json();
        setTemplates(data.items || []);
        
        // Extract unique categories
        const uniqueCategories = Array.from(
          new Set(data.items?.map((t: Template) => t.category).filter(Boolean))
        ) as string[];
        setCategories(uniqueCategories);
      } else {
        message.error('템플릿 목록을 불러오는데 실패했습니다');
      }
    } catch (error) {
      console.error('Failed to load templates:', error);
      message.error('템플릿 목록을 불러오는데 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch('/api/templates/stats', {
        headers,
      });

      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const handleCreateTemplate = async (values: TemplateFormData) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch('/api/templates/', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          ...values,
          definition: { nodes: [], edges: [] } // Empty template definition
        }),
      });

      if (response.ok) {
        message.success('템플릿이 성공적으로 생성되었습니다');
        setCreateModalVisible(false);
        createForm.resetFields();
        setFileList([]);
        loadTemplates();
      } else {
        const error = await response.json();
        message.error(error.detail || '템플릿 생성에 실패했습니다');
      }
    } catch (error) {
      console.error('Failed to create template:', error);
      message.error('템플릿 생성에 실패했습니다');
    }
  };

  const handleUpdateTemplate = async (values: TemplateFormData) => {
    if (!selectedTemplate) return;

    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`/api/templates/${selectedTemplate.id}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(values),
      });

      if (response.ok) {
        message.success('템플릿이 성공적으로 수정되었습니다');
        setEditModalVisible(false);
        editForm.resetFields();
        setSelectedTemplate(null);
        loadTemplates();
      } else {
        const error = await response.json();
        message.error(error.detail || '템플릿 수정에 실패했습니다');
      }
    } catch (error) {
      console.error('Failed to update template:', error);
      message.error('템플릿 수정에 실패했습니다');
    }
  };

  const handleDeleteTemplate = async (templateId: string) => {
    try {
      const headers = await getAuthHeaders();
      const response = await fetch(`/api/templates/${templateId}`, {
        method: 'DELETE',
        headers,
      });

      if (response.ok) {
        message.success('템플릿이 성공적으로 삭제되었습니다');
        loadTemplates();
      } else {
        const error = await response.json();
        message.error(error.detail || '템플릿 삭제에 실패했습니다');
      }
    } catch (error) {
      console.error('Failed to delete template:', error);
      message.error('템플릿 삭제에 실패했습니다');
    }
  };

  const handleViewTemplate = (template: Template) => {
    setSelectedTemplate(template);
    setViewModalVisible(true);
  };

  const handleEditTemplate = (template: Template) => {
    setSelectedTemplate(template);
    editForm.setFieldsValue({
      name: template.name,
      description: template.description,
      category: template.category,
      is_public: template.is_public,
    });
    setEditModalVisible(true);
  };

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      'General': 'default',
      'Data Processing': 'blue',
      'AI/ML': 'purple',
      'Automation': 'green',
      'Analysis': 'orange',
      'Integration': 'cyan'
    };
    return colors[category] || 'default';
  };

  const columns: ColumnsType<Template> = [
    {
      title: '템플릿 정보',
      key: 'template_info',
      render: (_, record) => (
        <Space>
          <div style={{
            width: 48,
            height: 48,
            backgroundColor: '#f5f5f5',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '1px solid #e8e8e8'
          }}>
            {record.thumbnail ? (
              <Image
                src={record.thumbnail}
                alt={record.name}
                width={46}
                height={46}
                style={{ objectFit: 'cover', borderRadius: '6px' }}
                fallback="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMIAAADDCAYAAADQvc6UAAABRWlDQ1BJQ0MgUHJvZmlsZQAAKJFjYGASSSwoyGFhYGDIzSspCnJ3UoiIjFJgf8LAwSDCIMogwMCcmFxc4BgQ4ANUwgCjUcG3awyMIPqyLsis7PPOq3QdDFcvjV3jOD1boQVTPQrgSkktTgbSf4A4LbmgqISBgTEFyFYuLykAsTuAbJEioKOA7DkgdjqEvQHEToKwj4DVhAQ5A9k3gGyB5IxEoBmML4BsnSQk8XQkNtReEOBxcfXxUQg1Mjc0dyHgXNJBSWpFCYh2zi+oLMpMzyhRcASGUqqCZ16yno6CkYGRAQMDKMwhqj/fAIcloxgHQqxAjIHBEugw5sUIsSQpBobtQPdLciLEVJYzMPBHMDBsayhILEqEO4DxG0txmrERhM29nYGBddr//5/DGRjYNRkY/l7////39v///y4Dmn+LgeHANwDrkl1AuO+pmgAAADhlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAAqACAAQAAAABAAAAwqADAAQAAAABAAAAwwAAAAD9b/HnAAAHlklEQVR4Ae3dP3Ik1RnG4W+FgYxN..."
              />
            ) : (
              <FileTextOutlined style={{ fontSize: 20, color: '#999' }} />
            )}
          </div>
          <div>
            <div style={{ fontWeight: 'bold', fontSize: '16px' }}>
              {record.name}
            </div>
            <div style={{ color: '#666', fontSize: '14px' }}>
              {record.description || '설명 없음'}
            </div>
          </div>
        </Space>
      ),
    },
    {
      title: '카테고리',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => (
        <Tag color={getCategoryColor(category)}>{category}</Tag>
      ),
    },
    {
      title: '공개 여부',
      dataIndex: 'is_public',
      key: 'is_public',
      render: (isPublic: boolean) => (
        <Tag color={isPublic ? 'green' : 'orange'}>
          {isPublic ? '공개' : '비공개'}
        </Tag>
      ),
    },
    {
      title: '사용 횟수',
      dataIndex: 'usage_count',
      key: 'usage_count',
      render: (count: number) => (
        <Badge count={count} style={{ backgroundColor: '#52c41a' }} />
      ),
    },
    {
      title: '생성일',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '작업',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="템플릿 보기">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewTemplate(record)}
            />
          </Tooltip>
          <Tooltip title="템플릿 편집">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditTemplate(record)}
            />
          </Tooltip>
          <Tooltip title="템플릿 삭제">
            <Popconfirm
              title="정말로 이 템플릿을 삭제하시겠습니까?"
              onConfirm={() => handleDeleteTemplate(record.id)}
              okText="삭제"
              cancelText="취소"
            >
              <Button type="text" icon={<DeleteOutlined />} danger />
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card>
            <Space align="center" style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <SettingOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
                <Title level={2} style={{ margin: 0 }}>
                  템플릿 관리
                </Title>
              </Space>
              <Space>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setCreateModalVisible(true)}
                >
                  새 템플릿 생성
                </Button>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={loadTemplates}
                  loading={loading}
                >
                  새로고침
                </Button>
              </Space>
            </Space>
          </Card>
        </Col>

        {/* 통계 카드 */}
        {stats && (
          <Col span={24}>
            <Row gutter={16}>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="전체 템플릿"
                    value={stats.total_templates || 0}
                    prefix={<FileTextOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="공개 템플릿"
                    value={stats.public_templates || 0}
                    prefix={<CloudUploadOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="카테고리 수"
                    value={categories.length}
                    prefix={<SettingOutlined />}
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="총 사용 횟수"
                    value={stats.total_usage || 0}
                    prefix={<FireOutlined />}
                  />
                </Card>
              </Col>
            </Row>
          </Col>
        )}

        {/* 검색 및 필터 */}
        <Col span={24}>
          <Card>
            <Space style={{ width: '100%', justifyContent: 'space-between' }}>
              <Space>
                <Input
                  placeholder="템플릿 이름 또는 설명으로 검색"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{ width: 300 }}
                  prefix={<SearchOutlined />}
                />
                <Select
                  value={selectedCategory}
                  onChange={setSelectedCategory}
                  style={{ width: 200 }}
                >
                  <Option value="all">모든 카테고리</Option>
                  {categories.map(category => (
                    <Option key={category} value={category}>
                      {category}
                    </Option>
                  ))}
                </Select>
              </Space>
              <Text type="secondary">
                {filteredTemplates.length}개의 템플릿
              </Text>
            </Space>
          </Card>
        </Col>

        {/* 템플릿 목록 */}
        <Col span={24}>
          <Card>
            <Table
              columns={columns}
              dataSource={filteredTemplates}
              rowKey="id"
              loading={loading}
              pagination={{ pageSize: 10 }}
              locale={{ emptyText: '템플릿이 없습니다' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 템플릿 생성 모달 */}
      <Modal
        title="새 템플릿 생성"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          createForm.resetFields();
          setFileList([]);
        }}
        onOk={() => createForm.submit()}
        okText="생성"
        cancelText="취소"
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateTemplate}
        >
          <Form.Item
            name="name"
            label="템플릿 이름"
            rules={[{ required: true, message: '템플릿 이름을 입력하세요' }]}
          >
            <Input placeholder="템플릿 이름을 입력하세요" />
          </Form.Item>

          <Form.Item
            name="description"
            label="설명"
          >
            <TextArea
              placeholder="템플릿 설명을 입력하세요"
              rows={3}
            />
          </Form.Item>

          <Form.Item
            name="category"
            label="카테고리"
            rules={[{ required: true, message: '카테고리를 선택하세요' }]}
          >
            <Select placeholder="카테고리를 선택하세요">
              <Option value="General">General</Option>
              <Option value="Data Processing">Data Processing</Option>
              <Option value="AI/ML">AI/ML</Option>
              <Option value="Automation">Automation</Option>
              <Option value="Analysis">Analysis</Option>
              <Option value="Integration">Integration</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="is_public"
            label="공개 여부"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren="공개" unCheckedChildren="비공개" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 템플릿 편집 모달 */}
      <Modal
        title="템플릿 편집"
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false);
          editForm.resetFields();
          setSelectedTemplate(null);
        }}
        onOk={() => editForm.submit()}
        okText="수정"
        cancelText="취소"
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleUpdateTemplate}
        >
          <Form.Item
            name="name"
            label="템플릿 이름"
            rules={[{ required: true, message: '템플릿 이름을 입력하세요' }]}
          >
            <Input placeholder="템플릿 이름을 입력하세요" />
          </Form.Item>

          <Form.Item
            name="description"
            label="설명"
          >
            <TextArea
              placeholder="템플릿 설명을 입력하세요"
              rows={3}
            />
          </Form.Item>

          <Form.Item
            name="category"
            label="카테고리"
            rules={[{ required: true, message: '카테고리를 선택하세요' }]}
          >
            <Select placeholder="카테고리를 선택하세요">
              <Option value="General">General</Option>
              <Option value="Data Processing">Data Processing</Option>
              <Option value="AI/ML">AI/ML</Option>
              <Option value="Automation">Automation</Option>
              <Option value="Analysis">Analysis</Option>
              <Option value="Integration">Integration</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="is_public"
            label="공개 여부"
            valuePropName="checked"
          >
            <Switch checkedChildren="공개" unCheckedChildren="비공개" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 템플릿 보기 모달 */}
      <Modal
        title="템플릿 상세 정보"
        open={viewModalVisible}
        onCancel={() => {
          setViewModalVisible(false);
          setSelectedTemplate(null);
        }}
        footer={[
          <Button key="close" onClick={() => setViewModalVisible(false)}>
            닫기
          </Button>
        ]}
        width={600}
      >
        {selectedTemplate && (
          <div>
            <Row gutter={16}>
              <Col span={24}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text strong>템플릿 이름:</Text>
                    <div style={{ marginTop: 4 }}>
                      <Text style={{ fontSize: '16px' }}>{selectedTemplate.name}</Text>
                    </div>
                  </div>
                  
                  <Divider />
                  
                  <div>
                    <Text strong>설명:</Text>
                    <div style={{ marginTop: 4 }}>
                      <Paragraph ellipsis={{ rows: 3, expandable: true }}>
                        {selectedTemplate.description || '설명 없음'}
                      </Paragraph>
                    </div>
                  </div>
                  
                  <Row gutter={16}>
                    <Col span={12}>
                      <Text strong>카테고리:</Text>
                      <div style={{ marginTop: 4 }}>
                        <Tag color={getCategoryColor(selectedTemplate.category)}>
                          {selectedTemplate.category}
                        </Tag>
                      </div>
                    </Col>
                    <Col span={12}>
                      <Text strong>공개 여부:</Text>
                      <div style={{ marginTop: 4 }}>
                        <Tag color={selectedTemplate.is_public ? 'green' : 'orange'}>
                          {selectedTemplate.is_public ? '공개' : '비공개'}
                        </Tag>
                      </div>
                    </Col>
                  </Row>
                  
                  <Row gutter={16}>
                    <Col span={12}>
                      <Text strong>사용 횟수:</Text>
                      <div style={{ marginTop: 4 }}>
                        <Badge count={selectedTemplate.usage_count} style={{ backgroundColor: '#52c41a' }} />
                      </div>
                    </Col>
                    <Col span={12}>
                      <Text strong>생성일:</Text>
                      <div style={{ marginTop: 4 }}>
                        <Text>{new Date(selectedTemplate.created_at).toLocaleString()}</Text>
                      </div>
                    </Col>
                  </Row>
                  
                  {selectedTemplate.thumbnail && (
                    <div>
                      <Text strong>썸네일:</Text>
                      <div style={{ marginTop: 8 }}>
                        <Image
                          src={selectedTemplate.thumbnail}
                          alt={selectedTemplate.name}
                          style={{ maxWidth: '100%', maxHeight: '200px' }}
                        />
                      </div>
                    </div>
                  )}
                </Space>
              </Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  );
};