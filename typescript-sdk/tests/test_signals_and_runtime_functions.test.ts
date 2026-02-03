import { describe, it, expect, beforeEach, vi } from 'vitest';
import { PruneSignal, ReQueueAfterSignal } from '../exospherehost/signals.js';
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

describe('TestPruneSignal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  it('should initialize with data', () => {
    const data = { reason: 'test', custom_field: 'value' };
    const signal = new PruneSignal(data);
    
    expect(signal.data).toEqual(data);
    expect(signal.message).toContain('Prune signal received with data');
    expect(signal.message).toContain('Do not catch this Exception');
  });
  it('should initialize without data', () => {
    const signal = new PruneSignal();
    
    expect(signal.data).toEqual({});
    expect(signal.message).toContain('Prune signal received with data');
  });

  it('should inherit from Error', () => {
    const signal = new PruneSignal();
    expect(signal).toBeInstanceOf(Error);
  });

  it('should send successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true
    });

    const data = { reason: 'test_prune' };
    const signal = new PruneSignal(data);
    
    await signal.send('http://test-endpoint/prune', 'test-api-key');
    
    expect(global.fetch).toHaveBeenCalledWith('http://test-endpoint/prune', {
      method: 'POST',
      headers: { 
        'x-api-key': 'test-api-key',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ data })
    });
  });

  it('should handle send failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false
    });

    const data = { reason: 'test_prune' };
    const signal = new PruneSignal(data);
    
    await expect(signal.send('http://test-endpoint/prune', 'test-api-key')).rejects.toThrow('Failed to send prune signal');
  });
});

describe('TestReQueueAfterSignal', () => {
  it('should initialize with delay', () => {
    const delayMs = 30000;
    const signal = new ReQueueAfterSignal(delayMs);
    
    expect(signal.delayMs).toBe(delayMs);
    expect(signal.message).toContain('ReQueueAfter signal received with delay');
    expect(signal.message).toContain('Do not catch this Exception');
  });

  it('should inherit from Error', () => {
    const signal = new ReQueueAfterSignal(5000);
    expect(signal).toBeInstanceOf(Error);
  });

  it('should send successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true
    });

    const delayMs = 45000;
    const signal = new ReQueueAfterSignal(delayMs);
    
    await signal.send('http://test-endpoint/requeue', 'test-api-key');
    
    expect(global.fetch).toHaveBeenCalledWith('http://test-endpoint/requeue', {
      method: 'POST',
      headers: { 
        'x-api-key': 'test-api-key',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ enqueue_after: delayMs })
    });
  });

  it('should send with minutes', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true
    });

    const delayMs = 150000; // 2.5 minutes
    const signal = new ReQueueAfterSignal(delayMs);
    
    await signal.send('http://test-endpoint/requeue', 'test-api-key');
    
    expect(global.fetch).toHaveBeenCalledWith('http://test-endpoint/requeue', {
      method: 'POST',
      headers: { 
        'x-api-key': 'test-api-key',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ enqueue_after: delayMs })
    });
  });

  it('should handle send failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false
    });

    const delayMs = 30000;
    const signal = new ReQueueAfterSignal(delayMs);
    
    await expect(signal.send('http://test-endpoint/requeue', 'test-api-key')).rejects.toThrow('Failed to send requeue after signal');
  });

  it('should validate delay is greater than 0', () => {
    expect(() => {
      new ReQueueAfterSignal(0);
    }).toThrow('Delay must be greater than 0');
  });
});

