"use client";

import { usePathname } from "next/navigation";
import ChatPage from "@/app/chat/page";
import DashboardPage from "@/app/dashboard/page";
import ActivityPage from "@/app/activity/page";
import BlocksPage from "@/app/blocks/page";

const TAB_ROUTES = ["/chat", "/dashboard", "/activity", "/blocks"] as const;

export function TabShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const isTabRoute = TAB_ROUTES.some((r) => pathname.startsWith(r));

  // For non-tab routes (e.g. /pipelines/[id]), render normally
  if (!isTabRoute) {
    return <>{children}</>;
  }

  const activeTab = pathname.startsWith("/chat")
    ? "chat"
    : pathname.startsWith("/dashboard")
    ? "dashboard"
    : pathname.startsWith("/activity")
    ? "activity"
    : "blocks";

  return (
    <>
      <div className={activeTab === "chat" ? "h-full" : "hidden"}>
        <ChatPage />
      </div>
      <div className={activeTab === "dashboard" ? "h-full overflow-auto" : "hidden"}>
        <DashboardPage />
      </div>
      <div className={activeTab === "activity" ? "h-full overflow-auto" : "hidden"}>
        <ActivityPage />
      </div>
      <div className={activeTab === "blocks" ? "h-full overflow-auto" : "hidden"}>
        <BlocksPage />
      </div>
    </>
  );
}
