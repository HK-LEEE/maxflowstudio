/**
 * Template Loader Modal Component
 * 템플릿 로딩 기능을 위한 모달
 */

import React, { useState, useEffect } from 'react';
import { 
  Modal, 
  List, 
  Input, 
  Select, 
  Spin, 
  Empty, 
  Tag, 
  Badge, 
  Space,
  Typography,
  message,
  Tooltip,
  Card
} from 'antd';
import { 
  FileTextOutlined, 
  SearchOutlined, 
  EyeOutlined,
  LoadingOutlined,
  UserOutlined,
  CalendarOutlined,
  FireOutlined
} from '@ant-design/icons';

const { Search } = Input;
const { Option } = Select;
const { Text, Paragraph } = Typography;

interface Template {
  id: string;
  name: string;
  description?: string;
  category?: string;
  thumbnail?: string;
  is_public: boolean;
  created_at: string;
  usage_count: number;
  display_name: string;
}

interface TemplateLoaderModalProps {
  visible: boolean;
  onCancel: () => void;
  onLoad: (templateId: string) => Promise<void>;
  loading?: boolean;
}

const TemplateLoaderModal: React.FC<TemplateLoaderModalProps> = ({
  visible,
  onCancel,
  onLoad,
  loading = false
}) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [filteredTemplates, setFilteredTemplates] = useState<Template[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [loadingTemplate, setLoadingTemplate] = useState(false);

  // Fetch templates when modal opens
  useEffect(() => {
    if (visible) {
      fetchTemplates();
    }
  }, [visible]);

  // Filter templates when search or category changes
  useEffect(() => {
    let filtered = templates;

    // Category filter
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(template => 
        template.category === selectedCategory
      );
    }

    // Search filter
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(template =>
        template.name.toLowerCase().includes(term) ||
        template.description?.toLowerCase().includes(term)
      );
    }

    setFilteredTemplates(filtered);
  }, [templates, searchTerm, selectedCategory]);

  const fetchTemplates = async () => {
    try {
      setLoadingTemplates(true);
      
      // Get token
      const { ensureValidToken } = await import('../../utils/auth');
      const token = await ensureValidToken();
      
      if (!token) {
        throw new Error('인증 토큰이 없습니다');
      }

      // Fetch templates
      const response = await fetch('/api/templates/?is_public=true&page_size=50', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('템플릿 목록을 가져오는데 실패했습니다');
      }

      const data = await response.json();
      setTemplates(data.items || []);

      // Extract unique categories
      const uniqueCategories = Array.from(
        new Set(data.items?.map((t: Template) => t.category).filter(Boolean))
      ) as string[];
      setCategories(uniqueCategories);

    } catch (error: any) {
      console.error('Failed to fetch templates:', error);
      message.error(error.message || '템플릿 목록을 가져오는데 실패했습니다');
    } finally {
      setLoadingTemplates(false);
    }
  };

  const handleLoadTemplate = async (template: Template) => {
    try {
      setLoadingTemplate(true);
      setSelectedTemplate(template);

      await onLoad(template.id);
      
      message.success(`템플릿 "${template.name}"을 성공적으로 로드했습니다!`);
      handleCancel();
      
    } catch (error: any) {
      console.error('Failed to load template:', error);
      message.error(error.message || '템플릿 로드에 실패했습니다');
    } finally {
      setLoadingTemplate(false);
      setSelectedTemplate(null);
    }
  };

  const handleCancel = () => {
    setSearchTerm('');
    setSelectedCategory('all');
    setSelectedTemplate(null);
    onCancel();
  };

  const getCategoryColor = (category?: string) => {
    const colors: Record<string, string> = {
      'General': 'default',
      'Data Processing': 'blue',
      'AI/ML': 'purple',
      'Automation': 'green',
      'Analysis': 'orange',
      'Integration': 'cyan'
    };
    return colors[category || 'General'] || 'default';
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <FileTextOutlined />
          템플릿 가져오기
        </div>
      }
      open={visible}
      onCancel={handleCancel}
      footer={null}
      width={800}
      destroyOnClose
    >
      <div style={{ marginBottom: 16 }}>
        <p style={{ color: '#666', margin: '0 0 16px 0' }}>
          사용 가능한 템플릿을 선택하여 현재 Flow Editor에 로드합니다.
        </p>

        {/* Search and Filter Controls */}
        <Space style={{ width: '100%', marginBottom: 16 }}>
          <Search
            placeholder="템플릿 이름 또는 설명으로 검색"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ width: 300 }}
            prefix={<SearchOutlined />}
          />
          <Select
            value={selectedCategory}
            onChange={setSelectedCategory}
            style={{ width: 180 }}
          >
            <Option value="all">모든 카테고리</Option>
            {categories.map(category => (
              <Option key={category} value={category}>
                {category}
              </Option>
            ))}
          </Select>
        </Space>
      </div>

      {/* Templates List */}
      <div style={{ maxHeight: 500, overflowY: 'auto' }}>
        {loadingTemplates ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin 
              size="large" 
              indicator={<LoadingOutlined style={{ fontSize: 24 }} spin />}
            />
            <div style={{ marginTop: 16, color: '#666' }}>
              템플릿을 불러오는 중...
            </div>
          </div>
        ) : filteredTemplates.length === 0 ? (
          <Empty
            description={
              searchTerm || selectedCategory !== 'all' 
                ? "검색 조건에 맞는 템플릿이 없습니다"
                : "사용 가능한 템플릿이 없습니다"
            }
          />
        ) : (
          <List
            dataSource={filteredTemplates}
            renderItem={(template) => (
              <List.Item
                key={template.id}
                style={{
                  padding: '12px',
                  border: '1px solid #f0f0f0',
                  borderRadius: '8px',
                  marginBottom: '8px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  backgroundColor: selectedTemplate?.id === template.id ? '#f6ffed' : '#fff'
                }}
                onMouseEnter={(e) => {
                  if (selectedTemplate?.id !== template.id) {
                    e.currentTarget.style.backgroundColor = '#fafafa';
                  }
                }}
                onMouseLeave={(e) => {
                  if (selectedTemplate?.id !== template.id) {
                    e.currentTarget.style.backgroundColor = '#fff';
                  }
                }}
                onClick={() => handleLoadTemplate(template)}
              >
                <List.Item.Meta
                  avatar={
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
                      {template.thumbnail ? (
                        <img 
                          src={template.thumbnail} 
                          alt={template.name}
                          style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '6px' }}
                        />
                      ) : (
                        <FileTextOutlined style={{ fontSize: 20, color: '#999' }} />
                      )}
                    </div>
                  }
                  title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Text strong style={{ fontSize: 16 }}>
                        {template.name}
                      </Text>
                      {template.category && (
                        <Tag color={getCategoryColor(template.category)} size="small">
                          {template.category}
                        </Tag>
                      )}
                      {template.usage_count > 0 && (
                        <Tooltip title={`${template.usage_count}번 사용됨`}>
                          <Badge 
                            count={template.usage_count} 
                            style={{ backgroundColor: '#52c41a' }}
                            size="small"
                          />
                        </Tooltip>
                      )}
                    </div>
                  }
                  description={
                    <div>
                      {template.description && (
                        <Paragraph 
                          ellipsis={{ rows: 2, expandable: false }}
                          style={{ 
                            margin: '4px 0 8px 0', 
                            color: '#666',
                            fontSize: '14px'
                          }}
                        >
                          {template.description}
                        </Paragraph>
                      )}
                      <Space size="small" style={{ fontSize: '12px', color: '#999' }}>
                        <CalendarOutlined />
                        {new Date(template.created_at).toLocaleDateString()}
                        {template.usage_count > 0 && (
                          <>
                            <FireOutlined />
                            {template.usage_count}회 사용
                          </>
                        )}
                      </Space>
                    </div>
                  }
                />
                {selectedTemplate?.id === template.id && loadingTemplate && (
                  <div style={{ textAlign: 'center', padding: '8px 0' }}>
                    <Spin size="small" />
                    <Text style={{ marginLeft: 8, fontSize: 12, color: '#666' }}>
                      로딩 중...
                    </Text>
                  </div>
                )}
              </List.Item>
            )}
          />
        )}
      </div>

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
          <li>템플릿을 선택하면 현재 Flow가 완전히 교체됩니다</li>
          <li>기존 작업 내용을 잃지 않으려면 먼저 저장해주세요</li>
          <li>템플릿 로드 후 필요에 따라 수정하고 저장할 수 있습니다</li>
        </ul>
      </div>
    </Modal>
  );
};

export default TemplateLoaderModal;