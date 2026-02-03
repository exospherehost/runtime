'use client';

import React, { useMemo, useState, useCallback } from 'react';
import { UpsertGraphTemplateResponse, NodeTemplate } from '@/types/state-manager';
import { X, GitBranch, Settings, Database, Workflow, Clock } from 'lucide-react';
import ReactFlow, { 
  Node, 
  Edge, 
  Controls, 
  useNodesState, 
  useEdgesState,
  Position,
  MarkerType,
  Handle
} from 'reactflow';
import 'reactflow/dist/style.css';

// Shadcn components
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface GraphTemplateDetailProps {
  graphTemplate: UpsertGraphTemplateResponse | null;
  isOpen: boolean;
  onClose: () => void;
}

const RETRY_STRATEGIES = [
  { value: 'EXPONENTIAL', label: 'Exponential' },
  { value: 'EXPONENTIAL_FULL_JITTER', label: 'Exponential Full Jitter' },
  { value: 'EXPONENTIAL_EQUAL_JITTER', label: 'Exponential Equal Jitter' },
  { value: 'LINEAR', label: 'Linear' },
  { value: 'LINEAR_FULL_JITTER', label: 'Linear Full Jitter' },
  { value: 'LINEAR_EQUAL_JITTER', label: 'Linear Equal Jitter' },
  { value: 'FIXED', label: 'Fixed' },
  { value: 'FIXED_FULL_JITTER', label: 'Fixed Full Jitter' },
  { value: 'FIXED_EQUAL_JITTER', label: 'Fixed Equal Jitter' },
];

// Custom node component for React Flow
const CustomNode: React.FC<{ data: NodeTemplate & { index: number } }> = ({ data }) => {
  return (
    <div className="px-4 py-3 shadow-sm rounded-xl border border-border min-w-[180px] relative bg-background">
      {/* Target Handle (Left side) */}
      <Handle
        type="target"
        position={Position.Left}
        id="target"
        style={{ background: 'var(--primary)', width: '12px', height: '12px' }}
      />
      
      {/* Source Handle (Right side) - only show if node has next_nodes */}
      {data.next_nodes && data.next_nodes.length > 0 && (
        <Handle
          type="source"
          position={Position.Right}
          id="source"
          style={{ background: 'hsl(var(--primary))', width: '12px', height: '12px' }}
        />
      )}
      
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Badge variant="outline" className="text-xs">
            #{data.index + 1}
          </Badge>
        </div>
      </div>
      
      <div className="text-sm font-medium text-card-foreground mb-1">{data.identifier}</div>
      <div className="text-xs text-muted-foreground mb-2">{data.node_name}</div>
      
      <div className="text-xs text-muted-foreground space-y-1">
        <div><span className="font-medium">Namespace:</span> {data.namespace}</div>
        <div><span className="font-medium">Inputs:</span> {Object.keys(data.inputs).length}</div>
      </div>
    </div>
  );
};

// Node types for React Flow
const nodeTypes = {
  custom: CustomNode,
};

