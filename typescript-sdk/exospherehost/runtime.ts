import { BaseNode } from './node/index.js';
import { PruneSignal, ReQueueAfterSignal } from './signals.js';
import { ZodObject } from 'zod';
import { logger } from './logger.js';
import { isZodObjectSchema, isZodStringSchema, generateFlatSchema } from './utils.js';


interface RuntimeOptions {
  stateManagerUri?: string;
  key?: string;
  batchSize?: number;
  workers?: number;
  stateManagerVersion?: string;
  pollInterval?: number;
}

interface StateItem {
  state_id: string;
  node_name: string;
  inputs: Record<string, string>;
}

class AsyncQueue<T> {
  private items: T[] = [];
  private resolvers: ((value: T) => void)[] = [];
  constructor(private capacity: number) {}

  size() {
    return this.items.length;
  }

  async put(item: T) {
    if (this.resolvers.length) {
      const resolve = this.resolvers.shift()!;
      resolve(item);
    } else {
      this.items.push(item);
    }
  }

  async get(): Promise<T> {
    if (this.items.length) {
      return this.items.shift()!;
    }
    return new Promise<T>(resolve => {
      this.resolvers.push(resolve);
    });
  }
}

type NodeCtor = (new () => BaseNode<any, any, any>) & {
  Inputs: ZodObject<any>;
  Outputs: ZodObject<any>;
  Secrets: ZodObject<any>;
  name: string;
};

export class Runtime {
  private key: string;
  private stateManagerUri: string;
  private stateManagerVersion: string;
  private batchSize: number;
  private workers: number;
  private pollInterval: number;
  private stateQueue: AsyncQueue<StateItem>;
  private nodeMapping: Record<string, NodeCtor>;
  private nodeNames: string[];

  constructor(
    private namespace: string,
    private name: string,
    private nodes: NodeCtor[],
    options: RuntimeOptions = {}
  ) {
    this.stateManagerUri = options.stateManagerUri ?? process.env.EXOSPHERE_STATE_MANAGER_URI ?? '';
    this.key = options.key ?? process.env.EXOSPHERE_API_KEY ?? '';
    this.stateManagerVersion = options.stateManagerVersion ?? 'v0';
    this.batchSize = options.batchSize ?? 16;
    this.workers = options.workers ?? 4;
    this.pollInterval = options.pollInterval ?? 1000;
    this.stateQueue = new AsyncQueue<StateItem>(2 * this.batchSize);
    this.nodeMapping = Object.fromEntries(nodes.map(n => [n.name, n]));
    this.nodeNames = nodes.map(n => n.name);

    this.validateRuntime();
    this.validateNodes();
    
    logger.debug('Runtime', `Initialized runtime with namespace: ${this.namespace}, name: ${this.name}, nodes: ${this.nodeNames.join(', ')}`);
  }

  private validateRuntime(): void {
    if (this.batchSize < 1) {
      throw new Error('Batch size should be at least 1');
    }
    if (this.workers < 1) {
      throw new Error('Workers should be at least 1');
    }
    if (!this.stateManagerUri) {
      throw new Error('State manager URI is not set');
    }
    if (!this.key) {
      throw new Error('API key is not set');
    }
  }

  private getEnqueueEndpoint() {
    return `${this.stateManagerUri}/${this.stateManagerVersion}/namespace/${this.namespace}/states/enqueue`;
  }
  private getExecutedEndpoint(stateId: string) {
    return `${this.stateManagerUri}/${this.stateManagerVersion}/namespace/${this.namespace}/state/${stateId}/executed`;
  }
  private getErroredEndpoint(stateId: string) {
    return `${this.stateManagerUri}/${this.stateManagerVersion}/namespace/${this.namespace}/state/${stateId}/errored`;
  }
  private getRegisterEndpoint() {
    return `${this.stateManagerUri}/${this.stateManagerVersion}/namespace/${this.namespace}/nodes/`;
  }
  private getSecretsEndpoint(stateId: string) {
    return `${this.stateManagerUri}/${this.stateManagerVersion}/namespace/${this.namespace}/state/${stateId}/secrets`;
  }
  private getPruneEndpoint(stateId: string) {
    return `${this.stateManagerUri}/${this.stateManagerVersion}/namespace/${this.namespace}/state/${stateId}/prune`;
  }
  private getRequeueAfterEndpoint(stateId: string) {
    return `${this.stateManagerUri}/${this.stateManagerVersion}/namespace/${this.namespace}/state/${stateId}/re-enqueue-after`;
  }


