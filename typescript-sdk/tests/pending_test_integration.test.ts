import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Runtime, StateManager, BaseNode } from '../exospherehost/index.js';
import { z } from 'zod';

// Mock fetch globally
global.fetch = vi.fn();

// Helper function to create proper fetch mock responses
const createFetchMock = (data: any, status = 200, ok = true) => ({
  ok,
  status,
  json: () => Promise.resolve(data),
  text: () => Promise.resolve(typeof data === 'string' ? data : JSON.stringify(data))
});

class IntegrationTestNode extends BaseNode {
  static Inputs = z.object({
    user_id: z.string(),
    action: z.string()
  });

  static Outputs = z.object({
    status: z.string(),
    message: z.string()
  });

  static Secrets = z.object({
    api_key: z.string(),
    database_url: z.string()
  });

  async execute() {
    return {
      status: 'completed',
      message: `Processed ${this.inputs.action} for user ${this.inputs.user_id}`
    };
  }
}

class MultiOutputNode extends BaseNode {
  static Inputs = z.object({
    count: z.string()
  });

  static Outputs = z.object({
    result: z.string()
  });

  static Secrets = z.object({
    api_key: z.string()
  });

  async execute() {
    const count = parseInt(this.inputs.count);
    return Array.from({ length: count }, (_, i) => ({ result: `item_${i}` }));
  }
}

class ErrorProneNode extends BaseNode {
  static Inputs = z.object({
    should_fail: z.string()
  });

  static Outputs = z.object({
    result: z.string()
  });

  static Secrets = z.object({
    api_key: z.string()
  });

  async execute() {
    if (this.inputs.should_fail === 'true') {
      throw new Error('Integration test error');
    }
    return { result: 'success' };
  }
}

describe('TestRuntimeStateManagerIntegration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should register runtime with state manager', async () => {
    (global.fetch as any).mockResolvedValueOnce(createFetchMock({ status: 'registered' }));

    const runtime = new Runtime('test_namespace', 'test_runtime', [IntegrationTestNode], {
      batchSize: 5,
      workers: 2
    });
    
    // Test registration
    const result = await (runtime as any).register();
    expect(result).toEqual({ status: 'registered' });
  });

  it('should execute worker with state manager', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce(createFetchMock({ status: 'registered' }))
      .mockResolvedValueOnce(createFetchMock({ states: [] }))
      .mockResolvedValueOnce(createFetchMock({ secrets: { api_key: 'test', database_url: 'db://test' } }));

    const runtime = new Runtime('test_namespace', 'test_runtime', [IntegrationTestNode], {
      batchSize: 5,
      workers: 1
    });
    
    // Create a test state
    const state = {
      state_id: 'test_state_1',
      node_name: 'IntegrationTestNode',
      inputs: { user_id: '123', action: 'login' }
    };
    
    // Add state to node mapping
    (runtime as any).nodeMapping['test_state_1'] = IntegrationTestNode;
    
    // Put state in queue and run worker
    await (runtime as any).stateQueue.put(state);
    
    // Mock the worker methods
    vi.spyOn(runtime as any, 'getSecrets').mockResolvedValue({ api_key: 'test', database_url: 'db://test' });
    vi.spyOn(runtime as any, 'notifyExecuted').mockResolvedValue(undefined);
    
    const workerPromise = (runtime as any).worker(1);
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect((runtime as any).getSecrets).toHaveBeenCalledWith('test_state_1');
  });
});

