import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Runtime } from '../exospherehost/runtime.js';
import { BaseNode } from '../exospherehost/node/BaseNode.js';
import { z } from 'zod';

// Mock fetch globally
global.fetch = vi.fn();

class MockTestNode extends BaseNode {
  static Inputs = z.object({
    name: z.string()
  });

  static Outputs = z.object({
    message: z.string()
  });

  static Secrets = z.object({
    api_key: z.string()
  });

  async execute() {
    return { message: `Hello ${this.inputs.name}` };
  }
}

class MockTestNodeWithListOutput extends BaseNode {
  static Inputs = z.object({
    count: z.string()
  });

  static Outputs = z.object({
    numbers: z.string()
  });

  static Secrets = z.object({
    api_key: z.string()
  });

  async execute() {
    const count = parseInt(this.inputs.count);
    return Array.from({ length: count }, (_, i) => ({ numbers: i.toString() }));
  }
}

class MockTestNodeWithError extends BaseNode {
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
      throw new Error('Test error');
    }
    return { result: 'success' };
  }
}

class MockTestNodeWithNoneOutput extends BaseNode {
  static Inputs = z.object({
    name: z.string()
  });

  static Outputs = z.object({
    message: z.string()
  });

  static Secrets = z.object({
    api_key: z.string()
  });

  async execute() {
    return null;
  }
}

describe('TestRuntimeInitialization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should initialize with all params', () => {
    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode], {
      stateManagerUri: 'http://localhost:8080',
      key: 'test_key',
      batchSize: 5,
      workers: 2,
      stateManagerVersion: 'v1',
      pollInterval: 1
    });

    expect(runtime).toBeDefined();
  });

  it('should initialize with env vars', () => {
    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    expect(runtime).toBeDefined();
  });

  it('should validate batch size less than one', () => {
    expect(() => {
      new Runtime('test_namespace', 'test_runtime', [MockTestNode], {
        batchSize: 0
      });
    }).toThrow('Batch size should be at least 1');
  });

  it('should validate workers less than one', () => {
    expect(() => {
      new Runtime('test_namespace', 'test_runtime', [MockTestNode], {
        workers: 0
      });
    }).toThrow('Workers should be at least 1');
  });

  it('should validate missing URI', () => {
    delete process.env.EXOSPHERE_STATE_MANAGER_URI;
    expect(() => {
      new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    }).toThrow('State manager URI is not set');
  });

  it('should validate missing key', () => {
    delete process.env.EXOSPHERE_API_KEY;
    expect(() => {
      new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    }).toThrow('API key is not set');
  });
});

describe('TestRuntimeEndpointConstruction', () => {
  let runtime: Runtime;

  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
    runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
  });

  it('should construct enqueue endpoint', () => {
    const endpoint = (runtime as any).getEnqueueEndpoint();
    expect(endpoint).toBe('http://localhost:8080/v0/namespace/test_namespace/states/enqueue');
  });

  it('should construct executed endpoint', () => {
    const endpoint = (runtime as any).getExecutedEndpoint('state123');
    expect(endpoint).toBe('http://localhost:8080/v0/namespace/test_namespace/state/state123/executed');
  });

  it('should construct errored endpoint', () => {
    const endpoint = (runtime as any).getErroredEndpoint('state123');
    expect(endpoint).toBe('http://localhost:8080/v0/namespace/test_namespace/state/state123/errored');
  });

  it('should construct register endpoint', () => {
    const endpoint = (runtime as any).getRegisterEndpoint();
    expect(endpoint).toBe('http://localhost:8080/v0/namespace/test_namespace/nodes/');
  });

  it('should construct secrets endpoint', () => {
    const endpoint = (runtime as any).getSecretsEndpoint('state123');
    expect(endpoint).toBe('http://localhost:8080/v0/namespace/test_namespace/state/state123/secrets');
  });
});

describe('TestRuntimeRegistration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should register successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'success' })
    });

    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    const result = await (runtime as any).register();
    
    expect(result).toEqual({ status: 'success' });
  });

  it('should handle registration failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      text: () => Promise.resolve('Bad request')
    });

    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    
    await expect((runtime as any).register()).rejects.toThrow('Failed to register nodes');
  });
});

describe('TestRuntimeEnqueue', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should enqueue call successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        states: [{ state_id: '1', node_name: 'MockTestNode', inputs: { name: 'test' } }]
      })
    });

    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    const result = await (runtime as any).enqueueCall();
    
    expect(result).toEqual({
      states: [{ state_id: '1', node_name: 'MockTestNode', inputs: { name: 'test' } }]
    });
  });

  it('should handle enqueue call failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      text: () => Promise.resolve('Internal server error')
    });

    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    
    await expect((runtime as any).enqueueCall()).rejects.toThrow('Failed to enqueue states');
  });
});

