"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { MessageSquare, LayoutDashboard, Blocks, Activity, Workflow } from "lucide-react";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/activity", label: "Activity", icon: Activity },
  { href: "/blocks", label: "Blocks", icon: Blocks },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 border-r border-white/5 bg-gray-950/80 backdrop-blur-xl flex flex-col">
      <div className="p-5 pb-4 border-b border-white/5">
        <Link href="/chat" className="flex items-center gap-2.5">
          <Workflow className="w-5 h-5 text-blue-400" />
          <span className="text-base font-semibold bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            AgentFlow
          </span>
        </Link>
        <p className="text-[11px] text-gray-600 mt-1">AI Automation Platform</p>
      </div>

      <nav className="flex-1 p-3 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={`relative flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? "text-white"
                  : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
              }`}
            >
              {active && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute left-0 top-1 bottom-1 w-[3px] rounded-full bg-blue-400"
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                />
              )}
              <Icon className={`w-4 h-4 ${active ? "text-blue-400" : ""}`} />
              <span className={active ? "font-medium" : ""}>{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-white/5">
        <div className="text-[11px] text-gray-700">
          AgentFlow Demo
        </div>
      </div>
    </aside>
  );
}
