/**
 * Custom Node Component
 * Represents individual nodes in the flow designer
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import type { NodeProps } from 'reactflow';
import { Card } from 'antd';
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
} from '@ant-design/icons';
import { getNodeHandles } from '../../types/nodeHandles';
import { NodeMenuDropdown } from './NodeMenuDropdown';

interface CustomNodeData {
  type: string;
  label: string;
  description?: string;
  config?: Record<string, any>;
  isHighlighted?: boolean;
  isConnecting?: boolean;
  isDimmed?: boolean;
  onDelete?: (nodeId: string) => void;
  onDuplicate?: (nodeId: string) => void;
  onOpenProperties?: (nodeId: string) => void;
}

// Utility functions for color manipulation
const adjustBrightness = (hex: string, percent: number): string => {
  const num = parseInt(hex.replace('#', ''), 16);
  const amt = Math.round(2.55 * percent);
  const R = (num >> 16) + amt;
  const G = (num >> 8 & 0x00FF) + amt;
  const B = (num & 0x0000FF) + amt;
  return '#' + (0x1000000 + (R < 255 ? R < 1 ? 0 : R : 255) * 0x10000 +
    (G < 255 ? G < 1 ? 0 : G : 255) * 0x100 +
    (B < 255 ? B < 1 ? 0 : B : 255)).toString(16).slice(1);
};

const hexToRgba = (hex: string, alpha: number): string => {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = num >> 16;
  const g = num >> 8 & 0x00FF;
  const b = num & 0x0000FF;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
};

const nodeIcons: Record<string, React.ReactNode> = {
  input: <PlayCircleOutlined />,
  output: <StopOutlined />,
  openai: <MessageOutlined />,
  anthropic: <MessageOutlined />,
  ollama: <RobotOutlined />,
  condition: <BranchesOutlined />,
  function: <FunctionOutlined />,
  database: <DatabaseOutlined />,
  api: <ApiOutlined />,
  transform: <ToolOutlined />,
  template: <FileTextOutlined />,
};

const nodeColors: Record<string, string> = {
  input: '#22c55e',     // Soft green
  output: '#3b82f6',    // Clean blue  
  openai: '#8b5cf6',    // Purple
  anthropic: '#f59e0b', // Amber
  ollama: '#10b981',    // Emerald
  condition: '#ef4444', // Red
  function: '#06b6d4',  // Cyan
  database: '#6366f1',  // Indigo
  api: '#ec4899',       // Pink
  transform: '#f97316', // Orange
  template: '#14b8a6',  // Teal
};

export const CustomNode: React.FC<NodeProps<CustomNodeData>> = memo(({ data, selected, id }) => {
  const { type, label, description, isHighlighted, isConnecting, isDimmed, onDelete, onDuplicate, onOpenProperties } = data;
  const icon = nodeIcons[type] || <FunctionOutlined />;
  const color = nodeColors[type] || '#666666';
  
  // Get handle configuration for this node type
  const handleConfig = getNodeHandles(type);
  const inputHandles = handleConfig.inputs || [];
  const outputHandles = handleConfig.outputs || [];

  // Calculate node height based on handle count
  const maxHandles = Math.max(inputHandles.length, outputHandles.length, 1);
  const nodeHeight = Math.max(60, maxHandles * 36 + 24); // Min 60px, 36px per handle + padding

  return (
    <div 
      className="relative flex flex-col rounded-2xl node-container overflow-hidden"
      style={{
        minWidth: '360px',
        height: `${nodeHeight + 32}px`, // Add 32px for header
        background: '#fefefe',
        border: `2px solid ${selected || isHighlighted ? color : hexToRgba(color, 0.3)}`,
        boxShadow: selected || isHighlighted
          ? `0 10px 30px ${hexToRgba(color, 0.2)}, 0 4px 12px ${hexToRgba(color, 0.1)}`
          : isConnecting 
          ? `0 8px 25px ${hexToRgba(color, 0.25)}`
          : '0 4px 12px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1)',
        filter: isConnecting ? `drop-shadow(0 0 8px ${hexToRgba(color, 0.4)})` : 'none',
      }}
    >
      {/* Header Section - Component Type and Menu */}
      <div 
        className="flex items-center justify-between px-4 py-2"
        style={{
          height: '32px',
          background: `linear-gradient(135deg, ${hexToRgba(color, 0.1)}, ${hexToRgba(color, 0.05)})`,
          borderBottom: `1px solid ${hexToRgba(color, 0.2)}`,
        }}
      >
        {/* Component Type - Center */}
        <div className="flex-1 flex justify-center">
          <span 
            className="font-semibold text-sm"
            style={{ color: color }}
          >
            {type.toUpperCase()}
          </span>
        </div>
        
        {/* Menu Button - Right */}
        <div className="flex-shrink-0">
          <NodeMenuDropdown
            nodeId={id}
            onDelete={onDelete || (() => {})}
            onDuplicate={onDuplicate}
            onOpenProperties={onOpenProperties}
          />
        </div>
      </div>

      {/* Main Content Section - 5 sections layout */}
      <div 
        className="flex-1 flex"
        style={{ height: `${nodeHeight}px` }}
      >
        {/* Section 1: Input Port Area */}
        {inputHandles.length > 0 && (
          <div 
            className="bg-gray-100/60 border-r-0 flex flex-col justify-center relative"
            style={{ minWidth: '20px' }}
          >
            {inputHandles.map((handle, index) => (
              <div 
                key={handle.id} 
                className="relative flex items-center justify-center"
                style={{ height: '36px' }}
              >
                  <Handle
                    id={handle.id}
                    type="target"
                    position={Position.Left}
                    className="hover:scale-110 transition-all duration-200"
                    style={{
                      background: handle.required ? color : '#9ca3af',
                      width: 12,
                      height: 12,
                      border: '2px solid #ffffff',
                      boxShadow: `0 2px 8px rgba(0,0,0,0.1), 0 0 0 1px ${hexToRgba(handle.required ? color : '#9ca3af', 0.2)}`,
                      left: '-6px',
                      position: 'absolute',
                      zIndex: 1000,
                      borderRadius: '50%'
                    }}
                  />
              </div>
            ))}
          </div>
        )}

        {/* Section 2: Input Labels */}
        {inputHandles.length > 0 && (
          <div 
            className="bg-gray-50/40 border-r-0 flex flex-col justify-center"
            style={{ minWidth: '80px' }}
          >
            {inputHandles.map((handle, index) => (
              <div 
                key={`label-${handle.id}`} 
                className="px-3 flex items-center"
                style={{ height: '36px' }}
              >
                <span 
                  className={`text-sm transition-colors duration-150 font-medium ${
                    handle.required 
                      ? 'text-gray-600' 
                      : 'text-gray-500'
                  }`}
                >
                  {handle.label}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Section 3: Center - Node Info */}
        <div className="flex-1 bg-white/95 flex items-center justify-center p-4">
          <div className="text-center">
            <div 
              style={{ color }} 
              className="text-2xl mb-2 transition-transform duration-200 filter drop-shadow-sm"
            >
              {icon}
            </div>
            <div className="font-semibold text-base text-gray-700 tracking-tight">
              {label}
            </div>
            {description && (
              <div className="text-sm text-gray-400 mt-1 max-w-32 truncate font-medium">
                {description}
              </div>
            )}
          </div>
        </div>

        {/* Section 4: Output Labels */}
        {outputHandles.length > 0 && (
          <div 
            className="bg-gray-50/40 border-l-0 flex flex-col justify-center"
            style={{ minWidth: '80px' }}
          >
            {outputHandles.map((handle, index) => (
              <div 
                key={`label-${handle.id}`} 
                className="px-3 flex items-center justify-end"
                style={{ height: '36px' }}
              >
                <span className="text-sm text-gray-600 transition-colors duration-150 font-medium">
                  {handle.label}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Section 5: Output Port Area */}
        {outputHandles.length > 0 && (
          <div 
            className="bg-gray-100/60 border-l-0 flex flex-col justify-center relative"
            style={{ minWidth: '20px' }}
          >
            {outputHandles.map((handle, index) => (
              <div 
                key={handle.id} 
                className="relative flex items-center justify-center"
                style={{ height: '36px' }}
              >
                <Handle
                  id={handle.id}
                  type="source"
                  position={Position.Right}
                  className="hover:scale-110 transition-all duration-200"
                  style={{
                    background: color,
                    width: 12,
                    height: 12,
                    border: '2px solid #ffffff',
                    boxShadow: `0 2px 8px rgba(0,0,0,0.1), 0 0 0 1px ${hexToRgba(color, 0.2)}`,
                    right: '-6px',
                    position: 'absolute',
                    zIndex: 1000,
                    borderRadius: '50%'
                  }}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});