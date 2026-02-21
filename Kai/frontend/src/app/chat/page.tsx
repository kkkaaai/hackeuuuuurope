"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send,
  Play,
  Save,
  X,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import { sendChat, savePipeline, runPipeline } from "@/lib/api";
import { PipelineGraph } from "@/components/pipeline/PipelineGraph";
import { PipelineResultDisplay } from "@/components/pipeline/PipelineResultDisplay";
import { setBlockMetadata, getBlockMeta } from "@/lib/utils";
import { listBlocks } from "@/lib/api";
import { CATEGORY_BG } from "@/lib/constants";
import type { ChatResponse, ExecutionResult } from "@/lib/types";

type Phase = "idle" | "loading" | "preview" | "executing" | "complete" | "error";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  pipeline?: ChatResponse;
  result?: ExecutionResult;
  error?: string;
}

interface State {
  phase: Phase;
  messages: Message[];
  currentPipeline: ChatResponse | null;
  nodeStatuses: Record<string, string>;
}

type Action =
  | { type: "SEND_MESSAGE"; content: string }
  | { type: "RECEIVE_PIPELINE"; pipeline: ChatResponse }
  | { type: "START_EXECUTION" }
  | { type: "UPDATE_NODE_STATUS"; nodeId: string; status: string }
  | { type: "EXECUTION_COMPLETE"; result: ExecutionResult }
  | { type: "ERROR"; error: string }
  | { type: "REJECT" }
  | { type: "RESET" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SEND_MESSAGE":
      return {
        ...state,
        phase: "loading",
        messages: [
          ...state.messages,
          { id: Date.now().toString(), role: "user", content: action.content },
        ],
      };
    case "RECEIVE_PIPELINE":
      return {
        ...state,
        phase: "preview",
        currentPipeline: action.pipeline,
        nodeStatuses: {},
        messages: [
          ...state.messages,
          {
            id: Date.now().toString(),
            role: "assistant",
            content: `I'll create a pipeline with ${action.pipeline.nodes.length} blocks to: "${action.pipeline.user_intent}"`,
            pipeline: action.pipeline,
          },
        ],
      };
    case "START_EXECUTION":
      return { ...state, phase: "executing", nodeStatuses: {} };
    case "UPDATE_NODE_STATUS":
      return {
        ...state,
        nodeStatuses: { ...state.nodeStatuses, [action.nodeId]: action.status },
      };
    case "EXECUTION_COMPLETE": {
      const lastMsg = state.messages[state.messages.length - 1];
      const updatedMessages = state.messages.slice(0, -1);
      updatedMessages.push({ ...lastMsg, result: action.result });
      const allDone: Record<string, string> = {};
      state.currentPipeline?.nodes.forEach((n) => {
        allDone[n.id] = action.result.status === "completed" ? "completed" : "failed";
      });
      return {
        ...state,
        phase: "complete",
        messages: updatedMessages,
        nodeStatuses: allDone,
      };
    }
    case "ERROR":
      return {
        ...state,
        phase: "error",
        messages: [
          ...state.messages,
          {
            id: Date.now().toString(),
            role: "assistant",
            content: action.error,
            error: action.error,
          },
        ],
      };
    case "REJECT":
      return { ...state, phase: "idle", currentPipeline: null, nodeStatuses: {} };
    case "RESET":
      return { ...state, phase: "idle", currentPipeline: null, nodeStatuses: {} };
    default:
      return state;
  }
}

const INITIAL_STATE: State = {
  phase: "idle",
  messages: [],
  currentPipeline: null,
  nodeStatuses: {},
};

