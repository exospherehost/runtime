import { GraphNode, GraphValidationStatus, TriggerState } from './types.js';
import { GraphNodeModel, RetryPolicyModel, StoreConfigModel } from './models.js';

export interface StateManagerOptions {
  stateManagerUri?: string;
  key?: string;
  stateManagerVersion?: string;
}

export class StateManager {
  private stateManagerUri: string;
  private key: string;
  private stateManagerVersion: string;

  constructor(private namespace: string, options: StateManagerOptions = {}) {
    this.stateManagerUri = options.stateManagerUri ?? process.env.EXOSPHERE_STATE_MANAGER_URI ?? '';
    this.key = options.key ?? process.env.EXOSPHERE_API_KEY ?? '';
    this.stateManagerVersion = options.stateManagerVersion ?? 'v0';

    if (!this.stateManagerUri) {
      throw new Error('State manager URI is not set');
    }
    if (!this.key) {
      throw new Error('API key is not set');
    }
  }

  private getTriggerStateEndpoint(graphName: string): string {
    return `${this.stateManagerUri}/${this.stateManagerVersion}/namespace/${this.namespace}/graph/${graphName}/trigger`;
  }

  private getUpsertGraphEndpoint(graphName: string): string {
    return `${this.stateManagerUri}/${this.stateManagerVersion}/namespace/${this.namespace}/graph/${graphName}`;
  }

  private getGetGraphEndpoint(graphName: string): string {
    return `${this.stateManagerUri}/${this.stateManagerVersion}/namespace/${this.namespace}/graph/${graphName}`;
  }

  async trigger(
    graphName: string, 
    inputs?: Record<string, string>, 
    store?: Record<string, string>, 
    startDelay: number = 0
  ): Promise<unknown> {
    if (inputs === undefined) inputs = {};
    if (store === undefined) store = {};

    const body = {
      start_delay: startDelay,
      inputs: inputs,
      store: store
    };
    const headers = { 'x-api-key': this.key } as HeadersInit;

    const endpoint = this.getTriggerStateEndpoint(graphName);
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        ...headers,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    if (!response.ok) {
      throw new Error(`Failed to trigger state: ${response.status} ${await response.text()}`);
    }
    return await response.json();
  }

  async getGraph(graphName: string): Promise<any> {
    const endpoint = this.getGetGraphEndpoint(graphName);
    const headers = { 'x-api-key': this.key } as HeadersInit;
    const response = await fetch(endpoint, { headers });
    if (!response.ok) {
      throw new Error(`Failed to get graph: ${response.status} ${await response.text()}`);
    }
    return await response.json();
  }

  async upsertGraph(
    graphName: string,
    graphNodes: GraphNodeModel[],
    secrets: Record<string, string>,
    retryPolicy?: RetryPolicyModel,
    storeConfig?: StoreConfigModel,
    validationTimeout: number = 60,
    pollingInterval: number = 1
  ): Promise<any> {
    const endpoint = this.getUpsertGraphEndpoint(graphName);
    const headers = { 'x-api-key': this.key } as HeadersInit;
    const body: any = { 
      secrets, 
      nodes: graphNodes.map(node => typeof node === 'object' && 'model_dump' in node ? (node as any).model_dump() : node)
    };

    if (retryPolicy !== undefined) {
      body.retry_policy = typeof retryPolicy === 'object' && 'model_dump' in retryPolicy ? (retryPolicy as any).model_dump() : retryPolicy;
    }
    if (storeConfig !== undefined) {
      body.store_config = typeof storeConfig === 'object' && 'model_dump' in storeConfig ? (storeConfig as any).model_dump() : storeConfig;
    }

    const putResponse = await fetch(endpoint, {
      method: 'PUT',
      headers: {
        ...headers,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    if (!(putResponse.status === 200 || putResponse.status === 201)) {
      throw new Error(`Failed to upsert graph: ${putResponse.status} ${await putResponse.text()}`);
    }
    let graph = await putResponse.json();
    let validationState = graph['validation_status'] as GraphValidationStatus;

    const start = Date.now();
    while (validationState === GraphValidationStatus.PENDING) {
      if (Date.now() - start > validationTimeout * 1000) {
        throw new Error(`Graph validation check timed out after ${validationTimeout} seconds`);
      }
      await new Promise((resolve) => setTimeout(resolve, pollingInterval * 1000));
      graph = await this.getGraph(graphName);
      validationState = graph['validation_status'];
    }

    if (validationState !== GraphValidationStatus.VALID) {
      throw new Error(`Graph validation failed: ${graph['validation_status']} and errors: ${JSON.stringify(graph['validation_errors'])}`);
    }

    return graph;
  }
}
