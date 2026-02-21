"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  listPipelines,
  deletePipeline,
  runPipeline,
} from "@/lib/api";
import type { PipelineListItem, ExecutionResult } from "@/lib/types";

interface DashboardState {
  pipelines: PipelineListItem[];
  loading: boolean;
  runningId: string | null;
  lastResult: ExecutionResult | null;
  runError: string | null;
  lastRunPipelineId: string | null;
  chatDraft: string;
  setChatDraft: (v: string) => void;
  fetchPipelines: () => Promise<void>;
  handleRun: (id: string) => Promise<void>;
  handleDelete: (id: string) => Promise<void>;
}

const DashboardContext = createContext<DashboardState | null>(null);

export function useDashboard(): DashboardState {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboard must be used within DashboardProvider");
  return ctx;
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const [pipelines, setPipelines] = useState<PipelineListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<ExecutionResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [lastRunPipelineId, setLastRunPipelineId] = useState<string | null>(null);
  const [chatDraft, setChatDraft] = useState("");

  const fetchPipelines = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listPipelines();
      setPipelines(data);
    } catch {
      /* backend may not be running */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPipelines();
  }, [fetchPipelines]);

  const handleRun = useCallback(async (id: string) => {
    setRunningId(id);
    setLastResult(null);
    setRunError(null);
    setLastRunPipelineId(id);
    try {
      const result = await runPipeline(id);
      setLastResult(result);
      fetchPipelines();
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Pipeline execution failed");
    } finally {
      setRunningId(null);
    }
  }, [fetchPipelines]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await deletePipeline(id);
      setPipelines((prev) => prev.filter((p) => p.id !== id));
    } catch {
      /* ignore */
    }
  }, []);

  return (
    <DashboardContext.Provider
      value={{
        pipelines,
        loading,
        runningId,
        lastResult,
        runError,
        lastRunPipelineId,
        chatDraft,
        setChatDraft,
        fetchPipelines,
        handleRun,
        handleDelete,
      }}
    >
      {children}
    </DashboardContext.Provider>
  );
}
