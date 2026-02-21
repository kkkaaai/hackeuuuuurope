"use client";

import { ExternalLink, Newspaper, Brain, Search, Bell, CreditCard, Mail, Mic } from "lucide-react";

interface SharedContext {
  [nodeId: string]: Record<string, unknown>;
}

interface Props {
  sharedContext: SharedContext;
  errors?: string[];
}

function isSafeUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

type NodeDisplayType =
  | "summary_card"
  | "summary"
  | "search_results"
  | "notification"
  | "confirmation"
  | "decision"
  | "audio"
  | "payment"
  | "email"
  | "trigger"
  | "branch"
  | "generic";

const HIDDEN_NODE_TYPES = new Set<NodeDisplayType>(["trigger", "branch", "notification", "confirmation"]);

function classifyNode(data: Record<string, unknown>): NodeDisplayType {
  if (data.card && typeof data.card === "object") return "summary_card";
  if (typeof data.summary === "string" && Array.isArray(data.key_points)) return "summary";
  if (Array.isArray(data.results) && data.results.length > 0) return "search_results";
  if (data.delivered === true && data.notification_id) return "notification";
  if (data.confirmed !== undefined && data.question) return "confirmation";
  if (data.chosen && data.reasoning) return "decision";
  if (data.audio_url || data.audio_path) return "audio";
  if (data.payment_status || data.client_secret) return "payment";
  if (data.email_sent === true) return "email";
  if (data.triggered_at) return "trigger";
  if (data.branch) return "branch";
  return "generic";
}

