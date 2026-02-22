"use client";

import { useEffect, useMemo } from "react";
import ReactFlow, {
  Background,
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
  fullHeight?: boolean;
}

export function PipelineGraph({
  nodes,
  edges,
  nodeStatuses,
  onNodeClick,
  mini = false,
  fullHeight = false,
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

  const heightClass = fullHeight ? "h-full" : mini ? "h-[280px]" : "h-[550px]";

  return (
    <div className={heightClass} style={{ width: "100%" }}>
      <ReactFlow
        nodes={rfNodes}
        edges={rfEdges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={(_, node) => onNodeClick?.(node.id)}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        panOnDrag={!mini}
        zoomOnScroll={!mini}
        nodesDraggable={!mini}
        nodesConnectable={false}
        minZoom={0.3}
        maxZoom={1.5}
      >
        <Background color="#e2e8f0" gap={20} size={1} />
        {!mini && <Controls className="!bg-white !border-slate-200" />}
      </ReactFlow>
    </div>
  );
}
