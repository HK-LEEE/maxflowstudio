/**
 * Silent Authentication Utility
 * Enables automatic SSO login by checking MAX Platform authentication status
 * without user interaction using iframe and prompt=none OAuth flow
 */

interface SilentAuthResult {
  success: boolean;
  token?: string;
  tokenData?: {
    access_token: string;
    token_type: string;
    expires_in: number;
    scope: string;
  };
  error?: string;
}

export class SilentAuth {
  private iframe: HTMLIFrameElement | null = null;
  private messageHandler: ((event: MessageEvent) => void) | null = null;
  private timeoutId: NodeJS.Timeout | null = null;

  private readonly clientId = 'maxflowstudio';
  private readonly redirectUri: string;
  private readonly authUrl: string;
  private readonly scopes = ['read:profile', 'read:groups', 'manage:workflows'];
  private readonly timeout = 5000; // 5 seconds timeout for silent auth

  constructor() {
    this.redirectUri = `${window.location.origin}/oauth/callback`;
    this.authUrl = import.meta.env.VITE_AUTH_SERVER_URL || 'http://localhost:8000';
  }

  /**
   * Generate PKCE code verifier
   */
  private generateCodeVerifier(): string {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return this.base64URLEncode(array);
  }

  /**
   * Generate PKCE code challenge from verifier
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
   * Exchange authorization code for access token
   */
  private async exchangeCodeForToken(code: string, codeVerifier: string): Promise<{
    access_token: string;
    token_type: string;
    expires_in: number;
    scope: string;
  }> {
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

    return responseData;
  }

  /**
   * Attempt silent authentication using iframe with prompt=none
   */
  async attemptSilentAuth(): Promise<SilentAuthResult> {
    const codeVerifier = this.generateCodeVerifier();
    const codeChallenge = await this.generateCodeChallenge(codeVerifier);
    
    return new Promise((resolve) => {
      try {
        console.log('🔇 Starting silent authentication...');

        // Generate PKCE parameters
        const state = this.generateCodeVerifier();

        // Store PKCE data temporarily
        sessionStorage.setItem('silent_oauth_state', state);
        sessionStorage.setItem('silent_oauth_code_verifier', codeVerifier);

        // Build silent OAuth URL with prompt=none
        const params = new URLSearchParams({
          response_type: 'code',
          client_id: this.clientId,
          redirect_uri: this.redirectUri,
          scope: this.scopes.join(' '),
          state: state,
          code_challenge: codeChallenge,
          code_challenge_method: 'S256',
          prompt: 'none' // Critical: no user interaction
        });

        const silentAuthUrl = `${this.authUrl}/api/oauth/authorize?${params}`;
        console.log('🔇 Silent auth URL:', silentAuthUrl);

        // Create hidden iframe
        this.iframe = document.createElement('iframe');
        this.iframe.style.display = 'none';
        this.iframe.style.position = 'absolute';
        this.iframe.style.top = '-1000px';
        this.iframe.style.left = '-1000px';
        this.iframe.style.width = '1px';
        this.iframe.style.height = '1px';
        this.iframe.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-forms allow-popups');

        // Set up message listener for callback
        this.messageHandler = async (event: MessageEvent) => {
          // Security: verify origin - also include the current port (3006)
          const trustedOrigins = [
            window.location.origin,  // FlowStudio (current port - e.g., http://localhost:3006)
            'http://localhost:3005',  // FlowStudio original port
            'http://localhost:3000'   // MAX Platform
          ];
          
          if (!trustedOrigins.includes(event.origin)) {
            console.warn('Silent auth: ignoring message from untrusted origin:', event.origin);
            return;
          }

          console.log('🔇 Silent auth received message:', event.data);

          if (event.data.type === 'OAUTH_SUCCESS') {
            this.cleanup();
            
            if (event.data.tokenData) {
              resolve({
                success: true,
                token: event.data.token,
                tokenData: event.data.tokenData
              });
            } else if (event.data.token) {
              resolve({
                success: true,
                token: event.data.token,
                tokenData: {
                  access_token: event.data.token,
                  token_type: 'Bearer',
                  expires_in: 3600,
                  scope: this.scopes.join(' ')
                }
              });
            } else {
              resolve({
                success: false,
                error: 'No token data received from silent auth'
              });
            }
          } else if (event.data.type === 'OAUTH_ERROR') {
            this.cleanup();
            
            // Common silent auth errors
            if (event.data.error === 'login_required' || 
                event.data.error === 'interaction_required' ||
                event.data.error === 'consent_required') {
              console.log('🔇 Silent auth failed: user not logged in to MAX Platform');
              resolve({
                success: false,
                error: 'login_required'
              });
            } else {
              console.warn('🔇 Silent auth error:', event.data.error);
              resolve({
                success: false,
                error: event.data.error || 'Silent authentication failed'
              });
            }
          }
        };

        window.addEventListener('message', this.messageHandler);

        // Set timeout for silent auth
        this.timeoutId = setTimeout(() => {
          console.log('🔇 Silent auth timeout');
          this.cleanup();
          resolve({
            success: false,
            error: 'silent_auth_timeout'
          });
        }, this.timeout);

        // Add iframe load listener for debugging
        this.iframe.onload = () => {
          console.log('🔇 Silent auth iframe loaded');
        };
        
        this.iframe.onerror = (error) => {
          console.error('🔇 Silent auth iframe error:', error);
          this.cleanup();
          resolve({
            success: false,
            error: 'iframe_load_error'
          });
        };

        // Load the iframe
        document.body.appendChild(this.iframe);
        this.iframe.src = silentAuthUrl;

      } catch (error) {
        console.error('🔇 Silent auth setup error:', error);
        this.cleanup();
        resolve({
          success: false,
          error: error instanceof Error ? error.message : 'Silent authentication setup failed'
        });
      }
    });
  }

  /**
   * Clean up iframe and event listeners
   */
  private cleanup(): void {
    if (this.iframe && this.iframe.parentNode) {
      this.iframe.parentNode.removeChild(this.iframe);
    }
    this.iframe = null;

    if (this.messageHandler) {
      window.removeEventListener('message', this.messageHandler);
      this.messageHandler = null;
    }

    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    // Clean up session storage
    sessionStorage.removeItem('silent_oauth_state');
    sessionStorage.removeItem('silent_oauth_code_verifier');
  }

  /**
   * Force cleanup (for external calls)
   */
  public forceCleanup(): void {
    this.cleanup();
  }
}

/**
 * Check if current page supports silent auth (not on login or callback pages)
 */
export function canAttemptSilentAuth(): boolean {
  const path = window.location.pathname;
  return path !== '/login' && path !== '/oauth/callback';
}

/**
 * Convenient function to attempt silent authentication
 */
export async function attemptSilentLogin(): Promise<SilentAuthResult> {
  if (!canAttemptSilentAuth()) {
    return {
      success: false,
      error: 'Cannot attempt silent auth on current page'
    };
  }

  const silentAuth = new SilentAuth();
  
  try {
    const result = await silentAuth.attemptSilentAuth();
    return result;
  } finally {
    silentAuth.forceCleanup();
  }
}