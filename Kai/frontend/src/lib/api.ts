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
} from "./types";

export async function sendChat(req: ChatRequest): Promise<ChatResponse> {
  const payload: Record<string, unknown> = {
    message: req.message,
    auto_execute: req.auto_execute,
  };
  if (req.session_id) payload.session_id = req.session_id;

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.status}`);
  return res.json();
}

export async function listPipelines(): Promise<PipelineListItem[]> {
  const res = await fetch("/api/pipelines");
  if (!res.ok) throw new Error(`List pipelines failed: ${res.status}`);
  return res.json();
}

export async function getPipeline(id: string): Promise<Record<string, unknown>> {
  const res = await fetch(`/api/pipelines/${id}`);
  if (!res.ok) throw new Error(`Get pipeline failed: ${res.status}`);
  return res.json();
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
  const res = await fetch("/api/pipelines", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pipeline }),
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