describe('TestRuntimeSignalHandling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://test-state-manager';
    process.env.EXOSPHERE_API_KEY = 'test-key';
  });

  it('should construct correct endpoints for signal handling', () => {
    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    // Test prune endpoint construction
    const pruneEndpoint = (runtime as any).getPruneEndpoint('test-state-id');
    expect(pruneEndpoint).toBe('http://test-state-manager/v0/namespace/test-namespace/state/test-state-id/prune');
    
    // Test requeue after endpoint construction
    const requeueEndpoint = (runtime as any).getRequeueAfterEndpoint('test-state-id');
    expect(requeueEndpoint).toBe('http://test-state-manager/v0/namespace/test-namespace/state/test-state-id/re-enqueue-after');
  });

  it('should handle signal sending with runtime endpoints', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true
    });

    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    // Test PruneSignal with runtime endpoint
    const pruneSignal = new PruneSignal({ reason: 'direct_test' });
    await pruneSignal.send((runtime as any).getPruneEndpoint('test-state'), (runtime as any).key);
    
    expect(global.fetch).toHaveBeenCalledWith(
      (runtime as any).getPruneEndpoint('test-state'),
      {
        method: 'POST',
        headers: { 
          'x-api-key': (runtime as any).key,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ data: { reason: 'direct_test' } })
      }
    );
  });

  it('should handle requeue signal with runtime endpoints', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true
    });

    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    // Test ReQueueAfterSignal with runtime endpoint
    const requeueSignal = new ReQueueAfterSignal(600000); // 10 minutes
    await requeueSignal.send((runtime as any).getRequeueAfterEndpoint('test-state'), (runtime as any).key);
    
    expect(global.fetch).toHaveBeenCalledWith(
      (runtime as any).getRequeueAfterEndpoint('test-state'),
      {
        method: 'POST',
        headers: { 
          'x-api-key': (runtime as any).key,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ enqueue_after: 600000 })
      }
    );
  });

  it('should check if secrets are needed', () => {
    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    // Test with node that has secrets
    expect((runtime as any).needSecrets(MockTestNode)).toBe(true);
    
    // Test with node that has no secrets
    class MockNodeWithoutSecrets extends BaseNode {
      static Inputs = z.object({ name: z.string() });
      static Outputs = z.object({ message: z.string() });
      static Secrets = z.object({});
      async execute() { return { message: 'test' }; }
    }
    
    expect((runtime as any).needSecrets(MockNodeWithoutSecrets)).toBe(false);
  });

  it('should get secrets successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ secrets: { api_key: 'test-secret' } })
    });

    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    const secrets = await (runtime as any).getSecrets('test-state-id');
    
    expect(secrets).toEqual({ api_key: 'test-secret' });
    expect(global.fetch).toHaveBeenCalledWith(
      (runtime as any).getSecretsEndpoint('test-state-id'),
      { headers: { 'x-api-key': 'test-key', 'Content-Type': 'application/json' } }
    );
  });

  it('should handle get secrets failure', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      text: () => Promise.resolve('Not found')
    });

    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    const secrets = await (runtime as any).getSecrets('test-state-id');
    
    expect(secrets).toEqual({});
  });

  it('should handle get secrets with no secrets field', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ data: 'some other data' })
    });

    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    const secrets = await (runtime as any).getSecrets('test-state-id');
    
    expect(secrets).toEqual({});
  });
});

describe('TestRuntimeEndpointFunctions', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://test-state-manager';
    process.env.EXOSPHERE_API_KEY = 'test-key';
  });

  it('should construct prune endpoint', () => {
    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    const endpoint = (runtime as any).getPruneEndpoint('state-123');
    expect(endpoint).toBe('http://test-state-manager/v0/namespace/test-namespace/state/state-123/prune');
  });

  it('should construct requeue after endpoint', () => {
    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    const endpoint = (runtime as any).getRequeueAfterEndpoint('state-456');
    expect(endpoint).toBe('http://test-state-manager/v0/namespace/test-namespace/state/state-456/re-enqueue-after');
  });

  it('should construct prune endpoint with custom version', () => {
    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key',
      stateManagerVersion: 'v1'
    });
    
    const endpoint = (runtime as any).getPruneEndpoint('state-789');
    expect(endpoint).toBe('http://test-state-manager/v1/namespace/test-namespace/state/state-789/prune');
  });

  it('should construct requeue after endpoint with custom version', () => {
    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key',
      stateManagerVersion: 'v2'
    });
    
    const endpoint = (runtime as any).getRequeueAfterEndpoint('state-101');
    expect(endpoint).toBe('http://test-state-manager/v2/namespace/test-namespace/state/state-101/re-enqueue-after');
  });
});

