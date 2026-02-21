"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Play,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  RotateCcw,
} from "lucide-react";
import { createAgentStream, savePipeline, runPipeline, listBlocks } from "@/lib/api";
import { PipelineGraph } from "@/components/pipeline/PipelineGraph";
import { PipelineResultDisplay } from "@/components/pipeline/PipelineResultDisplay";
import { StageProgressBar } from "@/components/thinker/StageProgressBar";
import { ThinkerLog } from "@/components/thinker/ThinkerLog";
import { setBlockMetadata, addBlockMetadata } from "@/lib/utils";
import type { SSEEvent, ThinkerStage, MagnusPipeline, ExecutionResult, PipelineNode, PipelineEdge, BlockCategory } from "@/lib/types";

// ── State machine ──

type Phase = "idle" | "thinking" | "ready" | "executing" | "complete" | "error";

interface State {
  phase: Phase;
  events: SSEEvent[];
  currentStage: ThinkerStage | null;
  completedStages: Set<string>;
  pipeline: MagnusPipeline | null;
  nodeStatuses: Record<string, string>;
  executionResult: ExecutionResult | null;
  errorMessage: string | null;
}

type Action =
  | { type: "START_THINKING" }
  | { type: "SSE_EVENT"; event: SSEEvent }
  | { type: "THINKING_COMPLETE"; pipeline: MagnusPipeline }
  | { type: "THINKING_ERROR"; error: string }
  | { type: "START_EXECUTION" }
  | { type: "UPDATE_NODE_STATUS"; nodeId: string; status: string }
  | { type: "EXECUTION_COMPLETE"; result: ExecutionResult }
  | { type: "RESET" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "START_THINKING":
      return {
        ...state,
        phase: "thinking",
        events: [],
        currentStage: null,
        completedStages: new Set(),
        pipeline: null,
        nodeStatuses: {},
        executionResult: null,
        errorMessage: null,
      };

    case "SSE_EVENT": {
      const newEvents = [...state.events, action.event];
      let newStage = state.currentStage;
      const newCompleted = new Set(state.completedStages);

      if (action.event.type === "stage") {
        // Complete previous stage when new stage starts
        if (newStage) newCompleted.add(newStage);
        newStage = action.event.stage as ThinkerStage;
      }

      if (action.event.type === "stage_result") {
        newCompleted.add(action.event.stage as string);
      }

      return {
        ...state,
        events: newEvents,
        currentStage: newStage,
        completedStages: newCompleted,
      };
    }

    case "THINKING_COMPLETE":
      return {
        ...state,
        phase: "ready",
        pipeline: action.pipeline,
        currentStage: null,
        completedStages: new Set(["decompose", "match", "create", "wire"]),
      };

    case "THINKING_ERROR":
      return {
        ...state,
        phase: "error",
        errorMessage: action.error,
      };

    case "START_EXECUTION":
      return { ...state, phase: "executing", nodeStatuses: {} };

    case "UPDATE_NODE_STATUS":
      return {
        ...state,
        nodeStatuses: { ...state.nodeStatuses, [action.nodeId]: action.status },
      };

    case "EXECUTION_COMPLETE": {
      const allDone: Record<string, string> = {};
      state.pipeline?.nodes.forEach((n) => {
        allDone[n.id] = action.result.status === "completed" ? "completed" : "failed";
      });
      return {
        ...state,
        phase: "complete",
        executionResult: action.result,
        nodeStatuses: allDone,
      };
    }

    case "RESET":
      return INITIAL_STATE;

    default:
      return state;
  }
}

const INITIAL_STATE: State = {
  phase: "idle",
  events: [],
  currentStage: null,
  completedStages: new Set(),
  pipeline: null,
  nodeStatuses: {},
  executionResult: null,
  errorMessage: null,
};

// ── Component ──

