import { describe, it, expect, beforeEach, vi } from 'vitest';
import { StateManager } from '../exospherehost/stateManager.js';
import { Runtime, BaseNode } from '../exospherehost/index.js';
import { PruneSignal, ReQueueAfterSignal } from '../exospherehost/signals.js';
import { z } from 'zod';

// Mock fetch globally
global.fetch = vi.fn();

class DummyNode extends BaseNode {
  static Inputs = z.object({
    x: z.string()
  });
  static Outputs = z.object({
    y: z.string()
  });
  static Secrets = z.object({});
  
  async execute() {
    return { y: 'ok' };
  }
}

describe('test_statemanager_trigger_defaults', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://sm';
    process.env.EXOSPHERE_API_KEY = 'k';
  });

  it('should handle trigger with defaults', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({})
    });

    const sm = new StateManager('ns');
    
    await sm.trigger('g');
    
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/graph/g/trigger'),
      expect.objectContaining({
        method: 'POST',
        headers: { 
          'x-api-key': 'k',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ start_delay: 0, inputs: {}, store: {} })
      })
    );
  });
});

describe('test_runtime_enqueue_puts_states_and_sleeps', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://sm';
    process.env.EXOSPHERE_API_KEY = 'k';
  });

  it('should enqueue states and sleep', async () => {
    const rt = new Runtime('ns', 'rt', [DummyNode], { batchSize: 2, workers: 1 });

    vi.spyOn(rt as any, 'enqueueCall').mockResolvedValueOnce({
      states: [{ state_id: 's1', node_name: 'DummyNode', inputs: {} }]
    });

    // Start enqueue process
    const enqueuePromise = (rt as any).enqueue();
    
    // Wait a bit for processing
    await new Promise(resolve => setTimeout(resolve, 10));
    
    // Check that state was added to queue
    expect((rt as any).stateQueue.size()).toBeGreaterThanOrEqual(1);
  });
});

describe('test_runtime_validate_nodes_not_subclass', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://sm';
    process.env.EXOSPHERE_API_KEY = 'k';
  });

  it('should validate nodes are subclasses of BaseNode', () => {
    class NotNode {
      // Not a BaseNode
    }

    expect(() => {
      new Runtime('ns', 'rt', [NotNode as any]);
    }).toThrow();
  });
});

class PruneNode extends BaseNode {
  static Inputs = z.object({ a: z.string() });
  static Outputs = z.object({ b: z.string() });
  static Secrets = z.object({});
  
  async execute() {
    throw new PruneSignal({ reason: 'test' });
  }
}

class RequeueNode extends BaseNode {
  static Inputs = z.object({ a: z.string() });
  static Outputs = z.object({ b: z.string() });
  static Secrets = z.object({});
  
  async execute() {
    throw new ReQueueAfterSignal(1000);
  }
}

describe('test_worker_handles_prune_signal', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://sm';
    process.env.EXOSPHERE_API_KEY = 'k';
  });

  it('should handle prune signal in worker', async () => {
    const rt = new Runtime('ns', 'rt', [PruneNode], { workers: 1 });

    vi.spyOn(PruneSignal.prototype, 'send').mockResolvedValue(undefined);

    await (rt as any).stateQueue.put({
      state_id: 's1',
      node_name: 'PruneNode',
      inputs: { a: '1' }
    });
    
    // Mock the worker methods
    vi.spyOn(rt as any, 'getSecrets').mockResolvedValue({});
    
    const workerPromise = (rt as any).worker(1);
    await new Promise(resolve => setTimeout(resolve, 20));
    
    expect(PruneSignal.prototype.send).toHaveBeenCalled();
  });
});

describe('test_worker_handles_requeue_signal', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://sm';
    process.env.EXOSPHERE_API_KEY = 'k';
  });

  it('should handle requeue signal in worker', async () => {
    const rt = new Runtime('ns', 'rt', [RequeueNode], { workers: 1 });

    vi.spyOn(ReQueueAfterSignal.prototype, 'send').mockResolvedValue(undefined);

    await (rt as any).stateQueue.put({
      state_id: 's2',
      node_name: 'RequeueNode',
      inputs: { a: '1' }
    });
    
    // Mock the worker methods
    vi.spyOn(rt as any, 'getSecrets').mockResolvedValue({});
    
    const workerPromise = (rt as any).worker(2);
    await new Promise(resolve => setTimeout(resolve, 20));
    
    expect(ReQueueAfterSignal.prototype.send).toHaveBeenCalled();
  });
});

describe('test_runtime_start_creates_tasks', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://sm';
    process.env.EXOSPHERE_API_KEY = 'k';
  });

  it('should create tasks when starting', async () => {
    const rt = new Runtime('ns', 'rt', [DummyNode], { workers: 1 });

    vi.spyOn(rt as any, 'register').mockResolvedValue(undefined);
    vi.spyOn(rt as any, 'enqueue').mockResolvedValue(undefined);
    vi.spyOn(rt as any, 'worker').mockResolvedValue(undefined);

    const startPromise = (rt as any).startInternal();
    await new Promise(resolve => setTimeout(resolve, 10));
    
    expect((rt as any).register).toHaveBeenCalled();
  });
});
