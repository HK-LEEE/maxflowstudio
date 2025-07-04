import React from 'react';
import { Modal, Typography, Divider, Alert, Button } from 'antd';
import { CopyOutlined } from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

interface DocumentationViewerProps {
  visible: boolean;
  onClose: () => void;
}

export const DocumentationViewer: React.FC<DocumentationViewerProps> = ({
  visible,
  onClose,
}) => {
  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
  };

  const curlExample = `curl -X POST http://localhost:8005/api/deployed/your-endpoint \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "field1": "value1",
    "field2": "value2"
  }'`;

  const pythonExample = `import requests

url = "http://localhost:8005/api/deployed/your-endpoint"
headers = {
    "Authorization": "Bearer YOUR_JWT_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "field1": "value1",
    "field2": "value2"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())`;

  return (
    <Modal
      title="API Deployment Usage Guide"
      open={visible}
      onCancel={onClose}
      width={800}
      footer={null}
    >
      <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
        <Alert
          message="FlowStudio API Deployment Guide"
          description="Learn how to use your deployed flow APIs with authentication, examples, and best practices."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Title level={3}>Endpoint Format</Title>
        <Paragraph>
          All deployed APIs follow this URL pattern:
        </Paragraph>
        <Text code>http://localhost:8005/api/deployed{'{endpoint_path}'}</Text>

        <Divider />

        <Title level={3}>Authentication</Title>
        <Paragraph>
          Most deployments require JWT authentication. To get your token:
        </Paragraph>
        <ol>
          <li>Login to FlowStudio at <Text code>http://localhost:3005</Text></li>
          <li>Open browser DevTools (F12)</li>
          <li>Go to Application/Storage → Local Storage</li>
          <li>Copy the <Text code>accessToken</Text> value</li>
        </ol>

        <Divider />

        <Title level={3}>Request Format</Title>
        <ul>
          <li><strong>Method:</strong> POST</li>
          <li><strong>Content-Type:</strong> application/json</li>
          <li><strong>Body:</strong> JSON object with your input data</li>
        </ul>

        <Divider />

        <Title level={3}>cURL Example</Title>
        <div style={{ position: 'relative' }}>
          <pre style={{
            background: '#f6f8fa',
            padding: '16px',
            border: '1px solid #e1e4e8',
            borderRadius: '6px',
            overflow: 'auto'
          }}>
            {curlExample}
          </pre>
          <Button
            type="text"
            icon={<CopyOutlined />}
            onClick={() => handleCopyCode(curlExample)}
            style={{ position: 'absolute', top: 8, right: 8 }}
          />
        </div>

        <Divider />

        <Title level={3}>Python Example</Title>
        <div style={{ position: 'relative' }}>
          <pre style={{
            background: '#f6f8fa',
            padding: '16px',
            border: '1px solid #e1e4e8',
            borderRadius: '6px',
            overflow: 'auto'
          }}>
            {pythonExample}
          </pre>
          <Button
            type="text"
            icon={<CopyOutlined />}
            onClick={() => handleCopyCode(pythonExample)}
            style={{ position: 'absolute', top: 8, right: 8 }}
          />
        </div>

        <Divider />

        <Title level={3}>Common Error Responses</Title>
        <ul>
          <li><strong>401 Unauthorized:</strong> Invalid or missing JWT token</li>
          <li><strong>404 Not Found:</strong> API endpoint not found</li>
          <li><strong>400 Bad Request:</strong> Invalid input data</li>
          <li><strong>503 Service Unavailable:</strong> Deployment is inactive</li>
          <li><strong>429 Too Many Requests:</strong> Rate limit exceeded</li>
        </ul>

        <Divider />

        <Title level={3}>Tips</Title>
        <ul>
          <li>Use the "How to Use" button (?) next to each deployment for specific examples</li>
          <li>Test your flow in the designer before deploying</li>
          <li>Check deployment status is "Active" before making requests</li>
          <li>Review input/output schemas for data format requirements</li>
        </ul>

        <Alert
          message="Need Help?"
          description="Click the question mark (?) button next to any deployment for specific usage examples with your endpoint URL and authentication requirements."
          type="success"
          showIcon
          style={{ marginTop: 16 }}
        />
      </div>
    </Modal>
  );
};