/**
 * UserSelector Component
 * Multi-select user picker with search and permission assignment
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
} from 'antd';
import type { MenuProps } from 'antd';
import {
  UserOutlined,
  DownOutlined,
  DeleteOutlined,
  CrownOutlined,
  EyeOutlined,
  EditOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { userService } from '../../services/user';
import type { User } from '../../services/user';
import { PermissionType } from '../../types';
import type { PermissionTypeType } from '../../types';

const { Text } = Typography;
const { Option } = Select;

export interface UserPermission {
  userId: string;
  user: User;
  permission: PermissionTypeType;
}

interface UserSelectorProps {
  value?: UserPermission[];
  onChange?: (users: UserPermission[]) => void;
  placeholder?: string;
  maxUsers?: number;
  disabled?: boolean;
  defaultPermission?: PermissionTypeType;
  showPermissionSelector?: boolean;
  excludeUserIds?: string[];
}

const permissionOptions = [
  { value: PermissionType.VIEWER, label: 'Viewer', icon: <EyeOutlined />, color: 'blue' },
  { value: PermissionType.MEMBER, label: 'Member', icon: <EditOutlined />, color: 'green' },
  { value: PermissionType.ADMIN, label: 'Admin', icon: <CrownOutlined />, color: 'red' },
];

export const UserSelector: React.FC<UserSelectorProps> = ({
  value = [],
  onChange,
  placeholder = "Search and select users...",
  maxUsers = 50,
  disabled = false,
  defaultPermission = PermissionType.MEMBER,
  showPermissionSelector = true,
  excludeUserIds = [],
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [open, setOpen] = useState(false);

  // Fetch users based on search query
  const { data: searchResults = [], isLoading: isSearching, error: searchError } = useQuery({
    queryKey: ['users-search', searchQuery],
    queryFn: () => userService.search(searchQuery, 20),
    enabled: searchQuery.length > 0,
    staleTime: 30000, // Cache for 30 seconds
    retry: 2,
  });

  // Filter out already selected users and excluded users
  const availableUsers = useMemo(() => {
    console.log('🔍 UserSelector - searchResults:', searchResults);
    console.log('🔍 UserSelector - value:', value);
    console.log('🔍 UserSelector - excludeUserIds:', excludeUserIds);
    
    const selectedUserIds = value.map(up => up.userId);
    const allExcludedIds = [...selectedUserIds, ...excludeUserIds];
    
    const filtered = searchResults.filter(user => 
      !allExcludedIds.includes(user.id) && user.is_active
    );
    
    console.log('✅ UserSelector - availableUsers:', filtered);
    return filtered;
  }, [searchResults, value, excludeUserIds]);

  const handleUserSelect = (userId: string) => {
    console.log('👆 UserSelector - handleUserSelect called with userId:', userId);
    console.log('🔍 UserSelector - searchResults for selection:', searchResults);
    
    const user = searchResults.find(u => u.id === userId);
    console.log('👤 UserSelector - found user:', user);
    
    if (!user) {
      console.error('❌ UserSelector - User not found for id:', userId);
      return;
    }

    if (value.length >= maxUsers) {
      console.warn('⚠️ UserSelector - Max users reached');
      return;
    }

    const newUserPermission: UserPermission = {
      userId: user.id,
      user,
      permission: defaultPermission,
    };

    console.log('➕ UserSelector - Adding user permission:', newUserPermission);
    onChange?.([...value, newUserPermission]);
    setSearchQuery('');
    setOpen(false);
  };

  const handleUserRemove = (userId: string) => {
    onChange?.(value.filter(up => up.userId !== userId));
  };

  const handlePermissionChange = (userId: string, permission: PermissionTypeType) => {
    onChange?.(
      value.map(up => 
        up.userId === userId 
          ? { ...up, permission }
          : up
      )
    );
  };

  const getPermissionMenuItems = (userId: string): MenuProps['items'] => {
    return permissionOptions.map(option => ({
      key: option.value,
      label: (
        <Space>
          {option.icon}
          {option.label}
        </Space>
      ),
      onClick: () => handlePermissionChange(userId, option.value),
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
        onSelect={handleUserSelect}
        showSearch
        filterOption={false}
        disabled={disabled}
        loading={isSearching}
        style={{ width: '100%' }}
        dropdownRender={(menu) => (
          <div>
            {searchQuery.length === 0 ? (
              <div style={{ padding: '8px 12px', color: '#999' }}>
                Type to search users...
              </div>
            ) : isSearching ? (
              <div style={{ padding: '8px 12px', textAlign: 'center' }}>
                <Spin size="small" /> Searching...
              </div>
            ) : searchError ? (
              <div style={{ padding: '8px 12px', color: '#ff4d4f' }}>
                Error searching users. Please try again.
              </div>
            ) : availableUsers.length === 0 ? (
              <div style={{ padding: '8px 12px', color: '#999' }}>
                No users found for "{searchQuery}"
              </div>
            ) : (
              menu
            )}
          </div>
        )}
      >
        {availableUsers.map(user => (
          <Option key={user.id} value={user.id}>
            <Space>
              <Avatar size="small" icon={<UserOutlined />} />
              <div>
                <div style={{ fontWeight: 500 }}>{user.full_name || user.username}</div>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {user.email}
                </Text>
              </div>
            </Space>
          </Option>
        ))}
      </Select>

      {/* Selected Users Display */}
      {value.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            {value.map(userPermission => (
              <div
                key={userPermission.userId}
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
                  <Avatar size="small" icon={<UserOutlined />} />
                  <div>
                    <div style={{ fontWeight: 500 }}>
                      {userPermission.user.full_name || userPermission.user.username}
                    </div>
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {userPermission.user.email}
                    </Text>
                  </div>
                </Space>

                <Space>
                  {showPermissionSelector && (
                    <Dropdown
                      menu={{ items: getPermissionMenuItems(userPermission.userId) }}
                      trigger={['click']}
                    >
                      <Button size="small" type="text">
                        {getPermissionDisplay(userPermission.permission)}
                        <DownOutlined />
                      </Button>
                    </Dropdown>
                  )}
                  <Tooltip title="Remove user">
                    <Button
                      size="small"
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => handleUserRemove(userPermission.userId)}
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
            {value.length} of {maxUsers} users selected
          </Text>
          {value.length >= maxUsers && (
            <Text type="warning" style={{ fontSize: '12px' }}>
              Maximum users reached
            </Text>
          )}
        </Space>
      </div>

      {/* Error/Warning Messages */}
      {value.length === 0 && (
        <Alert
          message="No users selected"
          description="Add users to grant them access to this workspace"
          type="info"
          showIcon
          style={{ marginTop: 8, fontSize: '12px' }}
        />
      )}
    </div>
  );
};