export default function AgentStudioPage() {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const [input, setInput] = useState("");
  const [blocksLoaded, setBlocksLoaded] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load block metadata on mount
  useEffect(() => {
    listBlocks()
      .then((blocks) => {
        setBlockMetadata(blocks);
        setBlocksLoaded(true);
      })
      .catch(() => setBlocksLoaded(true));
  }, []);

  const handleCreate = useCallback(async () => {
    const intent = input.trim();
    if (!intent || state.phase === "thinking") return;

    setInput("");
    dispatch({ type: "START_THINKING" });

    await createAgentStream(
      intent,
      "default",
      (eventType, data) => {
        const event: SSEEvent = { type: eventType, ...data };
        dispatch({ type: "SSE_EVENT", event });

        // Cache block metadata from match/create events
        if ((eventType === "match_found" || eventType === "block_created") && data.block_id) {
          addBlockMetadata([{
            id: data.block_id as string,
            name: (data.block_name || data.block_id) as string,
            category: (data.category as BlockCategory) || "process",
          }]);
        }

        // On complete, extract pipeline
        if (eventType === "complete" && data.pipeline) {
          dispatch({
            type: "THINKING_COMPLETE",
            pipeline: data.pipeline as MagnusPipeline,
          });
        }
      },
      (error) => {
        dispatch({ type: "THINKING_ERROR", error: error.message });
      }
    );
  }, [input, state.phase]);

  const handleExecute = useCallback(async () => {
    if (!state.pipeline) return;
    dispatch({ type: "START_EXECUTION" });

    const nodes = state.pipeline.nodes;
    const animationTimers: ReturnType<typeof setTimeout>[] = [];

    // Animate nodes sequentially
    nodes.forEach((node, i) => {
      animationTimers.push(
        setTimeout(() => {
          if (i > 0) dispatch({ type: "UPDATE_NODE_STATUS", nodeId: nodes[i - 1].id, status: "completed" });
          dispatch({ type: "UPDATE_NODE_STATUS", nodeId: node.id, status: "running" });
        }, i * 800)
      );
    });

    try {
      // Save pipeline first, then run it
      const saved = await savePipeline(state.pipeline as unknown as Record<string, unknown>);
      const result = await runPipeline(saved.id);

      animationTimers.forEach(clearTimeout);
      dispatch({ type: "EXECUTION_COMPLETE", result });
    } catch {
      animationTimers.forEach(clearTimeout);
      dispatch({
        type: "EXECUTION_COMPLETE",
        result: {
          pipeline_id: state.pipeline.id,
          run_id: "error",
          status: "failed",
          shared_context: {},
          node_results: [],
          errors: ["Execution failed. Check that the backend is running."],
        },
      });
    }
  }, [state.pipeline]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleCreate();
    }
  };

  // Convert Magnus pipeline to component-compatible format
  const pipelineNodes: PipelineNode[] = state.pipeline?.nodes || [];
  const pipelineEdges: PipelineEdge[] = (state.pipeline?.edges || []).map((e) => ({
    from: e.from,
    to: e.to,
  }));

  const isThinking = state.phase === "thinking";
  const showPipeline = state.pipeline && blocksLoaded;
  const showResults = state.phase === "complete" && state.executionResult;

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold">Agent Studio</h1>
            <p className="text-sm text-gray-500">
              Describe your automation — watch the AI think, then run it
            </p>
          </div>
          {state.phase !== "idle" && (
            <button
              onClick={() => dispatch({ type: "RESET" })}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 border border-gray-700 hover:border-gray-500 rounded-lg transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Input bar */}
      <div className="border-b border-gray-800 p-4">
        <div className="max-w-4xl mx-auto flex gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your automation..."
            rows={1}
            disabled={isThinking || state.phase === "executing"}
            className="flex-1 px-4 py-3 bg-gray-900 border border-gray-700 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 disabled:opacity-50 transition-all shadow-lg shadow-blue-500/5 resize-none"
          />
          <button
            onClick={handleCreate}
            disabled={!input.trim() || isThinking || state.phase === "executing"}
            className="px-5 py-3 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-xl disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            {isThinking ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Thinking...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Create Agent
              </>
            )}
          </button>
        </div>

        {/* Example prompts (idle state) */}
        {state.phase === "idle" && (
          <div className="max-w-4xl mx-auto mt-3 flex flex-wrap gap-2">
            {[
              "Search for AI news every morning",
              "Track Bitcoin price and alert if below $60k",
              "Summarize top Hacker News posts",
              "Find the best laptop deals under $1000",
            ].map((example) => (
              <button
                key={example}
                onClick={() => {
                  setInput(example);
                  inputRef.current?.focus();
                }}
                className="text-xs px-3 py-1.5 rounded-full border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Stage Progress Bar */}
      {state.phase !== "idle" && (
        <div className="border-b border-gray-800">
          <StageProgressBar
            currentStage={state.currentStage}
            completedStages={state.completedStages}
          />
        </div>
      )}

      {/* Main content: Split pane */}
      {state.phase !== "idle" ? (
        <div className="flex-1 flex overflow-hidden">
          {/* Left: Thinker Log */}
          <div className="w-[380px] border-r border-gray-800 flex flex-col">
            <div className="px-3 py-2 border-b border-gray-800 text-xs font-medium text-gray-500">
              Thinker Log
            </div>
            <div className="flex-1 overflow-hidden">
              <ThinkerLog events={state.events} />
            </div>
          </div>

          {/* Right: Pipeline Visualization + Results */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {showPipeline ? (
              <>
                <div className="flex-1 min-h-0">
                  <PipelineGraph
                    nodes={pipelineNodes}
                    edges={pipelineEdges}
                    nodeStatuses={state.nodeStatuses}
                  />
                </div>

                {/* Run button */}
                {state.phase === "ready" && (
                  <div className="border-t border-gray-800 p-4 flex justify-center">
                    <button
                      onClick={handleExecute}
                      className="flex items-center gap-2 px-6 py-2.5 bg-green-600 hover:bg-green-500 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      <Play className="w-4 h-4" />
                      Run Pipeline
                    </button>
                  </div>
                )}

                {/* Executing indicator */}
                {state.phase === "executing" && (
                  <div className="border-t border-gray-800 p-4 flex justify-center">
                    <div className="flex items-center gap-2 text-blue-400 text-sm">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Running pipeline...
                    </div>
                  </div>
                )}

                {/* Results */}
                {showResults && (
                  <div className="border-t border-gray-800 max-h-[40%] overflow-y-auto p-4">
                    <div className="flex items-center gap-2 mb-3">
                      {state.executionResult!.status === "completed" ? (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-green-400" />
                          <span className="text-sm font-medium text-green-400">
                            Pipeline completed
                          </span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="w-4 h-4 text-red-400" />
                          <span className="text-sm font-medium text-red-400">
                            Pipeline failed
                          </span>
                        </>
                      )}
                    </div>

                    {state.executionResult!.errors.length > 0 && (
                      <p className="text-xs text-red-300 mb-3">
                        {state.executionResult!.errors.join(", ")}
                      </p>
                    )}

                    {state.executionResult!.shared_context &&
                      Object.keys(state.executionResult!.shared_context).length > 0 && (
                        <PipelineResultDisplay
                          sharedContext={
                            state.executionResult!.shared_context as Record<
                              string,
                              Record<string, unknown>
                            >
                          }
                          errors={state.executionResult!.errors}
                        />
                      )}
                  </div>
                )}
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-600">
                <div className="text-center">
                  <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">Pipeline will appear here</p>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Idle state hero */
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Sparkles className="w-12 h-12 text-blue-500/50 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-300 mb-2">
              What do you want to automate?
            </h2>
            <p className="text-gray-500 max-w-md">
              Describe your automation in plain English. The AI will decompose it into
              blocks, wire them into a pipeline, and execute it — all in real-time.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
