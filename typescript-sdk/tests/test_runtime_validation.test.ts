import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Runtime } from '../exospherehost/runtime.js';
import { BaseNode } from '../exospherehost/node/BaseNode.js';
import { z } from 'zod';

// Mock fetch globally
global.fetch = vi.fn();

class GoodNode extends BaseNode {
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
    return { message: `hi ${this.inputs.name}` };
  }
}

class BadNodeWrongInputsBase extends BaseNode {
  static Inputs = {} as any; // not a zod schema
  static Outputs = z.object({
    message: z.string()
  });
  static Secrets = z.object({
    token: z.string()
  });
  
  async execute() {
    return { message: 'x' };
  }
}

class BadNodeWrongTypes extends BaseNode {
  static Inputs = z.object({
    count: z.number() // should be string
  });
  static Outputs = z.object({
    ok: z.boolean() // should be string
  });
  static Secrets = z.object({
    secret: z.instanceof(Buffer) // should be string
  });
  
  async execute() {
    return { ok: true };
  }
}

describe('test_runtime_missing_config_raises', () => {
  beforeEach(() => {
    delete process.env.EXOSPHERE_STATE_MANAGER_URI;
    delete process.env.EXOSPHERE_API_KEY;
  });

  it('should raise error when config is missing', () => {
    expect(() => {
      new Runtime('ns', 'rt', [GoodNode]);
    }).toThrow();
  });
});

describe('test_runtime_with_env_ok', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://sm';
    process.env.EXOSPHERE_API_KEY = 'k';
  });

  it('should work with env vars', () => {
    const rt = new Runtime('ns', 'rt', [GoodNode]);
    expect(rt).toBeDefined();
  });
});

describe('test_runtime_invalid_params_raises', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://sm';
    process.env.EXOSPHERE_API_KEY = 'k';
  });

  it('should raise error for invalid batch size', () => {
    expect(() => {
      new Runtime('ns', 'rt', [GoodNode], { batchSize: 0 });
    }).toThrow();
  });

  it('should raise error for invalid workers', () => {
    expect(() => {
      new Runtime('ns', 'rt', [GoodNode], { workers: 0 });
    }).toThrow();
  });
});

describe('test_node_validation_errors', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://sm';
    process.env.EXOSPHERE_API_KEY = 'k';
  });

  it('should validate node inputs base', () => {
    expect(() => {
      new Runtime('ns', 'rt', [BadNodeWrongInputsBase]);
    }).toThrow();
  });

  it('should validate node field types', () => {
    expect(() => {
      new Runtime('ns', 'rt', [BadNodeWrongTypes]);
    }).toThrow();
  });
});

describe('test_duplicate_node_names_raise', () => {
  beforeEach(() => {
    process.env.EXOSPHERE_STATE_MANAGER_URI = 'http://sm';
    process.env.EXOSPHERE_API_KEY = 'k';
  });

  it('should raise error for duplicate node names', () => {
    class GoodNode1 extends BaseNode {
      static Inputs = z.object({ name: z.string() });
      static Outputs = z.object({ message: z.string() });
      static Secrets = z.object({ api_key: z.string() });
      async execute() { return { message: 'ok' }; }
    }
    
    class GoodNode2 extends BaseNode {
      static Inputs = z.object({ name: z.string() });
      static Outputs = z.object({ message: z.string() });
      static Secrets = z.object({ api_key: z.string() });
      async execute() { return { message: 'ok' }; }
    }
    
    // Use the same name for both classes
    Object.defineProperty(GoodNode2, 'name', { value: 'GoodNode1' });
    
    expect(() => {
      new Runtime('ns', 'rt', [GoodNode1, GoodNode2]);
    }).toThrow();
  });
});
