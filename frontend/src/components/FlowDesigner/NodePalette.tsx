/**
 * Node Palette Component
 * Provides draggable node types for the flow designer
 */

import React, { useState, useEffect } from 'react';
import { Typography, Button, Input, Badge } from 'antd';
import {
  PlayCircleOutlined,
  StopOutlined,
  BranchesOutlined,
  FunctionOutlined,
  DatabaseOutlined,
  ApiOutlined,
  MessageOutlined,
  ToolOutlined,
  RobotOutlined,
  FileTextOutlined,
  RightOutlined,
  ExpandOutlined,
  CompressOutlined,
  QuestionCircleOutlined,
  InboxOutlined,
  RobotOutlined as AIOutlined,
  ToolOutlined as LogicOutlined,
  DatabaseOutlined as DataOutlined,
  SearchOutlined,
  DragOutlined,
} from '@ant-design/icons';
import { HelpModal } from './HelpModal';
import './NodePalette.css';

const { Title, Text } = Typography;

interface CategoryInfo {
  key: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  colorClass: string;
}

interface NodeType {
  type: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  category: string;
}

const nodeTypes: NodeType[] = [
  // Flow Input/Output nodes
  {
    type: 'input',
    label: 'Flow Input',
    description: 'Flow input parameter - receives data from outside the flow',
    icon: <PlayCircleOutlined />,
    color: '#52c41a',
    category: 'IO',
  },
  {
    type: 'output',
    label: 'Flow Output',
    description: 'Flow output result - returns data from the flow',
    icon: <StopOutlined />,
    color: '#1890ff',
    category: 'IO',
  },

  // LLM nodes
  {
    type: 'openai',
    label: 'OpenAI',
    description: 'OpenAI GPT models',
    icon: <MessageOutlined />,
    color: '#722ed1',
    category: 'LLM',
  },
  {
    type: 'anthropic',
    label: 'Claude',
    description: 'Anthropic Claude models',
    icon: <MessageOutlined />,
    color: '#eb2f96',
    category: 'LLM',
  },
  {
    type: 'ollama',
    label: 'Ollama',
    description: 'Local Ollama models',
    icon: <RobotOutlined />,
    color: '#10b981',
    category: 'LLM',
  },
  {
    type: 'azure-openai',
    label: 'Azure OpenAI',
    description: 'Azure OpenAI ChatGPT models',
    icon: <MessageOutlined />,
    color: '#0078d4',
    category: 'LLM',
  },

  // Logic nodes
  {
    type: 'condition',
    label: 'Condition',
    description: 'Conditional branching',
    icon: <BranchesOutlined />,
    color: '#fa8c16',
    category: 'Logic',
  },
  {
    type: 'function',
    label: 'Function',
    description: 'Custom function execution',
    icon: <FunctionOutlined />,
    color: '#13c2c2',
    category: 'Logic',
  },

  // Data nodes
  {
    type: 'database',
    label: 'Database',
    description: 'Database operations',
    icon: <DatabaseOutlined />,
    color: '#2f54eb',
    category: 'Data',
  },
  {
    type: 'api',
    label: 'API Call',
    description: 'HTTP API request',
    icon: <ApiOutlined />,
    color: '#f5222d',
    category: 'Data',
  },
  {
    type: 'transform',
    label: 'Transform',
    description: 'Data transformation',
    icon: <ToolOutlined />,
    color: '#fa541c',
    category: 'Data',
  },
  {
    type: 'template',
    label: 'Template',
    description: 'Template formatter',
    icon: <FileTextOutlined />,
    color: '#14b8a6',
    category: 'Data',
  },
];

const categories: CategoryInfo[] = [
  { 
    key: 'IO', 
    name: '입출력', 
    description: '워크플로우 시작점과 종료점',
    icon: <InboxOutlined />, 
    colorClass: 'io' 
  },
  { 
    key: 'LLM', 
    name: 'AI/LLM', 
    description: '인공지능 및 언어모델',
    icon: <AIOutlined />, 
    colorClass: 'ai' 
  },
  { 
    key: 'Logic', 
    name: '로직 & 변환', 
    description: '조건문과 함수 처리',
    icon: <LogicOutlined />, 
    colorClass: 'logic' 
  },
  { 
    key: 'Data', 
    name: '데이터 & 연동', 
    description: '데이터베이스 및 API 연동',
    icon: <DataOutlined />, 
    colorClass: 'data' 
  },
];

