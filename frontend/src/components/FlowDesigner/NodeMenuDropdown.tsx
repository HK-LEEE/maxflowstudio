/**
 * Node Menu Dropdown Component
 * Provides context menu for node operations (delete, duplicate, etc.)
 */

import React from 'react';
import { Dropdown, Menu, Button } from 'antd';
import { MoreOutlined, DeleteOutlined, CopyOutlined, SettingOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';

interface NodeMenuDropdownProps {
  nodeId: string;
  onDelete: (nodeId: string) => void;
  onDuplicate?: (nodeId: string) => void;
  onOpenProperties?: (nodeId: string) => void;
}

export const NodeMenuDropdown: React.FC<NodeMenuDropdownProps> = ({
  nodeId,
  onDelete,
  onDuplicate,
  onOpenProperties,
}) => {
  const handleMenuClick: MenuProps['onClick'] = ({ key, domEvent }) => {
    // Prevent event propagation to avoid node selection
    domEvent.stopPropagation();
    
    switch (key) {
      case 'delete':
        onDelete(nodeId);
        break;
      case 'duplicate':
        onDuplicate?.(nodeId);
        break;
      case 'properties':
        onOpenProperties?.(nodeId);
        break;
    }
  };

  const menuItems: MenuProps['items'] = [
    {
      key: 'properties',
      icon: <SettingOutlined />,
      label: '속성 편집',
      disabled: !onOpenProperties,
    },
    {
      key: 'duplicate',
      icon: <CopyOutlined />,
      label: '복제',
      disabled: !onDuplicate,
    },
    {
      type: 'divider',
    },
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: '삭제',
      danger: true,
    },
  ];

  // Function to find the best container for the dropdown
  const getDropdownContainer = (trigger: HTMLElement): HTMLElement => {
    // First, try to find the React Flow renderer or main container
    let current = trigger.parentElement;
    while (current) {
      if (current.classList.contains('react-flow__renderer') || 
          current.classList.contains('react-flow') ||
          current.classList.contains('react-flow__pane') ||
          current.querySelector('.react-flow__viewport')) {
        // Found the main React Flow container, use it
        return current;
      }
      current = current.parentElement;
    }
    
    // If we can't find React Flow container, look for the main flow designer container
    current = trigger.parentElement;
    while (current) {
      if (current.classList.contains('h-full') && current.classList.contains('flex')) {
        return current;
      }
      current = current.parentElement;
    }
    
    // Ultimate fallback to document body
    return document.body;
  };

  return (
    <Dropdown
      menu={{ items: menuItems, onClick: handleMenuClick }}
      trigger={['click']}
      placement="bottomRight"
      getPopupContainer={getDropdownContainer}
      overlayClassName="node-menu-dropdown"
      arrow={false}
      destroyPopupOnHide={true}
      autoAdjustOverflow={{
        adjustX: true,
        adjustY: true,
      }}
      align={{
        offset: [0, 4], // Add small offset for better positioning
      }}
    >
      <Button
        type="text"
        icon={<MoreOutlined />}
        size="small"
        className="node-menu-button"
        onClick={(e) => {
          e.stopPropagation(); // Prevent node selection when clicking menu button
        }}
        style={{
          border: 'none',
          boxShadow: 'none',
          padding: '4px',
          height: '28px',
          width: '28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: '6px',
          background: 'rgba(255, 255, 255, 0.8)',
          backdropFilter: 'blur(4px)',
          transition: 'all 0.2s ease',
        }}
      />
    </Dropdown>
  );
};