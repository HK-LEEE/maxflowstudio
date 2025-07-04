/**
 * Node Handle Definitions
 * Defines input/output handles for each node type
 */

export interface HandleDefinition {
  id: string;
  type: 'input' | 'output';
  label: string;
  dataType?: 'string' | 'number' | 'boolean' | 'object' | 'array' | 'any';
  required?: boolean;
}

export interface NodeHandleConfig {
  inputs?: HandleDefinition[];
  outputs?: HandleDefinition[];
}

// Define handles for each node type
export const nodeHandles: Record<string, NodeHandleConfig> = {
  // Flow I/O nodes
  input: {
    outputs: [
      { id: 'output', type: 'output', label: 'Flow Output', dataType: 'any' }
    ]
  },
  
  output: {
    inputs: [
      { id: 'input', type: 'input', label: 'Flow Input', dataType: 'any', required: true }
    ]
  },
  
  transform: {
    inputs: [
      { id: 'input', type: 'input', label: 'Data', dataType: 'any', required: true }
    ],
    outputs: [
      { id: 'output', type: 'output', label: 'Transformed', dataType: 'any' }
    ]
  },
  
  condition: {
    inputs: [
      { id: 'input', type: 'input', label: 'Value', dataType: 'any', required: true }
    ],
    outputs: [
      { id: 'true', type: 'output', label: 'True', dataType: 'any' },
      { id: 'false', type: 'output', label: 'False', dataType: 'any' }
    ]
  },
  
  api: {
    inputs: [
      { id: 'body', type: 'input', label: 'Request Body', dataType: 'any' },
      { id: 'params', type: 'input', label: 'Query Params', dataType: 'object' }
    ],
    outputs: [
      { id: 'response', type: 'output', label: 'Response', dataType: 'any' },
      { id: 'status', type: 'output', label: 'Status', dataType: 'number' },
      { id: 'error', type: 'output', label: 'Error', dataType: 'string' }
    ]
  },
  
  database: {
    inputs: [
      { id: 'params', type: 'input', label: 'Parameters', dataType: 'object' }
    ],
    outputs: [
      { id: 'result', type: 'output', label: 'Result', dataType: 'array' },
      { id: 'count', type: 'output', label: 'Count', dataType: 'number' },
      { id: 'error', type: 'output', label: 'Error', dataType: 'string' }
    ]
  },
  
  openai: {
    inputs: [
      { id: 'prompt', type: 'input', label: 'Prompt', dataType: 'string', required: true },
      { id: 'context', type: 'input', label: 'Context', dataType: 'string' }
    ],
    outputs: [
      { id: 'response', type: 'output', label: 'Response', dataType: 'string' },
      { id: 'tokens', type: 'output', label: 'Tokens Used', dataType: 'number' },
      { id: 'error', type: 'output', label: 'Error', dataType: 'string' }
    ]
  },
  
  anthropic: {
    inputs: [
      { id: 'prompt', type: 'input', label: 'Prompt', dataType: 'string', required: true },
      { id: 'context', type: 'input', label: 'Context', dataType: 'string' }
    ],
    outputs: [
      { id: 'response', type: 'output', label: 'Response', dataType: 'string' },
      { id: 'tokens', type: 'output', label: 'Tokens Used', dataType: 'number' },
      { id: 'error', type: 'output', label: 'Error', dataType: 'string' }
    ]
  },
  
  function: {
    inputs: [
      { id: 'data', type: 'input', label: 'Input Data', dataType: 'any', required: true },
      { id: 'params', type: 'input', label: 'Parameters', dataType: 'object' }
    ],
    outputs: [
      { id: 'result', type: 'output', label: 'Result', dataType: 'any' },
      { id: 'error', type: 'output', label: 'Error', dataType: 'string' }
    ]
  },
  
  ollama: {
    inputs: [
      { id: 'message', type: 'input', label: 'Message', dataType: 'string', required: true },
      { id: 'system_message', type: 'input', label: 'System Message', dataType: 'string' }
    ],
    outputs: [
      { id: 'response', type: 'output', label: 'Response', dataType: 'string' },
      { id: 'model', type: 'output', label: 'Model Used', dataType: 'string' },
      { id: 'tokens', type: 'output', label: 'Tokens', dataType: 'number' },
      { id: 'error', type: 'output', label: 'Error', dataType: 'string' }
    ]
  },
  
  template: {
    inputs: [
      { id: 'template', type: 'input', label: 'Template', dataType: 'string', required: true },
      { id: 'var_1', type: 'input', label: 'Variable1', dataType: 'any' },
      { id: 'var_2', type: 'input', label: 'Variable2', dataType: 'any' },
      { id: 'var_3', type: 'input', label: 'Variable3', dataType: 'any' },
      { id: 'var_4', type: 'input', label: 'Variable4', dataType: 'any' },
      { id: 'var_5', type: 'input', label: 'Variable5', dataType: 'any' }
    ],
    outputs: [
      { id: 'output', type: 'output', label: 'Formatted Text', dataType: 'string' },
      { id: 'used_variables', type: 'output', label: 'Used Variables', dataType: 'array' }
    ]
  }
};

// Helper function to get handles for a node type
export const getNodeHandles = (nodeType: string): NodeHandleConfig => {
  return nodeHandles[nodeType] || {
    inputs: [{ id: 'input', type: 'input', label: 'Input', dataType: 'any' }],
    outputs: [{ id: 'output', type: 'output', label: 'Output', dataType: 'any' }]
  };
};