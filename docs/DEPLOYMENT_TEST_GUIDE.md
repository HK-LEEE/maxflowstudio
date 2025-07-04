# FlowStudio Deployment Testing Guide

## Overview
This guide helps you test the complete deployment workflow to ensure everything works correctly.

## Prerequisites
1. FlowStudio backend running on `localhost:8005`
2. FlowStudio frontend running on `localhost:3005`
3. Auth server running on `localhost:8000`
4. Admin user account: `admin@test.com` / `admin123`

## Testing Steps

### 1. Create and Publish a Flow

1. **Login to FlowStudio**
   - Go to `http://localhost:3005`
   - Login with `admin@test.com` / `admin123`

2. **Create a Simple Flow**
   - Click "New Flow" 
   - Add an Input node (set name to "message", type to "string")
   - Add an Output node (set name to "response", type to "string")
   - Connect Input → Output
   - Save the flow with name "Test API Flow"

3. **Publish the Flow**
   - Click the "Publish" button
   - Enter version name "v1.0"
   - Add description "Test deployment"
   - Click "Publish"
   - Verify success message appears

### 2. Verify Deployment Creation

1. **Check API Deployments Page**
   - Go to "API Deployments" in the sidebar
   - Verify a new deployment appears with status "PENDING"
   - Note the deployment name (e.g., "Test API Flow - v1")

### 3. Approve Deployment (Admin)

1. **Approve the Deployment**
   - In API Deployments page, find the pending deployment
   - Click the green checkmark (✓) to approve
   - Verify status changes to "ACTIVE"
   - Note the endpoint path (e.g., `/flow-123-v1`)

### 4. Test API Usage

1. **Copy Endpoint Information**
   - Click the "?" (How to Use) button for your deployment
   - Review the Quick Start tab for endpoint details
   - Copy the cURL example from the cURL tab

2. **Get JWT Token**
   - Open browser DevTools (F12)
   - Go to Application → Local Storage
   - Copy the `accessToken` value

3. **Test with cURL**
   ```bash
   curl -X POST http://localhost:8005/api/deployed/flow-123-v1 \
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"message": "Hello FlowStudio!"}'
   ```

4. **Expected Response**
   ```json
   {
     "success": true,
     "data": {
       "response": "Hello FlowStudio!"
     },
     "message": "",
     "execution_id": "uuid-here"
   }
   ```

### 5. Test Python Integration

```python
import requests

# Replace with your actual endpoint and token
url = "http://localhost:8005/api/deployed/flow-123-v1"
token = "YOUR_JWT_TOKEN"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

data = {
    "message": "Hello from Python!"
}

response = requests.post(url, json=data, headers=headers)
print("Status:", response.status_code)
print("Response:", response.json())
```

## Verification Checklist

- [ ] Flow creation and editing works
- [ ] Publish creates deployment with PENDING status
- [ ] API Deployments page shows the deployment
- [ ] Admin can approve deployment (status → ACTIVE)
- [ ] "How to Use" modal shows correct information
- [ ] cURL request works with proper authentication
- [ ] Python script works with proper authentication
- [ ] Response format matches expected structure
- [ ] Rate limiting works (if configured)
- [ ] Error handling works for invalid requests

## Common Issues

### 1. 401 Unauthorized
- **Problem**: Invalid or expired JWT token
- **Solution**: Get fresh token from browser DevTools

### 2. 404 Not Found
- **Problem**: Incorrect endpoint URL or deployment not active
- **Solution**: Verify deployment status is ACTIVE, check endpoint path

### 3. 400 Bad Request
- **Problem**: Request data doesn't match input schema
- **Solution**: Check input requirements in "Schema" tab

### 4. 503 Service Unavailable
- **Problem**: Deployment is inactive or failed
- **Solution**: Check deployment status, try activating

## Performance Testing

For load testing, you can use this simple script:

```python
import requests
import concurrent.futures
import time

def make_request(url, headers, data):
    try:
        response = requests.post(url, json=data, headers=headers)
        return response.status_code, response.elapsed.total_seconds()
    except Exception as e:
        return 0, 0

# Configuration
url = "http://localhost:8005/api/deployed/your-endpoint"
headers = {"Authorization": "Bearer YOUR_TOKEN", "Content-Type": "application/json"}
data = {"message": "Load test"}

# Run 100 concurrent requests
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(make_request, url, headers, data) for _ in range(100)]
    results = [future.result() for future in futures]

success_count = sum(1 for code, _ in results if code == 200)
avg_time = sum(time for _, time in results if time > 0) / len(results)

print(f"Success rate: {success_count}/100")
print(f"Average response time: {avg_time:.3f}s")
```

---

*This guide ensures your FlowStudio deployment workflow is working correctly end-to-end.*