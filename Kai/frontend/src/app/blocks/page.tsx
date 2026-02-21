"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, X, Loader2, ChevronDown, ChevronUp } from "lucide-react";
import { listBlocks, searchBlocks } from "@/lib/api";
import {
  CATEGORY_COLORS,
  CATEGORY_BG,
  CATEGORY_ICONS,
  CATEGORY_LABELS,
  ALL_CATEGORIES,
} from "@/lib/constants";
import type { BlockDefinition, BlockCategory } from "@/lib/types";

export default function BlocksPage() {
  const [blocks, setBlocks] = useState<BlockDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedBlock, setExpandedBlock] = useState<string | null>(null);

  const fetchBlocks = useCallback(async (category?: string) => {
    setLoading(true);
    try {
      const data = await listBlocks(category || undefined);
      setBlocks(data);
    } catch {
      /* backend may not be running */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBlocks(selectedCategory || undefined);
  }, [selectedCategory, fetchBlocks]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchBlocks(selectedCategory || undefined);
      return;
    }
    setLoading(true);
    try {
      const data = await searchBlocks(searchQuery);
      setBlocks(data);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  };

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold">Block Library</h1>
        <p className="text-sm text-gray-500">
          {blocks.length} block{blocks.length !== 1 ? "s" : ""} available
        </p>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={handleSearchKeyDown}
          placeholder="Search blocks..."
          className="w-full pl-9 pr-8 py-2.5 bg-gray-900 border border-gray-700 rounded-lg text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        />
        {searchQuery && (
          <button
            onClick={() => { setSearchQuery(""); fetchBlocks(selectedCategory || undefined); }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setSelectedCategory(null)}
          className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
            !selectedCategory
              ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
              : "text-gray-400 border-gray-700 hover:border-gray-500"
          }`}
        >
          All
        </button>
        {ALL_CATEGORIES.map((cat) => {
          const Icon = CATEGORY_ICONS[cat];
          return (
            <button
              key={cat}
              onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
              className={`text-xs px-3 py-1.5 rounded-full border flex items-center gap-1.5 transition-colors ${
                selectedCategory === cat
                  ? CATEGORY_BG[cat]
                  : "text-gray-400 border-gray-700 hover:border-gray-500"
              }`}
            >
              <Icon className="w-3 h-3" />
              {CATEGORY_LABELS[cat]}
            </button>
          );
        })}
      </div>

      {/* Block grid */}
      {loading ? (
        <div className="flex items-center justify-center h-40 text-gray-500">
          <Loader2 className="w-5 h-5 animate-spin" />
        </div>
      ) : (
        <div className="grid gap-2">
          {blocks.map((block, i) => {
            const Icon = CATEGORY_ICONS[block.category];
            const color = CATEGORY_COLORS[block.category] || "#6b7280";
            const expanded = expandedBlock === block.id;

            return (
              <motion.div
                key={block.id}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.02 }}
                className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden hover:border-gray-700 transition-colors"
              >
                <button
                  onClick={() => setExpandedBlock(expanded ? null : block.id)}
                  className="w-full px-4 py-3 flex items-center gap-3 text-left"
                >
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ backgroundColor: `${color}15` }}
                  >
                    {Icon && <Icon className="w-4 h-4" style={{ color }} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-200">
                        {block.name}
                      </span>
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded border ${CATEGORY_BG[block.category]}`}
                      >
                        {block.category}
                      </span>
                      {block.tier === 1 && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/10 text-yellow-500 border border-yellow-500/30">
                          Tier 1
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5 truncate">
                      {block.description}
                    </p>
                  </div>
                  <div className="flex-shrink-0 text-gray-500">
                    {expanded ? (
                      <ChevronUp className="w-4 h-4" />
                    ) : (
                      <ChevronDown className="w-4 h-4" />
                    )}
                  </div>
                </button>

                <AnimatePresence>
                  {expanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="border-t border-gray-800"
                    >
                      <div className="px-4 py-3 space-y-3 text-xs">
                        <div>
                          <span className="text-gray-500">ID:</span>{" "}
                          <span className="font-mono text-gray-400">{block.id}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Organ:</span>{" "}
                          <span className="text-gray-400">{block.organ}</span>
                        </div>
                        <div>
                          <span className="text-gray-500 block mb-1">Inputs:</span>
                          <pre className="p-2 rounded bg-gray-950 text-gray-400 overflow-x-auto">
                            {JSON.stringify(block.input_schema, null, 2)}
                          </pre>
                        </div>
                        <div>
                          <span className="text-gray-500 block mb-1">Outputs:</span>
                          <pre className="p-2 rounded bg-gray-950 text-gray-400 overflow-x-auto">
                            {JSON.stringify(block.output_schema, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
