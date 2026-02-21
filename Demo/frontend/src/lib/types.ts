// ── Block Categories ──

export type BlockCategory =
  | "trigger"
  | "perceive"
  | "think"
  | "act"
  | "communicate"
  | "remember"
  | "control"
  // Magnus-native categories (mapped to Kai labels in frontend)
  | "input"
  | "process"
  | "action"
  | "memory";

// ── Block Definition (unified: Kai + Magnus fields) ──

export interface BlockDefinition {
  id: string;
  name: string;
  description: string;
  category: BlockCategory;
  // Kai fields (optional for Magnus blocks)
  organ?: string;
  api_type?: "real" | "mock";
  tier?: number;
  // Magnus fields
  execution_type?: "llm" | "python";
  prompt_template?: string;
  use_when?: string;
  tags?: string[];
  execution?: { runtime: string; entrypoint: string };
  metadata?: Record<string, unknown>;
  web_search_enabled?: boolean;
  // Shared
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  examples?: Array<{ inputs?: Record<string, unknown>; outputs?: Record<string, unknown>; input?: Record<string, unknown>; output?: Record<string, unknown> }>;
}

// ── Pipeline Types ──

export interface PipelineNode {
  id: string;
  block_id: string;
  inputs: Record<string, unknown>;
  config?: Record<string, unknown>;
}

export interface PipelineEdge {
  // Kai format
  from_node?: string;
  to_node?: string;
  // Magnus format
  from?: string;
  to?: string;
  condition?: string | null;
}

// ── Chat / Agent Creation ──

export interface ChatRequest {
  message: string;
  auto_execute: boolean;
}

export interface ChatResponse {
  pipeline_id: string;
  user_intent: string;
  trigger_type: string;
  nodes: PipelineNode[];
  edges: PipelineEdge[];
  missing_blocks: unknown[];
  execution_result: ExecutionResult | null;
}

// Magnus create-agent response
export interface CreateAgentResponse {
  pipeline_json: MagnusPipeline | null;
  status: string;
  log: Array<Record<string, unknown>>;
  missing_blocks: Array<Record<string, unknown>>;
}

export interface MagnusPipeline {
  id: string;
  name: string;
  user_prompt: string;
  nodes: PipelineNode[];
  edges: Array<{ from: string; to: string }>;
  memory_keys?: string[];
}

// ── SSE Event Types ──

export type ThinkerStage = "decompose" | "match" | "create" | "wire";

export interface SSEEvent {
  type: string;
  ts?: number;
  [key: string]: unknown;
}

export interface StageEvent extends SSEEvent {
  type: "stage";
  stage: ThinkerStage;
}

export interface StageResultEvent extends SSEEvent {
  type: "stage_result";
  stage: ThinkerStage;
  summary?: string;
}

export interface LLMPromptEvent extends SSEEvent {
  type: "llm_prompt";
  system_prompt?: string;
  user_prompt?: string;
}

export interface LLMResponseEvent extends SSEEvent {
  type: "llm_response";
  response?: string;
  elapsed?: number;
}

export interface MatchFoundEvent extends SSEEvent {
  type: "match_found";
  block_id: string;
  block_name?: string;
}

export interface MatchMissingEvent extends SSEEvent {
  type: "match_missing";
  suggested_id: string;
  description?: string;
}

export interface BlockCreatedEvent extends SSEEvent {
  type: "block_created";
  block_id: string;
  block_name?: string;
}

export interface ValidationEvent extends SSEEvent {
  type: "validation";
  valid: boolean;
  error?: string;
}

export interface CompleteEvent extends SSEEvent {
  type: "complete";
  pipeline?: MagnusPipeline;
}

// ── Execution ──

export interface ExecutionResult {
  pipeline_id: string;
  run_id: string;
  status: "pending" | "running" | "completed" | "failed";
  shared_context: Record<string, unknown>;
  node_results: unknown[];
  errors: string[];
}

// ── Pipeline List ──

export interface PipelineListItem {
  id: string;
  user_intent?: string;
  user_prompt?: string;
  name?: string;
  status: string;
  trigger_type?: string;
  node_count: number;
  created_at?: string;
}

// ── Execution History ──

export interface ExecutionRun {
  run_id: string;
  pipeline_id: string;
  pipeline_intent?: string;
  pipeline_name?: string;
  node_count: number;
  status: string;
  finished_at: string;
}

export interface ExecutionDetail {
  run_id: string;
  pipeline_id: string;
  status: string;
  nodes: ExecutionNodeLog[];
}

export interface ExecutionNodeLog {
  id: number;
  node_id: string;
  status: string;
  output_data: Record<string, unknown> | null;
  error: string | null;
  finished_at: string;
}

// ── Notifications ──

export interface Notification {
  id: number;
  pipeline_id: string | null;
  run_id: string | null;
  node_id: string | null;
  title: string;
  message: string;
  level: "info" | "success" | "warning" | "error";
  category: "notification" | "confirmation" | "summary_card";
  metadata: Record<string, unknown>;
  read: boolean;
  created_at: string;
}
