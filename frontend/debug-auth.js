// Debug script to check authentication state
// Run this in browser console to check auth status

console.log('=== FlowStudio Authentication Debug ===');

// Check localStorage tokens
const accessToken = localStorage.getItem('accessToken');
const refreshToken = localStorage.getItem('refreshToken');

console.log('Access Token:', accessToken ? 'Present' : 'Missing');
console.log('Refresh Token:', refreshToken ? 'Present' : 'Missing');

if (accessToken) {
  try {
    // Decode JWT without verification (for debugging only)
    const payload = JSON.parse(atob(accessToken.split('.')[1]));
    console.log('Token Payload:', payload);
    
    const exp = payload.exp * 1000; // Convert to milliseconds
    const now = Date.now();
    const isExpired = now >= exp;
    
    console.log('Token Expiry:', new Date(exp));
    console.log('Current Time:', new Date(now));
    console.log('Is Expired:', isExpired);
    
    if (isExpired) {
      console.log('⚠️ Token is expired!');
    } else {
      console.log('✅ Token is valid');
    }
  } catch (e) {
    console.error('❌ Failed to decode token:', e);
  }
}

// Test API call
if (accessToken) {
  console.log('Testing API call...');
  fetch('/api/deployments/', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    }
  })
  .then(response => {
    console.log('API Response Status:', response.status);
    if (response.status === 401) {
      console.log('❌ API call failed - Unauthorized');
    } else if (response.ok) {
      console.log('✅ API call successful');
      return response.json();
    } else {
      console.log('⚠️ API call failed with status:', response.status);
    }
  })
  .then(data => {
    if (data) {
      console.log('API Response Data:', data);
    }
  })
  .catch(error => {
    console.error('❌ API call error:', error);
  });
}