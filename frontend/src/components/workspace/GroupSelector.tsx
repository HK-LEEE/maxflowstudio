/**
 * GroupSelector Component
 * Multi-select group picker with search and permission assignment
 */

import React, { useState, useMemo } from 'react';
import {
  Select,
  Avatar,
  Tag,
  Space,
  Typography,
  Spin,
  Alert,
  Button,
  Tooltip,
  Dropdown,
  Badge,
} from 'antd';
import type { MenuProps } from 'antd';
import {
  TeamOutlined,
  DownOutlined,
  DeleteOutlined,
  CrownOutlined,
  EyeOutlined,
  EditOutlined,
  UsergroupAddOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { groupService } from '../../services/group';
import type { Group } from '../../services/group';
import { PermissionType } from '../../types';
import type { PermissionTypeType } from '../../types';

const { Text } = Typography;
const { Option } = Select;

export interface GroupPermission {
  groupId: string;
  group: Group;
  permission: PermissionTypeType;
}

interface GroupSelectorProps {
  value?: GroupPermission[];
  onChange?: (groups: GroupPermission[]) => void;
  placeholder?: string;
  maxGroups?: number;
  disabled?: boolean;
  defaultPermission?: PermissionTypeType;
  showPermissionSelector?: boolean;
  excludeGroupIds?: string[];
  includeSystemGroups?: boolean;
}

const permissionOptions = [
  { value: PermissionType.VIEWER, label: 'Viewer', icon: <EyeOutlined />, color: 'blue' },
  { value: PermissionType.MEMBER, label: 'Member', icon: <EditOutlined />, color: 'green' },
  { value: PermissionType.ADMIN, label: 'Admin', icon: <CrownOutlined />, color: 'red' },
];

export const GroupSelector: React.FC<GroupSelectorProps> = ({
  value = [],
  onChange,
  placeholder = "Search and select groups...",
  maxGroups = 20,
  disabled = false,
  defaultPermission = PermissionType.MEMBER,
  showPermissionSelector = true,
  excludeGroupIds = [],
  includeSystemGroups = true,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [open, setOpen] = useState(false);

  // Fetch groups based on search query
  const { data: searchResults = [], isLoading: isSearching, error: searchError } = useQuery({
    queryKey: ['groups-search', searchQuery, includeSystemGroups],
    queryFn: () => groupService.search(searchQuery, 20),
    enabled: searchQuery.length > 0,
    staleTime: 30000, // Cache for 30 seconds
    retry: 2,
  });

  // Filter out already selected groups and excluded groups
  const availableGroups = useMemo(() => {
    const selectedGroupIds = value.map(gp => gp.groupId);
    const allExcludedIds = [...selectedGroupIds, ...excludeGroupIds];
    
    return searchResults.filter(group => 
      !allExcludedIds.includes(group.id) && 
      group.is_active &&
      (includeSystemGroups || !group.is_system_group)
    );
  }, [searchResults, value, excludeGroupIds, includeSystemGroups]);

  const handleGroupSelect = (groupId: string) => {
    const group = searchResults.find(g => g.id === groupId);
    if (!group) return;

    if (value.length >= maxGroups) {
      return;
    }

    const newGroupPermission: GroupPermission = {
      groupId: group.id,
      group,
      permission: defaultPermission,
    };

    onChange?.([...value, newGroupPermission]);
    setSearchQuery('');
    setOpen(false);
  };

  const handleGroupRemove = (groupId: string) => {
    onChange?.(value.filter(gp => gp.groupId !== groupId));
  };

  const handlePermissionChange = (groupId: string, permission: PermissionTypeType) => {
    onChange?.(
      value.map(gp => 
        gp.groupId === groupId 
          ? { ...gp, permission }
          : gp
      )
    );
  };

  const getPermissionMenuItems = (groupId: string): MenuProps['items'] => {
    return permissionOptions.map(option => ({
      key: option.value,
      label: (
        <Space>
          {option.icon}
          {option.label}
        </Space>
      ),
      onClick: () => handlePermissionChange(groupId, option.value),
    }));
  };

  const getPermissionDisplay = (permission: PermissionTypeType) => {
    const option = permissionOptions.find(opt => opt.value === permission);
    return option ? (
      <Tag color={option.color} icon={option.icon}>
        {option.label}
      </Tag>
    ) : (
      <Tag>{permission}</Tag>
    );
  };

  const getGroupIcon = (group: Group) => {
    return group.is_system_group ? <UsergroupAddOutlined /> : <TeamOutlined />;
  };

  const getGroupTag = (group: Group) => {
    if (group.is_system_group) {
      return <Tag color="purple">System</Tag>;
    }
    return null;
  };

  return (
    <div>
      <Select
        mode="multiple"
        placeholder={placeholder}
        value={[]} // Keep empty to show custom selected items below
        open={open}
        onDropdownVisibleChange={setOpen}
        onSearch={setSearchQuery}
        searchValue={searchQuery}
        onSelect={handleGroupSelect}
        showSearch
        filterOption={false}
        disabled={disabled}
        loading={isSearching}
        style={{ width: '100%' }}
        dropdownRender={(menu) => (
          <div>
            {searchQuery.length === 0 ? (
              <div style={{ padding: '8px 12px', color: '#999' }}>
                Type to search groups...
              </div>
            ) : isSearching ? (
              <div style={{ padding: '8px 12px', textAlign: 'center' }}>
                <Spin size="small" /> Searching...
              </div>
            ) : searchError ? (
              <div style={{ padding: '8px 12px', color: '#ff4d4f' }}>
                Error searching groups. Please try again.
              </div>
            ) : availableGroups.length === 0 ? (
              <div style={{ padding: '8px 12px', color: '#999' }}>
                No groups found for "{searchQuery}"
              </div>
            ) : (
              menu
            )}
          </div>
        )}
      >
        {availableGroups.map(group => (
          <Option key={group.id} value={group.id}>
            <Space>
              <Avatar size="small" icon={getGroupIcon(group)} />
              <div>
                <Space align="start">
                  <div>
                    <div style={{ fontWeight: 500 }}>{group.name}</div>
                    {group.description && (
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {group.description}
                      </Text>
                    )}
                  </div>
                  {getGroupTag(group)}
                </Space>
                <div style={{ fontSize: '11px', color: '#999' }}>
                  {group.member_count} members
                </div>
              </div>
            </Space>
          </Option>
        ))}
      </Select>

      {/* Selected Groups Display */}
      {value.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            {value.map(groupPermission => (
              <div
                key={groupPermission.groupId}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  border: '1px solid #f0f0f0',
                  borderRadius: '6px',
                  backgroundColor: '#fafafa',
                }}
              >
                <Space>
                  <Avatar size="small" icon={getGroupIcon(groupPermission.group)} />
                  <div>
                    <Space align="start">
                      <div>
                        <div style={{ fontWeight: 500 }}>
                          {groupPermission.group.name}
                        </div>
                        {groupPermission.group.description && (
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {groupPermission.group.description}
                          </Text>
                        )}
                      </div>
                      {getGroupTag(groupPermission.group)}
                    </Space>
                    <div style={{ fontSize: '11px', color: '#999' }}>
                      <Badge 
                        count={groupPermission.group.member_count} 
                        showZero 
                        style={{ backgroundColor: '#52c41a' }}
                      />
                      <span style={{ marginLeft: 4 }}>members</span>
                    </div>
                  </div>
                </Space>

                <Space>
                  {showPermissionSelector && (
                    <Dropdown
                      menu={{ items: getPermissionMenuItems(groupPermission.groupId) }}
                      trigger={['click']}
                    >
                      <Button size="small" type="text">
                        {getPermissionDisplay(groupPermission.permission)}
                        <DownOutlined />
                      </Button>
                    </Dropdown>
                  )}
                  <Tooltip title="Remove group">
                    <Button
                      size="small"
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => handleGroupRemove(groupPermission.groupId)}
                      disabled={disabled}
                    />
                  </Tooltip>
                </Space>
              </div>
            ))}
          </Space>
        </div>
      )}

      {/* Info and Limits */}
      <div style={{ marginTop: 8 }}>
        <Space split={<span style={{ color: '#d9d9d9' }}>•</span>}>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {value.length} of {maxGroups} groups selected
          </Text>
          {value.length >= maxGroups && (
            <Text type="warning" style={{ fontSize: '12px' }}>
              Maximum groups reached
            </Text>
          )}
          {value.length > 0 && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              Total: {value.reduce((sum, gp) => sum + gp.group.member_count, 0)} members
            </Text>
          )}
        </Space>
      </div>

      {/* Error/Warning Messages */}
      {value.length === 0 && (
        <Alert
          message="No groups selected"
          description="Add groups to grant their members access to this workspace"
          type="info"
          showIcon
          style={{ marginTop: 8, fontSize: '12px' }}
        />
      )}

      {/* System Groups Info */}
      {!includeSystemGroups && (
        <Alert
          message="System groups are excluded"
          description="Only custom groups are available for selection"
          type="info"
          showIcon
          style={{ marginTop: 8, fontSize: '12px' }}
        />
      )}
    </div>
  );
};