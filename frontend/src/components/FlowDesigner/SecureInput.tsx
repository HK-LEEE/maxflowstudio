/**
 * SecureInput Component
 * 보안이 강화된 입력 컴포넌트 - API Key, URL 등 민감 정보용
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Input, Button, Tooltip } from 'antd';
import { EyeOutlined, EyeInvisibleOutlined, LockOutlined, SafetyOutlined } from '@ant-design/icons';
import './SecureInput.css';

interface SecureInputProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  envValue?: string; // 환경변수에서 가져온 값
  envKey?: string; // 환경변수 키 (DB에서 값을 가져오기 위함)
  type?: 'password' | 'url';
  disabled?: boolean;
  supportDbEnv?: boolean; // DB 환경변수 지원 여부
}

export const SecureInput: React.FC<SecureInputProps> = ({
  value = '',
  onChange,
  placeholder = '',
  envValue = '',
  envKey = '',
  type = 'password',
  disabled = false,
  supportDbEnv = false,
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const [dbEnvValue, setDbEnvValue] = useState<string>('');
  const [localValue, setLocalValue] = useState(value || envValue);

  // value prop이 변경될 때 localValue 동기화
  useEffect(() => {
    setLocalValue(value || envValue || dbEnvValue);
  }, [value, envValue, dbEnvValue]);

  // DB 환경변수 로드
  useEffect(() => {
    const loadDbEnvironmentVariable = async () => {
      if (supportDbEnv && envKey && !value && !envValue) {
        try {
          const response = await fetch('/api/environment-variables/values/resolved', {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
            },
          });
          
          if (response.ok) {
            const data = await response.json();
            const envVars = data.environment_variables || {};
            if (envVars[envKey]) {
              setDbEnvValue(envVars[envKey]);
              setLocalValue(envVars[envKey]);
            }
          }
        } catch (error) {
          console.warn('DB 환경변수 로드 실패:', error);
        }
      }
    };

    loadDbEnvironmentVariable();
  }, [supportDbEnv, envKey, value, envValue]);

  // 값이 있는지 확인
  const hasValue = localValue.length > 0;
  const isUsingEnvValue = envValue && !value;
  const isUsingDbEnvValue = dbEnvValue && !value && !envValue;

  // 마스킹 처리된 값 생성
  const getMaskedValue = useCallback(() => {
    if (!hasValue) return '';
    
    if (type === 'url') {
      // URL의 경우 도메인 부분만 마스킹
      const urlPattern = /^(https?:\/\/)([^\/]+)(\/.*)?$/;
      const match = localValue.match(urlPattern);
      if (match) {
        const [, protocol, domain, path] = match;
        const maskedDomain = domain.length > 6 
          ? domain.substring(0, 3) + '••••••' + domain.substring(domain.length - 3)
          : '••••••';
        return `${protocol}${maskedDomain}${path || ''}`;
      }
    }
    
    // API Key의 경우 완전 마스킹
    return '••••••••••••••••••••••••••••••••';
  }, [localValue, hasValue, type]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setLocalValue(newValue);
    onChange?.(newValue);
  };

  const toggleVisibility = () => {
    setIsVisible(!isVisible);
  };

  // 복사 방지 이벤트 핸들러
  const preventCopy = (e: React.ClipboardEvent) => {
    e.preventDefault();
    return false;
  };

  const preventContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    return false;
  };

  const displayValue = isVisible ? localValue : getMaskedValue();

  return (
    <div className="secure-input-container">
      <Input
        value={displayValue}
        onChange={handleChange}
        placeholder={isVisible ? placeholder : '••••••••••••••••'}
        disabled={disabled}
        onCopy={preventCopy}
        onCut={preventCopy}
        onPaste={(e) => {
          // 붙여넣기는 허용하되, 보안 상태 유지
          const pastedValue = e.clipboardData.getData('text');
          setLocalValue(pastedValue);
          onChange?.(pastedValue);
        }}
        onContextMenu={preventContextMenu}
        className={`secure-input ${hasValue ? 'has-value' : ''} ${isUsingEnvValue ? 'env-value' : ''}`}
        style={{
          userSelect: isVisible ? 'text' : 'none',
          fontFamily: isVisible ? 'inherit' : 'monospace',
        }}
        prefix={
          <Tooltip title={
            isUsingDbEnvValue ? 'DB 환경변수에서 로드됨' :
            isUsingEnvValue ? '.env 파일에서 로드됨' : 
            '보안 입력 필드'
          }>
            {(isUsingEnvValue || isUsingDbEnvValue) ? (
              <SafetyOutlined style={{ color: '#52c41a' }} />
            ) : (
              <LockOutlined style={{ color: '#8c8c8c' }} />
            )}
          </Tooltip>
        }
        suffix={
          hasValue && (
            <Button
              type="text"
              size="small"
              icon={isVisible ? <EyeInvisibleOutlined /> : <EyeOutlined />}
              onClick={toggleVisibility}
              className="visibility-toggle"
              style={{ border: 'none', boxShadow: 'none' }}
            />
          )
        }
      />
      
      {(isUsingEnvValue || isUsingDbEnvValue) && (
        <div className="env-indicator">
          <span>
            {isUsingDbEnvValue ? 'DB 환경변수 값 사용 중' : '.env 파일 값 사용 중'}
            {(isUsingDbEnvValue && envKey) && (
              <span style={{ marginLeft: '4px', fontWeight: 'bold' }}>({envKey})</span>
            )}
          </span>
        </div>
      )}
      
      {hasValue && !isVisible && (
        <div className="security-notice">
          <span>보안을 위해 마스킹 처리됨</span>
        </div>
      )}
    </div>
  );
};