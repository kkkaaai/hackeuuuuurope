"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Play,
  Clock,
  Trash2,
  Loader2,
  Calendar,
  Timer,
  Zap,
} from "lucide-react";
import {
  listPipelines,
  listSchedules,
  runPipeline,
  deletePipeline,
  listBlocks,
} from "@/lib/api";
import { PipelineGraph } from "@/components/pipeline/PipelineGraph";
import { setBlockMetadata } from "@/lib/utils";
import type { PipelineListItem } from "@/lib/types";

function useCountdown(targetIso: string | null) {
  const [remaining, setRemaining] = useState<string | null>(null);
  useEffect(() => {
    if (!targetIso) { setRemaining(null); return; }
    const tick = () => {
      const diff = new Date(targetIso).getTime() - Date.now();
      if (diff <= 0) { setRemaining("now"); return; }
      const hrs = Math.floor(diff / 3_600_000);
      const mins = Math.floor((diff % 3_600_000) / 60_000);
      const secs = Math.floor((diff % 60_000) / 1_000);
      setRemaining(hrs > 0 ? `${hrs}h ${mins}m` : `${mins}:${secs.toString().padStart(2, "0")}`);
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [targetIso]);
  return remaining;
}

const TRIGGER_CONFIG: Record<string, { icon: typeof Clock; label: string; color: string }> = {
  cron: { icon: Calendar, label: "Scheduled", color: "text-[#0000FF] bg-[#0000FF]/8 border-[#0000FF]/20" },
  interval: { icon: Timer, label: "Interval", color: "text-cyan-600 bg-cyan-50 border-cyan-200" },
  manual: { icon: Zap, label: "Manual", color: "text-slate-500 bg-slate-50 border-slate-200" },
  webhook: { icon: Zap, label: "Webhook", color: "text-amber-600 bg-amber-50 border-amber-200" },
};

function TriggerBadge({ triggerType }: { triggerType: string }) {
  const config = TRIGGER_CONFIG[triggerType] || TRIGGER_CONFIG.manual;
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full border ${config.color}`}>
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    completed: "bg-green-500",
    running: "bg-[#0000FF] animate-pulse",
    failed: "bg-red-500",
    created: "bg-slate-300",
  };
  return <div className={`w-2 h-2 rounded-full ${colors[status] || colors.created}`} title={status} />;
}

function PipelineCard({ pipeline, nextRun, blocksLoaded, onRun, onDelete }: {
  pipeline: PipelineListItem; nextRun: string | null; blocksLoaded: boolean;
  onRun: (id: string) => Promise<void>; onDelete: (id: string) => void;
}) {
  const countdown = useCountdown(nextRun);
  const isScheduled = pipeline.trigger_type === "cron" || pipeline.trigger_type === "interval";
  const [running, setRunning] = useState(false);
  const handleRun = async () => { setRunning(true); try { await onRun(pipeline.id); } finally { setRunning(false); } };

  return (
    <motion.div layout initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}
      className="rounded-xl border border-slate-200 bg-white overflow-hidden hover:border-[#0000FF]/30 hover:shadow-md transition-all group"
    >
      {blocksLoaded && pipeline.nodes.length > 0 && (
        <div className="border-b border-slate-100 bg-slate-50/50">
          <PipelineGraph nodes={pipeline.nodes} edges={pipeline.edges} mini />
        </div>
      )}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="text-sm font-semibold text-slate-800 line-clamp-2 flex-1">{pipeline.user_intent}</h3>
          <StatusDot status={pipeline.status} />
        </div>
        <div className="flex items-center gap-2 mb-3">
          <TriggerBadge triggerType={pipeline.trigger_type} />
          <span className="text-xs text-slate-400">{pipeline.node_count} blocks</span>
        </div>
        <div className="flex items-center gap-2">
          {isScheduled && countdown ? (
            <div className="flex items-center gap-1.5 text-xs text-[#0000FF]">
              <Clock className="w-3.5 h-3.5" />
              <span>Next run {countdown === "now" ? "now" : `in ${countdown}`}</span>
            </div>
          ) : (
            <button onClick={handleRun} disabled={running}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0000FF] hover:bg-[#2222FF] disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors">
              {running ? <Loader2 className="w-3 h-3 animate-spin" /> : <Play className="w-3 h-3" />}
              Execute
            </button>
          )}
          <button onClick={() => { if (window.confirm(`Delete "${pipeline.user_intent}"?`)) onDelete(pipeline.id); }}
            aria-label={`Delete pipeline: ${pipeline.user_intent}`}
            className="ml-auto p-1.5 text-slate-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-all">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

const POLL_INTERVAL_MS = 30_000;

export default function DashboardPage() {
  const [pipelines, setPipelines] = useState<PipelineListItem[]>([]);
  const [scheduleMap, setScheduleMap] = useState<Map<string, string | null>>(new Map());
  const [loading, setLoading] = useState(true);
  const [blocksLoaded, setBlocksLoaded] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval>>(undefined);

  const fetchData = useCallback(async () => {
    try {
      const [pipelineList, schedules] = await Promise.all([listPipelines(), listSchedules()]);
      setPipelines(pipelineList);
      const map = new Map<string, string | null>();
      for (const s of schedules) map.set(s.pipeline_id, s.next_run);
      setScheduleMap(map);
    } catch (err) { console.error("Failed to fetch dashboard data:", err); } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    listBlocks().then((blocks) => { setBlockMetadata(blocks); setBlocksLoaded(true); }).catch(() => setBlocksLoaded(true));
    fetchData();
    pollRef.current = setInterval(fetchData, POLL_INTERVAL_MS);
    return () => clearInterval(pollRef.current);
  }, [fetchData]);

  const handleRun = useCallback(async (id: string) => { await runPipeline(id); await fetchData(); }, [fetchData]);
  const handleDelete = useCallback(async (id: string) => { await deletePipeline(id); setPipelines((prev) => prev.filter((p) => p.id !== id)); }, []);

  return (
    <div className="flex flex-col h-screen">
      <div className="border-b border-slate-200 px-6 py-4 flex-shrink-0 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold flex items-center gap-2 text-slate-900">
            <LayoutDashboard className="w-5 h-5 text-[#0000FF]" />
            Dashboard
          </h1>
          <p className="text-sm text-slate-400">{pipelines.length} pipeline{pipelines.length !== 1 ? "s" : ""}</p>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-6 bg-slate-50/50">
        {loading ? (
          <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>
        ) : pipelines.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <LayoutDashboard className="w-12 h-12 text-slate-200 mb-4" />
            <h2 className="text-lg font-semibold text-slate-500 mb-1">No pipelines yet</h2>
            <p className="text-sm text-slate-400">Create a pipeline in Chat to see it here.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            <AnimatePresence>
              {pipelines.map((pipeline) => (
                <PipelineCard key={pipeline.id} pipeline={pipeline} nextRun={scheduleMap.get(pipeline.id) ?? null}
                  blocksLoaded={blocksLoaded} onRun={handleRun} onDelete={handleDelete} />
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </div>
  );
}
