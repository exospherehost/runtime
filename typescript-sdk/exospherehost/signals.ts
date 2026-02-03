export class PruneSignal extends Error {
  constructor(public data: Record<string, any> = {}) {
    super(`Prune signal received with data: ${JSON.stringify(data)} \n NOTE: Do not catch this Exception, let it bubble up to Runtime for handling at StateManager`);
  }

  async send(endpoint: string, key: string): Promise<void> {
    const body = { data: this.data };
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 
        'x-api-key': key,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    if (!res.ok) {
      throw new Error(`Failed to send prune signal to ${endpoint}`);
    }
  }
}

export class ReQueueAfterSignal extends Error {
  constructor(public delayMs: number) {
    if (delayMs <= 0) {
      throw new Error('Delay must be greater than 0');
    }
    super(`ReQueueAfter signal received with delay ${delayMs}ms \n NOTE: Do not catch this Exception, let it bubble up to Runtime for handling at StateManager`);
  }

  async send(endpoint: string, key: string): Promise<void> {
    const body = { enqueue_after: this.delayMs };
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 
        'x-api-key': key,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });
    if (!res.ok) {
      throw new Error(`Failed to send requeue after signal to ${endpoint}`);
    }
  }
}

