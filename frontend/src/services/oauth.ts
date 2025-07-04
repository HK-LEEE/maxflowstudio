/**
 * OAuth 2.0 Client with PKCE Support
 * Implements Authorization Code Flow for MAX Platform OAuth
 */

interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  scope: string;
  refresh_token?: string;
}

interface UserInfo {
  sub: string;
  email: string;
  real_name: string;
  display_name: string;
  is_admin: boolean;
  is_verified: boolean;
  groups: Array<{
    id: string;
    name: string;
  }>;
}

interface PKCEData {
  codeVerifier: string;
  codeChallenge: string;
}

export class MaxPlatformOAuth {
  private clientId: string;
  private redirectUri: string;
  private authUrl: string;
  private scopes: string[];

  constructor() {
    this.clientId = 'maxflowstudio';
    this.redirectUri = `${window.location.origin}/oauth/callback`;
    this.authUrl = import.meta.env.VITE_AUTH_SERVER_URL || 'http://localhost:8000';
    this.scopes = ['read:profile', 'read:groups', 'manage:workflows'];
  }

  /**
   * Generate PKCE code verifier and challenge
   */
  private async generatePKCE(): Promise<PKCEData> {
    const codeVerifier = this.generateCodeVerifier();
    const codeChallenge = await this.generateCodeChallenge(codeVerifier);
    
    return { codeVerifier, codeChallenge };
  }

  /**
   * Generate code verifier for PKCE
   */
  private generateCodeVerifier(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return this.base64URLEncode(array);
  }

  /**
   * Generate code challenge from verifier
   */
  private async generateCodeChallenge(verifier: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const digest = await crypto.subtle.digest('SHA-256', data);
    return this.base64URLEncode(new Uint8Array(digest));
  }

  /**
   * Base64 URL encode
   */
  private base64URLEncode(array: Uint8Array): string {
    return btoa(String.fromCharCode(...array))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=/g, '');
  }

  /**
   * Generate random state parameter
   */
  private generateState(): string {
    const array = new Uint8Array(16);
    crypto.getRandomValues(array);
    return this.base64URLEncode(array);
  }

  /**
   * Check if OAuth 2.0 is available on the auth server
   */
  private async isOAuthAvailable(): Promise<boolean> {
    try {
      const response = await fetch(`${this.authUrl}/api/oauth/.well-known/oauth-authorization-server`);
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Start OAuth 2.0 authorization flow
   */
  async startAuth(customScopes?: string[]): Promise<void> {
    // Check if OAuth 2.0 is available
    const oauthAvailable = await this.isOAuthAvailable();
    if (!oauthAvailable) {
      throw new Error('OAuth 2.0 is not available on the auth server. Please use the legacy login method.');
    }

    const state = this.generateState();
    const { codeVerifier, codeChallenge } = await this.generatePKCE();
    const scopes = customScopes || this.scopes;
    
    // Store state and code verifier in session storage
    sessionStorage.setItem('oauth_state', state);
    sessionStorage.setItem('oauth_code_verifier', codeVerifier);
    
    const params = new URLSearchParams({
      response_type: 'code',
      client_id: this.clientId,
      redirect_uri: this.redirectUri,
      scope: scopes.join(' '),
      state: state,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256',
      prompt: 'login'  // Force login prompt to handle login_required scenarios
    });
    
    const authUrl = `${this.authUrl}/api/oauth/authorize?${params}`;
    console.log('🔐 Redirecting to OAuth authorization:', authUrl);
    
    window.location.href = authUrl;
  }

  /**
   * Handle OAuth callback and exchange code for token
   */
  async handleCallback(): Promise<TokenResponse> {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const state = urlParams.get('state');
    const error = urlParams.get('error');
    
    if (error) {
      throw new Error(`OAuth Error: ${error}`);
    }
    
    if (!code) {
      throw new Error('No authorization code received');
    }
    
    // Verify state parameter
    const storedState = sessionStorage.getItem('oauth_state');
    if (state !== storedState) {
      throw new Error('Invalid state parameter - possible CSRF attack');
    }
    
    const codeVerifier = sessionStorage.getItem('oauth_code_verifier');
    if (!codeVerifier) {
      throw new Error('No code verifier found in session');
    }
    
    // Clean up session storage
    sessionStorage.removeItem('oauth_state');
    sessionStorage.removeItem('oauth_code_verifier');
    
    return await this.exchangeCodeForToken(code, codeVerifier);
  }

  /**
   * Exchange authorization code for access token
   */
  private async exchangeCodeForToken(code: string, codeVerifier: string): Promise<TokenResponse> {
    const response = await fetch(`${this.authUrl}/api/oauth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: this.redirectUri,
        client_id: this.clientId,
        code_verifier: codeVerifier
      })
    });
    
    // Read response body once
    const responseData = await response.json();
    
    if (!response.ok) {
      throw new Error(responseData.error_description || `Token exchange failed: ${response.statusText}`);
    }
    
    const tokenResponse = responseData as TokenResponse;
    console.log('✅ Token exchange successful:', { 
      token_type: tokenResponse.token_type,
      expires_in: tokenResponse.expires_in,
      scope: tokenResponse.scope 
    });
    
    return tokenResponse;
  }

  /**
   * Get user information using access token
   */
  async getUserInfo(accessToken: string): Promise<UserInfo> {
    const response = await fetch(`${this.authUrl}/api/oauth/userinfo`, {
      headers: {
        'Authorization': `Bearer ${accessToken}`
      }
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch user info: ${response.statusText}`);
    }
    
    const userInfo = await response.json() as UserInfo;
    console.log('👤 User info retrieved:', { 
      sub: userInfo.sub,
      email: userInfo.email,
      display_name: userInfo.display_name,
      groups: userInfo.groups?.map(g => g.name)
    });
    
    return userInfo;
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    console.log('🔄 OAuth: Attempting token refresh');
    
    const response = await fetch(`${this.authUrl}/api/oauth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
        client_id: this.clientId,
      })
    });
    
    // Read response body once
    const responseData = await response.json();
    
    if (!response.ok) {
      console.error('❌ OAuth: Token refresh failed:', responseData);
      throw new Error(responseData.error_description || `Token refresh failed: ${response.statusText}`);
    }
    
    const tokenResponse = responseData as TokenResponse;
    console.log('✅ OAuth: Token refreshed successfully');
    return tokenResponse;
  }

  /**
   * Revoke access token
   */
  async revokeToken(accessToken: string): Promise<void> {
    const response = await fetch(`${this.authUrl}/api/oauth/revoke`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        token: accessToken,
        client_id: this.clientId
      })
    });
    
    if (!response.ok) {
      console.warn('Token revocation failed:', response.statusText);
    } else {
      console.log('🔓 Token revoked successfully');
    }
  }

  /**
   * Check if callback URL indicates OAuth flow
   */
  static isOAuthCallback(): boolean {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.has('code') || urlParams.has('error');
  }
}

// Export singleton instance
export const oauthClient = new MaxPlatformOAuth();