describe('TestStateManagerGraphIntegration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should handle state manager graph lifecycle', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce(createFetchMock({
        name: 'test_graph',
        validation_status: 'PENDING',
        validation_errors: null
      }, 201))
      .mockResolvedValueOnce(createFetchMock({ 
        validation_status: 'PENDING',
        validation_errors: null
      }))
      .mockResolvedValueOnce(createFetchMock({ 
        validation_status: 'VALID', 
        name: 'test_graph',
        validation_errors: null
      }))
      .mockResolvedValueOnce(createFetchMock({ status: 'triggered' }));

    const sm = new StateManager('test_namespace');
    
    // Test graph creation
    const graphNodes = [{
      node_name: 'IntegrationTestNode',
      namespace: 'test_namespace',
      identifier: 'IntegrationTestNode',
      inputs: { type: 'test' },
      next_nodes: null,
      unites: null
    }];
    const secrets = { api_key: 'test_key', database_url: 'db://test' };
    
    const result = await sm.upsertGraph('test_graph', graphNodes, secrets, undefined, undefined, 10, 0.1);
    expect(result.validation_status).toBe('VALID');
    
    // Test graph triggering
    const triggerState = { identifier: 'test_trigger', inputs: { user_id: '123', action: 'login' } };
    
    const triggerResult = await sm.trigger('test_graph', triggerState.inputs);
    expect(triggerResult).toEqual({ status: 'triggered' });
  });
});

describe('TestNodeExecutionIntegration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should execute node with runtime worker', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce(createFetchMock({ status: 'registered' }))
      .mockResolvedValueOnce(createFetchMock({ states: [] }))
      .mockResolvedValueOnce(createFetchMock({ secrets: { api_key: 'test' } }));

    const runtime = new Runtime('test_namespace', 'test_runtime', [MultiOutputNode], {
      batchSize: 5,
      workers: 1
    });
    
    // Test node with multiple outputs
    const state = {
      state_id: 'test_state_1',
      node_name: 'MultiOutputNode',
      inputs: { count: '3' }
    };
    
    // Add state to node mapping
    (runtime as any).nodeMapping[state.state_id] = MultiOutputNode;
    
    await (runtime as any).stateQueue.put(state);
    
    // Mock the worker methods
    vi.spyOn(runtime as any, 'getSecrets').mockResolvedValue({ api_key: 'test' });
    vi.spyOn(runtime as any, 'notifyExecuted').mockResolvedValue(undefined);
    
    const workerPromise = (runtime as any).worker(1);
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect((runtime as any).getSecrets).toHaveBeenCalledWith('test_state_1');
  });

  it('should handle node error in integration', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce(createFetchMock({ status: 'registered' }))
      .mockResolvedValueOnce(createFetchMock({ states: [] }))
      .mockResolvedValueOnce(createFetchMock({ secrets: { api_key: 'test' } }));

    const runtime = new Runtime('test_namespace', 'test_runtime', [ErrorProneNode], {
      batchSize: 5,
      workers: 1
    });
    
    // Test node that raises an error
    const state = {
      state_id: 'test_state_1',
      node_name: 'ErrorProneNode',
      inputs: { should_fail: 'true' }
    };
    
    // Add state to node mapping
    (runtime as any).nodeMapping['test_state_1'] = ErrorProneNode;
    
    await (runtime as any).stateQueue.put(state);
    
    // Mock the worker methods
    vi.spyOn(runtime as any, 'getSecrets').mockResolvedValue({ api_key: 'test' });
    vi.spyOn(runtime as any, 'notifyErrored').mockResolvedValue(undefined);
    
    const workerPromise = (runtime as any).worker(1);
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect((runtime as any).notifyErrored).toHaveBeenCalled();
  });
});

