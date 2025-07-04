/**
 * Silent Login Loader Component
 * Shows loading indicator during silent SSO authentication attempt
 */

import React from 'react';
import { Spin, Card, Typography } from 'antd';
import { LoadingOutlined, UserOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

interface SilentLoginLoaderProps {
  isVisible: boolean;
}

export const SilentLoginLoader: React.FC<SilentLoginLoaderProps> = ({ isVisible }) => {
  if (!isVisible) return null;

  return (
    <div 
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
      }}
    >
      <Card
        style={{
          textAlign: 'center',
          border: 'none',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
          borderRadius: '16px',
          padding: '24px',
          minWidth: '320px'
        }}
      >
        {/* Icon and Loading Spinner */}
        <div style={{ marginBottom: '24px', position: 'relative' }}>
          <UserOutlined 
            style={{ 
              fontSize: '48px', 
              color: '#000000',
              display: 'block',
              margin: '0 auto 16px'
            }} 
          />
          <Spin 
            indicator={
              <LoadingOutlined 
                style={{ 
                  fontSize: 24, 
                  color: '#000000' 
                }} 
                spin 
              />
            }
          />
        </div>

        {/* Title */}
        <Title 
          level={4} 
          style={{ 
            marginBottom: '12px',
            color: '#000000',
            fontWeight: 600
          }}
        >
          MAX Platform 로그인 상태 확인 중
        </Title>

        {/* Description */}
        <Text 
          style={{ 
            color: '#666666',
            fontSize: '14px',
            lineHeight: 1.5,
            display: 'block',
            marginBottom: '8px'
          }}
        >
          자동 로그인을 시도하고 있습니다...
        </Text>

        <Text 
          style={{ 
            color: '#999999',
            fontSize: '12px',
            lineHeight: 1.4
          }}
        >
          MAX Platform에 로그인되어 있다면 자동으로 연결됩니다
        </Text>

        {/* Progress indicator */}
        <div style={{ 
          marginTop: '20px',
          height: '2px',
          backgroundColor: '#f0f0f0',
          borderRadius: '1px',
          overflow: 'hidden'
        }}>
          <div style={{
            height: '100%',
            backgroundColor: '#000000',
            borderRadius: '1px',
            animation: 'progress 2s ease-in-out infinite',
            width: '30%'
          }} />
        </div>

        <style>{`
          @keyframes progress {
            0% { 
              transform: translateX(-100%);
              width: 30%;
            }
            50% { 
              transform: translateX(150%);
              width: 30%;
            }
            100% { 
              transform: translateX(300%);
              width: 30%;
            }
          }
        `}</style>
      </Card>
    </div>
  );
};