export const NodePalette: React.FC = () => {
  const [helpModalVisible, setHelpModalVisible] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Load collapsed state from localStorage
  const loadCollapsedState = (): Set<string> => {
    const saved = localStorage.getItem('nodePaletteCollapsed');
    if (saved) {
      return new Set(JSON.parse(saved));
    }
    // Default: all categories collapsed
    return new Set(categories.map(c => c.key));
  };

  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(loadCollapsedState());

  // Save collapsed state to localStorage
  useEffect(() => {
    localStorage.setItem('nodePaletteCollapsed', JSON.stringify(Array.from(collapsedCategories)));
  }, [collapsedCategories]);

  const toggleCategory = (category: string) => {
    setCollapsedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(category)) {
        newSet.delete(category);
      } else {
        newSet.add(category);
      }
      return newSet;
    });
  };

  const toggleAll = () => {
    if (collapsedCategories.size === categories.length) {
      // All collapsed, expand all
      setCollapsedCategories(new Set());
    } else {
      // Some expanded, collapse all
      setCollapsedCategories(new Set(categories.map(c => c.key)));
    }
  };

  const getNodeCount = (category: string) => {
    return getFilteredNodes(category).length;
  };

  const getFilteredNodes = (category: string) => {
    const categoryNodes = nodeTypes.filter(node => node.category === category);
    if (!searchTerm) return categoryNodes;
    
    return categoryNodes.filter(node => 
      node.label.toLowerCase().includes(searchTerm.toLowerCase()) ||
      node.description.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  const onDragStart = (event: React.DragEvent, nodeType: string, label: string) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.setData('application/reactflow-label', label);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="node-palette">
      {/* Header */}
      <div className="palette-header">
        <div className="header-content">
          <h3 className="palette-title">노드 팔레트</h3>
          <div className="header-actions">
            <Button
              type="text"
              icon={<QuestionCircleOutlined />}
              onClick={() => setHelpModalVisible(true)}
              size="small"
              title="도움말"
            />
            <Button
              type="text"
              icon={collapsedCategories.size === categories.length ? <ExpandOutlined /> : <CompressOutlined />}
              onClick={toggleAll}
              size="small"
              title={collapsedCategories.size === categories.length ? "모두 펼치기" : "모두 접기"}
            />
          </div>
        </div>
      </div>
      
      {/* Search Bar */}
      <div className="search-bar">
        <Input
          placeholder="노드 검색..."
          prefix={<SearchOutlined />}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          allowClear
        />
      </div>
      
      {/* Categories Container */}
      <div className="categories-container">
        {categories.map((category) => {
          const isCollapsed = collapsedCategories.has(category.key);
          const isExpanded = !isCollapsed;
          const nodeCount = getNodeCount(category.key);
          const filteredNodes = getFilteredNodes(category.key);
          
          // Hide category if no nodes match search
          if (searchTerm && filteredNodes.length === 0) {
            return null;
          }
          
          return (
            <div key={category.key} className="category-section">
              {/* Category Header */}
              <div 
                className={`category-header ${category.colorClass} ${isExpanded ? 'expanded' : ''}`}
                onClick={() => toggleCategory(category.key)}
              >
                <div className="category-header-content">
                  <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>
                    <RightOutlined />
                  </span>
                  <div className={`category-icon ${category.colorClass}`}>
                    {category.icon}
                  </div>
                  <div className="category-info">
                    <h4 className="category-name">{category.name}</h4>
                    <p className="category-description">{category.description}</p>
                  </div>
                  <Badge className="category-badge" count={nodeCount} />
                </div>
              </div>
              
              {/* Nodes List */}
              <div className={`nodes-list-container ${isExpanded ? 'expanded' : 'collapsed'}`}>
                <div className="nodes-list">
                  {filteredNodes.map((node) => (
                    <div
                      key={node.type}
                      className="node-card"
                      draggable
                      onDragStart={(e) => onDragStart(e, node.type, node.label)}
                      style={{
                        '--node-color': node.color,
                        '--node-color-rgb': node.color.replace('#', '').match(/.{2}/g)?.map(hex => parseInt(hex, 16)).join(', ') || '0, 0, 0'
                      } as React.CSSProperties}
                    >
                      <div className="node-card-content">
                        <div className="node-icon">
                          {node.icon}
                        </div>
                        <div className="node-info">
                          <h5 className="node-name">{node.label}</h5>
                          <p className="node-description">{node.description}</p>
                        </div>
                        <div className="drag-indicator">
                          <DragOutlined />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      
      {/* Footer */}
      <div className="palette-footer">
        <div className="footer-tip">
          <Text className="ant-typography">
            💡 노드를 캔버스로 드래그하여 워크플로우를 구성하세요
          </Text>
        </div>
      </div>
      
      {/* Help Modal */}
      <HelpModal 
        visible={helpModalVisible}
        onClose={() => setHelpModalVisible(false)}
      />
    </div>
  );
};