import { describe, it, expect } from 'vitest';
import { BaseNode } from '../exospherehost/node/BaseNode.js';
import { z } from 'zod';

class EchoNode extends BaseNode {
  static Inputs = z.object({
    text: z.string()
  });

  static Outputs = z.object({
    message: z.string()
  });

  static Secrets = z.object({
    token: z.string()
  });

  async execute() {
    return { message: `${this.inputs.text}:${this.secrets.token}` };
  }
}

describe('test_base_node_execute_sets_inputs_and_returns_outputs', () => {
  it('should set inputs and return outputs correctly', async () => {
    const node = new EchoNode();
    const inputs = { text: 'hello' };
    const secrets = { token: 'tkn' };
    const outputs = await node._execute(inputs, secrets);

    expect(outputs).toEqual({ message: 'hello:tkn' });
    expect(node.inputs).toEqual(inputs);
    expect(node.secrets).toEqual(secrets);
  });
});
