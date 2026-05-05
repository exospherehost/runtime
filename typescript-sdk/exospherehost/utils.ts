import { ZodFirstPartyTypeKind, ZodObject } from 'zod';
import { z } from 'zod';
import { zodToJsonSchema } from 'zod-to-json-schema';

export function isZodObjectSchema(x: unknown): x is z.ZodObject<any> {
  return !!x
    && typeof x === "object"
    && typeof (x as any).parse === "function"
    && (
      (x as any)._def?.typeName === ZodFirstPartyTypeKind.ZodObject
      // fall back to string to survive enum mismatches
      || (x as any)._def?.typeName === "ZodObject"
    );
}

export function isZodStringSchema(x: unknown): x is z.ZodString {
  return !!x
    && typeof x === "object"
    && typeof (x as any).parse === "function"
    && (
      (x as any)._def?.typeName === ZodFirstPartyTypeKind.ZodString
      // fall back to string to survive enum mismatches
      || (x as any)._def?.typeName === "ZodString"
    );
}

export function generateFlatSchema(zodSchema: ZodObject<any>, title: string) {
  const jsonSchema = zodToJsonSchema(zodSchema);
  
  // If the schema has definitions and $ref, extract the actual schema from definitions
  if ('$ref' in jsonSchema && jsonSchema.$ref && 'definitions' in jsonSchema && jsonSchema.definitions) {
    const refKey = jsonSchema.$ref.replace('#/definitions/', '');
    const actualSchema = jsonSchema.definitions[refKey];
    
    // Return a flat schema matching Python's format
    return {
      type: 'object',
      properties: 'properties' in actualSchema ? actualSchema.properties : {},
      required: 'required' in actualSchema ? actualSchema.required || [] : [],
      title: title,
      additionalProperties: 'additionalProperties' in actualSchema ? actualSchema.additionalProperties || false : false
    };
  }
  
  // If it's already a flat schema, just add the title
  return {
    ...jsonSchema,
    title: title
  };
}
