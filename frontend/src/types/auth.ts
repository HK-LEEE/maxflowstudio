/**
 * 파일명: auth.ts (30줄)
 * 목적: OAuth 인증 관련 타입 정의
 * 동작 과정:
 * 1. OAuth 토큰 관리 타입
 * 2. 인증 상태 타입
 * 데이터베이스 연동: OAuth 서비스와 연동
 * 의존성: user.ts
 */

import type { User } from './user';

// OAuth token info
export interface TokenInfo {
  access_token: string;
  token_type: string;
  expires_in: number;
  scope: string;
}

// OAuth auth state
export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
}