"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Bell, CheckCircle2, AlertCircle, Info, AlertTriangle, X } from "lucide-react";

interface Notification {
  id: number;
  title: string;
  message: string;
  level: "info" | "success" | "warning" | "error";
  pipeline_id?: string;
  timestamp: number;
}

interface NotificationsContextValue {
  notifications: Notification[];
  unreadCount: number;
  markAllRead: () => void;
}

const NotificationsContext = createContext<NotificationsContextValue>({
  notifications: [],
  unreadCount: 0,
  markAllRead: () => {},
});

export function useNotifications() {
  return useContext(NotificationsContext);
}

const LEVEL_ICON = {
  info: Info,
  success: CheckCircle2,
  warning: AlertTriangle,
  error: AlertCircle,
};

const LEVEL_COLOR = {
  info: "border-[#0000FF]/30 bg-[#0000FF]/10",
  success: "border-green-500/30 bg-green-500/10",
  warning: "border-yellow-500/30 bg-yellow-500/10",
  error: "border-red-500/30 bg-red-500/10",
};

const LEVEL_TEXT = {
  info: "text-[#0000FF]",
  success: "text-green-600",
  warning: "text-yellow-600",
  error: "text-red-600",
};

function Toast({ notification, onDismiss }: { notification: Notification; onDismiss: () => void }) {
  const Icon = LEVEL_ICON[notification.level] || Bell;

  useEffect(() => {
    const timer = setTimeout(onDismiss, 5000);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  return (
    <motion.div
      initial={{ opacity: 0, x: 80 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 80 }}
      className={`relative flex items-start gap-3 p-3 rounded-lg border ${LEVEL_COLOR[notification.level]} backdrop-blur-sm max-w-sm shadow-lg`}
    >
      <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${LEVEL_TEXT[notification.level]}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-900 truncate">{notification.title}</p>
        <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{notification.message}</p>
      </div>
      <button onClick={onDismiss} className="text-slate-400 hover:text-slate-700 flex-shrink-0">
        <X className="w-3.5 h-3.5" />
      </button>
    </motion.div>
  );
}

export function NotificationsProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [toasts, setToasts] = useState<Notification[]>([]);
  const [readCount, setReadCount] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Connect to SSE
  useEffect(() => {
    const connect = () => {
      // Connect directly to backend (bypass Next.js proxy for SSE — proxy buffers SSE)
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const es = new EventSource(`${backendUrl}/api/notifications/stream`);
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const notification: Notification = {
            id: data.id,
            title: data.title,
            message: data.message,
            level: data.level || "info",
            pipeline_id: data.pipeline_id,
            timestamp: Date.now(),
          };
          setNotifications((prev) => [notification, ...prev].slice(0, 100));
          setToasts((prev) => [notification, ...prev].slice(0, 5));
        } catch { /* ignore parse errors */ }
      };

      es.onerror = () => {
        es.close();
        // Reconnect after 5s
        setTimeout(connect, 5000);
      };
    };

    connect();

    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const markAllRead = useCallback(() => {
    setReadCount(notifications.length);
  }, [notifications.length]);

  const unreadCount = Math.max(0, notifications.length - readCount);

  return (
    <NotificationsContext.Provider value={{ notifications, unreadCount, markAllRead }}>
      {children}
      {/* Toast container — fixed bottom-right */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        <AnimatePresence>
          {toasts.map((toast) => (
            <Toast key={toast.id} notification={toast} onDismiss={() => dismissToast(toast.id)} />
          ))}
        </AnimatePresence>
      </div>
    </NotificationsContext.Provider>
  );
}
