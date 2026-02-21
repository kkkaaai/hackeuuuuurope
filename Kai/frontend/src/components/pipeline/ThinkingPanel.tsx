"use client";

import { useState, useEffect, useRef, Fragment } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Check,
  ChevronDown,
  ChevronRight,
  Loader2,
  Sparkles,
  Search,
  Monitor,
  Cable,
} from "lucide-react";
import { getBlockMeta } from "@/lib/utils";
import { CATEGORY_COLORS, CATEGORY_BG, CATEGORY_ICONS } from "@/lib/constants";
import type { ChatResponse } from "@/lib/types";

const STAGES = ["decompose", "match", "create", "wire"] as const;
type Stage = (typeof STAGES)[number];

const STAGE_LABELS: Record<Stage, string> = {
  decompose: "Decompose",
  match: "Match",
  create: "Create",
  wire: "Wire",
};

const STAGE_ICONS: Record<Stage, typeof Sparkles> = {
  decompose: Sparkles,
  match: Search,
  create: Monitor,
  wire: Cable,
};

interface LogEntry {
  id: string;
  type: "status" | "stage-header" | "expandable" | "block-card" | "completion";
  stage: Stage;
  content: string;
  detail?: string;
  timing?: string;
  blockId?: string;
  blockCategory?: string;
  blockDescription?: string;
  found?: boolean;
}

interface ThinkingPanelProps {
  pipeline: ChatResponse;
  isActive: boolean;
}