  private async register() {
    const nodeNames = this.nodes.map(node => `${this.namespace}/${node.name}`);
    logger.info('Runtime', `Registering nodes: ${nodeNames.join(', ')}`);
    
    const body = {
      runtime_name: this.name,
      nodes: this.nodes.map(node => ({
        name: node.name,
        inputs_schema: generateFlatSchema(node.Inputs, 'Inputs'),
        outputs_schema: generateFlatSchema(node.Outputs, 'Outputs'),
        secrets: Object.keys((node.Secrets as ZodObject<any>).shape)
      }))
    };
    const res = await fetch(this.getRegisterEndpoint(), {
      method: 'PUT',
      headers: { 
        'x-api-key': this.key,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      const errorText = await res.text();
      logger.error('Runtime', `Failed to register nodes: ${errorText}`);
      throw new Error(`Failed to register nodes: ${errorText}`);
    }
    
    logger.info('Runtime', `Registered nodes: ${nodeNames.join(', ')}`);
    return res.json();
  }

  private async enqueueCall() {
    const res = await fetch(this.getEnqueueEndpoint(), {
      method: 'POST',
      headers: { 
        'x-api-key': this.key,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ nodes: this.nodeNames, batch_size: this.batchSize })
    });
    if (!res.ok) {
      throw new Error(`Failed to enqueue states: ${await res.text()}`);
    }
    return await res.json();
  }

  private async enqueue() {
    while (true) {
      try {
        if (this.stateQueue.size() < this.batchSize) {
          const data = await this.enqueueCall();
          const states = data.states ?? [];
          for (const state of states) {
            await this.stateQueue.put(state);
          }
          logger.info('Runtime', `Enqueued states: ${states.length}`);
        }
      } catch (e) {
        logger.error('Runtime', `Error enqueuing states: ${e}`);
        await new Promise(r => setTimeout(r, this.pollInterval * 2));
        continue;
      }
      await new Promise(r => setTimeout(r, this.pollInterval));
    }
  }

  private async notifyExecuted(stateId: string, outputs: any[]) {
    const res = await fetch(this.getExecutedEndpoint(stateId), {
      method: 'POST',
      headers: { 
        'x-api-key': this.key,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ outputs })
    });
    if (!res.ok) {
      const errorText = await res.text();
      logger.error('Runtime', `Failed to notify executed state ${stateId}: ${errorText}`);
    }
  }

