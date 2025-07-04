/**
 * Authentication utilities for FlowStudio
 */

/**
 * Get the current access token from localStorage
 */
export const getAccessToken = (): string | null => {
  return localStorage.getItem('accessToken');
};

/**
 * Set access token in localStorage
 */
export const setAccessToken = (token: string): void => {
  localStorage.setItem('accessToken', token);
};

/**
 * Remove access token from localStorage
 */
export const removeAccessToken = (): void => {
  localStorage.removeItem('accessToken');
};

/**
 * Check if current token is expired (basic check without verification)
 */
export const isTokenExpired = (token: string): boolean => {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000; // Convert to milliseconds
    return Date.now() >= exp;
  } catch {
    return true; // Consider invalid tokens as expired
  }
};

/**
 * Ensure we have a valid token, refresh if needed
 */
export const ensureValidToken = async (): Promise<string | null> => {
  const token = getAccessToken();
  
  if (!token) {
    return null;
  }
  
  if (isTokenExpired(token)) {
    try {
      // Import authService dynamically to avoid circular dependency
      const { authService } = await import('../services/auth');
      const refreshResult = await authService.refreshToken();
      return refreshResult.access_token;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return null;
    }
  }
  
  return token;
};