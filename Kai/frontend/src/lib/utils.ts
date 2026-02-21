import dagre from "dagre";
import type { Node, Edge } from "reactflow";
import type { PipelineNode, PipelineEdge, BlockDefinition } from "./types";
import { CATEGORY_COLORS } from "./constants";

const NODE_WIDTH = 300;
const NODE_HEIGHT = 88;

let blockMetadataCache: Record<string, { name: string; category: string; description: string }> = {};

export function setBlockMetadata(
  blocks: Array<Pick<BlockDefinition, "id" | "name" | "category" | "description">>
) {
  blockMetadataCache = {};
  for (const b of blocks) {
    blockMetadataCache[b.id] = { name: b.name, category: b.category, description: b.description };
  }
}

export function getBlockMeta(blockId: string) {
  return blockMetadataCache[blockId] || { name: blockId, category: "control", description: "" };
}

export function layoutPipeline(
  nodes: PipelineNode[],
  edges: PipelineEdge[],
  nodeStatuses?: Record<string, string>
): { flowNodes: Node[]; flowEdges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", ranksep: 100, nodesep: 80 });

  for (const n of nodes) {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const e of edges) {
    g.setEdge(e.from_node, e.to_node);
  }
  dagre.layout(g);

  const flowNodes: Node[] = nodes.map((n) => {
    const pos = g.node(n.id);
    const meta = getBlockMeta(n.block_id);
    return {
      id: n.id,
      type: "blockNode",
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
      data: {
        label: meta.name,
        blockId: n.block_id,
        category: meta.category,
        inputs: n.inputs,
        status: nodeStatuses?.[n.id] || "idle",
      },
    };
  });

  const flowEdges: Edge[] = edges.map((e, i) => ({
    id: `e-${i}`,
    source: e.from_node,
    target: e.to_node,
    animated: true,
    style: { stroke: "#4b5563", strokeWidth: 2, strokeDasharray: "8 4" },
    label: e.condition || undefined,
    labelStyle: { fill: "#9ca3af", fontSize: 11 },
  }));

  return { flowNodes, flowEdges };
}

export function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || "#6b7280";
}
