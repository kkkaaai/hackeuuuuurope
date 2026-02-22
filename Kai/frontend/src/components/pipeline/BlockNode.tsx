"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { CATEGORY_COLORS, CATEGORY_ICONS } from "@/lib/constants";

function BlockNodeComponent({ data }: NodeProps) {
  const { label, category, status, blockId } = data;
  const color = CATEGORY_COLORS[category] || "#6b7280";
  const Icon = CATEGORY_ICONS[category];

  return (
    <div
      className="px-5 py-4 rounded-xl bg-white border border-slate-200 min-w-[260px] transition-all duration-300"
      style={{
        borderLeftWidth: "3px",
        borderLeftColor: color,
        boxShadow:
          status === "running"
            ? `0 0 16px ${color}40, 0 0 6px ${color}30`
            : status === "completed"
              ? `0 0 12px ${color}20, 0 2px 8px rgba(0,0,0,0.06)`
              : `0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)`,
        animation: status === "running" ? "pulse-glow 1.5s ease-in-out infinite" : undefined,
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-300 !w-2.5 !h-2.5 !border-2 !border-white" />
      <div className="flex items-center gap-3">
        {Icon && (
          <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ backgroundColor: `${color}12` }}>
            <Icon className="w-4 h-4" style={{ color }} />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <span className="text-sm font-semibold text-slate-800 block truncate">{label}</span>
          <span className="text-xs text-slate-400 font-mono block mt-0.5">{blockId}</span>
        </div>
        <div className="flex-shrink-0">
          {status === "running" ? (
            <div className="w-7 h-7 rounded-full bg-[#0000FF]/10 flex items-center justify-center">
              <Loader2 className="w-4 h-4 animate-spin text-[#0000FF]" />
            </div>
          ) : status === "completed" ? (
            <div className="w-7 h-7 rounded-full bg-green-50 flex items-center justify-center">
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            </div>
          ) : status === "failed" ? (
            <div className="w-7 h-7 rounded-full bg-red-50 flex items-center justify-center">
              <XCircle className="w-4 h-4 text-red-500" />
            </div>
          ) : null}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-slate-300 !w-2.5 !h-2.5 !border-2 !border-white" />
    </div>
  );
}

export const BlockNode = memo(BlockNodeComponent);
