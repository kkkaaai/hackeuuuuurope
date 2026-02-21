import type {
  BlockDefinition,
  PipelineListItem,
  ExecutionResult,
  ExecutionRun,
  ExecutionDetail,
  Notification,
  MagnusPipeline,
  ChatMessage,
  ClarifyResult,
} from "./types";
import { streamSSE, type SSEEventHandler } from "./sse";

// ── Intent Clarification ──

export async function clarifyIntent(
  message: string,
  history: ChatMessage[]
): Promise<ClarifyResult> {
  const res = await fetch("/api/clarify", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) throw new Error(`Clarify failed: ${res.status}`);
  return res.json();
}

// ── Agent Creation (Magnus Thinker) ──

export async function createAgent(intent: string, userId = "default"): Promise<{
  pipeline_json: MagnusPipeline | null;
  status: string;
  log: Array<Record<string, unknown>>;
  missing_blocks: Array<Record<string, unknown>>;
}> {
  const res = await fetch("/api/create-agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intent, user_id: userId }),
  });
  if (!res.ok) throw new Error(`Create agent failed: ${res.status}`);
  return res.json();
}

export function createAgentStream(
  intent: string,
  userId: string,
  onEvent: SSEEventHandler,
  onError?: (error: Error) => void,
  onComplete?: () => void
): Promise<void> {
  return streamSSE(
    "/api/create-agent/stream",
    { intent, user_id: userId },
    onEvent,
    onError,
    onComplete
  );
}

// ── Pipeline CRUD ──

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

export async function savePipeline(pipeline: Record<string, unknown>): Promise<{ id: string }> {
  const res = await fetch("/api/pipelines", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pipeline }),
  });
  if (!res.ok) throw new Error(`Save pipeline failed: ${res.status}`);
  return res.json();
}

export async function deletePipeline(id: string): Promise<void> {
  const res = await fetch(`/api/pipelines/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Delete pipeline failed: ${res.status}`);
}

export async function runPipeline(id: string): Promise<ExecutionResult> {
  const res = await fetch(`/api/pipelines/${id}/run`, { method: "POST" });
  if (!res.ok) throw new Error(`Run pipeline failed: ${res.status}`);
  return res.json();
}

export async function runPipelineDirect(
  pipeline: Record<string, unknown>,
  userId = "default"
): Promise<Record<string, unknown>> {
  const res = await fetch("/api/pipeline/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pipeline, user_id: userId }),
  });
  if (!res.ok) throw new Error(`Run pipeline failed: ${res.status}`);
  return res.json();
}

// ── Blocks ──

export async function listBlocks(origin?: string): Promise<BlockDefinition[]> {
  const url = origin ? `/api/blocks?origin=${origin}` : "/api/blocks";
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

// ── Executions ──

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

// ── Notifications ──

export async function listNotifications(limit = 50): Promise<Notification[]> {
  const res = await fetch(`/api/notifications?limit=${limit}`);
  if (!res.ok) throw new Error(`List notifications failed: ${res.status}`);
  return res.json();
}

export async function markNotificationRead(id: number): Promise<void> {
  const res = await fetch(`/api/notifications/${id}/read`, { method: "POST" });
  if (!res.ok) throw new Error(`Mark notification read failed: ${res.status}`);
}
