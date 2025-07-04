/**
 * Popup-based OAuth 2.0 Authentication Utility
 * Provides seamless OAuth login through popup windows with PostMessage communication
 */

interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  scope: string;
}


interface OAuthMessage {
  type: 'OAUTH_SUCCESS' | 'OAUTH_ERROR';
  token?: string;
  tokenData?: TokenResponse;
  error?: string;
}

export class PopupOAuthLogin {
  private popup: Window | null = null;
  private checkInterval: NodeJS.Timeout | null = null;
  private messageHandler: ((event: MessageEvent) => void) | null = null;
  private messageReceived: boolean = false;

  private readonly clientId = 'maxflowstudio';
  private readonly redirectUri: string;
  private readonly authUrl: string;
  private readonly scopes = ['read:profile', 'read:groups', 'manage:workflows'];

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
   * Start popup-based OAuth authentication
   */
  async startAuth(): Promise<TokenResponse> {
    // Generate PKCE parameters
    const state = this.generateCodeVerifier();
    const codeVerifier = this.generateCodeVerifier();
    const codeChallenge = await this.generateCodeChallenge(codeVerifier);
    
    return new Promise((resolve, reject) => {
      try {

        // Store in session storage for callback validation
        sessionStorage.setItem('oauth_state', state);
        sessionStorage.setItem('oauth_code_verifier', codeVerifier);
        sessionStorage.setItem('oauth_popup_mode', 'true');

        // Build OAuth authorization URL
        const params = new URLSearchParams({
          response_type: 'code',
          client_id: this.clientId,
          redirect_uri: this.redirectUri,
          scope: this.scopes.join(' '),
          state: state,
          code_challenge: codeChallenge,
          code_challenge_method: 'S256'
        });

        const authUrl = `${this.authUrl}/api/oauth/authorize?${params}`;
        console.log('🔐 Opening OAuth popup:', authUrl);

        // Open popup window
        this.popup = window.open(
          authUrl,
          'oauth_login',
          'width=500,height=600,scrollbars=yes,resizable=yes,top=100,left=100'
        );

        if (!this.popup) {
          sessionStorage.removeItem('oauth_popup_mode');
          reject(new Error('Popup was blocked. Please allow popups and try again, or use the regular login method.'));
          return;
        }

        // Set up PostMessage event listener
        this.messageHandler = (event: MessageEvent<OAuthMessage>) => {
          // Security: verify origin - allow FlowStudio and MAX Platform
          const trustedOrigins = [
            window.location.origin,  // FlowStudio (current port)
            'http://localhost:3005',  // FlowStudio original port
            'http://localhost:3006',  // FlowStudio alternate port
            'http://localhost:3000'   // MAX Platform
          ];
          
          if (!trustedOrigins.includes(event.origin)) {
            console.warn('Ignoring message from untrusted origin:', event.origin);
            return;
          }

          console.log('📨 Received OAuth message:', event.data);
          
          // Mark that we received a message to prevent "cancelled" error
          this.messageReceived = true;

          if (event.data.type === 'OAUTH_SUCCESS') {
            // Clear interval immediately to prevent race condition
            if (this.checkInterval) {
              clearInterval(this.checkInterval);
              this.checkInterval = null;
            }
            
            this.cleanup();
            if (event.data.tokenData) {
              resolve(event.data.tokenData);
            } else if (event.data.token) {
              // Handle cases where only token is provided
              resolve({
                access_token: event.data.token,
                token_type: 'Bearer',
                expires_in: 3600,
                scope: 'read:profile read:groups manage:workflows'
              });
            } else {
              reject(new Error('No token data received'));
            }
          } else if (event.data.type === 'OAUTH_ERROR') {
            this.cleanup();
            reject(new Error(event.data.error || 'OAuth authentication failed'));
          }
        };

        window.addEventListener('message', this.messageHandler);

        // Monitor popup closure
        this.checkInterval = setInterval(() => {
          if (this.popup?.closed) {
            // Give a short delay to allow any pending messages to be processed
            setTimeout(() => {
              if (!this.messageReceived) {
                console.log('🚪 Popup closed without receiving message - user cancelled');
                this.cleanup();
                reject(new Error('Authentication was cancelled by the user'));
              }
            }, 100);
          }
        }, 500);

      } catch (error) {
        this.cleanup();
        reject(error);
      }
    });
  }

  /**
   * Clean up popup and event listeners
   */
  private cleanup(): void {
    if (this.popup && !this.popup.closed) {
      this.popup.close();
    }
    
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }

    if (this.messageHandler) {
      window.removeEventListener('message', this.messageHandler);
      this.messageHandler = null;
    }

    this.popup = null;
    this.messageReceived = false; // Reset flag
    
    // Clean up all OAuth-related session storage
    sessionStorage.removeItem('oauth_popup_mode');
    sessionStorage.removeItem('oauth_state');
    sessionStorage.removeItem('oauth_code_verifier');
  }

  /**
   * Force cleanup (for external calls)
   */
  public forceCleanup(): void {
    this.cleanup();
  }
}

/**
 * Exchange authorization code for access token
 */
export async function exchangeCodeForToken(code: string): Promise<TokenResponse> {
  // Check for both popup OAuth and silent auth code verifiers
  const codeVerifier = sessionStorage.getItem('oauth_code_verifier') || 
                      sessionStorage.getItem('silent_oauth_code_verifier');
  const authUrl = import.meta.env.VITE_AUTH_SERVER_URL || 'http://localhost:8000';
  
  if (!codeVerifier) {
    throw new Error('No code verifier found in session storage');
  }

  const response = await fetch(`${authUrl}/api/oauth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code: code,
      redirect_uri: `${window.location.origin}/oauth/callback`,
      client_id: 'maxflowstudio',
      code_verifier: codeVerifier
      // Note: client_secret omitted for security - should be handled by backend in production
    })
  });

  // Read response body once
  const responseData = await response.json();
  
  if (!response.ok) {
    throw new Error(responseData.error_description || `Token exchange failed: ${response.statusText}`);
  }

  const tokenData = responseData as TokenResponse;
  console.log('✅ Token exchange successful:', { 
    token_type: tokenData.token_type,
    expires_in: tokenData.expires_in,
    scope: tokenData.scope 
  });

  return tokenData;
}

/**
 * Check if current page is in popup mode
 */
export function isPopupMode(): boolean {
  return sessionStorage.getItem('oauth_popup_mode') === 'true' || 
         window.opener !== null;
}

/**
 * Get user info using access token
 */
export async function getUserInfo(accessToken: string): Promise<{
  sub: string;
  email: string;
  display_name: string;
  real_name: string;
  is_admin: boolean;
  groups?: Array<{ id: string; name: string }>;
}> {
  const authUrl = import.meta.env.VITE_AUTH_SERVER_URL || 'http://localhost:8000';
  
  const response = await fetch(`${authUrl}/api/oauth/userinfo`, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch user info: ${response.statusText}`);
  }

  return response.json();
}