export type BlockCategory =
  | "trigger"
  | "perceive"
  | "think"
  | "act"
  | "communicate"
  | "remember"
  | "control";

export interface BlockDefinition {
  id: string;
  name: string;
  description: string;
  category: BlockCategory;
  organ: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  api_type: "real" | "mock";
  tier: number;
  examples: Array<{ input: Record<string, unknown>; output: Record<string, unknown> }>;
}

export interface PipelineNode {
  id: string;
  block_id: string;
  inputs: Record<string, unknown>;
  config: Record<string, unknown>;
}

export interface PipelineEdge {
  from_node: string;
  to_node: string;
  condition: string | null;
}

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

export interface ExecutionResult {
  pipeline_id: string;
  run_id: string;
  status: "pending" | "running" | "completed" | "failed";
  shared_context: Record<string, unknown>;
  node_results: unknown[];
  errors: string[];
}

export interface PipelineListItem {
  id: string;
  user_intent: string;
  status: string;
  trigger_type: string;
  node_count: number;
}

export interface ExecutionRun {
  run_id: string;
  pipeline_id: string;
  pipeline_intent: string;
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