const GraphVisualizer: React.FC<{ nodes: NodeTemplate[] }> = ({ nodes }) => {
  const { flowNodes, flowEdges } = useMemo(() => {
    if (!nodes || nodes.length === 0) {
      return { flowNodes: [], flowEdges: [] };
    }

    // Create a map of node identifiers for easier lookup
    const nodeMap = new Map(nodes.map((node, index) => [node.identifier, { node, index }]));

    // Build adjacency lists for layout calculation
    const childrenMap = new Map<string, string[]>();
    const parentMap = new Map<string, string[]>();

    // Initialize maps
    nodes.forEach(node => {
      childrenMap.set(node.identifier, []);
      parentMap.set(node.identifier, []);
    });

    // Build relationships based on next_nodes
    nodes.forEach((node) => {
      if (node.next_nodes && Array.isArray(node.next_nodes)) {
        node.next_nodes.forEach((nextNodeId) => {
          if (nodeMap.has(nextNodeId)) {
            const children = childrenMap.get(node.identifier) || [];
            children.push(nextNodeId);
            childrenMap.set(node.identifier, children);

            const parents = parentMap.get(nextNodeId) || [];
            parents.push(node.identifier);
            parentMap.set(nextNodeId, parents);
          }
        });
      }
    });

    // Find root nodes (nodes with no parents)
    const rootNodes = nodes.filter(node => 
      (parentMap.get(node.identifier) || []).length === 0
    );

    // Build layers for horizontal layout
    const layers: NodeTemplate[][] = [];
    const visited = new Set<string>();

    // Start with root nodes
    if (rootNodes.length > 0) {
      layers.push(rootNodes);
      rootNodes.forEach(node => visited.add(node.identifier));
    }

    // Build layers
    let currentLayer = 0;
    while (visited.size < nodes.length && currentLayer < nodes.length) {
      const currentLayerNodes = layers[currentLayer] || [];
      const nextLayer: NodeTemplate[] = [];

      currentLayerNodes.forEach(node => {
        const children = childrenMap.get(node.identifier) || [];
        children.forEach(childId => {
          if (!visited.has(childId)) {
            const childNodeData = nodeMap.get(childId);
            if (childNodeData && !nextLayer.find(n => n.identifier === childId)) {
              nextLayer.push(childNodeData.node);
            }
          }
        });
      });

      if (nextLayer.length > 0) {
        layers.push(nextLayer);
        nextLayer.forEach(node => visited.add(node.identifier));
      }

      currentLayer++;
    }

    // Add any remaining nodes
    const remainingNodes = nodes.filter(node => !visited.has(node.identifier));
    if (remainingNodes.length > 0) {
      layers.push(remainingNodes);
    }

    // Convert to React Flow nodes with horizontal positioning
    const flowNodes: Node[] = [];
    const layerWidth = 400; // Horizontal spacing between layers
    const nodeHeight = 150; // Vertical spacing between nodes

    layers.forEach((layer, layerIndex) => {
      const layerX = layerIndex * layerWidth + 150;
      const totalHeight = layer.length * nodeHeight;
      const startY = (800 - totalHeight) / 2; // Center vertically

      layer.forEach((node, nodeIndex) => {
        const originalIndex = nodeMap.get(node.identifier)?.index || 0;
        const y = startY + nodeIndex * nodeHeight + nodeHeight / 2;

        flowNodes.push({
          id: node.identifier,
          type: 'custom',
          position: { x: layerX, y },
          data: { ...node, index: originalIndex },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          connectable: false,
          draggable: false,
        });
      });
    });

    // Create edges based on next_nodes relationships
    const flowEdges: Edge[] = [];
    nodes.forEach((node) => {
      // Ensure next_nodes exists and is an array
      if (node.next_nodes && Array.isArray(node.next_nodes)) {
        node.next_nodes.forEach((nextNodeId) => {
          // Only create edge if target node exists in the graph
          if (nodeMap.has(nextNodeId)) {
            flowEdges.push({
              id: `${node.identifier}-${nextNodeId}`,
              source: node.identifier,
              target: nextNodeId,
              sourceHandle: 'source',
              targetHandle: 'target',
              type: 'default',
              animated: false,
              style: { 
                stroke: 'var(--chart-1)',
                strokeWidth: 2,
                strokeDasharray: 'none',
              },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                width: 10,
                height: 10,
                color: 'var(--chart-1)',
              },
            });
          } else {
            // Log warning for dangling references (optional - for debugging)
            console.warn(`Node "${node.identifier}" references non-existent next node: "${nextNodeId}"`);
          }
        });
      }
    });

    return { flowNodes, flowEdges };
  }, [nodes]);

  const [flowNodesState, , onNodesChange] = useNodesState(flowNodes);
  const [flowEdgesState, , onEdgesChange] = useEdgesState(flowEdges);

  if (nodes.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center space-x-2">
            <GitBranch className="w-4 h-4" />
            <span>Graph Structure</span>
          </CardTitle>
          <CardDescription>Visual representation of the workflow nodes</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No nodes in this graph template.</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const [isInteractive, setIsInteractive] = useState(true);
  const handleInteractiveChange = useCallback((val: boolean) => setIsInteractive(val), []);

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center space-x-2">
          <GitBranch className="w-4 h-4" />
          <span>Graph Structure</span>
        </CardTitle>
        <CardDescription>Interactive visualization of the workflow nodes and their connections</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="border border-border rounded-xl overflow-hidden" style={{ height: '400px' }}>
          <ReactFlow
            nodes={flowNodesState}
            edges={flowEdgesState}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            fitViewOptions={{ padding: 0.3 }}
            minZoom={0.1}
            maxZoom={2}
            defaultViewport={{ x: 0, y: 0, zoom: 1.5 }}
            elementsSelectable={isInteractive}
            nodesConnectable={false}
            nodesDraggable={isInteractive}
            zoomOnScroll={isInteractive}
            panOnScroll={isInteractive}
            panOnDrag={isInteractive}
            zoomOnPinch={isInteractive}
            zoomOnDoubleClick={isInteractive}
            className="bg-background"
          >
            <Controls 
              position="bottom-left"
              onInteractiveChange={handleInteractiveChange} 
            />
          </ReactFlow>
        </div>
      </CardContent>
    </Card>
  );
};

