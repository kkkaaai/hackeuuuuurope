"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Play,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  RotateCcw,
  PanelLeftClose,
  PanelLeftOpen,
  ChevronDown,
  Send,
  MessageCircle,
} from "lucide-react";
import { createAgentStream, clarifyIntent, savePipeline, runPipeline, listBlocks } from "@/lib/api";
import { PipelineGraph } from "@/components/pipeline/PipelineGraph";
import { PipelineResultDisplay } from "@/components/pipeline/PipelineResultDisplay";
import { StageProgressBar } from "@/components/thinker/StageProgressBar";
import { ThinkerLog } from "@/components/thinker/ThinkerLog";
import { setBlockMetadata, addBlockMetadata } from "@/lib/utils";
import type { SSEEvent, ThinkerStage, MagnusPipeline, ExecutionResult, PipelineNode, PipelineEdge, BlockCategory, ChatMessage } from "@/lib/types";

// ── State machine ──

type Phase = "idle" | "clarifying" | "thinking" | "ready" | "executing" | "complete" | "error";

interface State {
  phase: Phase;
  messages: ChatMessage[];
  events: SSEEvent[];
  currentStage: ThinkerStage | null;
  completedStages: Set<string>;
  pipeline: MagnusPipeline | null;
  nodeStatuses: Record<string, string>;
  executionResult: ExecutionResult | null;
  errorMessage: string | null;
  userIntent: string | null;
}

