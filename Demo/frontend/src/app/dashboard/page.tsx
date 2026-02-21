"use client";

import { motion } from "framer-motion";
import {
  Play,
  Trash2,
  Workflow,
  Loader2,
  RefreshCw,
  RotateCcw,
} from "lucide-react";
import { PipelineResultDisplay } from "@/components/pipeline/PipelineResultDisplay";
import { CATEGORY_BG } from "@/lib/constants";
import { useDashboard } from "@/lib/dashboard-context";

export default function DashboardPage() {
  const {
    pipelines,
    loading,
    runningId,
    lastResult,
    runError,
    lastRunPipelineId,
    fetchPipelines,
    handleRun,
    handleDelete,
  } = useDashboard();

  const statusColors: Record<string, string> = {
    created: "bg-gray-500/20 text-gray-400",
    running: "bg-blue-500/20 text-blue-400",
    completed: "bg-green-500/20 text-green-400",
    failed: "bg-red-500/20 text-red-400",
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold">Dashboard</h1>
          <p className="text-sm text-gray-500">
            {pipelines.length} pipeline{pipelines.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={fetchPipelines}
          className="p-2 text-gray-400 hover:text-gray-200 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Last execution result */}
      {lastResult && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`mb-4 p-4 rounded-lg border ${
            lastResult.status === "completed"
              ? "bg-green-500/5 border-green-500/30"
              : "bg-red-500/5 border-red-500/30"
          }`}
        >
          <div className="flex items-center justify-between mb-3">
            <p className={`text-sm font-medium ${
              lastResult.status === "completed" ? "text-green-400" : "text-red-400"
            }`}>
              Pipeline {lastResult.status}
            </p>
            {lastResult.status === "failed" && lastRunPipelineId && (
              <button
                onClick={() => handleRun(lastRunPipelineId)}
                disabled={!!runningId}
                className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-md disabled:opacity-50 transition-colors"
              >
                {runningId === lastRunPipelineId ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <RotateCcw className="w-3 h-3" />
                )}
                Retry
              </button>
            )}
          </div>
          {lastResult.errors && lastResult.errors.length > 0 && (
            <p className="text-xs text-red-300 mb-3">{lastResult.errors.join(", ")}</p>
          )}
          {lastResult.shared_context && Object.keys(lastResult.shared_context).length > 0 && (
            <PipelineResultDisplay
              sharedContext={lastResult.shared_context as Record<string, Record<string, unknown>>}
              errors={lastResult.errors}
            />
          )}
        </motion.div>
      )}

      {/* Run error */}
      {runError && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-4 p-4 rounded-lg border bg-red-500/5 border-red-500/30"
        >
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-red-400">
              Run failed: {runError}
            </p>
            {lastRunPipelineId && (
              <button
                onClick={() => handleRun(lastRunPipelineId)}
                disabled={!!runningId}
                className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-md disabled:opacity-50 transition-colors"
              >
                {runningId === lastRunPipelineId ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <RotateCcw className="w-3 h-3" />
                )}
                Retry
              </button>
            )}
          </div>
        </motion.div>
      )}

      {loading && pipelines.length === 0 ? (
        <div className="flex items-center justify-center h-64 text-gray-500">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading pipelines...
        </div>
      ) : pipelines.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-gray-500">
          <Workflow className="w-10 h-10 mb-3 opacity-50" />
          <p>No pipelines yet</p>
          <p className="text-xs mt-1">Create one from the Chat page</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {pipelines.map((pipeline, i) => (
            <motion.div
              key={pipeline.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex items-center gap-4 hover:border-gray-700 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-200 truncate">
                  {(pipeline as any).user_prompt || pipeline.user_intent || (pipeline as any).name || "Untitled"}
                </p>
                <div className="flex items-center gap-2 mt-1.5">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      statusColors[pipeline.status] || statusColors.created
                    }`}
                  >
                    {pipeline.status}
                  </span>
                  {pipeline.trigger_type && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-400">
                      {pipeline.trigger_type}
                    </span>
                  )}
                  <span className="text-xs text-gray-600">
                    {pipeline.node_count} blocks
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-1">
                <button
                  onClick={() => handleRun(pipeline.id)}
                  disabled={runningId === pipeline.id}
                  className="p-2 text-gray-400 hover:text-green-400 disabled:opacity-50 transition-colors"
                  title="Run pipeline"
                >
                  {runningId === pipeline.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                </button>
                <button
                  onClick={() => handleDelete(pipeline.id)}
                  className="p-2 text-gray-400 hover:text-red-400 transition-colors"
                  title="Delete pipeline"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
