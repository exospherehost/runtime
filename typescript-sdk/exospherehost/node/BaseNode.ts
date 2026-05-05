import { z, ZodTypeAny, ZodObject } from 'zod';

export abstract class BaseNode<I extends ZodObject<any> = ZodObject<any>, O extends ZodObject<any> = ZodObject<any>, S extends ZodObject<any> = ZodObject<any>> {
  static Inputs: ZodObject<any> = z.object({});
  static Outputs: ZodObject<any> = z.object({});
  static Secrets: ZodObject<any> = z.object({});

  protected inputs!: z.infer<I>;
  protected secrets!: z.infer<S>;

  constructor() {
    if (this.constructor === BaseNode) {
      throw new Error('BaseNode is an abstract class and cannot be instantiated directly');
    }
  }

  async _execute(inputsRaw: unknown, secretsRaw: unknown): Promise<z.infer<O> | z.infer<O>[]> {
    const ctor = this.constructor as typeof BaseNode;
    const inputs = (ctor.Inputs as I).parse(inputsRaw);
    const secrets = (ctor.Secrets as S).parse(secretsRaw);
    this.inputs = inputs;
    this.secrets = secrets;
    const result = await this.execute();
    const outputsSchema = ctor.Outputs as O;
    if (Array.isArray(result)) {
      return result.map(r => outputsSchema.parse(r));
    }
    if (result === null) {
      return {} as z.infer<O>;
    }
    return outputsSchema.parse(result);
  }

  abstract execute(): Promise<z.infer<O> | z.infer<O>[]>;
}

