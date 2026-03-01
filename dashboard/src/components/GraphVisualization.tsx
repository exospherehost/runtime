'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Position,
  MarkerType,
  NodeTypes,
  ConnectionLineType,
  Handle,
  useReactFlow,
  Panel
} from 'reactflow';
import 'reactflow/dist/style.css';
import { clientApiService } from '@/services/clientApi';
import { 
  GraphStructureResponse,
  GraphNode as GraphNodeType,
  NodeRunDetailsResponse
} from '@/types/state-manager';
import {  
  RefreshCw, 
  AlertCircle,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Network,
  BarChart3,
  Maximize2
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { NodeDetailsModal } from '@/components/NodeDetailsModal';

interface GraphVisualizationProps {
  namespace: string;
  runId: string;
  onGraphTemplateRequest?: (graphName: string) => void;
}

// Custom Node Component
const CustomNode: React.FC<{
  data: {
    label: string;
    status: string;
    identifier: string;
    node: GraphNodeType;
  };
}> = ({ data }) => {
  const getStatusVariant = (status: string): "default" | "success" | "destructive" | "secondary" => {
    switch (status) {
      case 'EXECUTED':
      case 'SUCCESS':
        return 'success';
      case 'ERRORED':
      case 'TIMEDOUT':
      case 'CANCELLED':
        return 'destructive';
      case 'QUEUED':
        return 'secondary';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'CREATED':
        return <Clock className="w-4 h-4" />;
      case 'QUEUED':
        return <Loader2 className="w-4 h-4 animate-spin" />;
      case 'EXECUTED':
      case 'SUCCESS':
        return <CheckCircle className="w-4 h-4" />;
      case 'ERRORED':
      case 'TIMEDOUT':
      case 'CANCELLED':
        return <XCircle className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  return (
    <div className="px-4 py-3 shadow-sm rounded-xl  border border-border min-w-[160px] relative">
      {/* Source Handle (Right side) */}
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: 'hsl(var(--primary))', width: '12px', height: '12px' }}
      />
      
      {/* Target Handle (Left side) */}
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: 'hsl(var(--primary))', width: '12px', height: '12px' }}
      />
      
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          {getStatusIcon(data.status)}
          <Badge variant={getStatusVariant(data.status)}>
            {data.status}
          </Badge>
        </div>
      </div>
      <div className="text-sm font-medium text-card-foreground mb-1">{data.label}</div>
      <div className="text-xs text-foreground">{data.identifier}</div>
    </div>
  );
};

const nodeTypes: NodeTypes = {
  custom: CustomNode,
};

