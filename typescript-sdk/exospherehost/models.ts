import { z } from 'zod';

// Unites Strategy Enum
export enum UnitesStrategyEnum {
  ALL_SUCCESS = 'ALL_SUCCESS',
  ALL_DONE = 'ALL_DONE'
}

// Unites Model
export const UnitesModel = z.object({
  identifier: z.string().describe('Identifier of the node'),
  strategy: z.nativeEnum(UnitesStrategyEnum).default(UnitesStrategyEnum.ALL_SUCCESS).describe('Strategy of the unites')
});

export type UnitesModel = z.infer<typeof UnitesModel>;

// Graph Node Model
export const GraphNodeModel = z.object({
  node_name: z.string()
    .min(1, 'Node name cannot be empty')
    .transform((val: string) => val.trim())
    .refine((val: string) => val.length > 0, 'Node name cannot be empty')
    .describe('Name of the node'),
  namespace: z.string().describe('Namespace of the node'),
  identifier: z.string()
    .min(1, 'Node identifier cannot be empty')
    .transform((val: string) => val.trim())
    .refine((val: string) => val.length > 0, 'Node identifier cannot be empty')
    .refine((val: string) => val !== 'store', 'Node identifier cannot be reserved word \'store\'')
    .describe('Identifier of the node'),
  inputs: z.record(z.unknown()).default({}).describe('Inputs of the node'),
  next_nodes: z.array(z.string())
    .transform((nodes: string[]) => nodes.map((node: string) => node.trim()))
    .refine((nodes: string[]) => {
      const errors: string[] = [];
      const identifiers = new Set<string>();
      
      for (const node of nodes) {
        if (node === '') {
          errors.push('Next node identifier cannot be empty');
          continue;
        }
        if (identifiers.has(node)) {
          errors.push(`Next node identifier ${node} is not unique`);
          continue;
        }
        identifiers.add(node);
      }
      
      if (errors.length > 0) {
        throw new Error(errors.join('\n'));
      }
      return nodes;
    })
    .optional()
    .describe('Next nodes to execute'),
  unites: UnitesModel
    .transform((unites: z.infer<typeof UnitesModel>) => ({
      identifier: unites.identifier.trim(),
      strategy: unites.strategy
    }))
    .refine((unites: { identifier: string; strategy: UnitesStrategyEnum }) => unites.identifier.length > 0, 'Unites identifier cannot be empty')
    .optional()
    .describe('Unites of the node')
});

export type GraphNodeModel = z.infer<typeof GraphNodeModel>;

// Retry Strategy Enum
export enum RetryStrategyEnum {
  EXPONENTIAL = 'EXPONENTIAL',
  EXPONENTIAL_FULL_JITTER = 'EXPONENTIAL_FULL_JITTER',
  EXPONENTIAL_EQUAL_JITTER = 'EXPONENTIAL_EQUAL_JITTER',
  LINEAR = 'LINEAR',
  LINEAR_FULL_JITTER = 'LINEAR_FULL_JITTER',
  LINEAR_EQUAL_JITTER = 'LINEAR_EQUAL_JITTER',
  FIXED = 'FIXED',
  FIXED_FULL_JITTER = 'FIXED_FULL_JITTER',
  FIXED_EQUAL_JITTER = 'FIXED_EQUAL_JITTER'
}

// Retry Policy Model
export const RetryPolicyModel = z.object({
  max_retries: z.number().int().min(0).default(3).describe('The maximum number of retries'),
  strategy: z.nativeEnum(RetryStrategyEnum).default(RetryStrategyEnum.EXPONENTIAL).describe('The method of retry'),
  backoff_factor: z.number().int().positive().default(2000).describe('The backoff factor in milliseconds (default: 2000 = 2 seconds)'),
  exponent: z.number().int().positive().default(2).describe('The exponent for the exponential retry strategy'),
  max_delay: z.number().int().positive().optional().describe('The maximum delay in milliseconds (no default limit when None)')
});

export type RetryPolicyModel = z.infer<typeof RetryPolicyModel>;

// Store Config Model
export const StoreConfigModel = z.object({
  required_keys: z.array(z.string())
    .transform((keys: string[]) => keys.map((key: string) => key.trim()))
    .refine((keys: string[]) => {
      const errors: string[] = [];
      const keySet = new Set<string>();
      
      for (const key of keys) {
        if (key === '') {
          errors.push('Key cannot be empty or contain only whitespace');
          continue;
        }
        if (key.includes('.')) {
          errors.push(`Key '${key}' cannot contain '.' character`);
          continue;
        }
        if (keySet.has(key)) {
          errors.push(`Key '${key}' is duplicated`);
          continue;
        }
        keySet.add(key);
      }
      
      if (errors.length > 0) {
        throw new Error(errors.join('\n'));
      }
      return keys;
    })
    .default([])
    .describe('Required keys of the store'),
  default_values: z.record(z.string())
    .transform((values: Record<string, string>) => {
      const errors: string[] = [];
      const keySet = new Set<string>();
      const normalizedDict: Record<string, string> = {};
      
      for (const [key, value] of Object.entries(values)) {
        const trimmedKey = key.trim();
        
        if (trimmedKey === '') {
          errors.push('Key cannot be empty or contain only whitespace');
          continue;
        }
        if (trimmedKey.includes('.')) {
          errors.push(`Key '${trimmedKey}' cannot contain '.' character`);
          continue;
        }
        if (keySet.has(trimmedKey)) {
          errors.push(`Key '${trimmedKey}' is duplicated`);
          continue;
        }
        
        keySet.add(trimmedKey);
        normalizedDict[trimmedKey] = String(value);
      }
      
      if (errors.length > 0) {
        throw new Error(errors.join('\n'));
      }
      return normalizedDict;
    })
    .default({})
    .describe('Default values of the store')
});

export type StoreConfigModel = z.infer<typeof StoreConfigModel>;
