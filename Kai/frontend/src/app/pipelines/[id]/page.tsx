"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Play,
  ArrowLeft,
  Loader2,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react";
import { getPipeline, runPipeline, listBlocks } from "@/lib/api";
import { PipelineGraph } from "@/components/pipeline/PipelineGraph";
import { setBlockMetadata, getBlockMeta } from "@/lib/utils";
import { CATEGORY_BG } from "@/lib/constants";
import type { PipelineNode, PipelineEdge, ExecutionResult } from "@/lib/types";

interface PipelineDetail {
  id: string;
  user_intent: string;
  status: string;
  definition: {
    nodes: PipelineNode[];
    edges: PipelineEdge[];
    trigger: { type: string };
  };
  created_at: string;
}

export default function PipelineDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [pipeline, setPipeline] = useState<PipelineDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ExecutionResult | null>(null);
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, string>>({});
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  useEffect(() => {
    listBlocks().then((blocks) => setBlockMetadata(blocks)).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    getPipeline(id)
      .then((data) => setPipeline(data as unknown as PipelineDetail))
      .catch(() => setPipeline(null))
      .finally(() => setLoading(false));
  }, [id]);

  const handleRun = async () => {
    if (!pipeline) return;
    setRunning(true);
    setResult(null);
    setNodeStatuses({});

    // Animate nodes
    const nodes = pipeline.definition.nodes;
    const timers: ReturnType<typeof setTimeout>[] = [];
    nodes.forEach((node, i) => {
      timers.push(
        setTimeout(() => {
          if (i > 0) setNodeStatuses((s) => ({ ...s, [nodes[i - 1].id]: "completed" }));
          setNodeStatuses((s) => ({ ...s, [node.id]: "running" }));
        }, i * 800)
      );
    });

    try {
      const res = await runPipeline(id);
      timers.forEach(clearTimeout);
      setResult(res);
      const allDone: Record<string, string> = {};
      nodes.forEach((n) => {
        allDone[n.id] = res.status === "completed" ? "completed" : "failed";
      });
      setNodeStatuses(allDone);
    } catch {
      timers.forEach(clearTimeout);
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen text-slate-400">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  if (!pipeline) {
    return (
      <div className="flex flex-col items-center justify-center h-screen text-slate-400">
        <p>Pipeline not found</p>
        <button
          onClick={() => router.push("/dashboard")}
          className="mt-2 text-sm text-[#0000FF] hover:underline"
        >
          Back to dashboard
        </button>
      </div>
    );
  }

  const selectedNodeData = selectedNode
    ? pipeline.definition.nodes.find((n) => n.id === selectedNode)
    : null;

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b border-slate-200 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => router.push("/dashboard")}
          className="text-slate-400 hover:text-slate-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-semibold text-slate-900 truncate">{pipeline.user_intent}</h1>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-slate-400 font-mono">{pipeline.id}</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500">
              {pipeline.status}
            </span>
          </div>
        </div>
        <button
          onClick={handleRun}
          disabled={running}
          className="flex items-center gap-1.5 px-4 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
        >
          {running ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Play className="w-3.5 h-3.5" />
          )}
          {running ? "Running..." : "Run"}
        </button>
      </div>

      {/* Graph + detail panel */}
      <div className="flex-1 flex overflow-hidden">
        <div className={`flex-1 ${selectedNode ? "border-r border-slate-200" : ""}`}>
          <PipelineGraph
            nodes={pipeline.definition.nodes}
            edges={pipeline.definition.edges}
            nodeStatuses={nodeStatuses}
            onNodeClick={(nodeId) =>
              setSelectedNode(selectedNode === nodeId ? null : nodeId)
            }
          />
        </div>

        {/* Node detail panel */}
        {selectedNodeData && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 320, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            className="w-80 overflow-y-auto bg-slate-50 p-4"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-slate-900">Node Details</h3>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-400 hover:text-slate-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400">ID:</span>{" "}
                <span className="font-mono text-slate-700">{selectedNodeData.id}</span>
              </div>
              <div>
                <span className="text-slate-400">Block:</span>{" "}
                <span className="text-slate-700">
                  {getBlockMeta(selectedNodeData.block_id).name}
                </span>
              </div>
              <div>
                <span className="text-slate-400">Category:</span>{" "}
                <span
                  className={`px-1.5 py-0.5 rounded border ${
                    CATEGORY_BG[getBlockMeta(selectedNodeData.block_id).category] ||
                    ""
                  }`}
                >
                  {getBlockMeta(selectedNodeData.block_id).category}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block mb-1">Inputs:</span>
                <pre className="p-2 rounded bg-white border border-slate-200 text-slate-600 overflow-x-auto">
                  {JSON.stringify(selectedNodeData.inputs, null, 2)}
                </pre>
              </div>

              {result?.shared_context[selectedNodeData.id] != null && (
                <div>
                  <span className="text-slate-400 block mb-1">Output:</span>
                  <pre className="p-2 rounded bg-white border border-slate-200 text-green-700 overflow-x-auto">
                    {JSON.stringify(
                      result.shared_context[selectedNodeData.id] as Record<string, unknown>,
                      null,
                      2
                    )}
                  </pre>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </div>

      {/* Execution result bar */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`border-t px-6 py-3 flex items-center gap-2 text-sm ${
            result.status === "completed"
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          {result.status === "completed" ? (
            <CheckCircle2 className="w-4 h-4" />
          ) : (
            <AlertCircle className="w-4 h-4" />
          )}
          Pipeline {result.status} &middot; Run: {result.run_id}
          {result.errors.length > 0 && (
            <span className="text-xs ml-2">{result.errors.join(", ")}</span>
          )}
        </motion.div>
      )}
    </div>
  );
}
