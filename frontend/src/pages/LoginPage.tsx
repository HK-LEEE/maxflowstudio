/**
 * Login Page Component - MAX Platform OAuth-Only Login
 */

import React from 'react';
import { Button, Card, Typography, App } from 'antd';
import { PartitionOutlined, LoginOutlined } from '@ant-design/icons';
import { authService } from '../services/auth';

const { Title, Text } = Typography;

export const LoginPage: React.FC = () => {
  const [oauthLoading, setOauthLoading] = React.useState(false);
  const { message } = App.useApp();

  const handlePopupOAuthLogin = async () => {
    setOauthLoading(true);
    
    try {
      const user = await authService.loginWithPopupOAuth();
      
      message.success(`Welcome back, ${user.full_name || user.username}!`);
      
      // Navigate to dashboard
      window.location.href = '/dashboard';
      
    } catch (error: any) {
      console.error('Popup OAuth login error:', error);
      
      // Show user-friendly error messages with enhanced styling
      if (error.message?.includes('blocked')) {
        message.warning({
          content: (
            <div>
              <strong>Popup Blocked</strong><br />
              Please allow popups for this site and try again.
            </div>
          ),
          duration: 8,
          style: { marginTop: '20vh' }
        });
      } else if (error.message?.includes('cancelled')) {
        message.info({
          content: 'Login was cancelled by user.',
          duration: 4,
          style: { marginTop: '20vh' }
        });
      } else if (error.message?.includes('login_required')) {
        message.warning({
          content: (
            <div>
              <strong>MAX Platform Login Required</strong><br />
              Please log in to MAX Platform first at{' '}
              <a href="http://localhost:3000" target="_blank" rel="noopener noreferrer" style={{ color: '#667eea' }}>
                localhost:3000
              </a>
              , then try again.
            </div>
          ),
          duration: 12,
          style: { marginTop: '20vh' }
        });
      } else {
        message.error({
          content: (
            <div>
              <strong>Authentication Failed</strong><br />
              {error.message || 'Please try again or contact support.'}
            </div>
          ),
          duration: 8,
          style: { marginTop: '20vh' }
        });
      }
      
      setOauthLoading(false);
    }
  };

  const handleFallbackOAuthLogin = async () => {
    setOauthLoading(true);
    try {
      // Store current location for redirect after OAuth
      sessionStorage.setItem('oauthRedirectTo', window.location.pathname + window.location.search);
      
      await authService.loginWithOAuth();
    } catch (error: any) {
      console.error('Fallback OAuth login error:', error);
      
      // Show user-friendly error message
      if (error.message?.includes('not available')) {
        message.warning('OAuth login is temporarily unavailable. Please use email/password login below.');
      } else if (error.message?.includes('login_required')) {
        message.info({
          content: 'Please log in to MAX Platform first at http://localhost:3000, then try OAuth login again.',
          duration: 10
        });
      } else {
        message.error('OAuth login failed. Please try again or use email/password login.');
      }
      
      setOauthLoading(false);
    }
  };

  // Main OAuth login handler - tries popup first, then fallback
  const handleOAuthLogin = async () => {
    try {
      await handlePopupOAuthLogin();
    } catch (error: any) {
      // If popup fails due to blocking, offer fallback
      if (error.message?.includes('blocked')) {
        // Popup was blocked, user will see the message from handlePopupOAuthLogin
        // They can choose to enable popups or use regular login
      }
    }
  };

  const handleSignupRedirect = () => {
    authService.redirectToSignup();
  };

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ 
      backgroundColor: '#fafafa',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)'
    }}>
      <div style={{ width: '100%', maxWidth: '400px', padding: '0 24px' }}>
        <Card 
          style={{ 
            border: 'none',
            borderRadius: '16px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)',
            backgroundColor: '#ffffff',
            backdropFilter: 'blur(20px)',
            width: '100%',
            maxWidth: '400px',
            margin: '0 auto'
          }}
          styles={{ body: { padding: '40px 32px' } }}
        >
          {/* System Icon and Title - Centered */}
          <div className="text-center" style={{ marginBottom: '32px' }}>
            <div style={{ marginBottom: '20px' }}>
              <div style={{
                width: '48px',
                height: '48px',
                backgroundColor: '#000000',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto',
                fontSize: '24px',
                color: '#ffffff',
                fontWeight: 700,
                fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
              }}>
                MF
              </div>
            </div>
            <Title level={2} style={{ 
              color: '#000000', 
              marginBottom: '4px', 
              fontWeight: 700,
              fontSize: '24px',
              lineHeight: 1.2
            }}>
              MAX Flowstudio
            </Title>
            <Text style={{ 
              color: '#666666', 
              fontSize: '14px', 
              fontWeight: 400,
              lineHeight: 1.4,
              display: 'block'
            }}>
              노코드 워크플로우 플랫폼
            </Text>
          </div>

          {/* OAuth 2.0 Login Section */}
          <div style={{ textAlign: 'center' }}>
            <Text style={{ 
              color: '#666666', 
              fontSize: '15px', 
              display: 'block', 
              marginBottom: '28px',
              lineHeight: 1.5,
              fontWeight: 400
            }}>
              MAX Platform 계정으로 FlowStudio에 접근하세요
            </Text>
            
            <Button
              type="primary"
              icon={<LoginOutlined />}
              onClick={handleOAuthLogin}
              loading={oauthLoading}
              size="large"
              style={{ 
                height: '48px',
                borderRadius: '8px',
                backgroundColor: '#000000',
                borderColor: '#000000',
                fontSize: '15px',
                fontWeight: 500,
                marginBottom: '20px',
                boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
                transition: 'all 0.15s ease',
                minWidth: '200px',
                width: 'auto'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#1a1a1a';
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 4px 8px rgba(0, 0, 0, 0.15)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#000000';
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.1)';
              }}
            >
              MAX Platform으로 로그인
            </Button>

            <div className="text-center">
              <Text style={{ color: '#888888', fontSize: '14px', fontWeight: 400 }}>
                MAX Platform 계정이 없으신가요?{' '}
              </Text>
              <Button 
                type="link" 
                onClick={handleSignupRedirect}
                style={{ 
                  color: '#000000',
                  fontSize: '14px',
                  fontWeight: 500,
                  padding: '0 4px',
                  textDecoration: 'none',
                  height: 'auto'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.textDecoration = 'underline';
                  e.currentTarget.style.color = '#333333';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.textDecoration = 'none';
                  e.currentTarget.style.color = '#000000';
                }}
              >
                회원가입하기
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};