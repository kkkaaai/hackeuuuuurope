"use client";

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Activity, Bell, CheckCircle, XCircle, ChevronDown, ChevronRight, Clock, Loader2, RefreshCw, AlertTriangle, Info } from "lucide-react";
import { listExecutions, getExecution, listNotifications, markNotificationRead } from "@/lib/api";
import { PipelineResultDisplay } from "@/components/pipeline/PipelineResultDisplay";
import type { ExecutionRun, ExecutionDetail, ExecutionNodeLog, Notification } from "@/lib/types";

type Tab = "executions" | "notifications";

function buildSharedContext(nodes: ExecutionNodeLog[]): Record<string, Record<string, unknown>> {
  const context: Record<string, Record<string, unknown>> = {};
  for (const node of nodes) { if (node.output_data) context[node.node_id] = node.output_data; }
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
    try { const [execs, notifs] = await Promise.all([listExecutions(), listNotifications()]); setExecutions(execs); setNotifications(notifs); }
    catch { /* backend may not be running */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleExpandRun = async (runId: string) => {
    if (expandedRun === runId) { setExpandedRun(null); return; }
    setExpandedRun(runId);
    if (!runDetails[runId]) { try { const detail = await getExecution(runId); setRunDetails((prev) => ({ ...prev, [runId]: detail })); } catch { /* ignore */ } }
  };

  const handleMarkRead = async (id: number) => {
    try { await markNotificationRead(id); setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n))); } catch { /* ignore */ }
  };

  const unreadCount = notifications.filter((n) => !n.read).length;
  const statusColors: Record<string, string> = { completed: "text-green-600", failed: "text-red-600", running: "text-[#0000FF]" };

  const levelStyles: Record<string, { border: string; icon: typeof Info; color: string }> = {
    info: { border: "border-l-[#0000FF]", icon: Info, color: "text-[#0000FF]" },
    success: { border: "border-l-green-500", icon: CheckCircle, color: "text-green-600" },
    warning: { border: "border-l-yellow-500", icon: AlertTriangle, color: "text-yellow-600" },
    error: { border: "border-l-red-500", icon: XCircle, color: "text-red-600" },
  };

  const categoryLabels: Record<string, { label: string; bg: string }> = {
    notification: { label: "Notification", bg: "bg-[#0000FF]/8 text-[#0000FF]" },
    confirmation: { label: "Confirmation", bg: "bg-yellow-50 text-yellow-700" },
    summary_card: { label: "Summary", bg: "bg-purple-50 text-purple-700" },
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">Activity</h1>
          <p className="text-sm text-slate-400">Execution history and notifications</p>
        </div>
        <button onClick={fetchData} className="p-2 text-slate-400 hover:text-slate-700 transition-colors">
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="flex gap-1 mb-6 bg-slate-100 rounded-lg p-1 w-fit">
        <button onClick={() => setTab("executions")}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-colors ${tab === "executions" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>
          <Activity className="w-4 h-4" /> Executions
        </button>
        <button onClick={() => setTab("notifications")}
          className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm transition-colors ${tab === "notifications" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}>
          <Bell className="w-4 h-4" /> Notifications
          {unreadCount > 0 && <span className="bg-[#0000FF] text-white text-xs px-1.5 py-0.5 rounded-full">{unreadCount}</span>}
        </button>
      </div>

      {loading && executions.length === 0 && notifications.length === 0 ? (
        <div className="flex items-center justify-center h-64 text-slate-400">
          <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading activity...
        </div>
      ) : tab === "executions" ? (
        executions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400">
            <Activity className="w-10 h-10 mb-3 opacity-50" /><p>No executions yet</p><p className="text-xs mt-1">Run a pipeline to see results here</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {executions.map((run, i) => (
              <motion.div key={run.run_id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}>
                <button onClick={() => handleExpandRun(run.run_id)}
                  className="w-full bg-white border border-slate-200 rounded-lg p-4 hover:border-[#0000FF]/30 hover:shadow-sm transition-all text-left">
                  <div className="flex items-center gap-3">
                    {run.status === "completed" ? <CheckCircle className="w-4 h-4 text-green-500 shrink-0" /> : <XCircle className="w-4 h-4 text-red-500 shrink-0" />}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-800 truncate">{run.pipeline_intent}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`text-xs ${statusColors[run.status] || "text-slate-400"}`}>{run.status}</span>
                        <span className="text-xs text-slate-400">{run.node_count} nodes</span>
                        <span className="text-xs text-slate-400 flex items-center gap-1">
                          <Clock className="w-3 h-3" />{run.finished_at ? new Date(run.finished_at + "Z").toLocaleString() : "\u2014"}
                        </span>
                      </div>
                    </div>
                    {expandedRun === run.run_id ? <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" /> : <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />}
                  </div>
                </button>
                {expandedRun === run.run_id && runDetails[run.run_id] && (
                  <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} className="mt-1 ml-4 border-l-2 border-slate-200 pl-4 space-y-3">
                    {Object.keys(buildSharedContext(runDetails[run.run_id].nodes)).length > 0 && (
                      <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
                        <PipelineResultDisplay sharedContext={buildSharedContext(runDetails[run.run_id].nodes)} />
                      </div>
                    )}
                    <details className="text-xs">
                      <summary className="text-slate-400 cursor-pointer hover:text-slate-600">Per-node execution details ({runDetails[run.run_id].nodes.length} nodes)</summary>
                      <div className="mt-2 space-y-2">
                        {runDetails[run.run_id].nodes.map((node) => (
                          <div key={node.id} className="bg-slate-50 border border-slate-200 rounded-md p-3">
                            <div className="flex items-center gap-2 mb-1">
                              {node.status === "completed" ? <CheckCircle className="w-3 h-3 text-green-500" /> : <XCircle className="w-3 h-3 text-red-500" />}
                              <span className="text-xs font-mono text-slate-700">{node.node_id}</span>
                            </div>
                            {node.error && <p className="text-xs text-red-600 mt-1">{node.error}</p>}
                            {node.output_data && (
                              <details className="mt-2">
                                <summary className="text-xs text-slate-400 cursor-pointer hover:text-slate-600">Raw output</summary>
                                <pre className="text-xs text-slate-600 mt-1 bg-white rounded p-2 overflow-x-auto max-h-40 overflow-y-auto border border-slate-100">{JSON.stringify(node.output_data, null, 2)}</pre>
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
      ) : notifications.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-slate-400">
          <Bell className="w-10 h-10 mb-3 opacity-50" /><p>No notifications yet</p><p className="text-xs mt-1">Notifications from pipelines will appear here</p>
        </div>
      ) : (
        <div className="grid gap-3">
          {notifications.map((notif, i) => {
            const style = levelStyles[notif.level] || levelStyles.info;
            const LevelIcon = style.icon;
            const cat = categoryLabels[notif.category] || categoryLabels.notification;
            return (
              <motion.div key={notif.id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
                onClick={() => !notif.read && handleMarkRead(notif.id)}
                className={`bg-white border border-slate-200 rounded-lg p-4 border-l-4 ${style.border} ${!notif.read ? "cursor-pointer hover:shadow-sm" : ""} transition-all`}>
                <div className="flex items-start gap-3">
                  <LevelIcon className={`w-4 h-4 mt-0.5 shrink-0 ${style.color}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-slate-800">{notif.title}</p>
                      {!notif.read && <span className="w-2 h-2 bg-[#0000FF] rounded-full shrink-0" />}
                    </div>
                    <p className="text-sm text-slate-500 mt-0.5">{notif.message}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${cat.bg}`}>{cat.label}</span>
                      <span className="text-xs text-slate-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />{notif.created_at ? new Date(notif.created_at + "Z").toLocaleString() : "\u2014"}
                      </span>
                    </div>
                    {notif.category === "summary_card" && notif.metadata?.card ? (
                      <div className="mt-3 bg-slate-50 border border-slate-200 rounded-md p-3">
                        {((notif.metadata.card as Record<string, unknown>).fields as Array<{ label: string; value: string }> | undefined)?.map((field, idx) => (
                          <div key={idx} className="flex justify-between text-xs py-1 border-b border-slate-100 last:border-0">
                            <span className="text-slate-400">{field.label}</span>
                            <span className="text-slate-700">{field.value}</span>
                          </div>
                        ))}
                      </div>
                    ) : null}
                    {notif.category === "confirmation" && notif.metadata?.auto_confirmed ? (
                      <p className="text-xs text-yellow-600 mt-1">Auto-confirmed (demo mode)</p>
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
