import type {
  ChatRequest,
  ChatResponse,
  BlockDefinition,
  PipelineListItem,
  PipelineNode,
  PipelineEdge,
  TriggerConfig,
  ExecutionResult,
  ExecutionRun,
  ExecutionDetail,
  Notification,
  ScheduleItem,
} from "./types";

// ── Edge normalization helpers ──
// Demo backend stores edges as {from, to}; frontend uses {from_node, to_node, condition}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toFrontendEdge(e: any): PipelineEdge {
  return {
    from_node: (e.from ?? e.from_node) as string,
    to_node: (e.to ?? e.to_node) as string,
    condition: (e.condition as string) ?? null,
  };
}

function toBackendEdge(e: PipelineEdge): Record<string, unknown> {
  return { from: e.from_node, to: e.to_node };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function normalizePipeline(p: any): PipelineListItem {
  const nodes: PipelineNode[] = (p.nodes ?? []).map((n: any) => ({
    id: n.id,
    block_id: n.block_id,
    inputs: n.inputs ?? {},
    config: n.config ?? {},
  }));
  const edges: PipelineEdge[] = (p.edges ?? []).map(toFrontendEdge);
  return {
    id: p.id as string,
    user_intent: (p.user_intent ?? p.user_prompt ?? p.name ?? "") as string,
    status: (p.status ?? "active") as string,
    trigger_type: (p.trigger_type ?? (p.trigger as any)?.type ?? "manual") as string,
    node_count: nodes.length,
    nodes,
    edges,
    trigger: (p.trigger as TriggerConfig) ?? { type: "manual" },
  };
}

// ── Chat → wraps Demo's /api/create-agent ──

export async function sendChat(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch("/api/create-agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intent: req.message, user_id: "default_user" }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  const data = await res.json();

  // Demo returns {pipeline_json, status, log, missing_blocks}
  const pj = data.pipeline_json;
  if (!pj) {
    const reason = (data.log ?? []).map((l: any) => l.error ?? l.step).join(", ");
    throw new Error(reason || "No pipeline generated");
  }

  const nodes: PipelineNode[] = (pj.nodes ?? []).map((n: any) => ({
    id: n.id,
    block_id: n.block_id,
    inputs: n.inputs ?? {},
    config: {},
  }));
  const edges: PipelineEdge[] = (pj.edges ?? []).map(toFrontendEdge);

  return {
    response_type: "pipeline",
    pipeline_id: pj.id,
    user_intent: pj.user_prompt ?? pj.name ?? req.message,
    trigger_type: "manual",
    trigger: { type: "manual" },
    nodes,
    edges,
    missing_blocks: data.missing_blocks ?? [],
    execution_result: null,
    session_id: "",
    clarification_message: "",
    questions: [],
  };
}

export async function listPipelines(): Promise<PipelineListItem[]> {
  const res = await fetch("/api/pipelines");
  if (!res.ok) throw new Error(`List pipelines failed: ${res.status}`);
  const data = await res.json();
  return (data as any[]).map(normalizePipeline);
}

export async function getPipeline(id: string): Promise<Record<string, unknown>> {
  const res = await fetch(`/api/pipelines/${id}`);
  if (!res.ok) throw new Error(`Get pipeline failed: ${res.status}`);
  const data = await res.json();
  return normalizePipeline(data) as unknown as Record<string, unknown>;
}

export async function runPipeline(id: string): Promise<ExecutionResult> {
  const res = await fetch(`/api/pipelines/${id}/run`, { method: "POST" });
  if (!res.ok) throw new Error(`Run pipeline failed: ${res.status}`);
  return res.json();
}

export async function deletePipeline(id: string): Promise<void> {
  const res = await fetch(`/api/pipelines/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Delete pipeline failed: ${res.status}`);
}

interface SavePipelinePayload {
  id: string;
  user_intent: string;
  trigger: TriggerConfig;
  nodes: PipelineNode[];
  edges: PipelineEdge[];
}

export async function savePipeline(pipeline: SavePipelinePayload): Promise<{ id: string }> {
  // Store both user_intent and user_prompt so Demo's Doer and our normalizePipeline both work
  const backendPipeline = {
    id: pipeline.id,
    name: pipeline.user_intent,
    user_prompt: pipeline.user_intent,
    user_intent: pipeline.user_intent,
    trigger: pipeline.trigger,
    nodes: pipeline.nodes,
    edges: pipeline.edges.map(toBackendEdge), // Doer requires {from, to}
    memory_keys: [],
  };
  const res = await fetch("/api/pipelines", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pipeline: backendPipeline }),
  });
  if (!res.ok) throw new Error(`Save pipeline failed: ${res.status}`);
  return res.json();
}

export async function listBlocks(category?: string): Promise<BlockDefinition[]> {
  const url = category ? `/api/blocks?category=${category}` : "/api/blocks";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`List blocks failed: ${res.status}`);
  return res.json();
}

export async function searchBlocks(query: string): Promise<BlockDefinition[]> {
  const res = await fetch("/api/blocks/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(`Search blocks failed: ${res.status}`);
  return res.json();
}

export async function listExecutions(limit = 50): Promise<ExecutionRun[]> {
  const res = await fetch(`/api/executions?limit=${limit}`);
  if (!res.ok) throw new Error(`List executions failed: ${res.status}`);
  return res.json();
}

export async function getExecution(runId: string): Promise<ExecutionDetail> {
  const res = await fetch(`/api/executions/${runId}`);
  if (!res.ok) throw new Error(`Get execution failed: ${res.status}`);
  return res.json();
}

export async function listNotifications(limit = 50): Promise<Notification[]> {
  const res = await fetch(`/api/notifications?limit=${limit}`);
  if (!res.ok) throw new Error(`List notifications failed: ${res.status}`);
  return res.json();
}

export async function markNotificationRead(id: number): Promise<void> {
  const res = await fetch(`/api/notifications/${id}/read`, { method: "POST" });
  if (!res.ok) throw new Error(`Mark notification read failed: ${res.status}`);
}

export async function listSchedules(): Promise<ScheduleItem[]> {
  const res = await fetch("/api/schedules");
  if (res.status === 404) return []; // Demo backend doesn't have this endpoint
  if (!res.ok) throw new Error(`List schedules failed: ${res.status}`);
  return res.json();
}
