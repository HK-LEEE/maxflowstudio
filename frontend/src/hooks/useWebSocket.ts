/**
 * WebSocket Hook for Flow Testing
 * Manages WebSocket connection and message handling for interactive flow testing
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { ensureValidToken } from '../utils/auth';

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  isConnecting: boolean;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: WebSocketMessage) => void;
  connect: () => void;
  disconnect: () => void;
  connectionError: string | null;
}

export const useWebSocket = (options: UseWebSocketOptions): UseWebSocketReturn => {
  const {
    url,
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    reconnectAttempts = 3,
    reconnectInterval = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [connectionError, setConnectionError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(async () => {
    // Enhanced state checking to prevent multiple connections
    if (wsRef.current?.readyState === WebSocket.OPEN || 
        wsRef.current?.readyState === WebSocket.CONNECTING || 
        isConnecting) {
      return;
    }

    setIsConnecting(true);
    setConnectionError(null);

    try {
      // Get or ensure valid token
      const token = await ensureValidToken();
      
      if (!token) {
        throw new Error('No valid token available');
      }
      
      const wsUrl = `${url}?token=${encodeURIComponent(token)}`;
      console.log('🔗 Connecting to WebSocket with URL:', wsUrl);
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setIsConnecting(false);
        setConnectionError(null);
        reconnectCountRef.current = 0;
        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          setLastMessage(message);
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        setIsConnecting(false);
        
        if (event.code !== 1000) { // Not normal closure
          setConnectionError(`Connection closed: ${event.reason || 'Unknown reason'}`);
          
          // Attempt to reconnect
          if (reconnectCountRef.current < reconnectAttempts) {
            reconnectCountRef.current++;
            reconnectTimeoutRef.current = setTimeout(async () => {
              await connect();
            }, reconnectInterval);
          }
        }
        
        onDisconnect?.();
      };

      ws.onerror = (error) => {
        setConnectionError('WebSocket connection failed');
        setIsConnecting(false);
        onError?.(error);
      };

    } catch (error) {
      setIsConnecting(false);
      setConnectionError('Failed to create WebSocket connection');
    }
  }, [url, onMessage, onConnect, onDisconnect, onError, reconnectAttempts, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }
    
    setIsConnected(false);
    setIsConnecting(false);
    reconnectCountRef.current = 0;
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Cannot send message:', message);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    isConnecting,
    lastMessage,
    sendMessage,
    connect,
    disconnect,
    connectionError,
  };
};