"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  ChevronDown,
  ChevronRight,
  Check,
  X,
  Sparkles,
  Search,
  Hammer,
  MessageSquare,
  Zap,
  Clock,
  AlertCircle,
  ArrowDown,
} from "lucide-react";
import type { SSEEvent } from "@/lib/types";

interface ThinkerLogProps {
  events: SSEEvent[];
}

function EventItem({ event }: { event: SSEEvent }) {
  const [expanded, setExpanded] = useState(false);

  switch (event.type) {
    case "start":
      return (
        <div className="flex items-center gap-2 text-blue-400 text-xs py-1.5">
          <Zap className="w-3.5 h-3.5" />
          <span>Pipeline creation started</span>
        </div>
      );

    case "stage": {
      const stageNumbers: Record<string, number> = { decompose: 1, match: 2, create: 3, wire: 4 };
      const num = stageNumbers[String(event.stage)] ?? "";
      return (
        <div className="flex items-center gap-2 text-white text-sm font-medium pt-4 pb-1.5">
          <div className="w-0.5 h-4 rounded-full bg-blue-400/60 mr-0.5" />
          <Sparkles className="w-3.5 h-3.5 text-blue-400" />
          <span className="capitalize">{num ? `${num}. ` : ""}{String(event.stage)} Stage</span>
        </div>
      );
    }

    case "stage_result":
      return (
        <div className="flex items-center gap-2 text-green-400 text-xs py-1.5">
          <Check className="w-3.5 h-3.5" />
          <span>{String(event.summary || `${event.stage} complete`)}</span>
        </div>
      );

    case "llm_prompt":
      return (
        <div className="py-1">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-2 text-gray-400 text-xs hover:text-gray-300 transition-colors"
          >
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            <MessageSquare className="w-3.5 h-3.5 text-purple-400" />
            <span>LLM Prompt</span>
          </button>
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <pre className="mt-1.5 p-2.5 bg-black/30 rounded-lg text-[10px] text-gray-500 overflow-x-auto max-h-32 overflow-y-auto thin-scrollbar border border-white/5">
                  {(event.system || event.system_prompt) ? `[System]\n${String(event.system || event.system_prompt)}\n\n` : null}
                  {(event.user || event.user_prompt) ? `[User]\n${String(event.user || event.user_prompt)}` : null}
                </pre>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      );

    case "llm_response":
      return (
        <div className="py-1">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-2 text-gray-400 text-xs hover:text-gray-300 transition-colors"
          >
            {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            <Brain className="w-3.5 h-3.5 text-cyan-400" />
            <span>LLM Response</span>
            {(event.elapsed_s || event.elapsed) ? (
              <span className="text-gray-600 flex items-center gap-0.5">
                <Clock className="w-2.5 h-2.5" />
                {Number(event.elapsed_s || event.elapsed).toFixed(1)}s
              </span>
            ) : null}
          </button>
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <pre className="mt-1.5 p-2.5 bg-black/30 rounded-lg text-[10px] text-gray-500 overflow-x-auto max-h-48 overflow-y-auto thin-scrollbar border border-white/5">
                  {String(event.raw || event.response || "")}
                </pre>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      );

    case "match_found":
      return (
        <div className="py-1.5">
          <div className="flex items-center gap-2 text-xs">
            <Search className="w-3.5 h-3.5 text-green-400 flex-shrink-0" />
            <span className="px-1.5 py-0.5 bg-green-500/10 text-green-400 border border-green-500/20 rounded text-[10px] font-mono">
              {String(event.name || event.block_id)}
            </span>
            <span className="text-green-500/60">found in registry</span>
          </div>
          {typeof event.description === "string" && event.description && (
            <p className="ml-6 mt-0.5 text-[10px] text-gray-600 leading-tight">{event.description}</p>
          )}
        </div>
      );

    case "match_missing":
      return (
        <div className="py-1.5">
          <div className="flex items-center gap-2 text-xs">
            <AlertCircle className="w-3.5 h-3.5 text-orange-400 flex-shrink-0" />
            <span className="px-1.5 py-0.5 bg-orange-500/10 text-orange-400 border border-orange-500/20 rounded text-[10px] font-mono">
              {String(event.suggested_id || event.block_id || "unknown")}
            </span>
            <span className="text-orange-400/60">will be created</span>
          </div>
          {typeof event.description === "string" && event.description && (
            <p className="ml-6 mt-0.5 text-[10px] text-gray-600 leading-tight">{event.description}</p>
          )}
        </div>
      );

    case "creating_block":
      return (
        <div className="py-1.5">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <Hammer className="w-3.5 h-3.5 text-purple-400 animate-pulse flex-shrink-0" />
            <span>Creating</span>
            <span className="font-mono text-purple-300">{String(event.suggested_id || "block")}</span>
            {typeof event.total === "number" && event.total > 1 && (
              <span className="text-gray-600">({Number(event.index) + 1}/{event.total})</span>
            )}
          </div>
          {typeof event.description === "string" && event.description && (
            <p className="ml-6 mt-0.5 text-[10px] text-gray-600 leading-tight">{event.description}</p>
          )}
        </div>
      );

    case "block_created":
      return (
        <div className="py-1.5">
          <div className="flex items-center gap-2 text-xs">
            <Hammer className="w-3.5 h-3.5 text-purple-400 flex-shrink-0" />
            <span className="px-1.5 py-0.5 bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded text-[10px] font-mono">
              {String(event.name || event.block_id)}
            </span>
            <span className="text-purple-400/60">created</span>
            {typeof event.execution_type === "string" && (
              <span className="text-[10px] text-gray-600">({event.execution_type})</span>
            )}
          </div>
          {typeof event.description === "string" && event.description && (
            <p className="ml-6 mt-0.5 text-[10px] text-gray-600 leading-tight">{event.description}</p>
          )}
        </div>
      );

    case "validation":
      return (
        <div className="flex items-center gap-2 text-xs py-1.5">
          {event.valid ? (
            <>
              <Check className="w-3.5 h-3.5 text-green-400" />
              <span className="text-green-400">Validation passed</span>
            </>
          ) : (
            <>
              <X className="w-3.5 h-3.5 text-red-400" />
              <span className="text-red-400">Validation failed: {String(event.error || "")}</span>
            </>
          )}
        </div>
      );

    case "complete":
      return (
        <div className="flex items-center gap-2 text-green-400 text-xs py-2.5 mt-2">
          <div className="w-0.5 h-4 rounded-full bg-green-400/60 mr-0.5" />
          <Check className="w-4 h-4" />
          <span className="font-medium">Pipeline created successfully</span>
        </div>
      );

    case "error":
      return (
        <div className="flex items-center gap-2 text-red-400 text-xs py-1.5">
          <X className="w-3.5 h-3.5" />
          <span>{String(event.message || event.error || "Error occurred")}</span>
        </div>
      );

    default:
      return (
        <div className="text-[10px] text-gray-600 py-0.5">
          {event.type}: {JSON.stringify(event).slice(0, 100)}
        </div>
      );
  }
}

export function ThinkerLog({ events }: ThinkerLogProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;
    const el = scrollRef.current;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setIsAtBottom(atBottom);
  }, []);

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    }
  }, []);

  useEffect(() => {
    if (isAtBottom && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, isAtBottom]);

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-600">
        <Brain className="w-8 h-8 mb-2 opacity-30" />
        <p className="text-sm text-gray-600">Waiting for Thinker...</p>
      </div>
    );
  }

  return (
    <div className="relative h-full">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto px-4 py-3 space-y-0.5 thin-scrollbar"
      >
        <AnimatePresence>
          {events.map((event, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.15 }}
            >
              <EventItem event={event} />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Scroll to bottom button */}
      <AnimatePresence>
        {!isAtBottom && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={scrollToBottom}
            className="absolute bottom-3 right-3 p-1.5 rounded-full bg-gray-800/80 backdrop-blur-sm border border-white/10 text-gray-400 hover:text-white hover:bg-gray-700/80 transition-colors shadow-lg"
          >
            <ArrowDown className="w-3.5 h-3.5" />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}
