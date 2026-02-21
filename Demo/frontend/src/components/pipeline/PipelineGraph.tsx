"use client";

import { useEffect, useMemo } from "react";
import ReactFlow, {
  Controls,
  useNodesState,
  useEdgesState,
  type NodeTypes,
} from "reactflow";
import "reactflow/dist/style.css";
import { BlockNode } from "./BlockNode";
import { layoutPipeline } from "@/lib/utils";
import type { PipelineNode, PipelineEdge } from "@/lib/types";

const nodeTypes: NodeTypes = { blockNode: BlockNode };

interface Props {
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  nodeStatuses?: Record<string, string>;
  onNodeClick?: (nodeId: string) => void;
  mini?: boolean;
}

export function PipelineGraph({
  nodes,
  edges,
  nodeStatuses,
  onNodeClick,
  mini = false,
}: Props) {
  const layout = useMemo(
    () => layoutPipeline(nodes, edges, nodeStatuses),
    [nodes, edges, nodeStatuses]
  );

  const [rfNodes, setNodes, onNodesChange] = useNodesState(layout.flowNodes);
  const [rfEdges, setEdges, onEdgesChange] = useEdgesState(layout.flowEdges);

  useEffect(() => {
    const { flowNodes, flowEdges } = layoutPipeline(nodes, edges, nodeStatuses);
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [nodes, edges, nodeStatuses, setNodes, setEdges]);

  return (
    <div
      className={`${mini ? "h-[280px]" : "h-full"} rounded-xl overflow-hidden`}
      style={{
        width: "100%",
        background: "linear-gradient(180deg, #060a14 0%, #0a0f1a 100%)",
      }}
    >
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => onNodeClick?.(node.id)}
        fitView
        fitViewOptions={{ padding: 0.4 }}
        proOptions={{ hideAttribution: true }}
        panOnDrag={!mini}
        zoomOnScroll={!mini}
        nodesDraggable={!mini}
        nodesConnectable={false}
        minZoom={0.3}
        maxZoom={1.5}
      >
        {!mini && <Controls position="bottom-right" />}
      </ReactFlow>
    </div>
  );
}
