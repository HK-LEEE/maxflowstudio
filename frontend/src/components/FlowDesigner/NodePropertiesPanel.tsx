/**
 * Node Properties Panel Component
 * Provides UI for editing node configurations
 */

import React, { useEffect, useState } from 'react';
import { Form, Input, Select, Switch, Typography, Alert, Space, Button, Tooltip, Card, Divider, InputNumber, Tag, message, Modal } from 'antd';
import { 
  InfoCircleOutlined, 
  CopyOutlined,
  SettingOutlined,
  FileTextOutlined,
  RobotOutlined,
  ApiOutlined,
  DatabaseOutlined,
  FunctionOutlined,
  BranchesOutlined,
  PlayCircleOutlined,
  StopOutlined,
  ToolOutlined,
  MessageOutlined,
  EnvironmentOutlined,
  PlusOutlined,
  DeleteOutlined,
  PlaySquareOutlined,
  SearchOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import type { Node } from 'reactflow';
import { useFlowStore } from '../../store/flowStore';
import { SecureInput } from './SecureInput';
import { EnvironmentVariableManager } from './EnvironmentVariableManager';
import { OllamaService, type OllamaModel } from '../../services/ollama';
import './NodePropertiesPanel.css';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface NodePropertiesPanelProps {
  selectedNodeId: string | null;
  nodes: Node[];
  edges?: any[];
  onUpdateNode?: (nodeId: string, data: any) => void;
}

export const NodePropertiesPanel: React.FC<NodePropertiesPanelProps> = ({ selectedNodeId, nodes, edges = [], onUpdateNode }) => {
  const [form] = Form.useForm();
  const [templatePreview, setTemplatePreview] = useState<string>('');
  const [detectedVariables, setDetectedVariables] = useState<string[]>([]);
  const [connectedVariables, setConnectedVariables] = useState<string[]>([]);
  const [envVarManagerVisible, setEnvVarManagerVisible] = useState(false);
  const [environmentVariables, setEnvironmentVariables] = useState<Record<string, string>>({});
  
  // Ollama-specific state
  const [ollamaModels, setOllamaModels] = useState<OllamaModel[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelsModalVisible, setModelsModalVisible] = useState(false);
  const [modelValidationStatus, setModelValidationStatus] = useState<{
    isValidating: boolean;
    isValid: boolean | null;
    error?: string;
  }>({ isValidating: false, isValid: null });

  const selectedNode = nodes.find((node) => node.id === selectedNodeId);

  useEffect(() => {
    if (selectedNode?.data) {
      const config = selectedNode.data.config || {};
      form.setFieldsValue(config);
      
      // Detect variables in template if it's a template node
      if (selectedNode.data.type === 'template') {
        if (config.template) {
          detectVariables(config.template);
          updatePreview(config.template, {});
        }
        // Detect connected variables
        detectConnectedVariables();
      }
      
      // Validate Ollama model if it's an Ollama node
      if (selectedNode.data.type === 'ollama' && config.model) {
        validateOllamaModel(config);
      }
    }
  }, [selectedNode, form, edges]);

  const detectVariables = (template: string) => {
    const variablePattern = /\{([^}|]+)(?:\|[^}]+)?\}/g;
    const variables = new Set<string>();
    let match;
    
    while ((match = variablePattern.exec(template)) !== null) {
      variables.add(match[1].trim());
    }
    
    setDetectedVariables(Array.from(variables));
  };

  const detectConnectedVariables = () => {
    if (!selectedNodeId || !edges.length) return;
    
    // Find edges connected to this template node
    const connectedEdges = edges.filter(edge => edge.target === selectedNodeId);
    const connectedHandleNames = connectedEdges.map(edge => edge.targetHandle).filter(Boolean);
    
    // Show actual connected handle names (Variable1, Variable2, etc.)
    setConnectedVariables(connectedHandleNames);
  };

  const updatePreview = (template: string, mapping: Record<string, string>) => {
    let preview = template;
    const sampleValues: Record<string, string> = {
      name: '홍길동',
      topic: 'AI 기술',
      day: '월요일',
      time: '오후 2시',
      ...Object.fromEntries(
        Object.entries(mapping).map(([key, value]) => [value, `[${key} 값]`])
      )
    };
    
    // Simple variable replacement for preview
    Object.entries(sampleValues).forEach(([key, value]) => {
      preview = preview.replace(new RegExp(`\\{${key}(?:\\|[^}]+)?\\}`, 'g'), value);
    });
    
    setTemplatePreview(preview);
  };

  const handleFormChange = (changedValues: any, allValues: any) => {
    if (selectedNode && onUpdateNode) {
      onUpdateNode(selectedNode.id, {
        ...selectedNode.data,
        config: allValues,
      });
      
      // Update preview if template changed
      if (selectedNode.data.type === 'template') {
        if ('template' in changedValues) {
          detectVariables(allValues.template);
        }
        updatePreview(allValues.template || '', {});
      }
    }
  };

  // Ollama model query function
  const queryOllamaModels = async () => {
    const formValues = form.getFieldsValue();
    const host = formValues.host || OllamaService.getDefaultConnection().host;
    const port = formValues.port || OllamaService.getDefaultConnection().port;

    // Validate inputs
    const validation = OllamaService.validateConnection(host, port);
    if (!validation.isValid) {
      message.error(validation.error);
      return;
    }

    setLoadingModels(true);
    
    try {
      const models = await OllamaService.getModels(host, port);
      setOllamaModels(models);
      
      if (models.length === 0) {
        message.warning('연결은 성공했지만 사용 가능한 모델이 없습니다.');
      } else {
        message.success(`${models.length}개의 모델을 찾았습니다.`);
        setModelsModalVisible(true);
      }
    } catch (error) {
      message.error(error.message || 'Ollama 서버에 연결할 수 없습니다.');
      console.error('Failed to query Ollama models:', error);
    } finally {
      setLoadingModels(false);
    }
  };

  // Select model from modal
  const selectOllamaModel = (modelName: string) => {
    form.setFieldValue('model', modelName);
    setModelsModalVisible(false);
    
    // Clear validation status since we just selected a valid model
    setModelValidationStatus({ isValidating: false, isValid: true });
    
    // Trigger form change to update node data
    const allValues = form.getFieldsValue();
    allValues.model = modelName;
    handleFormChange({ model: modelName }, allValues);
    
    message.success(`모델 "${modelName}"을(를) 선택했습니다.`);
  };

  // Validate Ollama model
  const validateOllamaModel = async (config: any) => {
    const host = config.host || OllamaService.getDefaultConnection().host;
    const port = config.port || OllamaService.getDefaultConnection().port;
    const savedModel = config.model;

    if (!savedModel || savedModel.trim() === '') {
      setModelValidationStatus({ isValidating: false, isValid: null });
      return;
    }

    setModelValidationStatus({ isValidating: true, isValid: null });

    try {
      const validation = await OllamaService.validateSavedModel(host, port, savedModel);
      
      if (validation.isValid) {
        setModelValidationStatus({ isValidating: false, isValid: true });
      } else {
        setModelValidationStatus({ 
          isValidating: false, 
          isValid: false, 
          error: validation.error 
        });
        
        // Clear the model field if it doesn't exist on the server
        form.setFieldValue('model', '');
        
        // Update node data to reflect the cleared model
        const allValues = form.getFieldsValue();
        allValues.model = '';
        handleFormChange({ model: '' }, allValues);
        
        message.warning(`저장된 모델 "${savedModel}"을(를) 서버에서 찾을 수 없습니다. 모델 필드를 초기화했습니다.`);
      }
    } catch (error) {
      setModelValidationStatus({ 
        isValidating: false, 
        isValid: false, 
        error: error.message || '모델 검증 중 오류가 발생했습니다.' 
      });
    }
  };

  // Node type icons and descriptions
  const getNodeTypeInfo = (type: string) => {
    const typeMap: Record<string, { icon: React.ReactNode; description: string; name: string }> = {
      template: { icon: <FileTextOutlined />, description: '텍스트 템플릿 처리', name: '템플릿' },
      ollama: { icon: <RobotOutlined />, description: '로컬 LLM 모델', name: 'Ollama' },
      openai: { icon: <MessageOutlined />, description: 'OpenAI GPT 모델', name: 'OpenAI' },
      anthropic: { icon: <MessageOutlined />, description: 'Anthropic Claude 모델', name: 'Claude' },
      'azure-openai': { icon: <MessageOutlined />, description: 'Azure OpenAI ChatGPT', name: 'Azure OpenAI' },
      api: { icon: <ApiOutlined />, description: 'HTTP API 호출', name: 'API 호출' },
      database: { icon: <DatabaseOutlined />, description: '데이터베이스 연결', name: '데이터베이스' },
      function: { icon: <FunctionOutlined />, description: '사용자 정의 함수', name: '함수' },
      condition: { icon: <BranchesOutlined />, description: '조건부 분기', name: '조건문' },
      transform: { icon: <ToolOutlined />, description: '데이터 변환', name: '변환' },
      input: { icon: <PlayCircleOutlined />, description: '워크플로우 입력', name: '입력' },
      output: { icon: <StopOutlined />, description: '워크플로우 출력', name: '출력' },
    };
    return typeMap[type] || { icon: <SettingOutlined />, description: '노드 설정', name: type };
  };

  if (!selectedNode) {
    return (
      <div className="properties-panel">
        <div className="properties-header">
          <h3 className="properties-title">
            <SettingOutlined />
            노드 속성
          </h3>
        </div>
        <div className="properties-content">
          <div className="empty-state-card">
            <div className="empty-state-icon">
              <SettingOutlined />
            </div>
            <div className="empty-state-title">노드를 선택하세요</div>
            <div className="empty-state-description">
              캔버스에서 노드를 클릭하면<br />
              해당 노드의 속성을 편집할 수 있습니다.
            </div>
          </div>
        </div>
      </div>
    );
  }

  const nodeType = selectedNode.data.type;
  const nodeTypeInfo = getNodeTypeInfo(nodeType);

  return (
    <div className={`properties-panel node-type-${nodeType}`}>
      {/* Header */}
      <div className="properties-header">
        <h3 className="properties-title">
          <SettingOutlined />
          노드 속성
        </h3>
      </div>

      {/* Content */}
      <div className="properties-content">
        {/* Node Info Card */}
        <div className="node-info-card">
          <div className="node-info-header">
            <div className="node-type-icon">
              {nodeTypeInfo.icon}
            </div>
            <div className="node-type-info">
              <h4 className="node-type-name">{nodeTypeInfo.name}</h4>
              <p className="node-type-description">{nodeTypeInfo.description}</p>
            </div>
          </div>
          <div className="node-id-badge">
            <CopyOutlined style={{ fontSize: '10px' }} />
            {selectedNode.id}
          </div>
        </div>

        {/* Environment Variables Section */}
        <div className="env-variables-section-card">
          <div className="env-variables-header">
            <div className="env-variables-title">
              <EnvironmentOutlined />
              <span>환경변수</span>
              <Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>
                ({Object.keys(environmentVariables).length}개 로드됨)
              </Text>
            </div>
            <Button
              type="default"
              size="small"
              icon={<SettingOutlined />}
              onClick={() => setEnvVarManagerVisible(true)}
            >
              관리
            </Button>
          </div>
          
          {Object.keys(environmentVariables).length > 0 ? (
            <div className="env-variables-list">
              <Alert
                message="로드된 환경변수"
                description={
                  <div style={{ maxHeight: '120px', overflowY: 'auto' }}>
                    {Object.entries(environmentVariables).map(([key, value]) => (
                      <div key={key} style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center',
                        padding: '4px 0',
                        borderBottom: '1px solid #f0f0f0'
                      }}>
                        <Text code style={{ fontSize: '11px' }}>{key}</Text>
                        <Text type="secondary" style={{ 
                          fontSize: '10px', 
                          maxWidth: '100px', 
                          overflow: 'hidden', 
                          textOverflow: 'ellipsis' 
                        }}>
                          {value.length > 20 ? `${value.substring(0, 20)}...` : value}
                        </Text>
                      </div>
                    ))}
                  </div>
                }
                type="success"
                style={{ margin: '8px 0' }}
              />
            </div>
          ) : (
            <Alert
              message="환경변수 없음"
              description="현재 로드된 환경변수가 없습니다. 환경변수를 추가하려면 '관리' 버튼을 클릭하세요."
              type="info"
              size="small"
              style={{ margin: '8px 0' }}
            />
          )}
          
          <div className="env-usage-hint">
            <Text type="secondary" style={{ fontSize: '11px' }}>
              💡 노드 설정에서 ${'{'}환경변수명{'}'} 형식으로 환경변수를 사용할 수 있습니다
            </Text>
          </div>
        </div>

        {/* Form Section */}
        <div className="form-section-card">
          <Form
            form={form}
            layout="vertical"
            onValuesChange={handleFormChange}
            className="properties-form"
          >
            {/* Template Node Configuration */}
            {nodeType === 'template' && (
              <>
            <Form.Item
              name="template"
              label={
                <Space>
                  <span>템플릿 문자열</span>
                  <Tooltip title="변수는 {변수명} 형식으로 작성하세요">
                    <InfoCircleOutlined />
                  </Tooltip>
                </Space>
              }
            >
              <TextArea
                rows={4}
                placeholder="안녕하세요 {Variable1}님, 오늘의 주제는 {Variable2}입니다."
              />
            </Form.Item>

            {detectedVariables.length > 0 && (
              <Alert
                message="템플릿에서 감지된 변수"
                description={
                  <Space wrap>
                    {detectedVariables.map((variable) => (
                      <Text key={variable} code>{variable}</Text>
                    ))}
                  </Space>
                }
                type="info"
                className="variable-alert"
              />
            )}

            {connectedVariables.length > 0 && (
              <Alert
                message="연결된 변수 핸들"
                description={
                  <Space wrap>
                    {connectedVariables.map((variable) => (
                      <Text key={variable} code style={{ color: '#52c41a' }}>
                        {variable}
                      </Text>
                    ))}
                  </Space>
                }
                type="success"
                className="variable-alert"
              />
            )}

            <Form.Item
              name="template_mode"
              label="템플릿 모드"
            >
              <Select>
                <Option value="simple">단순 치환</Option>
                <Option value="advanced">고급 (기본값 지원)</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="undefined_behavior"
              label="정의되지 않은 변수 처리"
            >
              <Select>
                <Option value="empty">빈 문자열로 치환</Option>
                <Option value="keep">원본 유지</Option>
                <Option value="error">에러 발생</Option>
              </Select>
            </Form.Item>

            <Form.Item
              name="strip_whitespace"
              label="공백 제거"
              valuePropName="checked"
            >
              <Switch />
            </Form.Item>


            {templatePreview && (
              <div className="template-preview-card">
                <Card size="small" title="템플릿 미리보기">
                  <Paragraph copyable>{templatePreview}</Paragraph>
                </Card>
              </div>
            )}

            <div className="help-section">
              <Alert
                message="변수 입력 방법"
                description={
                  <ul>
                    <li>Variable1 ~ Variable5 핸들에 다른 노드의 출력을 연결하세요</li>
                    <li>템플릿에서 {'{Variable1}'}, {'{Variable2}'} 형식으로 변수를 사용하세요</li>
                    <li>고급 모드에서는 {'{변수명|default:기본값}'} 형식을 사용할 수 있습니다</li>
                  </ul>
                }
                type="info"
                showIcon
              />
            </div>
          </>
        )}

        {/* OLLAMA Node Configuration */}
        {nodeType === 'ollama' && (
          <>
            <Form.Item name="host" label="Ollama 호스트">
              <Input 
                placeholder={`기본값: ${import.meta.env.VITE_OLLAMA_HOST || 'localhost'}`}
                defaultValue={import.meta.env.VITE_OLLAMA_HOST}
              />
            </Form.Item>

            <Form.Item name="port" label="Ollama 포트">
              <Input 
                type="number"
                placeholder={`기본값: ${import.meta.env.VITE_OLLAMA_PORT || '11434'}`}
                defaultValue={import.meta.env.VITE_OLLAMA_PORT}
              />
            </Form.Item>

            <Form.Item label="모델">
              <Space.Compact style={{ width: '100%' }}>
                <Form.Item name="model" noStyle>
                  <Input 
                    placeholder="모델 이름 입력 또는 조회하기 버튼 사용" 
                    suffix={
                      modelValidationStatus.isValidating ? (
                        <ReloadOutlined spin style={{ color: '#1890ff' }} />
                      ) : modelValidationStatus.isValid === true ? (
                        <span style={{ color: '#52c41a' }}>✓</span>
                      ) : modelValidationStatus.isValid === false ? (
                        <Tooltip title={modelValidationStatus.error}>
                          <span style={{ color: '#ff4d4f' }}>✗</span>
                        </Tooltip>
                      ) : null
                    }
                  />
                </Form.Item>
                <Button 
                  type="primary" 
                  icon={<SearchOutlined />}
                  loading={loadingModels}
                  onClick={queryOllamaModels}
                >
                  조회하기
                </Button>
              </Space.Compact>
              
              {/* Model validation feedback */}
              {modelValidationStatus.isValid === false && (
                <Alert
                  message="모델 검증 실패"
                  description={modelValidationStatus.error}
                  type="warning"
                  size="small"
                  style={{ marginTop: 8 }}
                  action={
                    <Button size="small" onClick={queryOllamaModels}>
                      다시 조회
                    </Button>
                  }
                />
              )}
              
              {modelValidationStatus.isValid === true && (
                <Text type="success" style={{ fontSize: 12, marginTop: 4, display: 'block' }}>
                  모델이 서버에서 확인되었습니다.
                </Text>
              )}
            </Form.Item>

            <Form.Item name="temperature" label="Temperature">
              <Input type="number" min={0} max={2} step={0.1} placeholder="0.7" />
            </Form.Item>

            <Form.Item name="max_tokens" label="Max Tokens">
              <Input type="number" min={1} max={4096} placeholder="1024" />
            </Form.Item>

            <Form.Item name="system_prompt" label="시스템 프롬프트">
              <TextArea rows={3} placeholder="You are a helpful assistant..." />
            </Form.Item>
          </>
        )}

        {/* OpenAI Node Configuration */}
        {nodeType === 'openai' && (
          <>
            <Form.Item name="model" label="모델">
              <Select>
                <Option value="gpt-4">GPT-4</Option>
                <Option value="gpt-4-turbo">GPT-4 Turbo</Option>
                <Option value="gpt-3.5-turbo">GPT-3.5 Turbo</Option>
              </Select>
            </Form.Item>

            <Form.Item name="temperature" label="Temperature">
              <Input type="number" min={0} max={2} step={0.1} />
            </Form.Item>

            <Form.Item name="max_tokens" label="Max Tokens">
              <Input type="number" min={1} max={4096} />
            </Form.Item>
          </>
        )}

        {/* Azure OpenAI Node Configuration */}
        {nodeType === 'azure-openai' && (
          <>
            <Form.Item name="endpoint" label="Azure OpenAI Endpoint">
              <SecureInput
                placeholder="https://your-resource.openai.azure.com"
                envValue={import.meta.env.VITE_AZURE_OPENAI_ENDPOINT}
                envKey="AZURE_OPENAI_ENDPOINT"
                type="url"
                supportDbEnv={true}
                onChange={(value) => {
                  const allValues = form.getFieldsValue();
                  allValues.endpoint = value;
                  handleFormChange({ endpoint: value }, allValues);
                }}
              />
            </Form.Item>

            <Form.Item name="api_key" label="API Key">
              <SecureInput
                placeholder="API Key 입력"
                envValue={import.meta.env.VITE_AZURE_OPENAI_API_KEY}
                envKey="AZURE_OPENAI_API_KEY"
                type="password"
                supportDbEnv={true}
                onChange={(value) => {
                  const allValues = form.getFieldsValue();
                  allValues.api_key = value;
                  handleFormChange({ api_key: value }, allValues);
                }}
              />
            </Form.Item>

            <Form.Item name="model" label="모델">
              <Select placeholder={`기본값: ${import.meta.env.VITE_AZURE_OPENAI_MODEL || 'gpt-4'}`}>
                <Option value="gpt-4">GPT-4</Option>
                <Option value="gpt-4-turbo">GPT-4 Turbo</Option>
                <Option value="gpt-35-turbo">GPT-3.5 Turbo</Option>
                <Option value="gpt-4o">GPT-4o</Option>
              </Select>
            </Form.Item>

            <Form.Item name="api_version" label="API Version">
              <Select placeholder={`기본값: ${import.meta.env.VITE_AZURE_OPENAI_VERSION || '2024-02-15-preview'}`}>
                <Option value="2024-02-15-preview">2024-02-15-preview</Option>
                <Option value="2023-12-01-preview">2023-12-01-preview</Option>
                <Option value="2023-05-15">2023-05-15</Option>
              </Select>
            </Form.Item>

            <Form.Item name="temperature" label="Temperature">
              <Input type="number" min={0} max={2} step={0.1} />
            </Form.Item>

            <Form.Item name="max_tokens" label="Max Tokens">
              <Input type="number" min={1} max={4096} />
            </Form.Item>
          </>
        )}

        {/* Transform Node Configuration */}
        {nodeType === 'transform' && (
          <>
            <Form.Item name="operation" label="변환 작업">
              <Select>
                <Option value="uppercase">대문자 변환</Option>
                <Option value="lowercase">소문자 변환</Option>
                <Option value="trim">공백 제거</Option>
                <Option value="json_parse">JSON 파싱</Option>
                <Option value="json_stringify">JSON 문자열화</Option>
              </Select>
            </Form.Item>
          </>
        )}

        {/* API Node Configuration */}
        {nodeType === 'api' && (
          <>
            <Alert
              message="API 호출 노드"
              description="HTTP API를 호출하여 외부 서비스와 통신합니다. 인증, 재시도, 고급 옵션을 지원합니다."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form.Item name="url" label="API URL" rules={[{ required: true, message: 'API URL을 입력하세요' }]}>
              <Input placeholder="https://api.example.com/endpoint" />
            </Form.Item>

            <Form.Item name="method" label="HTTP 메서드">
              <Select defaultValue="GET">
                <Option value="GET">GET</Option>
                <Option value="POST">POST</Option>
                <Option value="PUT">PUT</Option>
                <Option value="PATCH">PATCH</Option>
                <Option value="DELETE">DELETE</Option>
                <Option value="HEAD">HEAD</Option>
                <Option value="OPTIONS">OPTIONS</Option>
              </Select>
            </Form.Item>

            <Divider orientation="left">인증 설정</Divider>

            <Form.Item name="auth_type" label="인증 방식">
              <Select defaultValue="none" onChange={(value) => {
                const allValues = form.getFieldsValue();
                allValues.auth_type = value;
                handleFormChange({ auth_type: value }, allValues);
              }}>
                <Option value="none">인증 없음</Option>
                <Option value="bearer">Bearer Token</Option>
                <Option value="basic">Basic Authentication</Option>
                <Option value="api_key">API Key</Option>
              </Select>
            </Form.Item>

            {(() => {
              const authType = form.getFieldValue('auth_type');

              if (authType === 'bearer') {
                return (
                  <Form.Item 
                    name={['auth_config', 'token']} 
                    label="Bearer Token"
                    rules={[{ required: true, message: 'Bearer Token을 입력하세요' }]}
                  >
                    <SecureInput
                      placeholder="Bearer Token을 입력하세요"
                      type="password"
                      supportDbEnv={true}
                    />
                  </Form.Item>
                );
              }

              if (authType === 'basic') {
                return (
                  <>
                    <Form.Item 
                      name={['auth_config', 'username']} 
                      label="사용자명"
                      rules={[{ required: true, message: '사용자명을 입력하세요' }]}
                    >
                      <Input placeholder="사용자명" />
                    </Form.Item>
                    <Form.Item 
                      name={['auth_config', 'password']} 
                      label="비밀번호"
                      rules={[{ required: true, message: '비밀번호를 입력하세요' }]}
                    >
                      <SecureInput
                        placeholder="비밀번호를 입력하세요"
                        type="password"
                        supportDbEnv={true}
                      />
                    </Form.Item>
                  </>
                );
              }

              if (authType === 'api_key') {
                return (
                  <>
                    <Form.Item 
                      name={['auth_config', 'header_name']} 
                      label="API Key 헤더명"
                    >
                      <Input placeholder="X-API-Key" defaultValue="X-API-Key" />
                    </Form.Item>
                    <Form.Item 
                      name={['auth_config', 'key']} 
                      label="API Key"
                      rules={[{ required: true, message: 'API Key를 입력하세요' }]}
                    >
                      <SecureInput
                        placeholder="API Key를 입력하세요"
                        type="password"
                        supportDbEnv={true}
                      />
                    </Form.Item>
                  </>
                );
              }

              return null;
            })()}

            <Divider orientation="left">요청 설정</Divider>

            <Form.Item name="headers" label="커스텀 헤더 (JSON)">
              <TextArea 
                rows={3} 
                placeholder='{"Content-Type": "application/json", "User-Agent": "MyApp/1.0"}'
                style={{ fontFamily: 'monospace' }}
              />
            </Form.Item>

            <Form.Item name="timeout" label="타임아웃 (초)">
              <InputNumber min={1} max={300} defaultValue={30} style={{ width: '100%' }} />
            </Form.Item>

            <Divider orientation="left">재시도 설정</Divider>

            <Form.Item name="retry_count" label="재시도 횟수">
              <InputNumber min={0} max={10} defaultValue={0} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item name="retry_delay" label="재시도 지연시간 (초)">
              <InputNumber min={0.1} max={60} step={0.1} defaultValue={1} style={{ width: '100%' }} />
            </Form.Item>

            <Alert
              message="재시도 정책"
              description="5xx 서버 오류에 대해서만 재시도합니다. 지연시간은 지수적으로 증가합니다 (exponential backoff)."
              type="info"
              size="small"
              style={{ marginBottom: 16 }}
            />

            <Divider orientation="left">도움말</Divider>

            <Alert
              message="환경변수 사용법"
              description={
                <div>
                  <div>• URL에서: <code>https://api.{`{ENVIRONMENT}`}.example.com</code></div>
                  <div>• 헤더에서: <code>{`{"Authorization": "Bearer {API_TOKEN}"}`}</code></div>
                  <div>• 인증에서: SecureInput 필드에서 환경변수 버튼 사용</div>
                </div>
              }
              type="info"
              size="small"
            />

            {(() => {
              const method = form.getFieldValue('method');
              if (['POST', 'PUT', 'PATCH'].includes(method)) {
                return (
                  <Alert
                    message="요청 본문"
                    description="POST, PUT, PATCH 요청의 본문 데이터는 Flow의 'body' 입력을 통해 전달됩니다. JSON 형식으로 입력하세요."
                    type="success"
                    size="small"
                    style={{ marginTop: 8 }}
                  />
                );
              }
              return null;
            })()}
          </>
        )}

        {/* Input Node Configuration */}
        {nodeType === 'input' && (
          <>
            <Form.Item name="name" label="입력 이름">
              <Input placeholder="user_input" />
            </Form.Item>

            <Form.Item name="dataType" label="데이터 타입">
              <Select>
                <Option value="string">문자열</Option>
                <Option value="number">숫자</Option>
                <Option value="boolean">불린</Option>
                <Option value="object">객체</Option>
                <Option value="array">배열</Option>
              </Select>
            </Form.Item>

            <Form.Item name="default_value" label="기본값">
              <Input placeholder="기본값 입력" />
            </Form.Item>
          </>
        )}

        {/* Output Node Configuration */}
        {nodeType === 'output' && (
          <>
            <Form.Item name="name" label="출력 이름">
              <Input placeholder="result" />
            </Form.Item>

            <Form.Item name="description" label="설명">
              <TextArea rows={2} placeholder="출력 설명" />
            </Form.Item>
          </>
        )}

        {/* Function Node Configuration */}
        {nodeType === 'function' && (
          <>
            <Alert
              message="Python 함수 노드"
              description="Python 코드를 실행하여 데이터를 처리합니다. 보안을 위해 샌드박스 환경에서 실행됩니다."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form.Item
              name="code"
              label={
                <Space>
                  <span>Python 코드</span>
                  <Tooltip title="입력 변수들을 사용하여 Python 코드를 작성하세요. 결과는 변수로 저장됩니다.">
                    <InfoCircleOutlined />
                  </Tooltip>
                </Space>
              }
              rules={[{ required: true, message: 'Python 코드를 입력하세요' }]}
            >
              <div style={{ border: '1px solid #d9d9d9', borderRadius: 6 }}>
                <Editor
                  height="300px"
                  defaultLanguage="python"
                  defaultValue="# Python 코드를 입력하세요
# 입력 변수: input1, input2, ...
# 결과를 변수에 저장하면 출력으로 사용됩니다

result = input1 + input2
message = f'결과: {result}'"
                  options={{
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    fontSize: 13,
                    lineNumbers: 'on',
                    roundedSelection: false,
                    scrollbar: { vertical: 'visible', horizontal: 'visible' },
                    automaticLayout: true
                  }}
                  onChange={(value) => {
                    const allValues = form.getFieldsValue();
                    allValues.code = value;
                    handleFormChange({ code: value }, allValues);
                  }}
                />
              </div>
            </Form.Item>

            <Form.Item
              name="timeout"
              label={
                <Space>
                  <span>실행 타임아웃 (초)</span>
                  <Tooltip title="코드 실행 최대 시간을 설정합니다">
                    <InfoCircleOutlined />
                  </Tooltip>
                </Space>
              }
            >
              <InputNumber min={1} max={300} defaultValue={30} style={{ width: '100%' }} />
            </Form.Item>

            <Divider orientation="left">입력 매핑</Divider>
            <Alert
              message="입력 변수 매핑"
              description="Flow의 입력을 Python 코드의 변수명으로 매핑합니다. 예: 'user_input' → 'input1'"
              type="info"
              size="small"
              style={{ marginBottom: 12 }}
            />

            <Form.List name="input_mapping">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                      <Form.Item
                        {...restField}
                        name={[name, 'flow_input']}
                        rules={[{ required: true, message: 'Flow 입력명을 입력하세요' }]}
                        style={{ marginBottom: 0, flex: 1 }}
                      >
                        <Input placeholder="Flow 입력명 (예: user_input)" />
                      </Form.Item>
                      <span>→</span>
                      <Form.Item
                        {...restField}
                        name={[name, 'python_var']}
                        rules={[{ required: true, message: 'Python 변수명을 입력하세요' }]}
                        style={{ marginBottom: 0, flex: 1 }}
                      >
                        <Input placeholder="Python 변수명 (예: input1)" />
                      </Form.Item>
                      <Button type="text" icon={<DeleteOutlined />} onClick={() => remove(name)} />
                    </Space>
                  ))}
                  <Form.Item style={{ marginBottom: 0 }}>
                    <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                      입력 매핑 추가
                    </Button>
                  </Form.Item>
                </>
              )}
            </Form.List>

            <Divider orientation="left">출력 매핑</Divider>
            <Alert
              message="출력 변수 매핑"
              description="Python 코드의 변수를 Flow 출력으로 매핑합니다. 예: 'result' → 'processed_data'"
              type="info"
              size="small"
              style={{ marginBottom: 12 }}
            />

            <Form.List name="output_mapping">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                      <Form.Item
                        {...restField}
                        name={[name, 'python_var']}
                        rules={[{ required: true, message: 'Python 변수명을 입력하세요' }]}
                        style={{ marginBottom: 0, flex: 1 }}
                      >
                        <Input placeholder="Python 변수명 (예: result)" />
                      </Form.Item>
                      <span>→</span>
                      <Form.Item
                        {...restField}
                        name={[name, 'flow_output']}
                        rules={[{ required: true, message: 'Flow 출력명을 입력하세요' }]}
                        style={{ marginBottom: 0, flex: 1 }}
                      >
                        <Input placeholder="Flow 출력명 (예: processed_data)" />
                      </Form.Item>
                      <Button type="text" icon={<DeleteOutlined />} onClick={() => remove(name)} />
                    </Space>
                  ))}
                  <Form.Item style={{ marginBottom: 0 }}>
                    <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                      출력 매핑 추가
                    </Button>
                  </Form.Item>
                </>
              )}
            </Form.List>

            <Divider orientation="left">허용된 Python 모듈</Divider>
            <div style={{ marginBottom: 16 }}>
              <Space wrap>
                {['json', 'math', 'datetime', 'time', 're', 'random', 'uuid', 'hashlib', 'base64', 'urllib.parse', 'collections', 'itertools', 'functools', 'operator'].map(module => (
                  <Tag key={module} color="green">{module}</Tag>
                ))}
              </Space>
            </div>

            <Alert
              message="보안 제한사항"
              description={
                <ul style={{ marginBottom: 0, paddingLeft: 16 }}>
                  <li>파일 시스템 접근 불가</li>
                  <li>네트워크 요청 불가</li>
                  <li>시스템 명령 실행 불가</li>
                  <li>위험한 내장 함수 사용 불가</li>
                </ul>
              }
              type="warning"
              size="small"
            />
          </>
        )}

        {/* Condition Node Configuration */}
        {nodeType === 'condition' && (
          <>
            <Alert
              message="조건문 노드"
              description="입력 값을 평가하여 True/False 출력으로 분기합니다. 다양한 조건 타입을 지원합니다."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            <Form.Item
              name="condition_type"
              label="조건 타입"
              rules={[{ required: true, message: '조건 타입을 선택하세요' }]}
            >
              <Select placeholder="조건 타입을 선택하세요" onChange={(value) => {
                const allValues = form.getFieldsValue();
                allValues.condition_type = value;
                handleFormChange({ condition_type: value }, allValues);
              }}>
                <Select.OptGroup label="기본 비교">
                  <Option value="equals">같음 (==)</Option>
                  <Option value="not_equals">다름 (!=)</Option>
                  <Option value="greater_than">초과 (&gt;)</Option>
                  <Option value="less_than">미만 (&lt;)</Option>
                  <Option value="greater_equal">이상 (&gt;=)</Option>
                  <Option value="less_equal">이하 (&lt;=)</Option>
                  <Option value="between">범위 내 (사이)</Option>
                </Select.OptGroup>
                <Select.OptGroup label="문자열 검사">
                  <Option value="contains">포함</Option>
                  <Option value="not_contains">포함하지 않음</Option>
                  <Option value="starts_with">시작</Option>
                  <Option value="ends_with">끝남</Option>
                </Select.OptGroup>
                <Select.OptGroup label="정규식">
                  <Option value="regex_match">정규식 전체 매칭</Option>
                  <Option value="regex_search">정규식 부분 검색</Option>
                </Select.OptGroup>
                <Select.OptGroup label="값 검사">
                  <Option value="is_empty">비어있음</Option>
                  <Option value="is_not_empty">비어있지 않음</Option>
                  <Option value="is_null">Null</Option>
                  <Option value="is_not_null">Null 아님</Option>
                </Select.OptGroup>
                <Select.OptGroup label="배열/객체">
                  <Option value="array_contains">배열 포함</Option>
                  <Option value="array_length">배열 길이</Option>
                  <Option value="json_path">JSONPath 쿼리</Option>
                </Select.OptGroup>
                <Select.OptGroup label="고급">
                  <Option value="custom">사용자 정의 표현식</Option>
                </Select.OptGroup>
              </Select>
            </Form.Item>

            {/* Conditional fields based on condition type */}
            {(() => {
              const conditionType = form.getFieldValue('condition_type');

              // Value input for most condition types
              if (['equals', 'not_equals', 'contains', 'not_contains', 'starts_with', 'ends_with', 
                   'greater_than', 'less_than', 'greater_equal', 'less_equal', 'regex_match', 
                   'regex_search', 'array_contains', 'array_length'].includes(conditionType)) {
                return (
                  <Form.Item
                    name="condition_value"
                    label={
                      conditionType?.includes('regex') ? '정규식 패턴' :
                      conditionType === 'array_length' ? '배열 길이' :
                      '비교 값'
                    }
                    rules={[{ required: true, message: '값을 입력하세요' }]}
                  >
                    {conditionType?.includes('regex') ? (
                      <TextArea 
                        rows={2} 
                        placeholder="^[a-zA-Z0-9]+$"
                        style={{ fontFamily: 'monospace' }}
                      />
                    ) : conditionType === 'array_length' ? (
                      <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                    ) : (
                      <Input placeholder="비교할 값을 입력하세요" />
                    )}
                  </Form.Item>
                );
              }

              // Between condition needs two values
              if (conditionType === 'between') {
                return (
                  <>
                    <Form.Item
                      name={['condition_value', 0]}
                      label="최솟값"
                      rules={[{ required: true, message: '최솟값을 입력하세요' }]}
                    >
                      <InputNumber style={{ width: '100%' }} placeholder="0" />
                    </Form.Item>
                    <Form.Item
                      name={['condition_value', 1]}
                      label="최댓값"
                      rules={[{ required: true, message: '최댓값을 입력하세요' }]}
                    >
                      <InputNumber style={{ width: '100%' }} placeholder="100" />
                    </Form.Item>
                  </>
                );
              }

              // JSONPath condition
              if (conditionType === 'json_path') {
                return (
                  <>
                    <Form.Item
                      name="jsonpath_query"
                      label="JSONPath 쿼리"
                      rules={[{ required: true, message: 'JSONPath 쿼리를 입력하세요' }]}
                    >
                      <Input 
                        placeholder="$.data.items[0].name"
                        style={{ fontFamily: 'monospace' }}
                      />
                    </Form.Item>
                    <Form.Item
                      name="condition_value"
                      label="비교 값"
                      rules={[{ required: true, message: '비교할 값을 입력하세요' }]}
                    >
                      <Input placeholder="예상되는 값" />
                    </Form.Item>
                  </>
                );
              }

              // Custom expression
              if (conditionType === 'custom') {
                return (
                  <Form.Item
                    name="custom_expression"
                    label="사용자 정의 표현식"
                    rules={[{ required: true, message: 'Python 표현식을 입력하세요' }]}
                  >
                    <TextArea 
                      rows={3} 
                      placeholder="len(input) > 5 and 'hello' in input.lower()"
                      style={{ fontFamily: 'monospace' }}
                    />
                  </Form.Item>
                );
              }

              return null;
            })()}

            {/* Case sensitivity option for string operations */}
            {(() => {
              const conditionType = form.getFieldValue('condition_type');
              if (['equals', 'not_equals', 'contains', 'not_contains', 'starts_with', 'ends_with', 'json_path'].includes(conditionType)) {
                return (
                  <Form.Item
                    name="case_sensitive"
                    label="대소문자 구분"
                    valuePropName="checked"
                  >
                    <Switch defaultChecked />
                  </Form.Item>
                );
              }
              return null;
            })()}

            {/* Regex flags for regex operations */}
            {(() => {
              const conditionType = form.getFieldValue('condition_type');
              if (conditionType?.includes('regex')) {
                return (
                  <Form.Item
                    name="regex_flags"
                    label="정규식 플래그"
                  >
                    <Select mode="multiple" placeholder="정규식 플래그를 선택하세요">
                      <Option value="i">대소문자 무시 (i)</Option>
                      <Option value="m">멀티라인 (m)</Option>
                      <Option value="s">도트올 (s)</Option>
                      <Option value="x">확장 문법 (x)</Option>
                    </Select>
                  </Form.Item>
                );
              }
              return null;
            })()}

            <Divider orientation="left">도움말</Divider>
            
            {(() => {
              const conditionType = form.getFieldValue('condition_type');
              
              const helpContent = {
                'equals': '입력 값이 지정한 값과 정확히 일치하는지 확인합니다.',
                'not_equals': '입력 값이 지정한 값과 다른지 확인합니다.',
                'contains': '입력 문자열이 지정한 문자열을 포함하는지 확인합니다.',
                'starts_with': '입력 문자열이 지정한 문자열로 시작하는지 확인합니다.',
                'ends_with': '입력 문자열이 지정한 문자열로 끝나는지 확인합니다.',
                'regex_match': '입력 문자열이 정규식 패턴과 완전히 일치하는지 확인합니다.',
                'regex_search': '입력 문자열에서 정규식 패턴을 찾을 수 있는지 확인합니다.',
                'greater_than': '입력 숫자가 지정한 값보다 큰지 확인합니다.',
                'less_than': '입력 숫자가 지정한 값보다 작은지 확인합니다.',
                'between': '입력 숫자가 지정한 범위 내에 있는지 확인합니다.',
                'is_empty': '입력 값이 비어있는지 확인합니다 (빈 문자열, 빈 배열, null 등).',
                'is_null': '입력 값이 null 또는 undefined인지 확인합니다.',
                'array_contains': '입력 배열이 지정한 값을 포함하는지 확인합니다.',
                'array_length': '입력 배열의 길이가 지정한 값과 같은지 확인합니다.',
                'json_path': 'JSONPath 쿼리를 사용하여 JSON 데이터에서 값을 추출하고 비교합니다.',
                'custom': 'Python 표현식을 사용하여 사용자 정의 조건을 평가합니다. input 변수로 입력 값에 접근할 수 있습니다.'
              };

              if (conditionType && helpContent[conditionType]) {
                return (
                  <Alert
                    message={`${conditionType} 조건`}
                    description={helpContent[conditionType]}
                    type="info"
                    size="small"
                  />
                );
              }

              return (
                <Alert
                  message="조건 타입을 선택하세요"
                  description="위에서 조건 타입을 선택하면 해당 조건에 대한 자세한 설명이 표시됩니다."
                  type="info"
                  size="small"
                />
              );
            })()}

            {form.getFieldValue('condition_type') === 'custom' && (
              <Alert
                message="사용자 정의 표현식 예시"
                description={
                  <div style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                    <div>• len(input) &gt; 10</div>
                    <div>• 'error' in input.lower()</div>
                    <div>• input.startswith('http')</div>
                    <div>• json.loads(input)['status'] == 'ok'</div>
                  </div>
                }
                type="success"
                size="small"
                style={{ marginTop: 8 }}
              />
            )}

            {form.getFieldValue('condition_type')?.includes('regex') && (
              <Alert
                message="정규식 패턴 예시"
                description={
                  <div style={{ fontFamily: 'monospace', fontSize: '12px' }}>
                    <div>• ^[A-Za-z0-9]+$ (영숫자만)</div>
                    <div>• ^\d{`{3}`}-\d{`{4}`}-\d{`{4}`}$ (전화번호)</div>
                    <div>• ^[\w\.-]+@[\w\.-]+\.\w+$ (이메일)</div>
                    <div>• ^https?:// (URL 시작)</div>
                  </div>
                }
                type="success"
                size="small"
                style={{ marginTop: 8 }}
              />
            )}
          </>
        )}
          </Form>
        </div>
      </div>

      {/* Ollama Models Selection Modal */}
      <Modal
        title="Ollama 모델 선택"
        open={modelsModalVisible}
        onCancel={() => setModelsModalVisible(false)}
        footer={null}
        width={600}
      >
        <div style={{ marginBottom: 16 }}>
          <Alert
            message={`총 ${ollamaModels.length}개의 모델을 찾았습니다`}
            type="info"
            showIcon
          />
        </div>
        
        <div style={{ maxHeight: 400, overflowY: 'auto' }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            {ollamaModels.map((model) => (
              <Card
                key={model.name}
                size="small"
                hoverable
                onClick={() => selectOllamaModel(model.name)}
                style={{ cursor: 'pointer' }}
                bodyStyle={{ padding: 12 }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <Text strong>{model.name}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {OllamaService.formatModelName(model)}
                    </Text>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    {model.details?.family && (
                      <Tag color="blue">{model.details.family}</Tag>
                    )}
                    {model.details?.parameter_size && (
                      <Tag color="green">{model.details.parameter_size}</Tag>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </Space>
        </div>
        
        {ollamaModels.length === 0 && (
          <div style={{ textAlign: 'center', padding: 20 }}>
            <Text type="secondary">사용 가능한 모델이 없습니다.</Text>
          </div>
        )}
      </Modal>

      {/* Environment Variable Manager Modal */}
      <EnvironmentVariableManager
        visible={envVarManagerVisible}
        onClose={() => setEnvVarManagerVisible(false)}
        onVariablesChange={setEnvironmentVariables}
      />
    </div>
  );
};