describe('TestEndToEndWorkflow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should handle complete workflow integration', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce(createFetchMock({ status: 'registered' }))
      .mockResolvedValueOnce(createFetchMock({
        states: [{
          state_id: 'workflow_state_1',
          node_name: 'IntegrationTestNode',
          inputs: { user_id: '456', action: 'process' }
        }]
      }))
      .mockResolvedValueOnce(createFetchMock({
        secrets: { api_key: 'workflow_key', database_url: 'workflow_db' }
      }));

    // Create runtime
    const runtime = new Runtime('workflow_namespace', 'workflow_runtime', [IntegrationTestNode], {
      batchSize: 10,
      workers: 2
    });
    
    // Test registration
    const registerResult = await (runtime as any).register();
    expect(registerResult).toEqual({ status: 'registered' });
    
    // Test enqueue
    const enqueueResult = await (runtime as any).enqueueCall();
    expect(enqueueResult.states).toHaveLength(1);
    expect(enqueueResult.states[0].state_id).toBe('workflow_state_1');
    
    // Test worker processing
    const state = enqueueResult.states[0];
    // Add state to node mapping
    (runtime as any).nodeMapping[state.state_id] = IntegrationTestNode;
    await (runtime as any).stateQueue.put(state);
    
    // Mock the worker methods
    vi.spyOn(runtime as any, 'getSecrets').mockResolvedValue({ api_key: 'workflow_key', database_url: 'workflow_db' });
    vi.spyOn(runtime as any, 'notifyExecuted').mockResolvedValue(undefined);
    
    const workerPromise = (runtime as any).worker(1);
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect((runtime as any).getSecrets).toHaveBeenCalledWith('workflow_state_1');
  });
});

describe('TestConfigurationIntegration', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should handle runtime configuration integration', () => {
    // Test that runtime can be configured with different parameters
    const runtime = new Runtime('config_test', 'config_runtime', [IntegrationTestNode], {
      batchSize: 20,
      workers: 5,
      stateManagerVersion: 'v2',
      pollInterval: 2
    });
    
    expect(runtime).toBeDefined();
  });

  it('should handle state manager configuration integration', () => {
    // Test that state manager can be configured with different parameters
    const sm = new StateManager('config_test', {
      stateManagerUri: 'http://custom-server:9090',
      key: 'custom_key',
      stateManagerVersion: 'v3'
    });
    
    expect(sm).toBeDefined();
  });
});

describe('TestErrorHandlingIntegration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should handle runtime error propagation', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Internal server error'),
      json: () => Promise.resolve({ error: 'Internal server error' })
    });

    const runtime = new Runtime('error_test', 'error_runtime', [IntegrationTestNode]);
    
    await expect((runtime as any).register()).rejects.toThrow('Failed to register nodes');
  });

  it('should handle state manager error propagation', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: () => Promise.resolve('Graph not found'),
      json: () => Promise.resolve({ error: 'Graph not found' })
    });

    const sm = new StateManager('error_test');
    const triggerState = { identifier: 'test', inputs: { key: 'value' } };
    
    await expect(sm.trigger('nonexistent_graph', triggerState.inputs)).rejects.toThrow('Failed to trigger state');
  });
});

describe('TestConcurrencyIntegration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should handle multiple workers integration', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce(createFetchMock({ status: 'registered' }))
      .mockResolvedValueOnce(createFetchMock({ states: [] }))
      .mockResolvedValue(createFetchMock({ secrets: { api_key: 'test' } }));

    const runtime = new Runtime('concurrency_test', 'concurrency_runtime', [IntegrationTestNode], {
      batchSize: 5,
      workers: 3
    });
    
    // Create multiple states
    const states = Array.from({ length: 5 }, (_, i) => ({
      state_id: `state_${i}`,
      node_name: 'IntegrationTestNode',
      inputs: { user_id: i.toString(), action: 'test' }
    }));
    
    // Add states to node mapping
    states.forEach(state => {
      (runtime as any).nodeMapping[state.state_id] = IntegrationTestNode;
    });
    
    // Put states in queue
    for (const state of states) {
      await (runtime as any).stateQueue.put(state);
    }
    
    // Mock the worker methods
    vi.spyOn(runtime as any, 'getSecrets').mockResolvedValue({ api_key: 'test' });
    vi.spyOn(runtime as any, 'notifyExecuted').mockResolvedValue(undefined);
    
    // Start multiple workers
    const workerPromises = Array.from({ length: 3 }, (_, idx) => (runtime as any).worker(idx));
    
    await new Promise(resolve => setTimeout(resolve, 100));
    
    expect((runtime as any).getSecrets).toHaveBeenCalled();
  });
});
