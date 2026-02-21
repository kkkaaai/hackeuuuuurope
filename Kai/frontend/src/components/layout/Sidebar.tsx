"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MessageSquare, LayoutDashboard, Blocks, Workflow, Activity } from "lucide-react";
import { useNotifications } from "@/lib/notifications";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/activity", label: "Activity", icon: Activity, showBadge: true },
  { href: "/blocks", label: "Blocks", icon: Blocks },
];

export function Sidebar() {
  const pathname = usePathname();
  const { unreadCount, markAllRead } = useNotifications();

  return (
    <aside className="w-64 border-r border-gray-800 bg-gray-950 flex flex-col">
      <div className="p-6 border-b border-gray-800">
        <Link href="/chat" className="flex items-center gap-2">
          <Workflow className="w-6 h-6 text-blue-500" />
          <span className="text-lg font-semibold">AgentFlow</span>
        </Link>
        <p className="text-xs text-gray-500 mt-1">AI Automation Platform</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon, showBadge }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={showBadge && active ? markAllRead : undefined}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-blue-500/10 text-blue-400"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
              {showBadge && unreadCount > 0 && (
                <span className="ml-auto inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-medium leading-none bg-blue-500 text-white rounded-full min-w-[18px]">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-gray-800">
        <div className="text-xs text-gray-600">
          35 blocks &middot; 7 categories
        </div>
      </div>
    </aside>
  );
}
