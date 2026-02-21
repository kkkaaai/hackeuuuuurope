"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { CATEGORY_COLORS, CATEGORY_ICONS } from "@/lib/constants";

function BlockNodeComponent({ data }: NodeProps) {
  const { label, category, status, blockId } = data;
  const color = CATEGORY_COLORS[category] || "#6b7280";
  const Icon = CATEGORY_ICONS[category];

  const statusIcon =
    status === "running" ? (
      <div className="p-0.5 rounded-full bg-blue-500/10">
        <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
      </div>
    ) : status === "completed" ? (
      <div className="p-0.5 rounded-full bg-green-500/10">
        <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
      </div>
    ) : status === "failed" ? (
      <div className="p-0.5 rounded-full bg-red-500/10">
        <XCircle className="w-3.5 h-3.5 text-red-400" />
      </div>
    ) : null;

  return (
    <div
      className={`group px-4 py-3.5 rounded-xl bg-gray-800/60 backdrop-blur-sm border border-white/[0.06] min-w-[230px] transition-all duration-300 hover:scale-[1.02] hover:border-white/10 ${
        status === "running" ? "node-running" : ""
      }`}
      style={{
        borderTopColor: color,
        borderTopWidth: "2px",
        boxShadow: `0 4px 24px rgba(0,0,0,0.3), 0 0 0 1px rgba(255,255,255,0.03)`,
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-500 !w-2 !h-2 !border-0" />
      <div className="flex items-center gap-2.5">
        {Icon && <Icon className="w-4 h-4 flex-shrink-0" style={{ color }} />}
        <span className="text-[13px] font-medium text-gray-100 truncate">{label}</span>
        <span className="ml-auto flex-shrink-0">{statusIcon}</span>
      </div>
      <div className="text-[11px] text-gray-500 mt-1 font-mono">{blockId}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-gray-500 !w-2 !h-2 !border-0" />
    </div>
  );
}

export const BlockNode = memo(BlockNodeComponent);