function SummaryCardView({ data }: { data: Record<string, unknown> }) {
  const card = data.card as Record<string, unknown>;
  const title = card.title as string;
  const highlight = card.highlight as string | undefined;
  const fields = card.fields as Array<Record<string, unknown>> | undefined;

  return (
    <div className="rounded-xl bg-blue-500/[0.04] backdrop-blur-sm border border-blue-500/20 p-5 shadow-lg shadow-blue-500/5">
      <div className="flex items-center gap-2.5 mb-3">
        <Newspaper className="w-4 h-4 text-blue-400" />
        <h3 className="text-sm font-semibold text-blue-300">{title}</h3>
      </div>
      {highlight && (
        <p className="text-sm text-gray-200 mb-4 leading-relaxed">{highlight}</p>
      )}
      {fields && fields.length > 0 && (
        <div className="space-y-2.5">
          {fields.map((field, i) => (
            <div key={i} className="flex gap-3">
              <span className="text-xs font-medium text-gray-400 min-w-[90px]">
                {String(field.label || field.name || "")}
              </span>
              <span className="text-xs text-gray-200 leading-relaxed">
                {String(field.value || "")}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SummaryView({ data }: { data: Record<string, unknown> }) {
  const summary = data.summary as string;
  const keyPoints = data.key_points as string[];

  return (
    <div className="rounded-xl bg-purple-500/[0.04] backdrop-blur-sm border border-purple-500/20 p-5 shadow-lg shadow-purple-500/5">
      <div className="flex items-center gap-2.5 mb-3">
        <Brain className="w-4 h-4 text-purple-400" />
        <h3 className="text-sm font-semibold text-purple-300">Summary</h3>
      </div>
      <p className="text-sm text-gray-200 mb-4 leading-relaxed">{summary}</p>
      {keyPoints.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-400 mb-2">Key Points</p>
          <ul className="space-y-1.5">
            {keyPoints.map((point, i) => (
              <li key={i} className="text-xs text-gray-300 flex gap-2 leading-relaxed">
                <span className="text-purple-400 mt-0.5">&#8226;</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SearchResultsView({ data }: { data: Record<string, unknown> }) {
  const results = data.results as Array<Record<string, unknown>>;
  const query = data.query as string | undefined;

  return (
    <div className="rounded-xl bg-cyan-500/[0.04] backdrop-blur-sm border border-cyan-500/20 p-5 shadow-lg shadow-cyan-500/5">
      <div className="flex items-center gap-2.5 mb-3">
        <Search className="w-4 h-4 text-cyan-400" />
        <h3 className="text-sm font-semibold text-cyan-300">
          {query ? `Search: "${query}"` : "Search Results"}
        </h3>
        <span className="text-xs text-gray-500">{results.length} results</span>
      </div>
      <div className="space-y-3">
        {results.slice(0, 10).map((result, i) => (
          <div key={i} className="group rounded-lg px-3 py-2 -mx-1 hover:bg-white/[0.03] transition-colors">
            <div className="flex items-start gap-2.5">
              <span className="text-xs text-gray-600 mt-0.5 min-w-[20px] font-mono">{i + 1}.</span>
              <div className="min-w-0">
                {result.link && isSafeUrl(String(result.link)) ? (
                  <a
                    href={String(result.link)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-medium text-cyan-300 hover:text-cyan-200 flex items-center gap-1"
                  >
                    <span className="truncate">{String(result.title || result.link)}</span>
                    <ExternalLink className="w-3 h-3 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </a>
                ) : (
                  <p className="text-xs font-medium text-gray-200">
                    {String(result.title || "Untitled")}
                  </p>
                )}
                {result.snippet ? (
                  <p className="text-xs text-gray-400 mt-0.5 line-clamp-2 leading-relaxed">
                    {String(result.snippet)}
                  </p>
                ) : null}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DecisionView({ data }: { data: Record<string, unknown> }) {
  const chosen = data.chosen as Record<string, unknown>;
  const reasoning = data.reasoning as string;
  const confidence = data.confidence as number | undefined;

  return (
    <div className="rounded-xl bg-amber-500/[0.04] backdrop-blur-sm border border-amber-500/20 p-5 shadow-lg shadow-amber-500/5">
      <div className="flex items-center gap-2.5 mb-3">
        <Brain className="w-4 h-4 text-amber-400" />
        <h3 className="text-sm font-semibold text-amber-300">Decision</h3>
        {confidence !== undefined && (
          <span className="text-xs text-gray-500">{Math.round(confidence * 100)}% confidence</span>
        )}
      </div>
      <div className="bg-amber-500/10 rounded-lg p-3 mb-3">
        <p className="text-xs font-medium text-amber-200">
          {typeof chosen === "string" ? chosen : JSON.stringify(chosen)}
        </p>
      </div>
      <p className="text-xs text-gray-300 leading-relaxed">{reasoning}</p>
    </div>
  );
}

function NotificationView({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-400">
      <Bell className="w-3.5 h-3.5 text-green-400" />
      <span>Notification sent</span>
    </div>
  );
}

function AudioView({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-400">
      <Mic className="w-3.5 h-3.5 text-violet-400" />
      <span>Audio generated ({String(data.character_count ?? "?")} characters)</span>
    </div>
  );
}

function PaymentView({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="rounded-xl bg-green-500/[0.04] backdrop-blur-sm border border-green-500/20 p-4 shadow-lg shadow-green-500/5">
      <div className="flex items-center gap-2.5 mb-2">
        <CreditCard className="w-4 h-4 text-green-400" />
        <h3 className="text-sm font-semibold text-green-300">Payment</h3>
      </div>
      <p className="text-xs text-gray-300">
        Status: {String(data.payment_status || "processed")}
        {data.amount ? ` — ${data.currency || ""}${data.amount}` : ""}
      </p>
    </div>
  );
}

function EmailView({ data }: { data: Record<string, unknown> }) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-400">
      <Mail className="w-3.5 h-3.5 text-blue-400" />
      <span>Email sent to {String(data.to || "recipient")}</span>
    </div>
  );
}

function getPriority(type: NodeDisplayType): number {
  switch (type) {
    case "summary_card": return 100;
    case "summary": return 90;
    case "decision": return 85;
    case "search_results": return 80;
    case "payment": return 70;
    case "email": return 60;
    case "audio": return 50;
    case "notification": return 10;
    case "confirmation": return 10;
    case "trigger": return 0;
    case "branch": return 0;
    default: return 5;
  }
}

function isVisible(type: NodeDisplayType): boolean {
  return !HIDDEN_NODE_TYPES.has(type);
}

function renderNode(type: NodeDisplayType, data: Record<string, unknown>) {
  switch (type) {
    case "summary_card": return <SummaryCardView data={data} />;
    case "summary": return <SummaryView data={data} />;
    case "search_results": return <SearchResultsView data={data} />;
    case "decision": return <DecisionView data={data} />;
    case "notification": return <NotificationView data={data} />;
    case "audio": return <AudioView data={data} />;
    case "payment": return <PaymentView data={data} />;
    case "email": return <EmailView data={data} />;
    default: return null;
  }
}

export function PipelineResultDisplay({ sharedContext, errors }: Props) {
  const entries = Object.entries(sharedContext)
    .map(([nodeId, data]) => {
      const safeData = (data && typeof data === "object" && !Array.isArray(data))
        ? data as Record<string, unknown>
        : {};
      const type = classifyNode(safeData);
      return { nodeId, data: safeData, type, priority: getPriority(type) };
    })
    .sort((a, b) => b.priority - a.priority);

  const visibleEntries = entries.filter((e) => isVisible(e.type));
  const hasContent = visibleEntries.length > 0;

  if (!hasContent && (!errors || errors.length === 0)) {
    return (
      <div className="text-xs text-gray-500 italic">
        Pipeline completed with no displayable output.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {visibleEntries.map((entry) => (
        <div key={entry.nodeId}>{renderNode(entry.type, entry.data)}</div>
      ))}

      {Object.keys(sharedContext).length > 0 && (
        <details className="text-xs">
          <summary className="text-gray-500 cursor-pointer hover:text-gray-400 transition-colors">
            Raw output data
          </summary>
          <pre className="mt-2 p-3 rounded-lg bg-black/20 border border-white/5 text-gray-400 overflow-x-auto max-h-40 overflow-y-auto thin-scrollbar">
            {JSON.stringify(sharedContext, null, 2)}
          </pre>
        </details>
      )}
    </div>
  );
}
