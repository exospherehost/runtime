export interface TriggerState {
  identifier: string;
  inputs: Record<string, string>;
}

export interface GraphNode {
  node_name: string;
  identifier: string;
  inputs: Record<string, unknown>;
  next_nodes?: string[];
  namespace?: string;
}

export const GraphValidationStatus = {
  VALID: 'VALID',
  INVALID: 'INVALID',
  PENDING: 'PENDING',
} as const;
export type GraphValidationStatus =
  (typeof GraphValidationStatus)[keyof typeof GraphValidationStatus];
