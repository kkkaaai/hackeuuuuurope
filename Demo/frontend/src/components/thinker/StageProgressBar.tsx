"use client";

import { motion } from "framer-motion";
import { Puzzle, Search, Hammer, GitBranch, Check } from "lucide-react";
import type { ThinkerStage } from "@/lib/types";

const STAGES: { key: ThinkerStage; label: string; icon: typeof Puzzle }[] = [
  { key: "decompose", label: "1. Decompose", icon: Puzzle },
  { key: "search", label: "2. Search", icon: Search },
  { key: "create", label: "3. Create", icon: Hammer },
  { key: "wire", label: "4. Wire", icon: GitBranch },
];

interface StageProgressBarProps {
  currentStage: ThinkerStage | null;
  completedStages: Set<string>;
}

export function StageProgressBar({ currentStage, completedStages }: StageProgressBarProps) {
  return (
    <div className="flex items-center gap-0.5 py-2 px-4">
      {STAGES.map((stage, i) => {
        const isActive = currentStage === stage.key;
        const isCompleted = completedStages.has(stage.key);
        const Icon = stage.icon;

        return (
          <div key={stage.key} className="flex items-center">
            {/* Stage dot + label */}
            <div className="flex items-center gap-1.5">
              <motion.div
                className={`relative w-6 h-6 rounded-full flex items-center justify-center transition-all duration-300 ${
                  isCompleted
                    ? "bg-green-500/20 text-green-400"
                    : isActive
                    ? "bg-blue-500/20 text-blue-400"
                    : "bg-white/5 text-gray-600"
                }`}
                animate={isActive ? { scale: [1, 1.1, 1] } : {}}
                transition={isActive ? { repeat: Infinity, duration: 2 } : {}}
              >
                {isCompleted ? (
                  <Check className="w-3 h-3" />
                ) : (
                  <Icon className="w-3 h-3" />
                )}
                {isActive && (
                  <motion.div
                    className="absolute inset-0 rounded-full border border-blue-400/50"
                    animate={{ opacity: [0.5, 0, 0.5], scale: [1, 1.4, 1] }}
                    transition={{ repeat: Infinity, duration: 2 }}
                  />
                )}
              </motion.div>
              {(isActive || isCompleted) && (
                <motion.span
                  initial={{ opacity: 0, width: 0 }}
                  animate={{ opacity: 1, width: "auto" }}
                  className={`text-[11px] font-medium whitespace-nowrap ${
                    isCompleted ? "text-green-400/70" : "text-blue-400/70"
                  }`}
                >
                  {stage.label}
                </motion.span>
              )}
            </div>

            {/* Connecting line */}
            {i < STAGES.length - 1 && (
              <div className="relative w-8 h-px mx-1.5">
                <div className="absolute inset-0 bg-white/10 rounded-full" />
                {isCompleted && (
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-r from-green-500/50 to-green-500/20 rounded-full"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: 1 }}
                    style={{ transformOrigin: "left" }}
                    transition={{ duration: 0.4 }}
                  />
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