export const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  namespace,
  runId,
  onGraphTemplateRequest
}) => {
  const { fitView } = useReactFlow();
  const [graphData, setGraphData] = useState<GraphStructureResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNodeType | null>(null);
  const [selectedNodeDetails, setSelectedNodeDetails] = useState<NodeRunDetailsResponse | null>(null);
  const [isLoadingNodeDetails, setIsLoadingNodeDetails] = useState(false);
  const [nodeDetailsError, setNodeDetailsError] = useState<string | null>(null);
  const [isInteractive, setIsInteractive] = useState(true);

  const handleFitView = useCallback(() => {
    fitView({ 
      duration: 800, // Animation duration in ms
      padding: 0.2   // 20% padding around the graph
    });
  }, [fitView]);

  const loadGraphStructure = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const data = await clientApiService.getGraphStructure(namespace, runId);
      setGraphData(data);
      
      // Request graph template details if callback is provided and graph name exists
      if (onGraphTemplateRequest && data.graph_name) {
        onGraphTemplateRequest(data.graph_name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load graph structure');
    } finally {
      setIsLoading(false);
    }
  }, [namespace, runId, onGraphTemplateRequest]);

  const loadNodeDetails = useCallback(async (nodeId: string, graphName: string) => {
    setIsLoadingNodeDetails(true);
    setNodeDetailsError(null);
    
    try {
      const details = await clientApiService.getNodeRunDetails(namespace, graphName, runId, nodeId);
      setSelectedNodeDetails(details);
    } catch (err) {
      setNodeDetailsError(err instanceof Error ? err.message : 'Failed to load node details');
    } finally {
      setIsLoadingNodeDetails(false);
    }
  }, [namespace, runId]);

  useEffect(() => {
    if (namespace && runId) {
      loadGraphStructure();
    }
  }, [namespace, runId, loadGraphStructure]);

  // Convert graph data to React Flow format with horizontal layout
  const { nodes, edges } = useMemo(() => {
    if (!graphData) return { nodes: [], edges: [] };

    // Build adjacency lists for layout calculation
    const nodeMap = new Map<string, GraphNodeType>();
    const childrenMap = new Map<string, string[]>();
    const parentMap = new Map<string, string[]>();

    // Initialize maps
    graphData.nodes.forEach(node => {
      nodeMap.set(node.id, node);
      childrenMap.set(node.id, []);
      parentMap.set(node.id, []);
    });

    // Build relationships
    graphData.edges.forEach(edge => {
      const children = childrenMap.get(edge.source) || [];
      children.push(edge.target);
      childrenMap.set(edge.source, children);

      const parents = parentMap.get(edge.target) || [];
      parents.push(edge.source);
      parentMap.set(edge.target, parents);
    });

    // Find root nodes (nodes with no parents)
    const rootNodes = graphData.nodes.filter(node => 
      (parentMap.get(node.id) || []).length === 0
    );

    // Build layers for horizontal layout
    const layers: GraphNodeType[][] = [];
    const visited = new Set<string>();

    // Start with root nodes
    if (rootNodes.length > 0) {
      layers.push(rootNodes);
      rootNodes.forEach(node => visited.add(node.id));
    }

    // Build layers
    let currentLayer = 0;
    while (visited.size < graphData.nodes.length && currentLayer < graphData.nodes.length) {
      const currentLayerNodes = layers[currentLayer] || [];
      const nextLayer: GraphNodeType[] = [];

      currentLayerNodes.forEach(node => {
        const children = childrenMap.get(node.id) || [];
        children.forEach(childId => {
          if (!visited.has(childId)) {
            const childNode = nodeMap.get(childId);
            if (childNode && !nextLayer.find(n => n.id === childId)) {
              nextLayer.push(childNode);
            }
          }
        });
      });

      if (nextLayer.length > 0) {
        layers.push(nextLayer);
        nextLayer.forEach(node => visited.add(node.id));
      }

      currentLayer++;
    }

    // Add any remaining nodes
    const remainingNodes = graphData.nodes.filter(node => !visited.has(node.id));
    if (remainingNodes.length > 0) {
      layers.push(remainingNodes);
    }

    // Convert to React Flow nodes with horizontal positioning
    const reactFlowNodes: Node[] = [];
    const layerWidth = 450; // Increased horizontal spacing between layers
    const nodeHeight = 250; // Increased vertical spacing between nodes

    layers.forEach((layer, layerIndex) => {
      const layerX = layerIndex * layerWidth + 200;
      const totalHeight = layer.length * nodeHeight;
      const startY = (800 - totalHeight) / 2; // Center vertically

      layer.forEach((node, nodeIndex) => {
        const y = startY + nodeIndex * nodeHeight + nodeHeight / 2;

        reactFlowNodes.push({
          id: node.id,
          type: 'custom',
          position: { x: layerX, y },
          data: {
            label: node.node_name,
            status: node.status,
            identifier: node.identifier,
            node: node
          },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          connectable: true,
          draggable: false,
        });
      });
    });

    // Convert edges
    const reactFlowEdges: Edge[] = graphData.edges.map((edge) => ({
      id: `edge-${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      type: 'default',
      animated: false,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        width: 10,
        height: 10,
        color: '#87ceeb',
      },
      style: {
        stroke: '#87ceeb',
        strokeWidth: 2,
        strokeDasharray: 'none',
      },
    }));
    
    return { nodes: reactFlowNodes, edges: reactFlowEdges };
  }, [graphData]);

  const [reactFlowNodes, setReactFlowNodes, onNodesChange] = useNodesState(nodes);
  const [reactFlowEdges, setReactFlowEdges, onEdgesChange] = useEdgesState(edges);

  // Update React Flow nodes and edges when graph data changes
  useEffect(() => {
    setReactFlowNodes(nodes);
    setReactFlowEdges(edges);
  }, [nodes, edges, setReactFlowNodes, setReactFlowEdges]);

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    const graphNode = node.data.node;
    setSelectedNode(graphNode);
    setSelectedNodeDetails(null); // Clear previous details
    
    // Load detailed node information
    if (graphData?.graph_name) {
      loadNodeDetails(graphNode.id, graphData.graph_name);
    }
  }, [graphData?.graph_name, loadNodeDetails]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
        <span className="ml-2 text-muted-foreground">Loading graph structure...</span>
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/20 bg-destructive/5">
        <CardContent className="pt-6">
          <div className="flex items-center">
            <AlertCircle className="w-5 h-5 text-destructive" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-destructive">Error</h3>
              <div className="mt-2 text-sm text-destructive/80">{error}</div>
              <Button
                onClick={loadGraphStructure}
                variant="outline"
                size="sm"
                className="mt-3"
              >
                <RefreshCw className="w-4 h-4 mr-1" />
                Retry
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!graphData) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <Network className="w-12 h-12 mx-auto mb-4 text-muted-foreground/50" />
            <p className="text-muted-foreground">No graph data available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Network className="w-8 h-8 text-primary" />
          <div>
            <h2 className="text-2xl font-bold text-foreground">Graph Visualization</h2>
            <p className="text-sm text-muted-foreground">
              Run ID: {runId} | Graph: {graphData.graph_name}
            </p>
          </div>
        </div>
        <Button onClick={loadGraphStructure} size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Execution Summary */}
      <Card className="bg-card border-border">
        <CardHeader className="pb-4">
          <div className="flex items-center space-x-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            <CardTitle>Execution Summary</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
            {Object.entries(graphData.execution_summary).map(([status, count]) => {
              const getStatusConfig = (status: string) => {
                switch (status.toLowerCase()) {
                  case 'success':
                    return {
                      bg: 'bg-secondary',
                      border: 'border-border',
                      text: 'text-chart-2', // Green from chart-2
                      icon: <CheckCircle className="w-4 h-4" />,
                      count: 'text-chart-2'
                    };
                  case 'created':
                    return {
                      bg: 'bg-secondary',
                      border: 'border-border',
                      text: 'text-chart-1', // Sky blue from chart-1
                      icon: <Clock className="w-4 h-4" />,
                      count: 'text-chart-1'
                    };
                  case 'queued':
                    return {
                      bg: 'bg-secondary',
                      border: 'border-border',
                      text: 'text-chart-3', // Yellow from chart-3
                      icon: <Loader2 className="w-4 h-4" />,
                      count: 'text-chart-3'
                    };
                  case 'executed':
                    return {
                      bg: 'bg-secondary',
                      border: 'border-border',
                      text: 'text-chart-5', // Purple from chart-5
                      icon: <CheckCircle className="w-4 h-4" />,
                      count: 'text-chart-5'
                    };
                  case 'errored':
                    return {
                      bg: 'bg-secondary',
                      border: 'border-border',
                      text: 'text-destructive', // Red from destructive
                      icon: <XCircle className="w-4 h-4" />,
                      count: 'text-destructive'
                    };
                  case 'next_created_error':
                    return {
                      bg: 'bg-secondary',
                      border: 'border-border',
                        text: 'text-chart-4', // Pink from chart-4
                      icon: <AlertCircle className="w-4 h-4" />,
                      count: 'text-chart-4'
                    };
                  case 'pruned':
                    return {
                      bg: 'bg-secondary',
                      border: 'border-border',
                      text: 'text-muted-foreground',
                      icon: <XCircle className="w-4 h-4" />,
                      count: 'text-muted-foreground'
                    };
                  case 'retry_created':
                    return {
                      bg: 'bg-secondary',
                      border: 'border-border',
                      text: 'text-primary', // Sky blue from primary
                      icon: <RefreshCw className="w-4 h-4" />,
                      count: 'text-primary'
                    };
                  default:
                    return {
                      bg: 'bg-muted',
                      border: 'border-border',
                      text: 'text-muted-foreground',
                      icon: <Clock className="w-4 h-4" />,
                      count: 'text-foreground'
                    };
                }
              };
              
              const config = getStatusConfig(status);
              const displayName = status.toLowerCase().replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
              
              return (
                <div 
                  key={status} 
                  className={`relative p-4 rounded-lg border transition-all duration-200 hover:shadow-md hover:scale-105 ${config.bg} ${config.border}`}
                >
                  <div className="flex flex-col items-center space-y-2">
                    <div className={`${config.text}`}>
                      {config.icon}
                    </div>
                    <div className={`text-2xl font-bold ${config.count}`}>
                      {count}
                    </div>
                    <div className={`text-xs font-medium text-center leading-tight ${config.text}`}>
                      {displayName}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Graph Visualization */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Graph Structure</CardTitle>
            <CardDescription>
              {graphData.node_count} nodes, {graphData.edge_count} edges 
            </CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <div className="border border-border rounded-xl overflow-hidden" style={{ height: '800px' }}>
            <ReactFlow
              nodes={reactFlowNodes}
              edges={reactFlowEdges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              fitView
              fitViewOptions={{ padding: 0.3 }}
              minZoom={0.1}
              maxZoom={2}
              defaultViewport={{ x: 0, y: 0, zoom: 0.7 }}
              proOptions={{ hideAttribution: true }}
              connectionLineType={ConnectionLineType.Straight}
              elementsSelectable={isInteractive}
              nodesConnectable={false}
              nodesDraggable={isInteractive}
              zoomOnScroll={isInteractive}
              panOnScroll={isInteractive}
              panOnDrag={isInteractive}
              zoomOnPinch={isInteractive}
              zoomOnDoubleClick={isInteractive}
            >
              <Background color="#031035" />
              <Controls 
                showInteractive={true}
                showFitView={true}
                position="bottom-left"
                onInteractiveChange={setIsInteractive}
              />
              <Panel position="top-right" className="flex gap-2 bg-card/90 backdrop-blur-sm rounded-lg p-2 border shadow-lg">
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={handleFitView}
                  className="text-xs h-8"
                  title="Fit graph to screen"
                >
                  <Maximize2 className="w-3 h-3 mr-1" />
                  Fit View
                </Button>
                <Button 
                  size="sm" 
                  variant="outline" 
                  onClick={loadGraphStructure}
                  className="text-xs h-8"
                  title="Refresh graph data"
                >
                  <RefreshCw className="w-3 h-3 mr-1" />
                  Refresh
                </Button>
              </Panel>
            </ReactFlow>
          </div>
        </CardContent>
      </Card>

      {/* Node Details Modal */}
      <NodeDetailsModal
        selectedNode={selectedNode}
        selectedNodeDetails={selectedNodeDetails}
        isLoadingNodeDetails={isLoadingNodeDetails}
        nodeDetailsError={nodeDetailsError}
        namespace={namespace}
        onClose={() => {
          setSelectedNode(null);
          setSelectedNodeDetails(null);
          setNodeDetailsError(null);
        }}
        onRefreshGraph={loadGraphStructure}
      />
    </div>
  );
};
