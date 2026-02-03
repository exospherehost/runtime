import { describe, it, expect } from 'vitest';
import { BaseNode } from '../exospherehost/node/BaseNode.js';
import { isZodObjectSchema, isZodStringSchema } from '../exospherehost/utils.js';
import { z } from 'zod';

class ValidNode extends BaseNode {
  static Inputs = z.object({
    name: z.string(),
    count: z.string()
  });

  static Outputs = z.object({
    message: z.string(),
    result: z.string()
  });

  static Secrets = z.object({
    api_key: z.string(),
    token: z.string()
  });

  async execute() {
    return {
      message: `Hello ${this.inputs.name}`,
      result: `Count: ${this.inputs.count}`
    };
  }
}

class NodeWithListOutput extends BaseNode {
  static Inputs = z.object({
    items: z.string()
  });

  static Outputs = z.object({
    processed: z.string()
  });

  static Secrets = z.object({
    api_key: z.string()
  });

  async execute() {
    const count = parseInt(this.inputs.items);
    return Array.from({ length: count }, (_, i) => ({ processed: i.toString() }));
  }
}

class NodeWithNoneOutput extends BaseNode {
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

class NodeWithError extends BaseNode {
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

class NodeWithComplexSecrets extends BaseNode {
  static Inputs = z.object({
    operation: z.string()
  });

  static Outputs = z.object({
    status: z.string()
  });

  static Secrets = z.object({
    database_url: z.string(),
    api_key: z.string(),
    encryption_key: z.string()
  });

