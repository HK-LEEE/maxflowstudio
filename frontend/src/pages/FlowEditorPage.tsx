/**
 * Flow Editor Page Component
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { App } from 'antd';
import { FlowDesigner } from '../components/FlowDesigner/FlowDesigner';
import { api } from '../services/api';
import { apiClient } from '../services/api';

export const FlowEditorPage: React.FC = () => {
  const { message } = App.useApp();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [flowName, setFlowName] = useState<string>('');
  const [flowDefinition, setFlowDefinition] = useState<any>(null);

  // Get workspace from URL params for new flows
  const workspaceId = searchParams.get('workspace');

  useEffect(() => {
    if (id && id !== 'new') {
      loadFlow(id);
    }
  }, [id]);

  const loadFlow = async (flowId: string) => {
    setLoading(true);
    try {
      // Try API first, fallback to localStorage
      try {
        const response = await api.flows.get(flowId);
        setFlowName(response.data.name || 'Untitled Flow');
        setFlowDefinition(response.data.definition || null);
      } catch (apiError) {
        // Check localStorage for local flows
        console.warn('API unavailable, checking localStorage:', apiError);
        const localFlowData = localStorage.getItem(`flow_${flowId}`);
        if (localFlowData) {
          const flowData = JSON.parse(localFlowData);
          setFlowName(flowData.name || 'Untitled Flow');
          setFlowDefinition(flowData.definition || null);
          message.info('Flow loaded from local storage (backend unavailable)');
        } else {
          throw new Error('Flow not found in local storage');
        }
      }
    } catch (error) {
      message.error('Failed to load flow');
      console.error('Load flow error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateFlowName = async (newName: string) => {
    if (id && id !== 'new') {
      try {
        await api.flows.update(id, { name: newName });
        setFlowName(newName);
        message.success('Flow name updated successfully!');
      } catch (error) {
        message.error('Failed to update flow name');
        console.error('Update flow name error:', error);
      }
    } else {
      setFlowName(newName);
    }
  };

  const handleSave = async (flowDesignData: any) => {
    setLoading(true);
    try {
      if (id && id !== 'new') {
        // Try API first, fallback to localStorage if backend unavailable
        try {
          const response = await apiClient.post(`/api/flows/${id}/versions`, {
            definition: flowDesignData,
            change_summary: 'Updated flow definition via editor'
          });
          message.success(`Flow saved as version ${response.data.version_number}!`);
        } catch (apiError) {
          // Fallback to localStorage
          console.warn('API unavailable, saving to localStorage:', apiError);
          const existingFlow = localStorage.getItem(`flow_${id}`);
          if (existingFlow) {
            const flowData = JSON.parse(existingFlow);
            flowData.definition = flowDesignData;
            flowData.updated_at = new Date().toISOString();
            localStorage.setItem(`flow_${id}`, JSON.stringify(flowData));
            message.success('Flow saved locally (backend unavailable)');
          }
        }
      } else {
        // Try API first, fallback to localStorage for new flows
        try {
          const response = await api.flows.create({
            name: flowName || `New Flow ${Date.now()}`,
            description: 'Created from Flow Editor',
            definition: flowDesignData,
            workspace_id: workspaceId,
          });
          message.success('Flow created successfully!');
          setFlowName(response.data.name);
          navigate(`/flows/${response.data.id}`);
        } catch (apiError) {
          // Fallback to localStorage for new flows
          console.warn('API unavailable, saving to localStorage:', apiError);
          const newId = `local_${Date.now()}`;
          const flowData = {
            id: newId,
            name: flowName || `New Flow ${Date.now()}`,
            description: 'Created from Flow Editor (Local)',
            definition: flowDesignData,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            workspace_id: workspaceId,
          };
          localStorage.setItem(`flow_${newId}`, JSON.stringify(flowData));
          
          // Save flow ID to list of local flows
          const localFlows = JSON.parse(localStorage.getItem('local_flows') || '[]');
          localFlows.push(newId);
          localStorage.setItem('local_flows', JSON.stringify(localFlows));
          
          message.success('Flow created locally (backend unavailable)');
          setFlowName(flowData.name);
          navigate(`/flows/${newId}`);
        }
      }
    } catch (error) {
      message.error('Failed to save flow');
      console.error('Save flow error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async () => {
    setLoading(true);
    try {
      if (!id || id === 'new') {
        message.warning('Please save the flow before running');
        return;
      }

      const response = await api.executions.start(id, {});
      message.success('Flow execution started!');
      console.log('Execution started:', response.data);
      
      // Navigate to executions page to see the result
      navigate('/executions');
    } catch (error) {
      message.error('Failed to run flow');
      console.error('Run flow error:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div>Loading...</div>
      </div>
    );
  }

  return (
    <div className="h-full">
      <FlowDesigner
        flowId={id}
        flowName={flowName}
        flowDefinition={flowDefinition}
        onSave={handleSave}
        onRun={handleRun}
        onUpdateFlowName={handleUpdateFlowName}
      />
    </div>
  );
};