export default function ChatPage() {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const [input, setInput] = useState("");
  const [blocksLoaded, setBlocksLoaded] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Load block metadata on mount
  useEffect(() => {
    listBlocks().then((blocks) => {
      setBlockMetadata(blocks);
      setBlocksLoaded(true);
    }).catch(() => setBlocksLoaded(true));
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.messages, state.phase]);

  const handleSend = useCallback(async () => {
    const message = input.trim();
    if (!message || state.phase === "loading") return;

    setInput("");
    dispatch({ type: "SEND_MESSAGE", content: message });

    try {
      const response = await sendChat({ message, auto_execute: false });
      dispatch({ type: "RECEIVE_PIPELINE", pipeline: response });
    } catch {
      dispatch({ type: "ERROR", error: "Failed to process your request. Is the backend running?" });
    }
  }, [input, state.phase]);

  const handleExecute = useCallback(async () => {
    if (!state.currentPipeline) return;
    dispatch({ type: "START_EXECUTION" });

    const nodes = state.currentPipeline.nodes;

    // Animate nodes sequentially
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
      // Save pipeline first, then run it
      const saved = await savePipeline({
        id: state.currentPipeline.pipeline_id,
        user_intent: state.currentPipeline.user_intent,
        trigger: { type: state.currentPipeline.trigger_type },
        nodes: state.currentPipeline.nodes,
        edges: state.currentPipeline.edges,
      });

      const result = await runPipeline(saved.id);

      // Clear animation timers
      animationTimers.forEach(clearTimeout);
      dispatch({ type: "EXECUTION_COMPLETE", result });
    } catch {
      animationTimers.forEach(clearTimeout);
      dispatch({
        type: "EXECUTION_COMPLETE",
        result: {
          pipeline_id: state.currentPipeline.pipeline_id,
          run_id: "error",
          status: "failed",
          shared_context: {},
          node_results: [],
          errors: ["Execution failed. Check that the backend is running."],
        },
      });
    }
  }, [state.currentPipeline]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-lg font-semibold">Chat</h1>
        <p className="text-sm text-gray-500">Describe what you want to automate</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {state.messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <Sparkles className="w-12 h-12 text-blue-500/50 mb-4" />
            <h2 className="text-xl font-semibold text-gray-300 mb-2">
              What do you want to automate?
            </h2>
            <p className="text-gray-500 max-w-md">
              Describe your automation in plain English. I&apos;ll break it into blocks,
              wire them into a pipeline, and execute it.
            </p>
            <div className="mt-6 flex flex-wrap gap-2 justify-center max-w-lg">
              {[
                "Search for AI news every morning",
                "Track Bitcoin price and alert if below $60k",
                "Summarize top Hacker News posts",
                "Find the best laptop deals under $1000",
              ].map((example) => (
                <button
                  key={example}
                  onClick={() => { setInput(example); inputRef.current?.focus(); }}
                  className="text-xs px-3 py-1.5 rounded-full border border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        )}

        <AnimatePresence>
          {state.messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-2xl rounded-2xl px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : msg.error
                    ? "bg-red-500/10 border border-red-500/30 text-red-300"
                    : "bg-gray-800 text-gray-200"
                }`}
              >
                <p className="text-sm">{msg.content}</p>

                {/* Pipeline preview */}
                {msg.pipeline && blocksLoaded && (
                  <div className="mt-3 border-t border-gray-700 pt-3">
                    <div className="text-xs text-gray-400 mb-2">
                      Pipeline: {msg.pipeline.nodes.length} blocks &middot;{" "}
                      {msg.pipeline.trigger_type} trigger
                    </div>

                    <div className="rounded-lg overflow-hidden border border-gray-700 bg-gray-900">
                      <PipelineGraph
                        nodes={msg.pipeline.nodes}
                        edges={msg.pipeline.edges}
                        nodeStatuses={state.nodeStatuses}
                        mini
                      />
                    </div>

                    {/* Node list */}
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {msg.pipeline.nodes.map((node) => {
                        const meta = getBlockMeta(node.block_id);
                        const bgClass = CATEGORY_BG[meta.category] || CATEGORY_BG.control;
                        return (
                          <span
                            key={node.id}
                            className={`text-xs px-2 py-0.5 rounded-full border ${bgClass}`}
                          >
                            {meta.name}
                          </span>
                        );
                      })}
                    </div>

                    {/* Approval bar */}
                    {state.phase === "preview" && (
                      <div className="mt-3 flex gap-2">
                        <button
                          onClick={handleExecute}
                          className="flex items-center gap-1.5 px-4 py-2 bg-green-600 hover:bg-green-500 text-white text-sm font-medium rounded-lg transition-colors"
                        >
                          <Play className="w-3.5 h-3.5" />
                          Run Pipeline
                        </button>
                        <button
                          onClick={() => dispatch({ type: "REJECT" })}
                          className="flex items-center gap-1.5 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm rounded-lg transition-colors"
                        >
                          <X className="w-3.5 h-3.5" />
                          Reject
                        </button>
                      </div>
                    )}

                    {/* Executing indicator */}
                    {state.phase === "executing" && (
                      <div className="mt-3 flex items-center gap-2 text-blue-400 text-sm">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Running pipeline...
                      </div>
                    )}

                    {/* Execution result */}
                    {msg.result && (
                      <div
                        className={`mt-3 rounded-lg p-3 border ${
                          msg.result.status === "completed"
                            ? "bg-green-500/10 border-green-500/30"
                            : "bg-red-500/10 border-red-500/30"
                        }`}
                      >
                        <div className="flex items-center gap-2 mb-2">
                          {msg.result.status === "completed" ? (
                            <CheckCircle2 className="w-4 h-4 text-green-400" />
                          ) : (
                            <AlertCircle className="w-4 h-4 text-red-400" />
                          )}
                          <span
                            className={`text-sm font-medium ${
                              msg.result.status === "completed" ? "text-green-400" : "text-red-400"
                            }`}
                          >
                            {msg.result.status === "completed" ? "Pipeline completed" : "Pipeline failed"}
                          </span>
                        </div>

                        {msg.result.errors.length > 0 && (
                          <div className="text-xs text-red-300 mb-2">
                            {msg.result.errors.join(", ")}
                          </div>
                        )}

                        {Object.keys(msg.result.shared_context).length > 0 && (
                          <PipelineResultDisplay
                            sharedContext={msg.result.shared_context as Record<string, Record<string, unknown>>}
                            errors={msg.result.errors}
                          />
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Loading indicator */}
        {state.phase === "loading" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="bg-gray-800 rounded-2xl px-4 py-3 flex items-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
              <span className="text-sm text-gray-400">Analyzing your request...</span>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="border-t border-gray-800 p-4">
        <div className="max-w-3xl mx-auto relative">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your automation..."
            disabled={state.phase === "loading" || state.phase === "executing"}
            className="w-full px-4 py-3 pr-12 bg-gray-900 border border-gray-700 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 disabled:opacity-50 transition-all shadow-lg shadow-blue-500/5"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || state.phase === "loading" || state.phase === "executing"}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2 text-gray-400 hover:text-blue-400 disabled:opacity-30 transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
