"use client";

import { motion } from "framer-motion";
import { Puzzle, Search, Hammer, GitBranch, Check } from "lucide-react";
import type { ThinkerStage } from "@/lib/types";

const STAGES: { key: ThinkerStage; label: string; icon: typeof Puzzle }[] = [
  { key: "decompose", label: "Decompose", icon: Puzzle },
  { key: "match", label: "Match", icon: Search },
  { key: "create", label: "Create", icon: Hammer },
  { key: "wire", label: "Wire", icon: GitBranch },
];

interface StageProgressBarProps {
  currentStage: ThinkerStage | null;
  completedStages: Set<string>;
}

export function StageProgressBar({ currentStage, completedStages }: StageProgressBarProps) {
  return (
    <div className="flex items-center justify-center gap-1 py-3 px-4">
      {STAGES.map((stage, i) => {
        const isActive = currentStage === stage.key;
        const isCompleted = completedStages.has(stage.key);
        const Icon = stage.icon;

        return (
          <div key={stage.key} className="flex items-center">
            {/* Stage dot */}
            <div className="flex flex-col items-center gap-1">
              <motion.div
                className={`relative w-9 h-9 rounded-full flex items-center justify-center border-2 transition-colors ${
                  isCompleted
                    ? "bg-green-500/20 border-green-500 text-green-400"
                    : isActive
                    ? "bg-blue-500/20 border-blue-500 text-blue-400"
                    : "bg-gray-800 border-gray-700 text-gray-600"
                }`}
                animate={isActive ? { scale: [1, 1.1, 1] } : {}}
                transition={isActive ? { repeat: Infinity, duration: 1.5 } : {}}
              >
                {isCompleted ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Icon className="w-4 h-4" />
                )}
                {isActive && (
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-blue-400"
                    animate={{ opacity: [0.5, 0, 0.5], scale: [1, 1.3, 1] }}
                    transition={{ repeat: Infinity, duration: 1.5 }}
                  />
                )}
              </motion.div>
              <span
                className={`text-[10px] font-medium ${
                  isCompleted
                    ? "text-green-400"
                    : isActive
                    ? "text-blue-400"
                    : "text-gray-600"
                }`}
              >
                {stage.label}
              </span>
            </div>

            {/* Connecting line */}
            {i < STAGES.length - 1 && (
              <div
                className={`w-8 h-0.5 mx-1 mt-[-16px] transition-colors ${
                  isCompleted ? "bg-green-500/50" : "bg-gray-700"
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
