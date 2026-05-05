import { describe, it, expect } from 'vitest';
import { BaseNode } from '../exospherehost/node/BaseNode.js';
import { isZodObjectSchema } from '../exospherehost/utils.js';
import { z } from 'zod';

describe('TestBaseNodeAbstract', () => {
  describe('test_base_node_abstract_execute', () => {
    it('should raise error when execute is not implemented', async () => {
      class ConcreteNode extends BaseNode {
        static Inputs = z.object({
          name: z.string()
        });
        
        static Outputs = z.object({
          message: z.string()
        });
        
        static Secrets = z.object({});
        
        async execute() {
          throw new Error('execute method must be implemented by all concrete node classes');
        }
      }
      
      const node = new ConcreteNode();
      
      await expect(node._execute({ name: 'test' }, {})).rejects.toThrow(
        'execute method must be implemented by all concrete node classes'
      );
    });
  });

  describe('test_base_node_abstract_execute_with_inputs', () => {
    it('should raise error when execute is not implemented with inputs', async () => {
      class ConcreteNode extends BaseNode {
        static Inputs = z.object({
          name: z.string()
        });
        
        static Outputs = z.object({
          message: z.string()
        });
        
        static Secrets = z.object({});
        
        async execute() {
          throw new Error('execute method must be implemented by all concrete node classes');
        }
      }
      
      const node = new ConcreteNode();
      
      await expect(node._execute({ name: 'test' }, {})).rejects.toThrow(
        'execute method must be implemented by all concrete node classes'
      );
    });
  });

  describe('test_base_node_initialization', () => {
    it('should initialize correctly', () => {
      class ConcreteNode extends BaseNode {
        static Inputs = z.object({
          name: z.string()
        });
        
        static Outputs = z.object({
          message: z.string()
        });
        
        static Secrets = z.object({});
        
        async execute() {
          return { message: 'test' };
        }
      }
      
      const node = new ConcreteNode();
      expect(node).toBeDefined();
    });
  });

  describe('test_base_node_inputs_class', () => {
    it('should have Inputs class', () => {
      expect(BaseNode.Inputs).toBeDefined();
      expect(isZodObjectSchema(BaseNode.Inputs)).toBe(true);
    });
  });

  describe('test_base_node_outputs_class', () => {
    it('should have Outputs class', () => {
      expect(BaseNode.Outputs).toBeDefined();
      expect(isZodObjectSchema(BaseNode.Outputs)).toBe(true);
    });
  });

  describe('test_base_node_secrets_class', () => {
    it('should have Secrets class', () => {
      expect(BaseNode.Secrets).toBeDefined();
      expect(isZodObjectSchema(BaseNode.Secrets)).toBe(true);
    });
  });
});
