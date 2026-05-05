import { describe, it, expect, beforeEach, vi } from 'vitest';
import { StateManager } from '../exospherehost/stateManager.js';
import { GraphNodeModel } from '../exospherehost/models.js';

// Mock fetch globally
global.fetch = vi.fn();

describe('TestStateManagerInitialization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should initialize with all params', () => {
    const sm = new StateManager('test_namespace', {
      stateManagerUri: 'http://localhost:8080',
      key: 'test_key',
      stateManagerVersion: 'v1'
    });
    expect(sm).toBeDefined();
  });

  it('should initialize with env vars', () => {
    const sm = new StateManager('test_namespace');
    expect(sm).toBeDefined();
  });

  it('should use default version', () => {
    const sm = new StateManager('test_namespace');
    expect(sm).toBeDefined();
  });
});

describe('TestStateManagerEndpointConstruction', () => {
  let sm: StateManager;

  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
    sm = new StateManager('test_namespace');
  });

  it('should construct trigger state endpoint', () => {
    const endpoint = (sm as any).getTriggerStateEndpoint('test_graph');
    expect(endpoint).toBe('http://localhost:8080/v0/namespace/test_namespace/graph/test_graph/trigger');
  });

  it('should construct upsert graph endpoint', () => {
    const endpoint = (sm as any).getUpsertGraphEndpoint('test_graph');
    expect(endpoint).toBe('http://localhost:8080/v0/namespace/test_namespace/graph/test_graph');
  });

  it('should construct get graph endpoint', () => {
    const endpoint = (sm as any).getGetGraphEndpoint('test_graph');
    expect(endpoint).toBe('http://localhost:8080/v0/namespace/test_namespace/graph/test_graph');
  });
});

describe('TestStateManagerTrigger', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should trigger single state successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'success' })
    });

    const sm = new StateManager('test_namespace');
    const state = { identifier: 'test', inputs: { key: 'value' } };
    
    const result = await sm.trigger('test_graph', state.inputs);
    
    expect(result).toEqual({ status: 'success' });
  });

  it('should trigger multiple states successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'success' })
    });

    const sm = new StateManager('test_namespace');
    const states = [
      { identifier: 'test1', inputs: { key1: 'value1' } },
      { identifier: 'test2', inputs: { key2: 'value2' } }
    ];
    
    const mergedInputs = { ...states[0].inputs, ...states[1].inputs };
    const result = await sm.trigger('test_graph', mergedInputs);
    
    expect(result).toEqual({ status: 'success' });
  });

  it('should handle trigger failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: () => Promise.resolve('Bad request')
    });

    const sm = new StateManager('test_namespace');
    const state = { identifier: 'test', inputs: { key: 'value' } };
    
    await expect(sm.trigger('test_graph', state.inputs)).rejects.toThrow('Failed to trigger state: 400 Bad request');
  });
});

describe('TestStateManagerGetGraph', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should get graph successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        name: 'test_graph',
        validation_status: 'VALID',
        nodes: []
      })
    });

    const sm = new StateManager('test_namespace');
    const result = await sm.getGraph('test_graph');
    
    expect(result.name).toBe('test_graph');
    expect(result.validation_status).toBe('VALID');
  });

  it('should handle get graph failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: () => Promise.resolve('Not found')
    });

    const sm = new StateManager('test_namespace');
    
    await expect(sm.getGraph('test_graph')).rejects.toThrow('Failed to get graph: 404 Not found');
  });
});