  private async notifyErrored(stateId: string, error: string) {
    const res = await fetch(this.getErroredEndpoint(stateId), {
      method: 'POST',
      headers: { 
        'x-api-key': this.key,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ error })
    });
    if (!res.ok) {
      const errorText = await res.text();
      logger.error('Runtime', `Failed to notify errored state ${stateId}: ${errorText}`);
    }
  }

  private async getSecrets(stateId: string): Promise<Record<string, string>> {
    const res = await fetch(this.getSecretsEndpoint(stateId), {
      headers: { 
        'x-api-key': this.key,
        'Content-Type': 'application/json'
       }
    });
    if (!res.ok) {
      const errorText = await res.text();
      logger.error('Runtime', `Failed to get secrets for state ${stateId}: ${errorText}`);
      return {};
    }
    const data = await res.json();
    if (!('secrets' in data)) {
      logger.error('Runtime', `'secrets' not found in response for state ${stateId}`);
      return {};
    }
    return data.secrets ?? {};
  }

  private validateNodes() {
    const errors: string[] = [];
    for (const node of this.nodes as NodeCtor[]) {
      const nodeName = node.name;
      if (!(node.prototype instanceof BaseNode)) {
        errors.push(`${nodeName} does not inherit from BaseNode`);
      }
      if (!('Inputs' in node)) errors.push(`${nodeName} missing Inputs schema`);
      if (!('Outputs' in node)) errors.push(`${nodeName} missing Outputs schema`);
      if (!('Secrets' in node)) errors.push(`${nodeName} missing Secrets schema`);

      // Validate that schemas are actually ZodObject instances
      if (!isZodObjectSchema(node.Inputs)) {
        errors.push(`${nodeName}.Inputs must be a ZodObject schema`);
      }
      if (!isZodObjectSchema(node.Outputs)) {
        errors.push(`${nodeName}.Outputs must be a ZodObject schema`);
      }
      if (!isZodObjectSchema(node.Secrets)) {
        errors.push(`${nodeName}.Secrets must be a ZodObject schema`);
      }
      
      const inputs = node.Inputs as ZodObject<any>;
      const outputs = node.Outputs as ZodObject<any>;
      const secrets = node.Secrets as ZodObject<any>;
      const checkStrings = (schema: ZodObject<any>, label: string) => {
        for (const key in schema.shape) {
          if (!isZodStringSchema(schema.shape[key])) {
            errors.push(`${nodeName}.${label} field '${key}' must be string`);
          }
        }
      };
      checkStrings(inputs, 'Inputs');
      checkStrings(outputs, 'Outputs');
      checkStrings(secrets, 'Secrets');
    }
    const names = this.nodes.map(n => n.name);
    const duplicates = names.filter((n, i) => names.indexOf(n) !== i);
    if (duplicates.length) {
      errors.push(`Duplicate node class names found: ${duplicates.join(', ')}`);
    }
    if (errors.length) {
      throw new Error('Node validation errors:\n' + errors.join('\n'));
    }
  }

  private needSecrets(node: typeof BaseNode) {
    return Object.keys((node.Secrets as ZodObject<any>).shape).length > 0;
  }

  private async worker(idx: number) {
    const nodeNames = this.nodes.map(node => `${this.namespace}/${node.name}`);
    logger.info('Runtime', `Starting worker thread ${idx} for nodes: ${nodeNames.join(', ')}`);

    while (true) {
      const state = await this.stateQueue.get();
      const nodeCls = this.nodeMapping[state.node_name];
      
      if (!nodeCls) {
        logger.error('Runtime', `Unknown node: ${state.node_name}`);
        await this.notifyErrored(state.state_id, 'Unknown node');
        continue;
      }
      
      const node = new nodeCls();
      logger.info('Runtime', `Executing state ${state.state_id} for node ${nodeCls.name}`);
      
      try {
        let secrets: Record<string, string> = {};
        if (this.needSecrets(nodeCls)) {
          secrets = await this.getSecrets(state.state_id);
          logger.info('Runtime', `Got secrets for state ${state.state_id} for node ${nodeCls.name}`);
        }
        
        const outputs = await node._execute(state.inputs, secrets);
        logger.info('Runtime', `Got outputs for state ${state.state_id} for node ${nodeCls.name}`);
        
        const outArray = Array.isArray(outputs) ? outputs : [outputs];
        await this.notifyExecuted(state.state_id, outArray);
        logger.info('Runtime', `Notified executed state ${state.state_id} for node ${nodeCls.name}`);
        
      } catch (err) {
        if (err instanceof PruneSignal) {
          logger.info('Runtime', `Pruning state ${state.state_id} for node ${nodeCls.name}`);
          await err.send(this.getPruneEndpoint(state.state_id), this.key);
          logger.info('Runtime', `Pruned state ${state.state_id} for node ${nodeCls.name}`);
        } else if (err instanceof ReQueueAfterSignal) {
          logger.info('Runtime', `Requeuing state ${state.state_id} for node ${nodeCls.name} after ${err.delayMs}ms`);
          await err.send(this.getRequeueAfterEndpoint(state.state_id), this.key);
          logger.info('Runtime', `Requeued state ${state.state_id} for node ${nodeCls.name} after ${err.delayMs}ms`);
        } else {
          logger.error('Runtime', `Error executing state ${state.state_id} for node ${nodeCls.name}: ${err}`);
          await this.notifyErrored(state.state_id, (err as Error).message);
          logger.info('Runtime', `Notified errored state ${state.state_id} for node ${nodeCls.name}`);
        }
      }
    }
  }

  private async startInternal() {
    await this.register();
    logger.info('Runtime', `Registered nodes: ${this.nodeNames.join(', ')}`);
    const poller = this.enqueue();
    const workers = Array.from({ length: this.workers }, (_, idx) => this.worker(idx));
    await Promise.all([poller, ...workers]);
    logger.info('Runtime', `Started workers: ${this.workers}`);
  }

  start() {
    return this.startInternal();
  }
}

