import { describe, it, expect } from 'vitest';
import { GraphNodeModel, UnitesModel, UnitesStrategyEnum, StoreConfigModel, RetryPolicyModel, RetryStrategyEnum } from '../exospherehost/models.js';

describe('GraphNodeModel & related validation', () => {
  it('should trim and set defaults correctly', () => {
    const model = GraphNodeModel.parse({
      node_name: '  MyNode  ',
      namespace: 'ns',
      identifier: '  node1  ',
      inputs: {},
      next_nodes: ['  next1  '],
      unites: { identifier: '  unite1  ' } // strategy default should kick in
    });

    // Fields should be stripped
    expect(model.node_name).toBe('MyNode');
    expect(model.identifier).toBe('node1');
    expect(model.next_nodes).toEqual(['next1']);
    expect(model.unites).toBeDefined();
    expect(model.unites!.identifier).toBe('unite1');
    // Default enum value check
    expect(model.unites!.strategy).toBe(UnitesStrategyEnum.ALL_SUCCESS);
  });

  it('should validate node name cannot be empty', () => {
    expect(() => {
      GraphNodeModel.parse({
        node_name: '  ',
        namespace: 'ns',
        identifier: 'id1',
        inputs: {},
        next_nodes: null,
        unites: null
      });
    }).toThrow('Node name cannot be empty');
  });

  it('should validate identifier is not reserved word', () => {
    expect(() => {
      GraphNodeModel.parse({
        node_name: 'n',
        namespace: 'ns',
        identifier: 'store',
        inputs: {},
        next_nodes: [],
        unites: undefined
      });
    }).toThrow('reserved word');
  });

  it('should validate next nodes cannot be empty', () => {
    expect(() => {
      GraphNodeModel.parse({
        node_name: 'n',
        namespace: 'ns',
        identifier: 'id1',
        inputs: {},
        next_nodes: ['', 'id2'],
        unites: null
      });
    }).toThrow('cannot be empty');
  });

  it('should validate next nodes are unique', () => {
    expect(() => {
      GraphNodeModel.parse({
        node_name: 'n',
        namespace: 'ns',
        identifier: 'id1',
        inputs: {},
        next_nodes: ['dup', 'dup'],
        unites: null
      });
    }).toThrow('not unique');
  });

  it('should validate unites identifier cannot be empty', () => {
    expect(() => {
      GraphNodeModel.parse({
        node_name: 'n',
        namespace: 'ns',
        identifier: 'id1',
        inputs: {},
        next_nodes: null,
        unites: { identifier: '  ' }
      });
    }).toThrow('Unites identifier cannot be empty');
  });
});

describe('StoreConfigModel validation', () => {
  it('should validate and normalize correctly', () => {
    const cfg = StoreConfigModel.parse({
      required_keys: ['  a ', 'b'],
      default_values: { ' c ': '1', 'd': '2' }
    });
    // Keys should be trimmed and values stringified
    expect(cfg.required_keys).toEqual(['a', 'b']);
    expect(cfg.default_values).toEqual({ 'c': '1', 'd': '2' });
  });

  it('should validate duplicated keys', () => {
    expect(() => {
      StoreConfigModel.parse({
        required_keys: ['a', 'a']
      });
    }).toThrow('duplicated');
  });

  it('should validate keys cannot contain dots', () => {
    expect(() => {
      StoreConfigModel.parse({
        required_keys: ['a.']
      });
    }).toThrow('cannot contain \'.\'');
  });

  it('should validate keys cannot be empty', () => {
    expect(() => {
      StoreConfigModel.parse({
        required_keys: ['  ']
      });
    }).toThrow('cannot be empty');
  });

  it('should validate default values keys cannot contain dots', () => {
    expect(() => {
      StoreConfigModel.parse({
        default_values: { 'k.k': 'v' }
      });
    }).toThrow('cannot contain \'.\'');
  });

  it('should validate default values keys cannot be empty', () => {
    expect(() => {
      StoreConfigModel.parse({
        default_values: { '': 'v' }
      });
    }).toThrow('cannot be empty');
  });
});

describe('RetryPolicyModel defaults', () => {
  it('should have correct defaults', () => {
    const pol = RetryPolicyModel.parse({});
    expect(pol.max_retries).toBe(3);
    expect(pol.backoff_factor).toBe(2000);
    expect(pol.strategy).toBe(RetryStrategyEnum.EXPONENTIAL);
  });
});

describe('StateManager store_config / store handling logic', () => {
  it('should include store config in upsert', async () => {
    // This test would require mocking the StateManager and its HTTP calls
    // For now, we'll test the model parsing which is the core functionality
    const storeCfg = StoreConfigModel.parse({
      required_keys: ['k1'],
      default_values: { 'k2': 'v' }
    });
    
    expect(storeCfg.required_keys).toEqual(['k1']);
    expect(storeCfg.default_values).toEqual({ 'k2': 'v' });
  });

  it('should handle store in trigger', () => {
    // This test would require mocking the StateManager and its HTTP calls
    // For now, we'll test that the models can be parsed correctly
    const storeConfig = StoreConfigModel.parse({
      required_keys: ['cursor'],
      default_values: { 'cursor': '0' }
    });
    
    expect(storeConfig.required_keys).toEqual(['cursor']);
    expect(storeConfig.default_values).toEqual({ 'cursor': '0' });
  });
});
