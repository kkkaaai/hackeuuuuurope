import {
  Zap,
  Eye,
  Brain,
  Cog,
  MessageCircle,
  Database,
  GitBranch,
} from "lucide-react";

export const CATEGORY_COLORS: Record<string, string> = {
  trigger: "#3b82f6",
  perceive: "#22c55e",
  think: "#a855f7",
  act: "#f97316",
  communicate: "#06b6d4",
  remember: "#ec4899",
  control: "#6b7280",
};

export const CATEGORY_BG: Record<string, string> = {
  trigger: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  perceive: "bg-green-500/10 text-green-400 border-green-500/30",
  think: "bg-purple-500/10 text-purple-400 border-purple-500/30",
  act: "bg-orange-500/10 text-orange-400 border-orange-500/30",
  communicate: "bg-cyan-500/10 text-cyan-400 border-cyan-500/30",
  remember: "bg-pink-500/10 text-pink-400 border-pink-500/30",
  control: "bg-gray-500/10 text-gray-400 border-gray-500/30",
};

export const CATEGORY_ICONS: Record<string, typeof Zap> = {
  trigger: Zap,
  perceive: Eye,
  think: Brain,
  act: Cog,
  communicate: MessageCircle,
  remember: Database,
  control: GitBranch,
};

export const CATEGORY_LABELS: Record<string, string> = {
  trigger: "Trigger",
  perceive: "Perceive",
  think: "Think",
  act: "Act",
  communicate: "Communicate",
  remember: "Remember",
  control: "Control Flow",
};

export const ALL_CATEGORIES = [
  "trigger",
  "perceive",
  "think",
  "act",
  "communicate",
  "remember",
  "control",
] as const;