type Action =
  | { type: "START_CLARIFYING"; message: string }
  | { type: "ADD_USER_MESSAGE"; content: string }
  | { type: "ADD_ASSISTANT_MESSAGE"; content: string }
  | { type: "CLARIFICATION_COMPLETE"; intent: string }
  | { type: "START_THINKING"; intent: string }
  | { type: "SSE_EVENT"; event: SSEEvent }
  | { type: "THINKING_COMPLETE"; pipeline: MagnusPipeline }
  | { type: "THINKING_ERROR"; error: string }
  | { type: "START_EXECUTION" }
  | { type: "UPDATE_NODE_STATUS"; nodeId: string; status: string }
  | { type: "EXECUTION_COMPLETE"; result: ExecutionResult }
  | { type: "RESET" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "START_CLARIFYING":
      return {
        ...state,
        phase: "clarifying",
        messages: [{ role: "user", content: action.message }],
        errorMessage: null,
      };

    case "ADD_USER_MESSAGE":
      return {
        ...state,
        messages: [...state.messages, { role: "user", content: action.content }],
      };

    case "ADD_ASSISTANT_MESSAGE":
      return {
        ...state,
        messages: [...state.messages, { role: "assistant", content: action.content }],
      };

    case "CLARIFICATION_COMPLETE":
      return {
        ...state,
        userIntent: action.intent,
      };

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
        userIntent: action.intent,
      };

    case "SSE_EVENT": {
      const newEvents = [...state.events, action.event];
      let newStage = state.currentStage;
      const newCompleted = new Set(state.completedStages);

      if (action.event.type === "stage") {
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
  messages: [],
  events: [],
  currentStage: null,
  completedStages: new Set(),
  pipeline: null,
  nodeStatuses: {},
  executionResult: null,
  errorMessage: null,
  userIntent: null,
};

// ── Component ──

export default function AgentStudioPage() {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const [input, setInput] = useState("");
  const [blocksLoaded, setBlocksLoaded] = useState(false);
  const [isClarifyLoading, setIsClarifyLoading] = useState(false);
  const [thinkerOpen, setThinkerOpen] = useState(true);
  const [resultsExpanded, setResultsExpanded] = useState(true);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const chatScrollRef = useRef<HTMLDivElement>(null);

  // Load block metadata on mount
  useEffect(() => {
    listBlocks()
      .then((blocks) => {
        setBlockMetadata(blocks);
        setBlocksLoaded(true);
      })
      .catch(() => setBlocksLoaded(true));
  }, []);

  // Auto-scroll chat
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [state.messages]);

  // Run the stream pipeline (extracted for reuse)
  const runStream = useCallback(async (intent: string) => {
    dispatch({ type: "START_THINKING", intent });

    await createAgentStream(
      intent,
      "default",
      (eventType, data) => {
        const event: SSEEvent = { type: eventType, ...data };
        dispatch({ type: "SSE_EVENT", event });

        if ((eventType === "match_found" || eventType === "block_created") && data.block_id) {
          addBlockMetadata([{
            id: data.block_id as string,
            name: (data.block_name || data.block_id) as string,
            category: (data.category as BlockCategory) || "process",
          }]);
        }

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
  }, []);

  const handleSubmit = useCallback(async () => {
    const text = input.trim();
    if (!text || isClarifyLoading || state.phase === "thinking" || state.phase === "executing") return;

    setInput("");

    // If we're already in clarification mode, add user message and continue
    if (state.phase === "clarifying") {
      dispatch({ type: "ADD_USER_MESSAGE", content: text });
      setIsClarifyLoading(true);

      try {
        const result = await clarifyIntent(text, state.messages);
        if (result.ready) {
          const intent = result.refined_intent || text;
          dispatch({ type: "CLARIFICATION_COMPLETE", intent });
          await runStream(intent);
        } else {
          dispatch({ type: "ADD_ASSISTANT_MESSAGE", content: result.question || "Could you tell me more?" });
        }
      } catch {
        await runStream(text);
      } finally {
        setIsClarifyLoading(false);
      }
      return;
    }

    // First submit — start clarification
    dispatch({ type: "START_CLARIFYING", message: text });
    setIsClarifyLoading(true);

    try {
      const result = await clarifyIntent(text, []);
      if (result.ready) {
        const intent = result.refined_intent || text;
        dispatch({ type: "CLARIFICATION_COMPLETE", intent });
        await runStream(intent);
      } else {
        dispatch({ type: "ADD_ASSISTANT_MESSAGE", content: result.question || "Could you tell me more?" });
      }
    } catch {
      await runStream(text);
    } finally {
      setIsClarifyLoading(false);
    }
  }, [input, state.phase, state.messages, isClarifyLoading, runStream]);

  const handleExecute = useCallback(async () => {
    if (!state.pipeline) return;
    dispatch({ type: "START_EXECUTION" });

    const nodes = state.pipeline.nodes;
    const animationTimers: ReturnType<typeof setTimeout>[] = [];

    nodes.forEach((node, i) => {
      animationTimers.push(
        setTimeout(() => {
          if (i > 0) dispatch({ type: "UPDATE_NODE_STATUS", nodeId: nodes[i - 1].id, status: "completed" });
          dispatch({ type: "UPDATE_NODE_STATUS", nodeId: node.id, status: "running" });
        }, i * 800)
      );
    });

    try {
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
      handleSubmit();
    }
  };

  const pipelineNodes: PipelineNode[] = state.pipeline?.nodes || [];
  const pipelineEdges: PipelineEdge[] = (state.pipeline?.edges || []).map((e) => ({
    from: e.from,
    to: e.to,
  }));

  const isThinking = state.phase === "thinking";
  const isClarifying = state.phase === "clarifying";
  const showPipeline = state.pipeline && blocksLoaded;
  const showResults = state.phase === "complete" && state.executionResult;
  const isActive = state.phase !== "idle" && !isClarifying;

  // Button content
  const buttonContent = (() => {
    if (isThinking || isClarifyLoading) {
      return (
        <>
          <Loader2 className="w-4 h-4 animate-spin" />
          Thinking...
        </>
      );
    }
    if (isClarifying) {
      return (
        <>
          <Send className="w-4 h-4" />
          Send
        </>
      );
    }
    return (
      <>
        <Sparkles className="w-4 h-4" />
        Create
      </>
    );
  })();

  return (
    <div className="flex flex-col h-screen">
      {isActive ? (
        /* ═══ ACTIVE STATE (thinking / ready / executing / complete) ═══ */
        <>
          {/* Compact top bar: toggle + intent + stage progress + reset */}
          <div className="border-b border-white/5 bg-gray-950/60 backdrop-blur-md">
            <div className="flex items-center gap-3 px-4 py-2.5">
              {/* Thinker toggle */}
              <button
                onClick={() => setThinkerOpen(!thinkerOpen)}
                className="p-1.5 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-white/5 transition-colors"
                title={thinkerOpen ? "Hide thinker log" : "Show thinker log"}
              >
                {thinkerOpen ? (
                  <PanelLeftClose className="w-4 h-4" />
                ) : (
                  <PanelLeftOpen className="w-4 h-4" />
                )}
              </button>

              {/* User intent */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-300 truncate">
                  {state.userIntent}
                </p>
              </div>

              {/* Inline stage progress */}
              <StageProgressBar
                currentStage={state.currentStage}
                completedStages={state.completedStages}
              />

              {/* Reset */}
              <button
                onClick={() => dispatch({ type: "RESET" })}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-gray-500 hover:text-gray-300 hover:bg-white/5 rounded-lg transition-colors"
              >
                <RotateCcw className="w-3 h-3" />
                Reset
              </button>
            </div>
          </div>

          {/* Main content area */}
          <div className="flex-1 flex overflow-hidden">
            {/* Left: Thinker Log (collapsible side panel) */}
            <AnimatePresence initial={false}>
              {thinkerOpen && (
                <motion.div
                  initial={{ width: 0, opacity: 0 }}
                  animate={{ width: 340, opacity: 1 }}
                  exit={{ width: 0, opacity: 0 }}
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  className="flex-shrink-0 overflow-hidden border-r border-white/5"
                >
                  <div className="w-[340px] h-full flex flex-col bg-gray-900/40 backdrop-blur-md">
                    <div className="px-4 py-2.5 border-b border-white/5 flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${
                        isThinking ? "bg-blue-400 animate-glow-pulse" : "bg-green-400/60"
                      }`} />
                      <span className="text-xs font-medium text-gray-400">AI Thinking</span>
                    </div>
                    <div className="flex-1 overflow-hidden">
                      <ThinkerLog events={state.events} />
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Right: Pipeline + Run + Results */}
            <div className="flex-1 flex flex-col overflow-hidden min-w-0 relative">
              {showPipeline ? (
                <>
                  <div className="flex-1 min-h-0">
                    <PipelineGraph
                      nodes={pipelineNodes}
                      edges={pipelineEdges}
                      nodeStatuses={state.nodeStatuses}
                    />
                  </div>

                  {/* Floating run button */}
                  {state.phase === "ready" && (
                    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10">
                      <motion.button
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        onClick={handleExecute}
                        className="flex items-center gap-2.5 px-8 py-3 bg-green-600 hover:bg-green-500 text-white text-sm font-medium rounded-xl transition-all shadow-lg shadow-green-500/20 hover:shadow-green-500/30"
                      >
                        <Play className="w-4 h-4" />
                        Run Pipeline
                      </motion.button>
                    </div>
                  )}

                  {/* Executing indicator */}
                  {state.phase === "executing" && (
                    <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-10">
                      <div className="flex items-center gap-2.5 px-6 py-3 rounded-xl glass text-blue-400 text-sm">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Running pipeline...
                      </div>
                    </div>
                  )}

                  {/* Results overlay */}
                  <AnimatePresence>
                    {showResults && (
                      <motion.div
                        initial={{ y: "100%" }}
                        animate={{ y: 0 }}
                        exit={{ y: "100%" }}
                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                        className="absolute bottom-0 left-0 right-0 z-20 max-h-[50%] bg-gray-950/90 backdrop-blur-xl border-t border-white/10 rounded-t-2xl shadow-2xl shadow-black/50"
                      >
                        <button
                          onClick={() => setResultsExpanded(!resultsExpanded)}
                          className="w-full flex items-center justify-between px-6 py-3 hover:bg-white/5 transition-colors rounded-t-2xl"
                        >
                          <div className="flex items-center gap-2">
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
                          <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${resultsExpanded ? "" : "rotate-180"}`} />
                        </button>

                        {resultsExpanded && (
                          <div className="overflow-y-auto max-h-[calc(50vh-48px)] px-6 pb-6 thin-scrollbar">
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
                      </motion.div>
                    )}
                  </AnimatePresence>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-600">
                  <div className="text-center">
                    <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    <p className="text-sm text-gray-600">Pipeline will appear here</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      ) : isClarifying ? (
        /* ═══ CLARIFYING STATE ═══ */
        <>
          {/* Header */}
          <div className="border-b border-white/5 bg-gray-950/60 backdrop-blur-md px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-lg font-semibold text-gray-200">Agent Studio</h1>
                <p className="text-sm text-gray-600">
                  Let&apos;s refine your idea
                </p>
              </div>
              <button
                onClick={() => dispatch({ type: "RESET" })}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-gray-500 hover:text-gray-300 hover:bg-white/5 rounded-lg transition-colors"
              >
                <RotateCcw className="w-3 h-3" />
                Reset
              </button>
            </div>
          </div>

          {/* Chat messages */}
          <div className="flex-1 overflow-hidden flex flex-col">
            <div ref={chatScrollRef} className="flex-1 overflow-y-auto px-6 py-6 thin-scrollbar">
              <div className="max-w-2xl mx-auto space-y-3">
                <AnimatePresence>
                  {state.messages.map((msg, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2 }}
                      className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      <div
                        className={`max-w-[75%] px-4 py-2.5 rounded-2xl text-sm ${
                          msg.role === "user"
                            ? "bg-blue-600/80 text-white rounded-br-md"
                            : "bg-white/[0.04] border border-white/[0.06] text-gray-200 rounded-bl-md"
                        }`}
                      >
                        {msg.role === "assistant" && (
                          <MessageCircle className="w-3 h-3 text-gray-500 mb-1 inline-block mr-1.5" />
                        )}
                        {msg.content}
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
                {isClarifyLoading && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex justify-start"
                  >
                    <div className="bg-white/[0.04] border border-white/[0.06] text-gray-400 px-4 py-2.5 rounded-2xl rounded-bl-md text-sm flex items-center gap-2">
                      <Loader2 className="w-3 h-3 animate-spin" />
                      Thinking...
                    </div>
                  </motion.div>
                )}
              </div>
            </div>

            {/* Clarification input */}
            <div className="border-t border-white/5 p-4">
              <div className="max-w-2xl mx-auto flex gap-3">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Reply to the assistant..."
                  rows={1}
                  disabled={isClarifyLoading}
                  className="flex-1 px-4 py-3 bg-white/[0.03] border border-white/10 rounded-xl text-sm text-gray-100 placeholder-gray-600 focus:outline-none input-glow focus:border-blue-500/30 disabled:opacity-50 transition-all resize-none"
                />
                <button
                  onClick={handleSubmit}
                  disabled={!input.trim() || isClarifyLoading}
                  className="px-5 py-3 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-xl disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center gap-2"
                >
                  {buttonContent}
                </button>
              </div>
            </div>
          </div>
        </>
      ) : (
        /* ═══ IDLE STATE — Hero Layout ═══ */
        <div className="flex-1 flex flex-col items-center justify-center px-6">
          <div className="w-full max-w-2xl text-center">
            {/* Animated gradient orb */}
            <div className="relative inline-flex mb-8">
              <div className="absolute inset-0 blur-3xl opacity-30 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full scale-150 animate-glow-pulse" />
              <Sparkles className="relative w-14 h-14 text-blue-400/80 animate-float" />
            </div>

            <h2 className="text-2xl font-semibold text-gray-200 mb-3">
              What do you want to automate?
            </h2>
            <p className="text-gray-500 mb-10 max-w-lg mx-auto leading-relaxed">
              Describe your automation in plain English. The AI will decompose it into
              blocks, wire them into a pipeline, and execute it — all in real-time.
            </p>

            {/* Hero input area */}
            <div className="relative mb-6">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Describe your automation..."
                rows={2}
                disabled={isThinking}
                className="w-full px-5 py-4 bg-white/[0.03] border border-white/10 rounded-2xl text-sm text-gray-100 placeholder-gray-600 focus:outline-none input-glow focus:border-blue-500/30 disabled:opacity-50 transition-all resize-none"
              />
              <button
                onClick={handleSubmit}
                disabled={!input.trim() || isThinking}
                className="absolute right-3 bottom-3 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-xl disabled:opacity-30 disabled:cursor-not-allowed transition-all flex items-center gap-2"
              >
                <Sparkles className="w-4 h-4" />
                Create
              </button>
            </div>

            {/* Example prompts as glass pills */}
            <div className="flex flex-wrap justify-center gap-2">
              {[
                "Look up AirPods price, generate a budget, check if it fits",
                "Search top stories across BBC, CNN, Reuters. Score & rank them",
                "Search for AI news every morning",
                "Summarize top Hacker News posts",
              ].map((example) => (
                <button
                  key={example}
                  onClick={() => {
                    setInput(example);
                    inputRef.current?.focus();
                  }}
                  className="text-xs px-3.5 py-2 rounded-full bg-white/[0.03] border border-white/[0.06] text-gray-500 hover:text-gray-300 hover:bg-white/[0.06] hover:border-white/10 transition-all"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
