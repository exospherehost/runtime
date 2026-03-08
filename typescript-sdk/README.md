# ExosphereHost TypeScript SDK

[![npm version](https://badge.fury.io/js/exospherehost.svg)](https://badge.fury.io/js/exospherehost)
[![Node.js 18+](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The official TypeScript SDK for [ExosphereHost](https://exosphere.host) - an open-source infrastructure layer for background AI workflows and agents. This SDK enables you to create distributed, stateful applications using a node-based architecture.

## Overview

ExosphereHost provides a robust, affordable, and effortless infrastructure for building scalable AI workflows and agents. The TypeScript SDK allows you to:

- Create distributed workflows using a simple node-based architecture.
- Build stateful applications that can scale across multiple compute resources.
- Execute complex AI workflows with automatic state management.
- Integrate with the ExosphereHost platform for optimized performance.

## Installation

```bash
npm install exospherehost
```

## Quick Start

> Important: In v1, all fields in `Inputs`, `Outputs`, and `Secrets` must be strings. If you need to pass complex data (e.g., JSON), serialize the data to a string first, then parse that string within your node.

### Basic Node Creation

Create a simple node that processes data:

```typescript
import { Runtime, BaseNode } from 'exospherehost';
import { z } from 'zod';

class SampleNode extends BaseNode {
  static name = 'sample-node';
  
  static Inputs = z.object({
    name: z.string(),
    data: z.string() // v1: strings only
  });
  
  static Outputs = z.object({
    message: z.string(),
    processed_data: z.string() // v1: strings only
  });
  
  static Secrets = z.object({});

  async execute() {
    console.log(`Processing data for: ${this.inputs.name}`);
    // Your processing logic here; serialize complex data to strings (e.g., JSON)
    const processed_data = `completed:${this.inputs.data}`;
    return {
      message: "success",
      processed_data: processed_data
    };
  }
}

// Initialize the runtime
const runtime = new Runtime(
  "MyProject",
  "DataProcessor",
  [SampleNode],
  {
    stateManagerUri: process.env.EXOSPHERE_STATE_MANAGER_URI || 'http://localhost:8000',
    key: process.env.EXOSPHERE_API_KEY || '',
    stateManagerVersion: 'v0'
  }
);

await runtime.start();
```

## Environment Configuration

The SDK requires the following environment variables for authentication with ExosphereHost:

```bash
export EXOSPHERE_STATE_MANAGER_URI="your-state-manager-uri"
export EXOSPHERE_API_KEY="your-api-key"
```

## Key Features

- **Distributed Execution**: Run nodes across multiple compute resources
- **State Management**: Automatic state persistence and recovery
- **Type Safety**: Full TypeScript and Zod integration for input/output validation
- **String-only data model (v1)**: All `Inputs`, `Outputs`, and `Secrets` fields are strings. Serialize non-string data (e.g., JSON) as needed.
- **Async Support**: Native async/await support for high-performance operations
- **Error Handling**: Built-in retry mechanisms and error recovery
- **Scalability**: Designed for high-volume batch processing and workflows
- **Graph Store**: Strings-only key-value store with per-run scope for sharing data across nodes (not durable across separate runs or clusters)

## Architecture

The SDK is built around two core concepts:

### Runtime

The `Runtime` class manages the execution environment and coordinates with the ExosphereHost state manager. It handles:

- Node lifecycle management
- State coordination
- Error handling and recovery
- Resource allocation

### Nodes

Nodes are the building blocks of your workflows. Each node:

- Defines input/output schemas using Zod schemas
- Implements an `execute` method for processing logic
- Can be connected to other nodes to form workflows
- Automatically handles state persistence

## Advanced Usage

### Custom Node Configuration

```typescript
import { BaseNode } from 'exospherehost';
import { z } from 'zod';

class ConfigurableNode extends BaseNode {
  static name = 'configurable-node';
  
  static Inputs = z.object({
    text: z.string(),
    max_length: z.string().default("100") // v1: strings only
  });
  
  static Outputs = z.object({
    result: z.string(),
    length: z.string() // v1: strings only
  });
  
  static Secrets = z.object({});

  async execute() {
    const max_length = parseInt(this.inputs.max_length);
    const result = this.inputs.text.substring(0, max_length);
    return {
      result: result,
      length: result.length.toString()
    };
  }
}
```

### Error Handling

```typescript
import { BaseNode } from 'exospherehost';
import { z } from 'zod';

class RobustNode extends BaseNode {
  static name = 'robust-node';
  
  static Inputs = z.object({
    data: z.string()
  });
  
  static Outputs = z.object({
    success: z.string(),
    result: z.string()
  });
  
  static Secrets = z.object({});

  async execute() {
    throw new Error("This is a test error");
  }
}
```

Error handling is automatically handled by the runtime and the state manager.

### Working with Secrets

Secrets allow you to securely manage sensitive configuration data like API keys, database credentials, and authentication tokens. Here's how to use secrets in your nodes:

```typescript
import { BaseNode } from 'exospherehost';
import { z } from 'zod';

class APINode extends BaseNode {
  static name = 'api-node';
  
  static Inputs = z.object({
    user_id: z.string(),
    query: z.string()
  });
  
  static Outputs = z.object({
    response: z.string(), // v1: strings only
    status: z.string()
  });
  
  static Secrets = z.object({
    api_key: z.string(),
    api_endpoint: z.string(),
    database_url: z.string()
  });

  async execute() {
    // Access secrets via this.secrets
    const headers = { "Authorization": `Bearer ${this.secrets.api_key}` };
    
    // Use secrets for API calls
    const response = await fetch(
      `${this.secrets.api_endpoint}/process`,
      {
        method: 'POST',
        headers: {
          ...headers,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          user_id: this.inputs.user_id,
          query: this.inputs.query
        })
      }
    );
    
    // Serialize body: prefer JSON if valid; fallback to text or empty string
    let response_str = "";
    try {
      const responseData = await response.json();
      response_str = JSON.stringify(responseData);
    } catch {
      try {
        response_str = await response.text() || "";
      } catch {
        response_str = "";
      }
    }

    return {
      response: response_str,
      status: "success"
    };
  }
}
```

**Key points about secrets:**

- **Security**: Secrets are stored securely by the ExosphereHost Runtime and are never exposed in logs or error messages
- **Validation**: The `Secrets` schema uses Zod for automatic validation of secret values
- **String-only (v1)**: All `Secrets` fields must be strings.
- **Access**: Secrets are available via `this.secrets` during node execution
- **Types**: Common secret types include API keys, database credentials, encryption keys, and authentication tokens
- **Injection**: Secrets are injected by the Runtime at execution time, so you don't need to handle them manually

### Advanced Control Flow with Signals

The SDK provides signals for advanced control flow:

```typescript
import { BaseNode, PruneSignal, ReQueueAfterSignal } from 'exospherehost';
import { z } from 'zod';

class ConditionalNode extends BaseNode {
  static name = 'conditional-node';
  
  static Inputs = z.object({
    data: z.string(),
    should_retry: z.string()
  });
  
  static Outputs = z.object({
    result: z.string()
  });
  
  static Secrets = z.object({});

  async execute() {
    const shouldRetry = this.inputs.should_retry === 'true';
    
    if (shouldRetry) {
      // Requeue this state after 5 seconds
      throw new ReQueueAfterSignal(5000);
    }
    
    if (this.inputs.data === 'invalid') {
      // Drop this state completely
      throw new PruneSignal();
    }
    
    return {
      result: `Processed: ${this.inputs.data}`
    };
  }
}
```

## State Management

The SDK provides a `StateManager` class for programmatically triggering graph executions and managing workflow states. This is useful for integrating ExosphereHost workflows into existing applications or for building custom orchestration logic.

### StateManager Class

The `StateManager` class allows you to trigger graph executions with custom trigger states and create/update graph definitions using model-based parameters. It handles authentication and communication with the ExosphereHost state manager service.

#### Initialization

```typescript
import { StateManager } from 'exospherehost';

// Initialize with explicit configuration
const stateManager = new StateManager(
  "MyProject",
  {
    stateManagerUri: "https://your-state-manager.exosphere.host",
    key: "your-api-key",
    stateManagerVersion: "v0"
  }
);

// Or initialize with environment variables
const stateManager = new StateManager("MyProject", {
  stateManagerUri: process.env.EXOSPHERE_STATE_MANAGER_URI || 'http://localhost:8000',
  key: process.env.EXOSPHERE_API_KEY || ''
});
```

**Parameters:**

- `namespace` (string): The namespace for your project
- `config.stateManagerUri` (string, optional): The URI of the state manager service. If not provided, reads from `EXOSPHERE_STATE_MANAGER_URI` environment variable
- `config.key` (string, optional): Your API key. If not provided, reads from `EXOSPHERE_API_KEY` environment variable
- `config.stateManagerVersion` (string): The API version to use (default: "v0")

#### Creating/Updating Graph Definitions

```typescript
import { StateManager, GraphNodeModel } from 'exospherehost';

async function createGraph() {
  const stateManager = new StateManager("MyProject", {
    stateManagerUri: process.env.EXOSPHERE_STATE_MANAGER_URI || 'http://localhost:8000',
    key: process.env.EXOSPHERE_API_KEY || ''
  });
  
  // Define graph nodes using models
  const graphNodes: GraphNodeModel[] = [
    {
      node_name: "DataProcessorNode",
      namespace: "MyProject",
      identifier: "data_processor",
      inputs: {
        "source": "initial",
        "format": "json"
      },
      next_nodes: ["data_validator"]
    },
    {
      node_name: "DataValidatorNode", 
      namespace: "MyProject",
      identifier: "data_validator",
      inputs: {
        "data": "${{ data_processor.outputs.processed_data }}",
        "validation_rules": "initial"
      },
      next_nodes: []
    }
  ];
  
  // Create or update the graph 
  const result = await stateManager.upsertGraph(
    "my-workflow",
    graphNodes,
    {
      "api_key": "your-api-key",
      "database_url": "your-database-url"
    }
  );
  
  console.log(`Graph created/updated: ${result.validation_status}`);
  return result;
}
```

**Parameters:**

- `graphName` (string): Name of the graph to create/update
- `graphNodes` (GraphNodeModel[]): List of graph node models defining the workflow 
- `secrets` (Record<string, string>): Key/value secrets available to all nodes

**Returns:**

- `Promise<any>`: Validated graph object returned by the API

**Raises:**

- `Error`: If validation fails or times out

#### Triggering Graph Execution

```typescript
import { StateManager } from 'exospherehost';

// Create a single trigger state
const triggerState = {
  identifier: "user-login",
  inputs: {
    "user_id": "12345",
    "session_token": "abc123def456",
    "timestamp": "2024-01-15T10:30:00Z"
  }
};

// Trigger the graph 
const result = await stateManager.trigger(
  "my-graph",
  {
    "user_id": "12345",
    "session_token": "abc123def456"
  },
  {
    "cursor": "0" // persisted across nodes
  }
);
```

**Parameters:**

- `graphName` (string): Name of the graph to execute
- `inputs` (Record<string, string> | undefined): Key/value inputs for the first node (strings only)
- `store` (Record<string, string> | undefined): Graph-level key/value store persisted across nodes

**Returns:**

- `Promise<any>`: JSON payload from the state manager

**Raises:**

- `Error`: If the HTTP request fails

## Complete Minimal Example

Here's a complete example that demonstrates the full workflow:

```typescript
import { StateManager, BaseNode, Runtime, GraphNodeModel } from 'exospherehost';
import { z } from 'zod';

// 1. Define a custom node
class GreetingNode extends BaseNode {
  static name = 'greeting';
  
  static Inputs = z.object({
    name: z.string()
  });
  
  static Outputs = z.object({
    greeting: z.string()
  });
  
  static Secrets = z.object({});

  async execute() {
    return {
      greeting: `Hello, ${this.inputs.name}!`
    };
  }
}

// 2. Set up the state manager
const sm = new StateManager('example-namespace', {
  stateManagerUri: 'http://localhost:8000',
  key: 'your-api-key'
});

// 3. Define the workflow graph
const nodes: GraphNodeModel[] = [
  {
    node_name: 'greeting',
    namespace: 'example-namespace',
    identifier: 'greeter',
    inputs: {
      name: "store.name"
    }
  }
];

// 4. Create the graph
await sm.upsertGraph('greeting-workflow', nodes, {});

// 5. Start the runtime to process nodes
const runtime = new Runtime('example-namespace', 'greeting-runtime', [GreetingNode], {
  stateManagerUri: 'http://localhost:8000',
  key: 'your-api-key'
});

await runtime.start();

// 6. Trigger the workflow
const store = { name: 'World' };
await sm.trigger('greeting-workflow', { name: 'World' }, store);
```

## License

MIT