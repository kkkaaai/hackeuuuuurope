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
      <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
    ) : status === "completed" ? (
      <CheckCircle2 className="w-4 h-4 text-green-400" />
    ) : status === "failed" ? (
      <XCircle className="w-4 h-4 text-red-400" />
    ) : null;

  return (
    <div
      className={`px-4 py-3 rounded-lg bg-gray-800 border border-gray-700 shadow-lg min-w-[220px] transition-all duration-300 border-l-4 ${
        status === "running" ? "node-running" : ""
      }`}
      style={{ borderLeftColor: color }}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-500 !w-2 !h-2" />
      <div className="flex items-center gap-2">
        {Icon && <Icon className="w-4 h-4 flex-shrink-0" style={{ color }} />}
        <span className="text-sm font-medium text-gray-100 truncate">{label}</span>
        <span className="ml-auto flex-shrink-0">{statusIcon}</span>
      </div>
      <div className="text-xs text-gray-500 mt-1 font-mono">{blockId}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-gray-500 !w-2 !h-2" />
    </div>
  );
}

export const BlockNode = memo(BlockNodeComponent);
