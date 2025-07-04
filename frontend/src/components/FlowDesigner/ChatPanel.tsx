/**
 * Chat Panel Component for Flow Testing
 * Provides interactive chat interface for flow testing with real-time updates
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Drawer,
  Input,
  Button,
  List,
  Typography,
  Space,
  Tag,
  Avatar,
  Spin,
  Alert,
  Divider,
  Card,
  Badge,
} from 'antd';
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import { useWebSocket } from '../../hooks/useWebSocket';
import { MessageRenderer } from './MessageRenderer';

const { TextArea } = Input;
const { Text, Title } = Typography;

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface ChatMessage {
  id: string;
  type: 'user' | 'system' | 'node_output' | 'node_start' | 'node_complete' | 'node_error' | 'input_required' | 'streaming_update';
  content: string;
  timestamp: string;
  nodeId?: string;
  nodeLabel?: string;
  data?: any;
  isStreaming?: boolean;
  accumulated?: string;
}

interface ChatPanelProps {
  visible: boolean;
  onClose: () => void;
  flowId: string;
  flowName: string;
  onNodeExecutionUpdate?: (nodeId: string, status: 'executing' | 'completed' | 'error' | 'reset') => void;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  visible,
  onClose,
  flowId,
  flowName,
  onNodeExecutionUpdate,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isFlowRunning, setIsFlowRunning] = useState(false);
  const [pendingInputs, setPendingInputs] = useState<Map<string, any>>(new Map());
  const [streamingMessages, setStreamingMessages] = useState<Map<string, string>>(new Map());
  const [streamingTimeouts, setStreamingTimeouts] = useState<Map<string, NodeJS.Timeout>>(new Map());
  const [lastStreamingActivity, setLastStreamingActivity] = useState<Map<string, number>>(new Map());
  const streamingTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Environment-based WebSocket URL
  const getWebSocketUrl = () => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = import.meta.env.VITE_WS_HOST || 'localhost:8005';
    return `${wsProtocol}//${wsHost}/ws/flow-test/${flowId}`;
  };
  
  const wsUrl = getWebSocketUrl();
  
  console.log('Attempting WebSocket connection to:', wsUrl);

  // Streaming timeout configuration
  const STREAMING_TIMEOUT = 30000; // 30 seconds timeout
  const STREAMING_HEARTBEAT_INTERVAL = 5000; // Check every 5 seconds

  // Handle streaming timeout
  const handleStreamingTimeout = useCallback((nodeId: string) => {
    setMessages(prev => prev.map(msg => {
      if (msg.nodeId === nodeId && msg.isStreaming) {
        return {
          ...msg,
          isStreaming: false,
          content: msg.content + '\n\n⚠️ Streaming timed out. Response may be incomplete.',
          type: 'node_error' as const
        };
      }
      return msg;
    }));
    
    // Clean up streaming state
    setStreamingMessages(prev => {
      const newMap = new Map(prev);
      newMap.delete(nodeId);
      return newMap;
    });
    
    setLastStreamingActivity(prev => {
      const newMap = new Map(prev);
      newMap.delete(nodeId);
      return newMap;
    });
  }, []);

  // Setup streaming timeout for a node
  const setupStreamingTimeout = useCallback((nodeId: string) => {
    // Clear existing timeout
    const existingTimeout = streamingTimeoutsRef.current.get(nodeId);
    if (existingTimeout) {
      clearTimeout(existingTimeout);
    }

    // Set new timeout
    const timeout = setTimeout(() => {
      handleStreamingTimeout(nodeId);
    }, STREAMING_TIMEOUT);

    streamingTimeoutsRef.current.set(nodeId, timeout);
    setStreamingTimeouts(prev => new Map(prev.set(nodeId, timeout)));
    setLastStreamingActivity(prev => new Map(prev.set(nodeId, Date.now())));
  }, [handleStreamingTimeout]);

  // Clear streaming timeout for a node
  const clearStreamingTimeout = useCallback((nodeId: string) => {
    const timeout = streamingTimeoutsRef.current.get(nodeId);
    if (timeout) {
      clearTimeout(timeout);
      streamingTimeoutsRef.current.delete(nodeId);
      setStreamingTimeouts(prev => {
        const newMap = new Map(prev);
        newMap.delete(nodeId);
        return newMap;
      });
    }
    
    setLastStreamingActivity(prev => {
      const newMap = new Map(prev);
      newMap.delete(nodeId);
      return newMap;
    });
  }, []);

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    const timestamp = new Date().toISOString();
    
    switch (message.type) {
      case 'connected':
        addMessage({
          id: `${Date.now()}`,
          type: 'system',
          content: `Connected to flow: ${message.flow_name}`,
          timestamp,
        });
        break;
        
      case 'session_started':
        setIsFlowRunning(true);
        // Reset all node states
        onNodeExecutionUpdate?.('all', 'reset');
        addMessage({
          id: `${Date.now()}`,
          type: 'system',
          content: 'Flow execution started',
          timestamp,
        });
        break;
        
      case 'flow_restarted':
        setIsFlowRunning(true);
        // Reset all node states for new execution
        onNodeExecutionUpdate?.('all', 'reset');
        addMessage({
          id: `${Date.now()}`,
          type: 'system',
          content: `Processing: ${message.message}`,
          timestamp,
        });
        break;
        
      case 'node_start':
        onNodeExecutionUpdate?.(message.node_id, 'executing');
        addMessage({
          id: `${Date.now()}`,
          type: 'node_start',
          content: `Started: ${message.node_label || message.node_id}`,
          timestamp,
          nodeId: message.node_id,
          nodeLabel: message.node_label,
        });
        break;
        
      case 'node_complete':
        onNodeExecutionUpdate?.(message.node_id, 'completed');
        addMessage({
          id: `${Date.now()}`,
          type: 'node_complete',
          content: `Completed: ${message.node_label || message.node_id}`,
          timestamp,
          nodeId: message.node_id,
          data: message.result,
        });
        break;
        
      case 'node_error':
        onNodeExecutionUpdate?.(message.node_id, 'error');
        addMessage({
          id: `${Date.now()}`,
          type: 'node_error',
          content: `Error in ${message.node_id}: ${message.error}`,
          timestamp,
          nodeId: message.node_id,
        });
        break;
        
      case 'node_output':
        // Check if this is a flow output node to display as final response
        const isFlowOutput = message.node_type === 'output' || message.node_id?.includes('output');
        
        addMessage({
          id: `${Date.now()}`,
          type: isFlowOutput ? 'system' : 'node_output',
          content: isFlowOutput ? 
            (typeof message.output === 'string' ? message.output : formatNodeOutput(message.output)) :
            formatNodeOutput(message.output),
          timestamp,
          nodeId: message.node_id,
          data: message.output,
        });
        break;
        
      case 'flow_complete':
        setIsFlowRunning(false);
        addMessage({
          id: `${Date.now()}`,
          type: 'system',
          content: message.output || 'Flow execution completed',
          timestamp,
          data: message.result,
        });
        break;
        
      case 'input_required':
        setPendingInputs(prev => new Map(prev.set(message.node_id, message.input_schema)));
        addMessage({
          id: `${Date.now()}`,
          type: 'input_required',
          content: `Input needed for: ${message.node_id}`,
          timestamp,
          nodeId: message.node_id,
          data: message.input_schema,
        });
        break;
        
      case 'streaming_update':
        // Handle real-time streaming updates
        const nodeKey = message.node_id;
        const currentStreaming = streamingMessages.get(nodeKey) || '';
        const newAccumulated = message.accumulated || currentStreaming + (message.delta || '');
        
        // Update streaming activity timestamp
        setLastStreamingActivity(prev => new Map(prev.set(nodeKey, Date.now())));
        
        // Setup or refresh timeout for this streaming node
        if (!message.is_complete) {
          setupStreamingTimeout(nodeKey);
        }
        
        setStreamingMessages(prev => new Map(prev.set(nodeKey, newAccumulated)));
        
        // Update or create streaming message
        setMessages(prev => {
          const existingIndex = prev.findIndex(msg => 
            msg.nodeId === nodeKey && (msg.isStreaming || msg.type === 'streaming_update')
          );
          
          const streamingMessage: ChatMessage = {
            id: existingIndex >= 0 ? prev[existingIndex].id : `stream-${nodeKey}-${Date.now()}`,
            type: 'streaming_update',
            content: newAccumulated,
            timestamp,
            nodeId: nodeKey,
            nodeLabel: message.node_label,
            isStreaming: !message.is_complete,
            accumulated: newAccumulated,
          };
          
          if (existingIndex >= 0) {
            // Update existing streaming message
            const newMessages = [...prev];
            newMessages[existingIndex] = streamingMessage;
            
            // If streaming is complete, convert to regular node_output
            if (message.is_complete) {
              streamingMessage.type = 'node_output';
              streamingMessage.isStreaming = false;
              clearStreamingTimeout(nodeKey);
              setStreamingMessages(prev => {
                const newMap = new Map(prev);
                newMap.delete(nodeKey);
                return newMap;
              });
            }
            
            return newMessages;
          } else {
            // Add new streaming message
            return [...prev, streamingMessage];
          }
        });
        break;
        
      case 'error':
        addMessage({
          id: `${Date.now()}`,
          type: 'system',
          content: `Error: ${message.message}`,
          timestamp,
        });
        setIsFlowRunning(false);
        break;
    }
  };

  const {
    isConnected,
    isConnecting,
    sendMessage,
    connect,
    disconnect,
    connectionError,
  } = useWebSocket({
    url: wsUrl,
    onMessage: handleWebSocketMessage,
    onConnect: () => {
      console.log('✅ Connected to flow test WebSocket');
      addMessage({
        id: `${Date.now()}`,
        type: 'system',
        content: 'Connected to flow test session',
        timestamp: new Date().toISOString(),
      });
    },
    onDisconnect: () => {
      console.log('❌ Disconnected from flow test WebSocket');
      setIsFlowRunning(false);
    },
    onError: (error) => {
      console.error('🔴 WebSocket error:', error);
    },
  });

  const addMessage = (message: ChatMessage) => {
    setMessages(prev => [...prev, message]);
  };

  const formatNodeOutput = (output: any): string => {
    if (typeof output === 'string') {
      return output;
    }
    return JSON.stringify(output, null, 2);
  };

  const handleSendMessage = () => {
    if (!inputValue.trim() || !isConnected) return;

    // Add user message to chat
    addMessage({
      id: `${Date.now()}`,
      type: 'user',
      content: inputValue,
      timestamp: new Date().toISOString(),
    });

    // Check if there are pending inputs that need user response
    if (pendingInputs.size > 0) {
      // Handle pending input - send user_input message
      const [nodeId] = pendingInputs.keys();
      sendMessage({
        type: 'user_input',
        node_id: nodeId,
        input: { value: inputValue },
      });
      // Clear the pending input
      setPendingInputs(prev => {
        const newMap = new Map(prev);
        newMap.delete(nodeId);
        return newMap;
      });
    } else {
      // Send message as flow input - this will trigger flow execution with user input
      sendMessage({
        type: 'flow_input',
        message: inputValue,
        timestamp: new Date().toISOString(),
      });
    }

    setInputValue('');
  };

  const handleStopFlow = () => {
    sendMessage({ type: 'stop' });
    setIsFlowRunning(false);
    setPendingInputs(new Map());
    
    // Clear all streaming timeouts
    streamingTimeoutsRef.current.forEach((timeout) => {
      clearTimeout(timeout);
    });
    streamingTimeoutsRef.current.clear();
    setStreamingTimeouts(new Map());
    setStreamingMessages(new Map());
    setLastStreamingActivity(new Map());
  };

  const handleRetryConnection = () => {
    disconnect();
    setTimeout(async () => {
      await connect().catch(console.error);
    }, 1000);
  };

  const handleRetryStreaming = (nodeId: string) => {
    // Find the last user message and retry the flow
    const lastUserMessage = messages.findLast(msg => msg.type === 'user');
    if (lastUserMessage) {
      // Clear the failed streaming message
      setMessages(prev => prev.filter(msg => !(msg.nodeId === nodeId && msg.isStreaming)));
      clearStreamingTimeout(nodeId);
      
      // Restart the flow with the same input
      sendMessage({
        type: 'flow_input',
        message: lastUserMessage.content,
        timestamp: new Date().toISOString(),
      });
    }
  };

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'user':
        return <UserOutlined />;
      case 'system':
        return <RobotOutlined />;
      case 'node_start':
        return <PlayCircleOutlined style={{ color: '#1890ff' }} />;
      case 'node_complete':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'node_error':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'input_required':
        return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
      case 'node_output':
        return <RobotOutlined style={{ color: '#722ed1' }} />;
      case 'streaming_update':
        return <RobotOutlined style={{ color: '#722ed1' }} />;
      default:
        return <RobotOutlined />;
    }
  };

  const getMessageColor = (type: string) => {
    switch (type) {
      case 'user':
        return '#e6f7ff';
      case 'system':
        return '#f6ffed';
      case 'node_start':
        return '#e6f7ff';
      case 'node_complete':
        return '#f6ffed';
      case 'node_error':
        return '#fff2f0';
      case 'input_required':
        return '#fffbf0';
      case 'node_output':
        return '#f9f0ff';
      case 'streaming_update':
        return '#f9f0ff';
      default:
        return '#fafafa';
    }
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Connect when panel opens
  useEffect(() => {
    if (visible && !isConnected && !isConnecting) {
      connect().catch(console.error);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, isConnected, isConnecting]); // connect는 의존성에서 제외

  // Cleanup on close
  useEffect(() => {
    if (!visible) {
      disconnect();
      setMessages([]);
      setIsFlowRunning(false);
      setPendingInputs(new Map());
      setStreamingMessages(new Map());
      
      // Clear all streaming timeouts
      streamingTimeoutsRef.current.forEach((timeout) => {
        clearTimeout(timeout);
      });
      streamingTimeoutsRef.current.clear();
      setStreamingTimeouts(new Map());
      setLastStreamingActivity(new Map());
    }
  }, [visible, disconnect]); // streamingTimeouts 의존성 제거

  // Cleanup all timeouts on component unmount
  useEffect(() => {
    return () => {
      streamingTimeoutsRef.current.forEach((timeout) => {
        clearTimeout(timeout);
      });
      streamingTimeoutsRef.current.clear();
    };
  }, []); // 컴포넌트 언마운트 시에만 실행

  return (
    <Drawer
      title={
        <Space>
          <Title level={4} style={{ margin: 0 }}>
            Flow Test: {flowName}
          </Title>
          <Badge
            status={isConnected ? 'success' : 'error'}
            text={isConnected ? 'Connected' : 'Disconnected'}
          />
        </Space>
      }
      placement="right"
      width={400}
      open={visible}
      onClose={onClose}
      extra={
        <Space>
          {isFlowRunning && (
            <Button
              type="primary"
              danger
              size="small"
              icon={<StopOutlined />}
              onClick={handleStopFlow}
            >
              Stop
            </Button>
          )}
        </Space>
      }
    >
      <div className="h-full flex flex-col">
        {/* Connection Status */}
        {connectionError && (
          <Alert
            message="Connection Error"
            description={
              <div>
                <div>{connectionError}</div>
                <Button 
                  type="link" 
                  size="small" 
                  onClick={handleRetryConnection}
                  className="p-0 h-auto mt-1"
                >
                  Retry Connection
                </Button>
              </div>
            }
            type="error"
            closable
            style={{ marginBottom: 16 }}
          />
        )}

        {isConnecting && (
          <Card size="small" style={{ marginBottom: 16 }}>
            <Spin size="small" /> Connecting to flow test session...
          </Card>
        )}

        {/* Pending Inputs Alert */}
        {pendingInputs.size > 0 && (
          <Alert
            message="Input Required"
            description="The flow is waiting for your input. Type your message below."
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 250px)' }}>
          <List
            dataSource={messages}
            renderItem={(message) => (
              <List.Item style={{ padding: '8px 0' }}>
                <Card
                  size="small"
                  className={message.isStreaming ? 'streaming-pulse' : ''}
                  style={{
                    width: '100%',
                    backgroundColor: getMessageColor(message.type),
                    border: message.isStreaming ? '2px solid #1890ff' : '1px solid #f0f0f0',
                    borderRadius: '8px',
                  }}
                >
                  <div className="flex items-start space-x-2">
                    <Avatar size="small" icon={getMessageIcon(message.type)} />
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <Text strong className="text-xs">
                          {message.type === 'user' ? 'You' : 
                           message.nodeLabel || message.type.replace('_', ' ')}
                        </Text>
                        <Text type="secondary" className="text-xs">
                          {new Date(message.timestamp).toLocaleTimeString()}
                        </Text>
                      </div>
                      <div className="relative">
                        <MessageRenderer
                          content={message.content}
                          mode="auto"
                          showModeToggle={message.type === 'node_output' || message.type === 'system' || message.type === 'streaming_update'}
                          isStreaming={message.isStreaming}
                          className="text-sm"
                        />
                        {message.isStreaming && (
                          <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                            <div className="flex items-center">
                              <div className="flex space-x-1 mr-2">
                                <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                                <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                                <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                              </div>
                              <span className="text-blue-600 font-medium">Generating response...</span>
                            </div>
                            <Button
                              type="text"
                              size="small"
                              danger
                              icon={<StopOutlined />}
                              onClick={handleStopFlow}
                              className="text-xs"
                            >
                              Stop
                            </Button>
                          </div>
                        )}
                      </div>
                      {message.data && (
                        <div className="mt-2">
                          <Text code className="text-xs">
                            {JSON.stringify(message.data, null, 2)}
                          </Text>
                        </div>
                      )}
                      
                      {/* Retry button for failed streaming */}
                      {message.type === 'node_error' && message.nodeId && message.content.includes('timed out') && (
                        <div className="mt-2">
                          <Button
                            type="primary"
                            size="small"
                            onClick={() => handleRetryStreaming(message.nodeId!)}
                            className="text-xs"
                          >
                            Retry Streaming
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              </List.Item>
            )}
          />
          <div ref={messagesEndRef} />
        </div>

        <Divider style={{ margin: '12px 0' }} />

        {/* Input Area */}
        <div className="flex space-x-2">
          <TextArea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={
              pendingInputs.size > 0 
                ? "Enter input for the flow..." 
                : "Type a message..."
            }
            autoSize={{ minRows: 1, maxRows: 4 }}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            disabled={!isConnected}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSendMessage}
            disabled={!isConnected || !inputValue.trim()}
          >
            Send
          </Button>
        </div>
      </div>
    </Drawer>
  );
};