describe('TestSignalIntegration', () => {
  it('should behave as proper exceptions', () => {
    // Test PruneSignal
    const pruneSignal = new PruneSignal({ test: 'data' });
    expect(pruneSignal.data).toEqual({ test: 'data' });
    expect(pruneSignal).toBeInstanceOf(Error);
    
    // Test ReQueueAfterSignal
    const requeueSignal = new ReQueueAfterSignal(30000);
    expect(requeueSignal.delayMs).toBe(30000);
    expect(requeueSignal).toBeInstanceOf(Error);
  });

  it('should work with runtime endpoints', () => {
    const runtime = new Runtime('production', 'signal-runtime', [MockTestNode], {
      stateManagerUri: 'https://api.exosphere.host',
      key: 'prod-api-key',
      stateManagerVersion: 'v1'
    });
    
    // Test PruneSignal with production-like endpoint
    const pruneSignal = new PruneSignal({ reason: 'cleanup', batch_id: 'batch-123' });
    const expectedPruneEndpoint = 'https://api.exosphere.host/v1/namespace/production/state/prod-state-456/prune';
    const actualPruneEndpoint = (runtime as any).getPruneEndpoint('prod-state-456');
    expect(actualPruneEndpoint).toBe(expectedPruneEndpoint);
    
    // Test ReQueueAfterSignal with production-like endpoint
    const requeueSignal = new ReQueueAfterSignal(9000000); // 2.5 hours
    const expectedRequeueEndpoint = 'https://api.exosphere.host/v1/namespace/production/state/prod-state-789/re-enqueue-after';
    const actualRequeueEndpoint = (runtime as any).getRequeueAfterEndpoint('prod-state-789');
    expect(actualRequeueEndpoint).toBe(expectedRequeueEndpoint);
    
    // Test that signal data is preserved
    expect(pruneSignal.data).toEqual({ reason: 'cleanup', batch_id: 'batch-123' });
    expect(requeueSignal.delayMs).toBe(9000000);
  });

  it('should work with different endpoint configurations', () => {
    const testCases = [
      { uri: 'http://localhost:8080', version: 'v0', namespace: 'dev' },
      { uri: 'https://api.production.com', version: 'v2', namespace: 'production' },
      { uri: 'http://staging.internal:3000', version: 'v1', namespace: 'staging' }
    ];
    
    testCases.forEach(({ uri, version, namespace }) => {
      const runtime = new Runtime(namespace, 'test-runtime', [MockTestNode], {
        stateManagerUri: uri,
        key: 'test-key',
        stateManagerVersion: version
      });
      
      // Test prune endpoint construction
      const pruneEndpoint = (runtime as any).getPruneEndpoint('test-state');
      const expectedPrune = `${uri}/${version}/namespace/${namespace}/state/test-state/prune`;
      expect(pruneEndpoint).toBe(expectedPrune);
      
      // Test requeue endpoint construction
      const requeueEndpoint = (runtime as any).getRequeueAfterEndpoint('test-state');
      const expectedRequeue = `${uri}/${version}/namespace/${namespace}/state/test-state/re-enqueue-after`;
      expect(requeueEndpoint).toBe(expectedRequeue);
    });
  });
});