describe('TestRuntimeWorker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should execute worker successfully', async () => {
    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode], {
      workers: 1
    });

    // Mock getSecrets and notifyExecuted
    vi.spyOn(runtime as any, 'getSecrets').mockResolvedValue({ api_key: 'test_key' });
    vi.spyOn(runtime as any, 'notifyExecuted').mockResolvedValue(undefined);

    const state = {
      state_id: 'test_state_1',
      node_name: 'MockTestNode',
      inputs: { name: 'test_user' }
    };

    // Add state to queue
    await (runtime as any).stateQueue.put(state);

    // Start worker and let it process one item
    const workerPromise = (runtime as any).worker(1);
    
    // Wait a bit for processing
    await new Promise(resolve => setTimeout(resolve, 100));
    
    // Verify secrets were fetched
    expect((runtime as any).getSecrets).toHaveBeenCalledWith('test_state_1');
    
    // Verify execution was notified
    expect((runtime as any).notifyExecuted).toHaveBeenCalled();
  });

  it('should handle worker with list output', async () => {
    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNodeWithListOutput], {
      workers: 1
    });

    vi.spyOn(runtime as any, 'getSecrets').mockResolvedValue({ api_key: 'test_key' });
    vi.spyOn(runtime as any, 'notifyExecuted').mockResolvedValue(undefined);
    vi.spyOn(runtime as any, 'register').mockResolvedValue({ status: 'registered' });

    const state = {
      state_id: 'test_state_1',
      node_name: 'MockTestNodeWithListOutput',
      inputs: { count: '3' }
    };

    // Start the worker
    const workerPromise = (runtime as any).worker(1);
    await (runtime as any).stateQueue.put(state);
    await new Promise(resolve => setTimeout(resolve, 100));

    expect((runtime as any).notifyExecuted).toHaveBeenCalled();
  });

  it('should handle worker with none output', async () => {
    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNodeWithNoneOutput], {
      workers: 1
    });

    vi.spyOn(runtime as any, 'getSecrets').mockResolvedValue({ api_key: 'test_key' });
    vi.spyOn(runtime as any, 'notifyExecuted').mockResolvedValue(undefined);
    vi.spyOn(runtime as any, 'register').mockResolvedValue({ status: 'registered' });

    const state = {
      state_id: 'test_state_1',
      node_name: 'MockTestNodeWithNoneOutput',
      inputs: { name: 'test' }
    };

    // Start the worker
    const workerPromise = (runtime as any).worker(1);
    await (runtime as any).stateQueue.put(state);
    await new Promise(resolve => setTimeout(resolve, 100));

    expect((runtime as any).notifyExecuted).toHaveBeenCalled();
  });

  it('should handle worker execution error', async () => {
    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNodeWithError], {
      workers: 1
    });

    vi.spyOn(runtime as any, 'getSecrets').mockResolvedValue({ api_key: 'test_key' });
    vi.spyOn(runtime as any, 'notifyErrored').mockResolvedValue(undefined);
    vi.spyOn(runtime as any, 'register').mockResolvedValue({ status: 'registered' });

    const state = {
      state_id: 'test_state_1',
      node_name: 'MockTestNodeWithError',
      inputs: { should_fail: 'true' }
    };

    // Start the worker
    const workerPromise = (runtime as any).worker(1);
    await (runtime as any).stateQueue.put(state);
    await new Promise(resolve => setTimeout(resolve, 100));

    expect((runtime as any).notifyErrored).toHaveBeenCalled();
  });
});

describe('TestRuntimeNotification', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should notify executed successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'success' })
    });

    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    const outputs = [{ message: 'test output' }];
    
    await (runtime as any).notifyExecuted('test_state_1', outputs);
    
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8080/v0/namespace/test_namespace/state/test_state_1/executed',
      expect.objectContaining({
        method: 'POST',
        headers: { 
          'x-api-key': 'test_key',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ outputs })
      })
    );
  });

  it('should handle notify executed failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      text: () => Promise.resolve('Bad request')
    });

    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    const outputs = [{ message: 'test output' }];
    
    // Should not throw exception, just log error
    await (runtime as any).notifyExecuted('test_state_1', outputs);
  });

  it('should notify errored successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'success' })
    });

    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    
    await (runtime as any).notifyErrored('test_state_1', 'Test error message');
    
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8080/v0/namespace/test_namespace/state/test_state_1/errored',
      expect.objectContaining({
        method: 'POST',
        headers: { 
          'x-api-key': 'test_key',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ error: 'Test error message' })
      })
    );
  });

  it('should handle notify errored failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      text: () => Promise.resolve('Bad request')
    });

    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    
    // Should not throw exception, just log error
    await (runtime as any).notifyErrored('test_state_1', 'Test error message');
  });
});

describe('TestRuntimeSecrets', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should get secrets successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ secrets: { api_key: 'secret_key' } })
    });

    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    const result = await (runtime as any).getSecrets('test_state_1');
    
    expect(result).toEqual({ api_key: 'secret_key' });
  });

  it('should handle get secrets failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      text: () => Promise.resolve('Not found')
    });

    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    const result = await (runtime as any).getSecrets('test_state_1');
    
    // Should return empty object on failure
    expect(result).toEqual({});
  });
});

describe('TestRuntimeStart', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should start with existing loop', async () => {
    vi.spyOn(Runtime.prototype as any, 'register').mockResolvedValue(undefined);
    vi.spyOn(Runtime.prototype as any, 'enqueue').mockResolvedValue(undefined);
    vi.spyOn(Runtime.prototype as any, 'worker').mockResolvedValue(undefined);

    const runtime = new Runtime('test_namespace', 'test_runtime', [MockTestNode]);
    
    const task = runtime.start();
    
    expect(task).toBeInstanceOf(Promise);
  });
});
