/**
 * Debug utility to test auth server connectivity
 */

import { authApiClient } from '../services/api';

export const testAuthServer = async () => {
  console.log('🧪 Testing Auth Server connectivity...');
  
  try {
    // Test basic connectivity
    const healthResponse = await authApiClient.get('/health');
    console.log('✅ Auth Server health check:', healthResponse.data);
  } catch (error: any) {
    console.error('❌ Auth Server health check failed:', error);
  }
  
  try {
    // Test admin groups endpoint
    const groupsResponse = await authApiClient.get('/admin/groups');
    console.log('✅ Groups endpoint response:', groupsResponse.data);
  } catch (error: any) {
    console.error('❌ Groups endpoint failed:', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
    });
  }
  
  try {
    // Test admin users endpoint  
    const usersResponse = await authApiClient.get('/admin/users');
    console.log('✅ Users endpoint response:', usersResponse.data);
  } catch (error: any) {
    console.error('❌ Users endpoint failed:', {
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
    });
  }
};

// Make it available in browser console
(window as any).testAuthServer = testAuthServer;