  async execute() {
    return { status: `Operation ${this.inputs.operation} completed` };
  }
}

describe('TestBaseNodeInitialization', () => {
  it('should have expected attributes', () => {
    expect(BaseNode.Inputs).toBeDefined();
    expect(BaseNode.Outputs).toBeDefined();
    expect(BaseNode.Secrets).toBeDefined();
    // execute is abstract, so we check that concrete implementations have it
    expect(typeof ValidNode.prototype.execute).toBe('function');
  });

  it('should initialize valid node correctly', () => {
    const node = new ValidNode();
    expect(node).toBeDefined();
    expect(ValidNode.Inputs).toBeDefined();
    expect(ValidNode.Outputs).toBeDefined();
    expect(ValidNode.Secrets).toBeDefined();
  });

  it('should validate node schema', () => {
    expect(isZodObjectSchema(ValidNode.Inputs)).toBe(true);
    expect(isZodObjectSchema(ValidNode.Outputs)).toBe(true);
    expect(isZodObjectSchema(ValidNode.Secrets)).toBe(true);
  });

  it('should validate node schema fields are strings', () => {
    const inputsShape = (ValidNode.Inputs as z.ZodObject<any>).shape;
    const outputsShape = (ValidNode.Outputs as z.ZodObject<any>).shape;
    const secretsShape = (ValidNode.Secrets as z.ZodObject<any>).shape;

    Object.values(inputsShape).forEach(field => {
      expect(isZodStringSchema(field)).toBe(true);
    });

    Object.values(outputsShape).forEach(field => {
      expect(isZodStringSchema(field)).toBe(true);
    });

    Object.values(secretsShape).forEach(field => {
      expect(isZodStringSchema(field)).toBe(true);
    });
  });
});

describe('TestBaseNodeExecute', () => {
  it('should execute valid node successfully', async () => {
    const node = new ValidNode();
    const inputs = { name: 'test_user', count: '5' };
    const secrets = { api_key: 'test_key', token: 'test_token' };
    
    const result = await node._execute(inputs, secrets);
    
    expect(result).toEqual({
      message: 'Hello test_user',
      result: 'Count: 5'
    });
    expect((node as any).inputs).toEqual(inputs);
    expect((node as any).secrets).toEqual(secrets);
  });

  it('should handle node with list output', async () => {
    const node = new NodeWithListOutput();
    const inputs = { items: '3' };
    const secrets = { api_key: 'test_key' };
    
    const result = await node._execute(inputs, secrets);
    
    expect(Array.isArray(result)).toBe(true);
    expect(result).toHaveLength(3);
    expect(result).toEqual([
      { processed: '0' },
      { processed: '1' },
      { processed: '2' }
    ]);
  });

  it('should handle node with null output', async () => {
    const node = new NodeWithNoneOutput();
    const inputs = { name: 'test' };
    const secrets = { api_key: 'test_key' };
    
    const result = await node._execute(inputs, secrets);

    expect(result).toEqual({});
    expect((node as any).inputs).toEqual(inputs);
    expect((node as any).secrets).toEqual(secrets);
  });

  it('should handle node with error', async () => {
    const node = new NodeWithError();
    const inputs = { should_fail: 'true' };
    const secrets = { api_key: 'test_key' };
    
    await expect(node._execute(inputs, secrets)).rejects.toThrow('Test error');
  });

  it('should handle node with complex secrets', async () => {
    const node = new NodeWithComplexSecrets();
    const inputs = { operation: 'backup' };
    const secrets = {
      database_url: 'postgresql://localhost/db',
      api_key: 'secret_key',
      encryption_key: 'encryption_key'
    };
    
    const result = await node._execute(inputs, secrets);
    
    expect(result).toEqual({ status: 'Operation backup completed' });
    expect((node as any).secrets).toEqual(secrets);
  });
});

describe('TestBaseNodeEdgeCases', () => {
  it('should handle node with empty strings', async () => {
    const node = new ValidNode();
    const inputs = { name: '', count: '0' };
    const secrets = { api_key: '', token: '' };
    
    const result = await node._execute(inputs, secrets);
    
    expect(result.message).toBe('Hello ');
    expect(result.result).toBe('Count: 0');
  });

  it('should handle node with special characters', async () => {
    const node = new ValidNode();
    const inputs = { name: 'test@user.com', count: '42' };
    const secrets = { api_key: 'key!@#$%', token: 'token&*()' };
    
    const result = await node._execute(inputs, secrets);
    
    expect(result.message).toBe('Hello test@user.com');
    expect(result.result).toBe('Count: 42');
  });

  it('should handle node with unicode characters', async () => {
    const node = new ValidNode();
    const inputs = { name: 'José', count: '100' };
    const secrets = { api_key: '🔑', token: '🎫' };
    
    const result = await node._execute(inputs, secrets);
    
    expect(result.message).toBe('Hello José');
    expect(result.result).toBe('Count: 100');
  });
});

describe('TestBaseNodeErrorHandling', () => {
  it('should handle custom exception', async () => {
    class NodeWithCustomError extends BaseNode {
      static Inputs = z.object({
        trigger: z.string()
      });

      static Outputs = z.object({
        result: z.string()
      });

      static Secrets = z.object({
        api_key: z.string()
      });

      async execute() {
        if (this.inputs.trigger === 'custom') {
          throw new Error('Custom runtime error');
        }
        return { result: 'ok' };
      }
    }

    const node = new NodeWithCustomError();
    const inputs = { trigger: 'custom' };
    const secrets = { api_key: 'test' };
    
    await expect(node._execute(inputs, secrets)).rejects.toThrow('Custom runtime error');
  });

  it('should handle attribute error', async () => {
    class NodeWithAttributeError extends BaseNode {
      static Inputs = z.object({
        name: z.string()
      });

      static Outputs = z.object({
        result: z.string()
      });

      static Secrets = z.object({
        api_key: z.string()
      });

      async execute() {
        // This will cause an error when accessing non-existent field
        return { result: (this.inputs as any).nonexistent_field };
      }
    }

    const node = new NodeWithAttributeError();
    const inputs = { name: 'test' };
    const secrets = { api_key: 'test' };
    
    await expect(node._execute(inputs, secrets)).rejects.toThrow();
  });
});

describe('TestBaseNodeAbstractMethods', () => {
  it('should not be instantiable directly', () => {
    expect(() => new (BaseNode as any)()).toThrow();
  });

  it('should implement execute method', () => {
    const node = new ValidNode();
    expect(typeof node._execute).toBe('function');
  });
});

describe('TestBaseNodeModelValidation', () => {
  it('should validate inputs', () => {
    expect(() => {
      ValidNode.Inputs.parse({ name: 123, count: '5' });
    }).toThrow();
  });

  it('should validate outputs', () => {
    expect(() => {
      ValidNode.Outputs.parse({ message: 123, result: 'test' });
    }).toThrow();
  });

  it('should validate secrets', () => {
    expect(() => {
      ValidNode.Secrets.parse({ api_key: 123, token: 'test' });
    }).toThrow();
  });
});

describe('TestBaseNodeConcurrency', () => {
  it('should handle multiple concurrent executions', async () => {
    const node = new ValidNode();
    const inputs = { name: 'test', count: '1' };
    const secrets = { api_key: 'key', token: 'token' };
    
    const promises = Array.from({ length: 5 }, () => node._execute(inputs, secrets));
    const results = await Promise.all(promises);
    
    expect(results).toHaveLength(5);
    results.forEach(result => {
      expect(result).toEqual({
        message: 'Hello test',
        result: 'Count: 1'
      });
    });
  });

  it('should handle node with async operation', async () => {
    class AsyncNode extends BaseNode {
      static Inputs = z.object({
        delay: z.string()
      });

      static Outputs = z.object({
        result: z.string()
      });

      static Secrets = z.object({
        api_key: z.string()
      });

      async execute() {
        const delay = parseFloat(this.inputs.delay);
        await new Promise(resolve => setTimeout(resolve, delay * 1000));
        return { result: `Completed after ${delay}s` };
      }
    }

    const node = new AsyncNode();
    const inputs = { delay: '0.1' };
    const secrets = { api_key: 'test' };
    
    const result = await node._execute(inputs, secrets);
    expect(result.result).toBe('Completed after 0.1s');
  });
});

describe('TestBaseNodeIntegration', () => {
  it('should handle node chain execution', async () => {
    const node1 = new ValidNode();
    const node2 = new NodeWithComplexSecrets();
    
    const inputs1 = { name: 'user1', count: '10' };
    const secrets1 = { api_key: 'key1', token: 'token1' };
    
    const inputs2 = { operation: 'process' };
    const secrets2 = {
      database_url: 'db://test',
      api_key: 'key2',
      encryption_key: 'enc2'
    };
    
    const result1 = await node1._execute(inputs1, secrets1);
    const result2 = await node2._execute(inputs2, secrets2);
    
    expect(result1.message).toBe('Hello user1');
    expect(result2.status).toBe('Operation process completed');
  });

  it('should handle different output types', async () => {
    const node1 = new ValidNode();
    const node2 = new NodeWithListOutput();
    const node3 = new NodeWithNoneOutput();
    
    const inputs1 = { name: 'test', count: '1' };
    const secrets1 = { api_key: 'key', token: 'token' };
    
    const inputs2 = { items: '2' };
    const secrets2 = { api_key: 'key' };
    
    const inputs3 = { name: 'test' };
    const secrets3 = { api_key: 'key' };
    
    const result1 = await node1._execute(inputs1, secrets1);
    const result2 = await node2._execute(inputs2, secrets2);
    const result3 = await node3._execute(inputs3, secrets3);
    
    expect(result1).toEqual({
      message: 'Hello test',
      result: 'Count: 1'
    });
    expect(Array.isArray(result2)).toBe(true);
    expect(result3).toEqual({});
  });
});
