"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  Bell,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronRight,
  Clock,
  Loader2,
  RefreshCw,
  AlertTriangle,
  Info,
} from "lucide-react";
import {
  listExecutions,
  getExecution,
  listNotifications,
  markNotificationRead,
} from "@/lib/api";
import { PipelineResultDisplay } from "@/components/pipeline/PipelineResultDisplay";
import type {
  ExecutionRun,
  ExecutionDetail,
  ExecutionNodeLog,
  Notification,
} from "@/lib/types";

type Tab = "executions" | "notifications";

function buildSharedContext(
  nodes: ExecutionNodeLog[]
): Record<string, Record<string, unknown>> {
  const context: Record<string, Record<string, unknown>> = {};
  for (const node of nodes) {
    if (node.output_data) {
      context[node.node_id] = node.output_data;
    }
  }
  return context;
}

export default function ActivityPage() {
  const [tab, setTab] = useState<Tab>("executions");
  const [executions, setExecutions] = useState<ExecutionRun[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedRun, setExpandedRun] = useState<string | null>(null);
  const [runDetails, setRunDetails] = useState<Record<string, ExecutionDetail>>({});

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [execs, notifs] = await Promise.all([
        listExecutions(),
        listNotifications(),
      ]);
      setExecutions(execs);
      setNotifications(notifs);
    } catch {
      /* backend may not be running */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExpandRun = async (runId: string) => {
    if (expandedRun === runId) {
      setExpandedRun(null);
      return;
    }
    setExpandedRun(runId);
    if (!runDetails[runId]) {
      try {
        const detail = await getExecution(runId);
        setRunDetails((prev) => ({ ...prev, [runId]: detail }));
      } catch {
        /* ignore */
      }
    }
  };

  const handleMarkRead = async (id: number) => {
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read: true } : n))
      );
    } catch {
      /* ignore */
    }
  };

  const unreadCount = notifications.filter((n) => !n.read).length;

  const statusColors: Record<string, string> = {
    completed: "text-green-400",
    failed: "text-red-400",
    running: "text-blue-400",
  };

  const levelStyles: Record<string, { border: string; icon: typeof Info; color: string }> = {
    info: { border: "border-l-blue-500", icon: Info, color: "text-blue-400" },
    success: { border: "border-l-green-500", icon: CheckCircle, color: "text-green-400" },
    warning: { border: "border-l-yellow-500", icon: AlertTriangle, color: "text-yellow-400" },
    error: { border: "border-l-red-500", icon: XCircle, color: "text-red-400" },
  };

  const categoryLabels: Record<string, { label: string; bg: string }> = {
    notification: { label: "Notification", bg: "bg-blue-500/20 text-blue-400" },
    confirmation: { label: "Confirmation", bg: "bg-yellow-500/20 text-yellow-400" },
    summary_card: { label: "Summary", bg: "bg-purple-500/20 text-purple-400" },
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold">Activity</h1>
          <p className="text-sm text-gray-500">
            Execution history and notifications
          </p>
        </div>
        <button
          onClick={fetchData}
          className="p-2 text-gray-400 hover:text-gray-200 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-900 rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab("executions")}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-colors ${
            tab === "executions"
              ? "bg-gray-800 text-white"
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          <Activity className="w-4 h-4" />
          Executions
        </button>
        <button
          onClick={() => setTab("notifications")}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-colors ${
            tab === "notifications"
              ? "bg-gray-800 text-white"
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          <Bell className="w-4 h-4" />
          Notifications
          {unreadCount > 0 && (
            <span className="bg-blue-500 text-white text-xs px-1.5 py-0.5 rounded-full">
              {unreadCount}
            </span>
          )}
        </button>
      </div>

      {/* Loading state */}
      {loading && executions.length === 0 && notifications.length === 0 ? (
        <div className="flex items-center justify-center h-64 text-gray-500">
          <Loader2 className="w-5 h-5 animate-spin mr-2" />
          Loading activity...
        </div>
      ) : tab === "executions" ? (
        /* Executions tab */
        executions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-500">
            <Activity className="w-10 h-10 mb-3 opacity-50" />
            <p>No executions yet</p>
            <p className="text-xs mt-1">Run a pipeline to see results here</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {executions.map((run, i) => (
              <motion.div
                key={run.run_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
              >
                <button
                  onClick={() => handleExpandRun(run.run_id)}
                  className="w-full bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-gray-700 transition-colors text-left"
                >
                  <div className="flex items-center gap-3">
                    {run.status === "completed" ? (
                      <CheckCircle className="w-4 h-4 text-green-400 shrink-0" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400 shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-200 truncate">
                        {run.pipeline_intent}
                      </p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-xs ${statusColors[run.status] || "text-gray-400"}`}>
                          {run.status}
                        </span>
                        <span className="text-xs text-gray-600">
                          {run.node_count} nodes
                        </span>
                        <span className="text-xs text-gray-600 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {run.finished_at ? new Date(run.finished_at + "Z").toLocaleString() : "—"}
                        </span>
                      </div>
                    </div>
                    {expandedRun === run.run_id ? (
                      <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />
                    )}
                  </div>
                </button>

                {/* Expanded execution details */}
                {expandedRun === run.run_id && runDetails[run.run_id] && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    className="mt-1 ml-4 border-l-2 border-gray-800 pl-4 space-y-3"
                  >
                    {/* Formatted result summary */}
                    {Object.keys(buildSharedContext(runDetails[run.run_id].nodes)).length > 0 && (
                      <div className="bg-gray-950 border border-gray-800 rounded-lg p-4">
                        <PipelineResultDisplay
                          sharedContext={buildSharedContext(runDetails[run.run_id].nodes)}
                        />
                      </div>
                    )}

                    {/* Per-node details (collapsed by default) */}
                    <details className="text-xs">
                      <summary className="text-gray-500 cursor-pointer hover:text-gray-400">
                        Per-node execution details ({runDetails[run.run_id].nodes.length} nodes)
                      </summary>
                      <div className="mt-2 space-y-2">
                        {runDetails[run.run_id].nodes.map((node) => (
                          <div
                            key={node.id}
                            className="bg-gray-950 border border-gray-800 rounded-md p-3"
                          >
                            <div className="flex items-center gap-2 mb-1">
                              {node.status === "completed" ? (
                                <CheckCircle className="w-3 h-3 text-green-400" />
                              ) : (
                                <XCircle className="w-3 h-3 text-red-400" />
                              )}
                              <span className="text-xs font-mono text-gray-300">
                                {node.node_id}
                              </span>
                            </div>
                            {node.error && (
                              <p className="text-xs text-red-400 mt-1">{node.error}</p>
                            )}
                            {node.output_data && (
                              <details className="mt-2">
                                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">
                                  Raw output
                                </summary>
                                <pre className="text-xs text-gray-400 mt-1 bg-gray-900 rounded p-2 overflow-x-auto max-h-40 overflow-y-auto">
                                  {JSON.stringify(node.output_data, null, 2)}
                                </pre>
                              </details>
                            )}
                          </div>
                        ))}
                      </div>
                    </details>
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
        )
      ) : /* Notifications tab */
      notifications.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-gray-500">
          <Bell className="w-10 h-10 mb-3 opacity-50" />
          <p>No notifications yet</p>
          <p className="text-xs mt-1">
            Notifications from pipelines will appear here
          </p>
        </div>
      ) : (
        <div className="grid gap-3">
          {notifications.map((notif, i) => {
            const style = levelStyles[notif.level] || levelStyles.info;
            const LevelIcon = style.icon;
            const cat = categoryLabels[notif.category] || categoryLabels.notification;

            return (
              <motion.div
                key={notif.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                onClick={() => !notif.read && handleMarkRead(notif.id)}
                className={`bg-gray-900 border border-gray-800 rounded-lg p-4 border-l-4 ${style.border} ${
                  !notif.read ? "cursor-pointer hover:border-gray-700" : ""
                } transition-colors`}
              >
                <div className="flex items-start gap-3">
                  <LevelIcon className={`w-4 h-4 mt-0.5 shrink-0 ${style.color}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-200">
                        {notif.title}
                      </p>
                      {!notif.read && (
                        <span className="w-2 h-2 bg-blue-500 rounded-full shrink-0" />
                      )}
                    </div>
                    <p className="text-sm text-gray-400 mt-0.5">{notif.message}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${cat.bg}`}>
                        {cat.label}
                      </span>
                      <span className="text-xs text-gray-600 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {notif.created_at ? new Date(notif.created_at + "Z").toLocaleString() : "—"}
                      </span>
                    </div>

                    {notif.category === "summary_card" && notif.metadata?.card ? (
                      <div className="mt-3 bg-gray-950 border border-gray-800 rounded-md p-3">
                        {((notif.metadata.card as Record<string, unknown>).fields as Array<{ label: string; value: string }> | undefined)?.map(
                          (field, idx) => (
                            <div key={idx} className="flex justify-between text-xs py-1 border-b border-gray-800 last:border-0">
                              <span className="text-gray-500">{field.label}</span>
                              <span className="text-gray-300">{field.value}</span>
                            </div>
                          )
                        )}
                      </div>
                    ) : null}

                    {notif.category === "confirmation" && notif.metadata?.auto_confirmed ? (
                      <p className="text-xs text-yellow-500/70 mt-1">
                        Auto-confirmed (demo mode)
                      </p>
                    ) : null}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
