/**
 * Ollama API Service
 * Handles communication with Ollama servers for model discovery and management
 */

import axios from 'axios';

export interface OllamaModel {
  name: string;
  model: string;
  modified_at: string;
  size: number;
  digest: string;
  details: {
    parent_model?: string;
    format?: string;
    family?: string;
    families?: string[];
    parameter_size?: string;
    quantization_level?: string;
  };
}

export interface OllamaModelsResponse {
  models: OllamaModel[];
}

export interface OllamaServerInfo {
  host: string;
  port: number;
  status: 'connected' | 'disconnected' | 'error';
  version?: string;
  models?: OllamaModel[];
}

export class OllamaService {
  private static createClient(host: string, port: number) {
    const baseURL = `http://${host}:${port}`;
    return axios.create({
      baseURL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  /**
   * Test connection to Ollama server
   */
  static async testConnection(host: string, port: number): Promise<boolean> {
    try {
      const client = this.createClient(host, port);
      const response = await client.get('/api/tags');
      return response.status === 200;
    } catch (error) {
      console.error('Ollama connection test failed:', error);
      return false;
    }
  }

  /**
   * Get server version and info
   */
  static async getServerInfo(host: string, port: number): Promise<string | null> {
    try {
      const client = this.createClient(host, port);
      const response = await client.get('/api/version');
      return response.data?.version || 'Unknown';
    } catch (error) {
      console.error('Failed to get Ollama server info:', error);
      return null;
    }
  }

  /**
   * Get list of available models from Ollama server
   */
  static async getModels(host: string, port: number): Promise<OllamaModel[]> {
    try {
      const client = this.createClient(host, port);
      const response = await client.get<OllamaModelsResponse>('/api/tags');
      
      if (response.data && Array.isArray(response.data.models)) {
        return response.data.models.sort((a, b) => a.name.localeCompare(b.name));
      }
      
      return [];
    } catch (error: any) {
      console.error('Failed to fetch Ollama models:', error);
      throw new Error(
        error.response?.status === 404 
          ? 'Ollama server not found. Please check host and port.'
          : error.response?.status === 0
          ? 'Cannot connect to Ollama server. Please check if the server is running.'
          : `Failed to fetch models: ${error?.message || 'Unknown error'}`
      );
    }
  }

  /**
   * Get complete server information including models
   */
  static async getCompleteServerInfo(host: string, port: number): Promise<OllamaServerInfo> {
    const serverInfo: OllamaServerInfo = {
      host,
      port,
      status: 'disconnected'
    };

    try {
      // Test connection first
      const isConnected = await this.testConnection(host, port);
      
      if (!isConnected) {
        serverInfo.status = 'error';
        return serverInfo;
      }

      serverInfo.status = 'connected';

      // Get version info
      const version = await this.getServerInfo(host, port);
      if (version) {
        serverInfo.version = version;
      }

      // Get models
      const models = await this.getModels(host, port);
      serverInfo.models = models;

      return serverInfo;
    } catch (error) {
      console.error('Failed to get complete server info:', error);
      serverInfo.status = 'error';
      return serverInfo;
    }
  }

  /**
   * Format model name for display
   */
  static formatModelName(model: OllamaModel): string {
    const sizeFormatted = this.formatBytes(model.size);
    const family = model.details?.family || '';
    const paramSize = model.details?.parameter_size || '';
    
    let displayName = model.name;
    
    if (paramSize) {
      displayName += ` (${paramSize})`;
    } else if (family) {
      displayName += ` (${family})`;
    }
    
    displayName += ` - ${sizeFormatted}`;
    
    return displayName;
  }

  /**
   * Format bytes to human readable string
   */
  private static formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  /**
   * Get default host and port from environment or fallback values
   */
  static getDefaultConnection(): { host: string; port: number } {
    return {
      host: import.meta.env.VITE_OLLAMA_HOST || 'localhost',
      port: parseInt(import.meta.env.VITE_OLLAMA_PORT || '11434', 10)
    };
  }

  /**
   * Check if a specific model exists on the server
   */
  static async modelExists(host: string, port: number, modelName: string): Promise<boolean> {
    try {
      const models = await this.getModels(host, port);
      return models.some(model => model.name === modelName);
    } catch (error) {
      console.error('Failed to check model existence:', error);
      return false;
    }
  }

  /**
   * Validate a saved model against current server models
   */
  static async validateSavedModel(
    host: string, 
    port: number, 
    savedModelName: string
  ): Promise<{ isValid: boolean; availableModels?: OllamaModel[]; error?: string }> {
    if (!savedModelName || savedModelName.trim() === '') {
      return { isValid: true }; // Empty model is considered valid (no validation needed)
    }

    try {
      const models = await this.getModels(host, port);
      const modelExists = models.some(model => model.name === savedModelName);
      
      return {
        isValid: modelExists,
        availableModels: models,
        error: modelExists ? undefined : `Model "${savedModelName}" not found on server`
      };
    } catch (error: any) {
      return {
        isValid: false,
        error: `Cannot connect to Ollama server: ${error?.message || 'Unknown error'}`
      };
    }
  }

  /**
   * Validate host and port inputs
   */
  static validateConnection(host: string, port: string | number): { isValid: boolean; error?: string } {
    if (!host || host.trim() === '') {
      return { isValid: false, error: 'Host is required' };
    }

    const portNum = typeof port === 'string' ? parseInt(port, 10) : port;
    
    if (isNaN(portNum) || portNum <= 0 || portNum > 65535) {
      return { isValid: false, error: 'Port must be a valid number between 1 and 65535' };
    }

    // Basic host validation (could be IP or hostname)
    const hostPattern = /^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$/;
    if (!hostPattern.test(host.trim())) {
      return { isValid: false, error: 'Invalid host format' };
    }

    return { isValid: true };
  }
}

export default OllamaService;