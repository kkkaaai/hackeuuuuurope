"use client";

import { useEffect, useRef, useState } from "react";
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
        <div className="flex items-center gap-2 text-blue-400 text-xs py-1">
          <Zap className="w-3.5 h-3.5" />
          <span>Pipeline creation started</span>
        </div>
      );

    case "stage":
      return (
        <div className="flex items-center gap-2 text-white text-sm font-medium pt-3 pb-1 border-t border-gray-800 first:border-0 first:pt-0">
          <Sparkles className="w-4 h-4 text-blue-400" />
          <span className="capitalize">{String(event.stage)} Stage</span>
        </div>
      );

    case "stage_result":
      return (
        <div className="flex items-center gap-2 text-green-400 text-xs py-1">
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
                className="overflow-hidden"
              >
                <pre className="mt-1 p-2 bg-gray-950 rounded text-[10px] text-gray-500 overflow-x-auto max-h-32 overflow-y-auto">
                  {event.system_prompt ? `[System]\n${String(event.system_prompt)}\n\n` : null}
                  {event.user_prompt ? `[User]\n${String(event.user_prompt)}` : null}
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
            {event.elapsed ? (
              <span className="text-gray-600 flex items-center gap-0.5">
                <Clock className="w-2.5 h-2.5" />
                {Number(event.elapsed).toFixed(1)}s
              </span>
            ) : null}
          </button>
          <AnimatePresence>
            {expanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <pre className="mt-1 p-2 bg-gray-950 rounded text-[10px] text-gray-500 overflow-x-auto max-h-48 overflow-y-auto">
                  {String(event.response || "")}
                </pre>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      );

    case "match_found":
      return (
        <div className="flex items-center gap-2 text-xs py-1">
          <Search className="w-3.5 h-3.5 text-green-400" />
          <span className="px-1.5 py-0.5 bg-green-500/10 text-green-400 border border-green-500/30 rounded text-[10px]">
            {String(event.block_name || event.block_id)}
          </span>
          <span className="text-gray-500">matched</span>
        </div>
      );

    case "match_missing":
      return (
        <div className="flex items-center gap-2 text-xs py-1">
          <AlertCircle className="w-3.5 h-3.5 text-orange-400" />
          <span className="px-1.5 py-0.5 bg-orange-500/10 text-orange-400 border border-orange-500/30 rounded text-[10px]">
            {String(event.suggested_id || "unknown")}
          </span>
          <span className="text-gray-500">needs creation</span>
        </div>
      );

    case "creating_block":
      return (
        <div className="flex items-center gap-2 text-xs py-1 text-gray-400">
          <Hammer className="w-3.5 h-3.5 text-purple-400 animate-pulse" />
          <span>Creating block...</span>
        </div>
      );

    case "block_created":
      return (
        <div className="flex items-center gap-2 text-xs py-1">
          <Hammer className="w-3.5 h-3.5 text-purple-400" />
          <span className="px-1.5 py-0.5 bg-purple-500/10 text-purple-400 border border-purple-500/30 rounded text-[10px]">
            {String(event.block_name || event.block_id)}
          </span>
          <span className="text-gray-500">created</span>
        </div>
      );

    case "validation":
      return (
        <div className="flex items-center gap-2 text-xs py-1">
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
        <div className="flex items-center gap-2 text-green-400 text-xs py-2 border-t border-gray-800 mt-1">
          <Check className="w-4 h-4" />
          <span className="font-medium">Pipeline created successfully</span>
        </div>
      );

    case "error":
      return (
        <div className="flex items-center gap-2 text-red-400 text-xs py-1">
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

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-600">
        <Brain className="w-8 h-8 mb-2 opacity-40" />
        <p className="text-sm">Waiting for Thinker...</p>
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto px-3 py-2 space-y-0.5">
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
  );
}