describe('TestStateManagerUpsertGraph', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should upsert graph successfully with 201 status', async () => {
    // Mock the initial PUT response
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: () => Promise.resolve({
          name: 'test_graph',
          validation_status: 'PENDING'
        })
      })
      // Mock the polling responses
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ validation_status: 'PENDING' })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ validation_status: 'VALID', name: 'test_graph' })
      });

    const sm = new StateManager('test_namespace');
    const graphNodes = [{
      node_name: 'node1',
      namespace: 'test_namespace',
      identifier: 'node1',
      inputs: { type: 'test' },
      next_nodes: null,
      unites: null
    }];
    const secrets = { secret1: 'value1' };
    
    const result = await sm.upsertGraph('test_graph', graphNodes, secrets);
    
    expect(result.validation_status).toBe('VALID');
    expect(result.name).toBe('test_graph');
  });

  it('should upsert graph successfully with 200 status', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({
        name: 'test_graph',
        validation_status: 'VALID'
      })
    });

    const sm = new StateManager('test_namespace');
    const graphNodes = [{
      node_name: 'node1',
      namespace: 'test_namespace',
      identifier: 'node1',
      inputs: { type: 'test' },
      next_nodes: null,
      unites: null
    }];
    const secrets = { secret1: 'value1' };
    
    const result = await sm.upsertGraph('test_graph', graphNodes, secrets);
    
    expect(result.validation_status).toBe('VALID');
  });

  it('should handle upsert graph PUT failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Internal server error')
    });

    const sm = new StateManager('test_namespace');
    const graphNodes = [{
      node_name: 'node1',
      namespace: 'test_namespace',
      identifier: 'node1',
      inputs: { type: 'test' },
      next_nodes: null,
      unites: null
    }];
    const secrets = { secret1: 'value1' };
    
    await expect(sm.upsertGraph('test_graph', graphNodes, secrets)).rejects.toThrow('Failed to upsert graph: 500 Internal server error');
  });

  it('should handle validation timeout', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: () => Promise.resolve({
          name: 'test_graph',
          validation_status: 'PENDING'
        })
      })
      // Mock the polling responses to always return PENDING
      .mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ validation_status: 'PENDING' })
      });

    const sm = new StateManager('test_namespace');
    const graphNodes = [{
      node_name: 'node1',
      namespace: 'test_namespace',
      identifier: 'node1',
      inputs: { type: 'test' },
      next_nodes: null,
      unites: null
    }];
    const secrets = { secret1: 'value1' };
    
    await expect(sm.upsertGraph('test_graph', graphNodes, secrets, undefined, undefined, 1, 0.1)).rejects.toThrow('Graph validation check timed out after 1 seconds');
  });

  it('should handle validation failed', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: () => Promise.resolve({
          name: 'test_graph',
          validation_status: 'PENDING'
        })
      })
      // Mock the polling responses
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ validation_status: 'PENDING' })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          validation_status: 'INVALID',
          validation_errors: ["Node 'node1' not found"]
        })
      });

    const sm = new StateManager('test_namespace');
    const graphNodes = [{
      node_name: 'node1',
      namespace: 'test_namespace',
      identifier: 'node1',
      inputs: { type: 'test' },
      next_nodes: null,
      unites: null
    }];
    const secrets = { secret1: 'value1' };
    
    await expect(sm.upsertGraph('test_graph', graphNodes, secrets, undefined, undefined, 10, 0.1)).rejects.toThrow('Graph validation failed: INVALID and errors: ["Node \'node1\' not found"]');
  });

  it('should handle custom timeout and polling', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: () => Promise.resolve({
          name: 'test_graph',
          validation_status: 'PENDING'
        })
      })
      // Mock the polling responses
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ validation_status: 'PENDING' })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ validation_status: 'VALID', name: 'test_graph' })
      });

    const sm = new StateManager('test_namespace');
    const graphNodes = [{
      node_name: 'node1',
      namespace: 'test_namespace',
      identifier: 'node1',
      inputs: { type: 'test' },
      next_nodes: null,
      unites: null
    }];
    const secrets = { secret1: 'value1' };
    
    const result = await sm.upsertGraph('test_graph', graphNodes, secrets, undefined, undefined, 30, 2);
    
    expect(result.validation_status).toBe('VALID');
  });
});
