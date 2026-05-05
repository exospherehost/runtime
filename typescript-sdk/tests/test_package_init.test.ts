import { describe, it, expect } from 'vitest';
import * as exospherehost from '../exospherehost/index.js';

describe('test_package_imports', () => {
  it('should import all expected classes and constants', () => {
    expect(exospherehost.Runtime).toBeDefined();
    expect(exospherehost.BaseNode).toBeDefined();
    expect(exospherehost.StateManager).toBeDefined();
  });
});

describe('test_package_all_imports', () => {
  it('should export all expected classes', () => {
    // Check that all expected exports are available
    const expectedExports = [
      'Runtime',
      'BaseNode', 
      'StateManager',
      'PruneSignal',
      'ReQueueAfterSignal',
      'UnitesStrategyEnum',
      'UnitesModel',
      'GraphNodeModel',
      'RetryStrategyEnum',
      'RetryPolicyModel',
      'StoreConfigModel'
    ];
    
    expectedExports.forEach(exportName => {
      expect(exospherehost[exportName as keyof typeof exospherehost]).toBeDefined();
    });
  });
});

describe('test_runtime_class_import', () => {
  it('should import Runtime class correctly', () => {
    expect(exospherehost.Runtime).toBeDefined();
    expect(typeof exospherehost.Runtime).toBe('function');
  });
});

describe('test_base_node_class_import', () => {
  it('should import BaseNode class correctly', () => {
    expect(exospherehost.BaseNode).toBeDefined();
    expect(typeof exospherehost.BaseNode).toBe('function');
  });
});

describe('test_state_manager_class_import', () => {
  it('should import StateManager class correctly', () => {
    expect(exospherehost.StateManager).toBeDefined();
    expect(typeof exospherehost.StateManager).toBe('function');
  });
});

describe('test_package_structure', () => {
  it('should have expected package structure', () => {
    // Check that the package has expected attributes
    expect(exospherehost.Runtime).toBeDefined();
    expect(exospherehost.BaseNode).toBeDefined();
    expect(exospherehost.StateManager).toBeDefined();
  });
});

describe('test_package_example_usage', () => {
  it('should allow creating a sample node', () => {
    const { BaseNode } = exospherehost;
    const { z } = require('zod');
    
    // Create a sample node as shown in documentation
    class SampleNode extends BaseNode {
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
        return { message: 'success' };
      }
    }
    
    // Test that the node can be instantiated
    const node = new SampleNode();
    expect(node).toBeInstanceOf(BaseNode);
    expect(typeof node.execute).toBe('function');
    
    // Test that Runtime can be referenced
    expect(exospherehost.Runtime).toBeDefined();
    expect(typeof exospherehost.Runtime).toBe('function');
  });
});