export function ThinkingPanel({ pipeline, isActive }: ThinkingPanelProps) {
  const [currentStage, setCurrentStage] = useState<Stage | null>(null);
  const [completedStages, setCompletedStages] = useState<Stage[]>([]);
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logEntries]);

  // Animation sequence
  useEffect(() => {
    if (!isActive || !pipeline) return;

    const timers: ReturnType<typeof setTimeout>[] = [];
    const addEntry = (entry: LogEntry, delay: number) => {
      timers.push(
        setTimeout(() => {
          setLogEntries((prev) => [...prev, entry]);
        }, delay)
      );
    };

    const setStage = (stage: Stage, delay: number) => {
      timers.push(setTimeout(() => setCurrentStage(stage), delay));
    };

    const completeStage = (stage: Stage, delay: number) => {
      timers.push(
        setTimeout(() => setCompletedStages((prev) => [...prev, stage]), delay)
      );
    };

    let t = 0;

    // --- Stage 1: Decompose ---
    setStage("decompose", t);
    addEntry(
      { id: "start", type: "status", stage: "decompose", content: "Pipeline creation started" },
      t
    );
    t += 300;

    addEntry(
      { id: "decompose-header", type: "stage-header", stage: "decompose", content: "1. Decompose Stage" },
      t
    );
    t += 200;

    addEntry(
      {
        id: "llm-prompt",
        type: "expandable",
        stage: "decompose",
        content: "LLM Prompt",
        detail: pipeline.user_intent,
      },
      t
    );
    t += 400;

    const responseTime = (1.5 + Math.random() * 2).toFixed(1);
    addEntry(
      {
        id: "llm-response",
        type: "expandable",
        stage: "decompose",
        content: "LLM Response",
        detail: `Identified ${pipeline.nodes.length} blocks, trigger: ${pipeline.trigger_type}`,
        timing: `${responseTime}s`,
      },
      t
    );
    t += 400;

    addEntry(
      { id: "decompose-done", type: "completion", stage: "decompose", content: "decompose complete" },
      t
    );
    t += 200;

    addEntry(
      { id: "validation", type: "completion", stage: "decompose", content: "Validation passed" },
      t
    );
    completeStage("decompose", t);
    t += 300;

    // --- Stage 2: Match ---
    setStage("match", t);
    addEntry(
      { id: "match-header", type: "stage-header", stage: "match", content: "2. Match Stage" },
      t
    );
    t += 200;

    const missingBlockIds = new Set(
      (pipeline.missing_blocks || []).map((b: unknown) => {
        const block = b as Record<string, string>;
        return block.block_id || block.id || "";
      })
    );

    for (let i = 0; i < pipeline.nodes.length; i++) {
      const node = pipeline.nodes[i];
      const meta = getBlockMeta(node.block_id);
      const found = !missingBlockIds.has(node.block_id);

      addEntry(
        {
          id: `block-${i}`,
          type: "block-card",
          stage: "match",
          content: meta.name,
          blockId: node.block_id,
          blockCategory: meta.category,
          blockDescription: meta.description,
          found,
        },
        t
      );
      t += 300;
    }

    addEntry(
      { id: "match-done", type: "completion", stage: "match", content: "match complete" },
      t
    );
    completeStage("match", t);
    t += 300;

    // --- Stage 3: Create ---
    setStage("create", t);
    addEntry(
      { id: "create-header", type: "stage-header", stage: "create", content: "3. Create Stage" },
      t
    );
    t += 200;

    if (pipeline.missing_blocks && pipeline.missing_blocks.length > 0) {
      addEntry(
        {
          id: "creating",
          type: "status",
          stage: "create",
          content: `Builder creating ${pipeline.missing_blocks.length} missing block(s)...`,
        },
        t
      );
      t += 600;
    }

    addEntry(
      { id: "create-done", type: "completion", stage: "create", content: "create complete" },
      t
    );
    completeStage("create", t);
    t += 300;

    // --- Stage 4: Wire ---
    setStage("wire", t);
    addEntry(
      { id: "wire-header", type: "stage-header", stage: "wire", content: "4. Wire Stage" },
      t
    );
    t += 200;

    addEntry(
      {
        id: "wiring",
        type: "status",
        stage: "wire",
        content: `Connecting ${pipeline.edges.length} edges between ${pipeline.nodes.length} blocks`,
      },
      t
    );
    t += 600;

    addEntry(
      { id: "wire-done", type: "completion", stage: "wire", content: "Pipeline wired successfully" },
      t
    );
    completeStage("wire", t);

    timers.push(setTimeout(() => setCurrentStage(null), t + 200));

    return () => timers.forEach(clearTimeout);
  }, [isActive, pipeline]);

  return (
    <div className="flex flex-col h-full bg-gray-950/50">
      {/* Progress bar */}
      <div className="flex items-center gap-0 px-4 py-3 border-b border-gray-800 flex-shrink-0">
        {STAGES.map((stage, i) => {
          const isComplete = completedStages.includes(stage);
          const isActiveStage = currentStage === stage;
          const StageIcon = STAGE_ICONS[stage];
          return (
            <Fragment key={stage}>
              {i > 0 && (
                <div
                  className={`flex-1 h-px mx-2 transition-colors duration-300 ${
                    completedStages.includes(STAGES[i - 1])
                      ? "bg-green-500"
                      : "bg-gray-700"
                  }`}
                />
              )}
              <div className="flex items-center gap-1.5">
                {isComplete ? (
                  <Check className="w-3.5 h-3.5 text-green-400" />
                ) : isActiveStage ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
                ) : (
                  <div className="w-3.5 h-3.5 rounded-full border border-gray-600" />
                )}
                <span
                  className={`text-xs font-medium ${
                    isComplete
                      ? "text-green-400"
                      : isActiveStage
                        ? "text-blue-400"
                        : "text-gray-500"
                  }`}
                >
                  {i + 1}. {STAGE_LABELS[stage]}
                </span>
              </div>
            </Fragment>
          );
        })}
      </div>

      {/* AI Thinking header */}
      <div className="px-4 py-2 border-b border-gray-800/50 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs font-medium text-gray-400">AI Thinking</span>
        </div>
      </div>

      {/* Log entries */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-2 thinking-scroll">
        <AnimatePresence>
          {logEntries.map((entry) => (
            <motion.div
              key={entry.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25 }}
            >
              <LogEntryRenderer entry={entry} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

function LogEntryRenderer({ entry }: { entry: LogEntry }) {
  const StageIcon = STAGE_ICONS[entry.stage] || Sparkles;

  switch (entry.type) {
    case "status":
      return (
        <div className="flex items-center gap-2 text-xs text-gray-400 py-0.5">
          <StageIcon className="w-3.5 h-3.5 text-blue-400 flex-shrink-0" />
          <span>{entry.content}</span>
        </div>
      );

    case "stage-header":
      return (
        <div className="flex items-center gap-2 pt-2 pb-1">
          <div className="w-0.5 h-4 bg-blue-500 rounded-full" />
          <StageIcon className="w-3.5 h-3.5 text-blue-400" />
          <span className="text-sm font-semibold text-gray-200">{entry.content}</span>
        </div>
      );

    case "expandable":
      return <ExpandableLogItem entry={entry} />;

    case "block-card":
      return <BlockMatchCard entry={entry} />;

    case "completion":
      return (
        <div className="flex items-center gap-2 text-xs py-0.5">
          <Check className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
          <span className="text-green-400">{entry.content}</span>
        </div>
      );

    default:
      return null;
  }
}

function ExpandableLogItem({ entry }: { entry: LogEntry }) {
  const [open, setOpen] = useState(false);
  const StageIcon = STAGE_ICONS[entry.stage] || Sparkles;

  return (
    <div className="border-l-2 border-gray-700 pl-3 ml-2">
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-200 transition-colors w-full"
      >
        {open ? (
          <ChevronDown className="w-3 h-3 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3 h-3 flex-shrink-0" />
        )}
        <StageIcon className="w-3 h-3 flex-shrink-0" />
        <span>{entry.content}</span>
        {entry.timing && (
          <span className="text-gray-600 ml-auto flex-shrink-0">
            {entry.timing}
          </span>
        )}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <pre className="text-[11px] text-gray-500 mt-1 whitespace-pre-wrap font-mono bg-gray-900/50 rounded p-2 max-h-32 overflow-y-auto">
              {entry.detail}
            </pre>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function BlockMatchCard({ entry }: { entry: LogEntry }) {
  const category = entry.blockCategory || "control";
  const color = CATEGORY_COLORS[category] || "#6b7280";
  const Icon = CATEGORY_ICONS[category];
  const found = entry.found !== false;

  return (
    <div className="flex items-start gap-3 px-3 py-2 rounded-lg bg-gray-900/50 border border-gray-800 ml-4">
      <Search className="w-3.5 h-3.5 text-blue-400 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <code
            className="text-[11px] px-1.5 py-0.5 rounded font-mono border"
            style={{
              color,
              backgroundColor: `${color}10`,
              borderColor: `${color}30`,
            }}
          >
            {entry.content}
          </code>
          <span
            className={`text-[10px] ${
              found ? "text-green-400" : "text-orange-400"
            }`}
          >
            {found ? "found in registry" : "needs creation"}
          </span>
        </div>
        {entry.blockDescription && (
          <p className="text-xs text-gray-400 mt-1 leading-relaxed line-clamp-2">
            {entry.blockDescription}
          </p>
        )}
      </div>
    </div>
  );
}
