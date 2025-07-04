/**
 * OAuth 2.0 Callback Page
 * Handles the OAuth authorization code exchange and user login completion
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Spin, Alert, Typography, Card } from 'antd';
import { LoadingOutlined, CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { authService } from '../services/auth';
import { oauthClient, MaxPlatformOAuth } from '../services/oauth';
import { exchangeCodeForToken, isPopupMode } from '../utils/popupOAuth';
import { SilentAuth } from '../utils/silentAuth';

const { Title, Paragraph } = Typography;

interface CallbackState {
  status: 'loading' | 'success' | 'error';
  message: string;
  error?: string;
}

export const OAuthCallback: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [state, setState] = useState<CallbackState>({
    status: 'loading',
    message: 'Processing OAuth callback...'
  });

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        // Check if this is an OAuth callback
        if (!MaxPlatformOAuth.isOAuthCallback()) {
          throw new Error('Invalid OAuth callback - missing required parameters');
        }

        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');
        const errorDescription = searchParams.get('error_description');
        
        // Check if we're in popup mode or silent auth mode
        const inPopupMode = isPopupMode();
        const isSilentAuth = sessionStorage.getItem('silent_oauth_state') !== null;
        
        if (error) {
          const errorMessage = errorDescription || `OAuth error: ${error}`;
          
          if (inPopupMode || isSilentAuth) {
            // Send error to parent window (popup or iframe)
            window.opener?.postMessage({
              type: 'OAUTH_ERROR',
              error: errorMessage
            }, window.location.origin);
            
            if (inPopupMode) {
              window.close();
            }
            return;
          } else {
            // Handle non-popup mode errors
            if (error === 'login_required') {
              setState({
                status: 'error',
                message: 'MAX Platform Login Required',
                error: 'Please log in to MAX Platform first at http://localhost:3000, then try the OAuth login again. Redirecting to FlowStudio login...'
              });
              
              setTimeout(() => {
                navigate('/login', { replace: true });
              }, 5000);
              return;
            }
            
            throw new Error(errorMessage);
          }
        }

        if (!code) {
          throw new Error('No authorization code received');
        }

        setState({
          status: 'loading',
          message: 'Exchanging authorization code for access token...'
        });

        if (inPopupMode || isSilentAuth) {
          // Popup/Silent mode: handle token exchange and send to parent
          try {
            // Validate state parameter (check both popup and silent auth storage)
            const storedState = sessionStorage.getItem('oauth_state') || 
                               sessionStorage.getItem('silent_oauth_state');
            if (state !== storedState) {
              window.opener?.postMessage({
                type: 'OAUTH_ERROR',
                error: 'Invalid state parameter - possible security issue'
              }, window.location.origin);
              
              if (inPopupMode) {
                window.close();
              }
              return;
            }

            // Exchange code for token
            const tokenResponse = await exchangeCodeForToken(code);
            
            // Clean up session storage
            sessionStorage.removeItem('oauth_state');
            sessionStorage.removeItem('oauth_code_verifier');
            sessionStorage.removeItem('oauth_popup_mode');
            sessionStorage.removeItem('silent_oauth_state');
            sessionStorage.removeItem('silent_oauth_code_verifier');
            
            // Send success message to parent window
            window.opener?.postMessage({
              type: 'OAUTH_SUCCESS',
              token: tokenResponse.access_token,
              tokenData: tokenResponse
            }, window.location.origin);
            
            if (inPopupMode) {
              window.close();
            }
            
          } catch (error: any) {
            console.error('OAuth token exchange error:', error);
            window.opener?.postMessage({
              type: 'OAUTH_ERROR',
              error: error.message || 'Token exchange failed'
            }, window.location.origin);
            
            if (inPopupMode) {
              window.close();
            }
          }
        } else {
          // Regular mode: use existing auth service
          const user = await authService.handleOAuthCallback();

          setState({
            status: 'success',
            message: `Welcome back, ${user.full_name || user.username}! Redirecting...`
          });

          // Redirect to the intended page or dashboard after a short delay
          setTimeout(() => {
            const redirectTo = sessionStorage.getItem('oauthRedirectTo') || '/';
            sessionStorage.removeItem('oauthRedirectTo');
            navigate(redirectTo, { replace: true });
          }, 2000);
        }

      } catch (error: any) {
        console.error('OAuth callback error:', error);
        
        const inErrorPopupMode = isPopupMode();
        const inErrorSilentAuth = sessionStorage.getItem('silent_oauth_state') !== null;
        
        if (inErrorPopupMode || inErrorSilentAuth) {
          window.opener?.postMessage({
            type: 'OAUTH_ERROR',
            error: error.message || 'Authentication failed'
          }, window.location.origin);
          
          if (inErrorPopupMode) {
            window.close();
          }
        } else {
          setState({
            status: 'error',
            message: 'Authentication failed',
            error: error.message || 'An unexpected error occurred during authentication'
          });

          // Redirect to login page after 5 seconds
          setTimeout(() => {
            navigate('/login', { replace: true });
          }, 5000);
        }
      }
    };

    handleOAuthCallback();
  }, [navigate, searchParams]);

  const renderIcon = () => {
    switch (state.status) {
      case 'loading':
        return <LoadingOutlined style={{ fontSize: 48, color: '#1890ff' }} spin />;
      case 'success':
        return <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />;
      case 'error':
        return <ExclamationCircleOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />;
    }
  };

  const renderAlert = () => {
    if (state.status === 'error') {
      return (
        <Alert
          message="Authentication Error"
          description={state.error}
          type="error"
          showIcon
          style={{ marginTop: 24 }}
          action={
            <span style={{ fontSize: '14px', color: '#666' }}>
              Redirecting to login page in a few seconds...
            </span>
          }
        />
      );
    }
    return null;
  };

  // Check if we're in popup mode for simplified UI
  const inPopupMode = isPopupMode();

  if (inPopupMode) {
    // Simplified popup UI
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)'
      }}>
        <div style={{ 
          textAlign: 'center', 
          padding: '40px',
          backgroundColor: '#ffffff',
          borderRadius: '16px',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)',
          backdropFilter: 'blur(20px)'
        }}>
          <div style={{ marginBottom: '24px' }}>
            <div style={{
              width: '64px',
              height: '64px',
              backgroundColor: '#000000',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 20px',
              fontSize: '32px',
              color: '#ffffff',
              fontWeight: 700,
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
            }}>MF</div>
          </div>
          <div style={{
            border: '3px solid #f0f0f0',
            borderTop: '3px solid #000000',
            borderRadius: '50%',
            width: '32px',
            height: '32px',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 20px'
          }}></div>
          <Title level={4} style={{ marginBottom: 8, color: '#000000' }}>
            인증 처리 중...
          </Title>
          <Paragraph style={{ fontSize: 14, color: '#666', margin: 0 }}>
            로그인을 완료하는 동안 잠시 기다려 주세요.
          </Paragraph>
          <style>{`
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    );
  }

  // Regular full-page UI for non-popup mode
  return (
    <div style={{ 
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)',
      padding: '20px',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
    }}>
      <Card
        style={{
          width: '100%',
          maxWidth: 500,
          textAlign: 'center',
          borderRadius: 16,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.08)',
          backgroundColor: '#ffffff',
          backdropFilter: 'blur(20px)',
          border: 'none'
        }}
        styles={{ body: { padding: '48px 32px' } }}
      >
        <div style={{ marginBottom: 24 }}>
          <div style={{
            width: '64px',
            height: '64px',
            backgroundColor: '#000000',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 24px',
            fontSize: '32px',
            color: '#ffffff',
            fontWeight: 700,
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
          }}>MF</div>
          {renderIcon()}
        </div>
        
        <Title level={3} style={{ marginBottom: 16, color: '#000000' }}>
          {state.status === 'loading' && '인증 중...'}
          {state.status === 'success' && '로그인 성공!'}
          {state.status === 'error' && '인증 실패'}
        </Title>
        
        <Paragraph style={{ fontSize: 16, color: '#666', marginBottom: 8 }}>
          {state.message}
        </Paragraph>
        
        {state.status === 'loading' && (
          <Paragraph style={{ fontSize: 14, color: '#999' }}>
            인증을 완료하는 동안 잠시 기다려 주세요...
          </Paragraph>
        )}
        
        {state.status === 'success' && (
          <Paragraph style={{ fontSize: 14, color: '#52c41a' }}>
            곧 대시보드로 이동합니다.
          </Paragraph>
        )}
        
        {renderAlert()}
      </Card>
    </div>
  );
};