const NodeDetailView: React.FC<{ node: NodeTemplate; index: number }> = ({ node, index }) => {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">
            Node {index + 1}: {node.identifier}
          </CardTitle>
          <Badge variant="outline" className="text-xs">
            {index + 1}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Node Name</label>
            <div className="text-sm font-mono bg-muted p-2 rounded mt-1">
              {node.node_name}
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Namespace</label>
            <div className="text-sm font-mono bg-muted p-2 rounded mt-1">
              {node.namespace}
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Identifier</label>
            <div className="text-sm font-mono bg-muted p-2 rounded mt-1">
              {node.identifier}
            </div>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Next Nodes</label>
            <div className="text-sm font-mono bg-muted p-2 rounded mt-1">
              {node.next_nodes.length > 0 ? node.next_nodes.join(', ') : 'None'}
            </div>
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-muted-foreground mb-2 block">Node Inputs</label>
          <div className="bg-muted p-3 rounded border max-h-32 overflow-y-auto">
            <pre className="text-xs font-mono text-foreground whitespace-pre-wrap">
              {JSON.stringify(node.inputs, null, 2)}
            </pre>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

interface RetryPolicy {
  max_retries: number;
  strategy: string;
  backoff_factor: number;
  exponent: number;
  max_delay?: number;
}

const RetryPolicyViewer: React.FC<{ 
  retryPolicy: RetryPolicy;
}> = ({ retryPolicy }) => {
  const getStrategyLabel = (strategy: string) => {
    return RETRY_STRATEGIES.find(s => s.value === strategy)?.label || strategy;
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center space-x-2">
          <Clock className="w-4 h-4" />
          <span>Retry Policy Configuration</span>
        </CardTitle>
        <CardDescription>Current retry policy settings for handling node execution failures</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Max Retries</label>
            <div className="text-sm font-mono bg-muted p-2 rounded mt-1">
              {retryPolicy.max_retries}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Maximum number of retry attempts</p>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Retry Strategy</label>
            <div className="text-sm font-mono bg-muted p-2 rounded mt-1">
              {getStrategyLabel(retryPolicy.strategy)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Strategy for calculating retry delays</p>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Backoff Factor</label>
            <div className="text-sm font-mono bg-muted p-2 rounded mt-1">
              {retryPolicy.backoff_factor} ms
            </div>
            <p className="text-xs text-muted-foreground mt-1">Base delay in milliseconds</p>
          </div>

          <div>
            <label className="text-xs font-medium text-muted-foreground">Exponent</label>
            <div className="text-sm font-mono bg-muted p-2 rounded mt-1">
              {retryPolicy.exponent}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Multiplier for exponential strategies</p>
          </div>

          <div className="md:col-span-2">
            <label className="text-xs font-medium text-muted-foreground">Max Delay</label>
            <div className="text-sm font-mono bg-muted p-2 rounded mt-1">
              {retryPolicy.max_delay ? `${retryPolicy.max_delay} ms` : 'No maximum delay'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Maximum delay cap in milliseconds</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

interface StoreConfig {
  required_keys?: string[];
  default_values?: Record<string, unknown>;
}

const StoreConfigViewer: React.FC<{ 
  storeConfig: StoreConfig;
}> = ({ storeConfig }) => {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center space-x-2">
            <Database className="w-4 h-4" />
            <span>Required Keys</span>
          </CardTitle>
          <CardDescription>Keys that must be present in the store when triggering the graph</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            {storeConfig.required_keys && storeConfig.required_keys.length > 0 ? (
              storeConfig.required_keys.map((key: string, index: number) => (
                <div key={index} className="text-sm font-mono bg-muted p-2 rounded">
                  {key}
                </div>
              ))
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                <p>No required keys configured</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center space-x-2">
            <Settings className="w-4 h-4" />
            <span>Default Values</span>
          </CardTitle>
          <CardDescription>Default values for store keys when they are not provided</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            {storeConfig.default_values && Object.keys(storeConfig.default_values).length > 0 ? (
              Object.entries(storeConfig.default_values).map(([key, value]) => (
                <div key={key} className="grid grid-cols-2 gap-2">
                  <div className="text-sm font-mono bg-muted p-2 rounded">
                    {key}
                  </div>
                  <div className="text-sm font-mono bg-muted p-2 rounded">
                    {String(value)}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-4 text-muted-foreground">
                <p>No default values configured</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export const GraphTemplateDetail: React.FC<GraphTemplateDetailProps> = ({
  graphTemplate,
  isOpen,
  onClose
}) => {
  if (!isOpen || !graphTemplate) return null;

  return (
    <Card className="w-full">
      {/* Header */}
      <CardHeader className="bg-background/60 border-b">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl">{graphTemplate.name}</CardTitle>
            <CardDescription className="mt-1">
              Graph Template Configuration
            </CardDescription>
          </div>
          <Button
            onClick={onClose}
            variant="ghost"
            size="sm"
          >
            <X className="w-5 h-5" />
          </Button>
        </div>
      </CardHeader>

      {/* Content */}
      <CardContent className="p-6">
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="visualization">Visualization</TabsTrigger>
            <TabsTrigger value="nodes">Nodes</TabsTrigger>
            <TabsTrigger value="retry-policy">Retry Policy</TabsTrigger>
            <TabsTrigger value="store-config">Store Config</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6 mt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center space-x-2">
                    <Database className="w-4 h-4" />
                    <span>Template Information</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Name</label>
                    <div className="text-sm font-mono bg-muted p-2 rounded mt-1">{graphTemplate.name}</div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Namespace</label>
                    <div className="text-sm font-mono bg-muted p-2 rounded mt-1">{graphTemplate.namespace}</div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Created</label>
                    <div className="text-sm bg-muted p-2 rounded mt-1">
                      {new Date(graphTemplate.created_at).toLocaleString()}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center space-x-2">
                    <Workflow className="w-4 h-4" />
                    <span>Statistics</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Total Nodes</span>
                    <Badge variant="secondary">{graphTemplate.nodes?.length || 0}</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Secrets</span>
                    <Badge variant="secondary">
                      {graphTemplate.secrets ? Object.keys(graphTemplate.secrets).length : 0}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Status</span>
                    <Badge variant={graphTemplate.validation_status === 'VALID' ? 'default' : 'destructive'}>
                      {graphTemplate.validation_status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            </div>

            {graphTemplate.validation_errors && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">Validation Errors</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-sm bg-muted p-3 rounded border">
                    {graphTemplate.validation_errors}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="visualization" className="mt-6">
            <GraphVisualizer nodes={graphTemplate.nodes || []} />
          </TabsContent>

          <TabsContent value="nodes" className="space-y-4 mt-6">
            {graphTemplate.nodes && graphTemplate.nodes.length > 0 ? (
              <div className="space-y-4">
                {graphTemplate.nodes.map((node, index) => (
                  <NodeDetailView key={index} node={node} index={index} />
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="text-center py-8">
                  <Database className="w-12 h-12 mx-auto mb-4 text-muted-foreground opacity-50" />
                  <h3 className="text-lg font-medium text-foreground mb-2">No Nodes</h3>
                  <p className="text-muted-foreground">This graph template doesn&apos;t have any nodes configured.</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="retry-policy" className="mt-6">
            <RetryPolicyViewer retryPolicy={graphTemplate.retry_policy} />
          </TabsContent>

          <TabsContent value="store-config" className="mt-6">
            <StoreConfigViewer storeConfig={graphTemplate.store_config} />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};
