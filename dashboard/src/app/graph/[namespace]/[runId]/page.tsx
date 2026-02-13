'use client';

import React, { useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ReactFlowProvider } from 'reactflow';
import { GraphVisualization } from '@/components/GraphVisualization';
import { GraphTemplateDetail } from '@/components/GraphTemplateDetail';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';
import { clientApiService } from '@/services/clientApi';
import { UpsertGraphTemplateResponse } from '@/types/state-manager';

export default function GraphPage() {
  const router = useRouter();
  const params = useParams();
  
  const namespace = params?.namespace as string;
  const runId = params?.runId as string;

  // Graph template state
  const [graphTemplate, setGraphTemplate] = useState<UpsertGraphTemplateResponse | null>(null);
  const [isLoadingTemplate, setIsLoadingTemplate] = useState(false);
  const [templateError, setTemplateError] = useState<string | null>(null);

  const handleBack = () => {
    // Go back to the previous page or close the tab if opened from external link
    if (typeof window !== 'undefined') {
      if (window.history.length > 1) {
        router.back();
      } else {
        window.close();
      }
    } else {
      // Fallback for SSR
      router.back();
    }
  };

  const handleOpenGraphTemplate = useCallback(async (graphName: string) => {
    if (!graphName || !namespace) return;
    
    try {
      setIsLoadingTemplate(true);
      setTemplateError(null);
      const template = await clientApiService.getGraphTemplate(namespace, graphName);
      // Add name and namespace to the template
      template.name = graphName;
      template.namespace = namespace;
      setGraphTemplate(template);
    } catch (err) {
      setTemplateError(err instanceof Error ? err.message : 'Failed to load graph template');
    } finally {
      setIsLoadingTemplate(false);
    }
  }, [namespace]);

  const handleCloseGraphTemplate = () => {
    setGraphTemplate(null);
    setTemplateError(null);
  };

  if (!namespace || !runId) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <Button
                onClick={handleBack}
                variant="ghost"
                size="sm"
                className="flex items-center space-x-2"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back</span>
              </Button>
              <div className="h-6 w-px bg-border" />
              <div>
                <h1 className="text-xl font-semibold text-foreground">
                  Graph Visualization
                </h1>
                <p className="text-sm text-muted-foreground">
                  Namespace: {namespace} | Run: {runId}
                </p>
              </div>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ReactFlowProvider>
          <GraphVisualization
            namespace={namespace}
            runId={runId}
            onGraphTemplateRequest={handleOpenGraphTemplate}
          />
        </ReactFlowProvider>
      </main>

      {/* Graph Template Detail Modal - Inline at bottom */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-8">
        {templateError && (
          <div className="mb-4 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <p className="text-sm text-destructive">{templateError}</p>
          </div>
        )}
        
        {isLoadingTemplate && (
          <div className="mb-4 p-4 bg-muted rounded-lg">
            <div className="flex items-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary mr-2"></div>
              <p className="text-sm text-muted-foreground">Loading graph template...</p>
            </div>
          </div>
        )}

        <GraphTemplateDetail
          graphTemplate={graphTemplate}
          isOpen={!!graphTemplate}
          onClose={handleCloseGraphTemplate}
        />
      </div>
    </div>
  );
} 