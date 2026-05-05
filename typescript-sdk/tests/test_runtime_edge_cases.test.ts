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

class MockTestNodeWithNonStringFields extends BaseNode {
  static Inputs = z.object({
    name: z.string(),
    count: z.number() // This should cause validation error
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

class MockTestNodeWithoutSecrets extends BaseNode {
  static Inputs = z.object({
    name: z.string()
  });

  static Outputs = z.object({
    message: z.string()
  });

  static Secrets = z.object({}); // Empty secrets

  async execute() {
    return { message: `Hello ${this.inputs.name}` };
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

describe('TestRuntimeEdgeCases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://localhost:8080';
    process.env.EXOSPHERE_API_KEY = 'test_key';
  });

  it('should validate non-string fields', () => {
    expect(() => {
      new Runtime('test', 'test', [MockTestNodeWithNonStringFields], {
        stateManagerUri: 'http://localhost:8080',
        key: 'test_key'
      });
    }).toThrow('must be string');
  });

  it('should validate duplicate node names', () => {
    class TestNode1 extends MockTestNode {}
    class TestNode2 extends MockTestNode {}
    
    // Rename the second class to have the same name as the first
    Object.defineProperty(TestNode2, 'name', { value: 'TestNode1' });
    
    expect(() => {
      new Runtime('test', 'test', [TestNode1, TestNode2], {
        stateManagerUri: 'http://localhost:8080',
        key: 'test_key'
      });
    }).toThrow('Duplicate node class names found');
  });

  it('should handle empty secrets', () => {
    const runtime = new Runtime('test', 'test', [MockTestNodeWithoutSecrets], {
      stateManagerUri: 'http://localhost:8080',
      key: 'test_key'
    });
    
    // Should return false for empty secrets
    expect((runtime as any).needSecrets(MockTestNodeWithoutSecrets)).toBe(false);
  });

  it('should handle secrets with fields', () => {
    const runtime = new Runtime('test', 'test', [MockTestNode], {
      stateManagerUri: 'http://localhost:8080',
      key: 'test_key'
    });
    
    // Should return true for secrets with fields
    expect((runtime as any).needSecrets(MockTestNode)).toBe(true);
  });

  it('should handle enqueue error', async () => {
    const runtime = new Runtime('test', 'test', [MockTestNode], {
      stateManagerUri: 'http://localhost:8080',
      key: 'test_key'
    });
    
    // Mock enqueueCall to throw an exception
    vi.spyOn(runtime as any, 'enqueueCall').mockRejectedValue(new Error('Test error'));
    
    // This should not raise an exception but log an error
    const enqueuePromise = (runtime as any).enqueue();
    
    // Wait a bit and then we can't easily test the infinite loop, but we can verify it doesn't crash immediately
    await new Promise(resolve => setTimeout(resolve, 100));
  });

  it('should start without running loop', () => {
    const runtime = new Runtime('test', 'test', [MockTestNode], {
      stateManagerUri: 'http://localhost:8080',
      key: 'test_key'
    });
    
    // Mock startInternal to avoid actual execution
    vi.spyOn(runtime as any, 'startInternal').mockResolvedValue(undefined);
    
    // This should not raise an exception
    const result = runtime.start();
    expect(result).toBeInstanceOf(Promise);
  });

  it('should start with running loop', () => {
    const runtime = new Runtime('test', 'test', [MockTestNode], {
      stateManagerUri: 'http://localhost:8080',
      key: 'test_key'
    });
    
    // Mock startInternal to avoid actual execution
    vi.spyOn(runtime as any, 'startInternal').mockResolvedValue(undefined);
    
    const result = runtime.start();
    expect(result).toBeInstanceOf(Promise);
  });
});