describe('TestSignalEdgeCases', () => {
  it('should handle prune signal with empty data', () => {
    const signal = new PruneSignal({});
    expect(signal.data).toEqual({});
    expect(signal).toBeInstanceOf(Error);
  });

  it('should handle prune signal with complex data', () => {
    const complexData = {
      reason: 'batch_cleanup',
      metadata: {
        batch_id: 'batch-456',
        items: ['item1', 'item2', 'item3'],
        timestamp: '2023-12-01T10:00:00Z'
      },
      config: {
        force: true,
        notify_users: false
      }
    };
    const signal = new PruneSignal(complexData);
    expect(signal.data).toEqual(complexData);
  });

  it('should handle requeue signal with large delay', () => {
    const largeDelayMs = 7 * 24 * 60 * 60 * 1000 + 12 * 60 * 60 * 1000 + 30 * 60 * 1000 + 45 * 1000; // 7 days, 12 hours, 30 minutes, 45 seconds
    const signal = new ReQueueAfterSignal(largeDelayMs);
    expect(signal.delayMs).toBe(largeDelayMs);
  });

  it('should convert delay correctly to milliseconds', async () => {
    const testCases = [
      { delayMs: 1000, expected: 1000 },
      { delayMs: 60000, expected: 60000 },
      { delayMs: 3600000, expected: 3600000 },
      { delayMs: 86400000, expected: 86400000 },
      { delayMs: 30500, expected: 30500 } // 30.5 seconds
    ];
    
    for (const { delayMs, expected } of testCases) {
      (global.fetch as any).mockResolvedValueOnce({ ok: true });
      
      const signal = new ReQueueAfterSignal(delayMs);
      await signal.send('http://test-endpoint', 'test-key');
      
      expect(global.fetch).toHaveBeenCalledWith('http://test-endpoint', {
        method: 'POST',
        headers: { 
          'x-api-key': 'test-key',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ enqueue_after: expected })
      });
    }
  });

  it('should have proper string representations', () => {
    const pruneSignal = new PruneSignal({ test: 'data' });
    const pruneStr = pruneSignal.message;
    expect(pruneStr).toContain('Prune signal received with data');
    expect(pruneStr).toContain('Do not catch this Exception');
    expect(pruneStr).toContain('{"test":"data"}');
    
    const requeueSignal = new ReQueueAfterSignal(300000); // 5 minutes
    const requeueStr = requeueSignal.message;
    expect(requeueStr).toContain('ReQueueAfter signal received with delay');
    expect(requeueStr).toContain('Do not catch this Exception');
  });
});

describe('TestRuntimeHelperFunctions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://test-state-manager';
    process.env.EXOSPHERE_API_KEY = 'test-key';
  });

  it('should notify executed successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'success' })
    });

    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    const outputs = [{ message: 'output1' }, { message: 'output2' }];
    
    await (runtime as any).notifyExecuted('test-state-id', outputs);
    
    expect(global.fetch).toHaveBeenCalledWith(
      (runtime as any).getExecutedEndpoint('test-state-id'),
      {
        method: 'POST',
        headers: { 
          'x-api-key': 'test-key',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ outputs })
      }
    );
  });

  it('should notify errored successfully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ status: 'success' })
    });

    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    await (runtime as any).notifyErrored('test-state-id', 'Test error message');
    
    expect(global.fetch).toHaveBeenCalledWith(
      (runtime as any).getErroredEndpoint('test-state-id'),
      {
        method: 'POST',
        headers: { 
          'x-api-key': 'test-key',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ error: 'Test error message' })
      }
    );
  });

  it('should handle notification failures gracefully', async () => {
    (global.fetch as any)
      .mockResolvedValueOnce({
        ok: false,
        text: () => Promise.resolve('Internal server error')
      })
      .mockResolvedValueOnce({
        ok: false,
        text: () => Promise.resolve('Internal server error')
      });

    const runtime = new Runtime('test-namespace', 'test-runtime', [MockTestNode], {
      stateManagerUri: 'http://test-state-manager',
      key: 'test-key'
    });
    
    const outputs = [{ message: 'test' }];
    
    // These should not throw exceptions, just log errors
    await (runtime as any).notifyExecuted('test-state-id', outputs);
    await (runtime as any).notifyErrored('test-state-id', 'Test error');
    
    // Verify both endpoints were called despite failures
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });
});
