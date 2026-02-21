import dagre from "dagre";
import type { Node, Edge } from "reactflow";
import type { PipelineNode, PipelineEdge, BlockDefinition } from "./types";
import { CATEGORY_COLORS } from "./constants";

const NODE_WIDTH = 260;
const NODE_HEIGHT = 72;

let blockMetadataCache: Record<string, { name: string; category: string }> = {};

export function setBlockMetadata(
  blocks: Array<Pick<BlockDefinition, "id" | "name" | "category">>
) {
  blockMetadataCache = {};
  for (const b of blocks) {
    blockMetadataCache[b.id] = { name: b.name, category: b.category };
  }
}

/** Merge new block metadata into the cache (for incremental SSE updates). */
export function addBlockMetadata(
  blocks: Array<Pick<BlockDefinition, "id" | "name" | "category">>
) {
  for (const b of blocks) {
    blockMetadataCache[b.id] = { name: b.name, category: b.category };
  }
}

export function getBlockMeta(blockId: string) {
  return blockMetadataCache[blockId] || { name: blockId, category: "control" };
}

/** Normalize edge endpoints — supports both Kai (from_node/to_node) and Magnus (from/to). */
function resolveEdge(e: PipelineEdge): { from: string; to: string } | null {
  const from = e.from_node || e.from;
  const to = e.to_node || e.to;
  return from && to ? { from, to } : null;
}

export function layoutPipeline(
  nodes: PipelineNode[],
  edges: PipelineEdge[],
  nodeStatuses?: Record<string, string>
): { flowNodes: Node[]; flowEdges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "TB", ranksep: 80, nodesep: 60 });

  for (const n of nodes) {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  }
  for (const e of edges) {
    const resolved = resolveEdge(e);
    if (resolved) g.setEdge(resolved.from, resolved.to);
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

  const flowEdges: Edge[] = edges.map((e, i) => {
    const resolved = resolveEdge(e);
    return {
      id: `e-${i}`,
      source: resolved?.from ?? "",
      target: resolved?.to ?? "",
      animated: true,
      style: { stroke: "#4b5563", strokeWidth: 2 },
      label: e.condition || undefined,
      labelStyle: { fill: "#9ca3af", fontSize: 11 },
    };
  });

  return { flowNodes, flowEdges };
}

export function getCategoryColor(category: string): string {
  return CATEGORY_COLORS[category] || "#6b7280";
}
