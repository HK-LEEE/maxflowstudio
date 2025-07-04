# FlowStudio API Deployment Usage Guide

## Overview

When you deploy a flow in FlowStudio, it becomes accessible as a REST API endpoint. This guide explains how to use your deployed APIs.

## Endpoint Format

All deployed APIs follow this URL pattern:
```
http://localhost:8005/api/deployed{endpoint_path}
```

For example, if your deployment has endpoint_path `/flow-123-v1`, the full URL would be:
```
http://localhost:8005/api/deployed/flow-123-v1
```

## Authentication

### Required Authentication (Default)
Most deployments require authentication by default. You need to include a JWT token in the Authorization header:

```bash
curl -X POST http://localhost:8005/api/deployed/flow-123-v1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_field": "value"}'
```

### Getting a JWT Token
1. Login to FlowStudio at http://localhost:3005
2. Open browser DevTools (F12)
3. Go to Application/Storage → Local Storage
4. Copy the `accessToken` value

### Public APIs
If a deployment is marked as public (`is_public: true`), no authentication is required.

## Making API Requests

### Request Format
- **Method**: POST
- **Content-Type**: application/json
- **Body**: JSON object with your input data

### Example Request with cURL
```bash
curl -X POST http://localhost:8005/api/deployed/flow-123-v1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Hello from API"
  }'
```

### Example Request with Python
```python
import requests

url = "http://localhost:8005/api/deployed/flow-123-v1"
headers = {
    "Authorization": "Bearer YOUR_JWT_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Hello from API"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

### Example Request with JavaScript/Node.js
```javascript
const axios = require('axios');

const url = 'http://localhost:8005/api/deployed/flow-123-v1';
const headers = {
    'Authorization': 'Bearer YOUR_JWT_TOKEN',
    'Content-Type': 'application/json'
};
const data = {
    name: 'John Doe',
    email: 'john@example.com',
    message: 'Hello from API'
};

axios.post(url, data, { headers })
    .then(response => console.log(response.data))
    .catch(error => console.error(error));
```

## Input/Output Schema

### Understanding Input Requirements
Each deployment has an input schema that defines:
- Required fields
- Field types (string, number, boolean, array, object)
- Field descriptions

The input schema is automatically generated from your flow's input nodes.

### Example Input Schema
```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "User's full name"
    },
    "age": {
      "type": "number",
      "description": "User's age"
    },
    "subscribe": {
      "type": "boolean",
      "description": "Newsletter subscription"
    }
  },
  "required": ["name"]
}
```

### Output Format
The API returns a JSON object with the flow execution results:
```json
{
  "status": "success",
  "data": {
    "output_field_1": "processed value",
    "output_field_2": 42
  },
  "execution_time": 1234
}
```

## Rate Limiting

If rate limiting is enabled for your deployment:
- Default limit: 1000 requests per minute
- Exceeding the limit returns: `429 Too Many Requests`
- Rate limits are per IP address

## Error Handling

### Common Error Responses

#### 401 Unauthorized
```json
{
  "detail": "Authentication required"
}
```
**Solution**: Include a valid JWT token in the Authorization header

#### 404 Not Found
```json
{
  "detail": "API endpoint not found"
}
```
**Solution**: Check the endpoint URL is correct

#### 400 Bad Request
```json
{
  "detail": "Invalid input: Required field 'name' is missing"
}
```
**Solution**: Ensure your request body matches the input schema

#### 503 Service Unavailable
```json
{
  "detail": "API endpoint is not active"
}
```
**Solution**: The deployment may be inactive. Contact admin to activate it.

#### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded"
}
```
**Solution**: Wait before making more requests

## Monitoring and Statistics

### Viewing API Usage
1. Go to API Deployments page
2. Find your deployment
3. Click the settings icon to view statistics:
   - Total requests
   - Last request time
   - Average response time

### Checking Deployment Status
Deployments can have these statuses:
- **Pending**: Awaiting admin approval
- **Active**: Ready to receive requests
- **Inactive**: Temporarily disabled
- **Failed**: Deployment error occurred

## Best Practices

1. **Test First**: Always test your flow in the designer before deploying
2. **Version Control**: Use meaningful version names when publishing
3. **Documentation**: Add descriptions to your input/output nodes
4. **Error Handling**: Design your flows to handle edge cases
5. **Security**: Never include sensitive data in public deployments
6. **Rate Limits**: Set appropriate rate limits to prevent abuse

## Troubleshooting

### API Not Responding
1. Check deployment status is "Active"
2. Verify the endpoint URL is correct
3. Ensure authentication token is valid
4. Check if rate limit is exceeded

### Unexpected Results
1. Test the flow in the designer first
2. Verify input data format matches schema
3. Check flow logs for execution errors

### Authentication Issues
1. Ensure token hasn't expired
2. Try logging in again to get a fresh token
3. Verify the deployment requires authentication

## Advanced Usage

### Webhook Integration
Deployed APIs can be used as webhooks for external services:
```javascript
// Example: GitHub webhook
{
  "url": "http://your-domain.com/api/deployed/github-webhook",
  "content_type": "json",
  "secret": "your-webhook-secret"
}
```

### Batch Processing
For processing multiple items:
```json
{
  "items": [
    {"id": 1, "data": "..."},
    {"id": 2, "data": "..."},
    {"id": 3, "data": "..."}
  ]
}
```

### Async Operations
Long-running flows return immediately with a job ID:
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "check_url": "/api/jobs/123e4567-e89b-12d3-a456-426614174000"
}
```

## Support

For issues or questions:
1. Check the flow execution logs
2. Review the deployment configuration
3. Contact your FlowStudio administrator

---

*Last updated: 2025-01-01*