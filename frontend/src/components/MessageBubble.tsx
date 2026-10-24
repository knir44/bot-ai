import { useState } from "react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "../types";
import { SourceCard } from "./SourceCard";
import { TraceView } from "./TraceView";
import { Avatar } from "./Welcome";

export function MessageBubble({ m }: { m: ChatMessage }) {
  const [showSources, setShowSources] = useState(false);
  const [showTrace, setShowTrace] = useState(false);

  // בעברית (RTL) "התחלה" היא הצד הימני: הבוט מימין עם אווטאר, המשתמש משמאל.
  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div dir="auto" className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-ee-sm bg-gradient-to-br from-teal-500 to-sky-500 px-3 py-2 text-sm font-medium text-white shadow-sm">
          {m.content}
        </div>
      </div>
    );
  }
  const hasSources = !!m.sources?.length;
  return (
    <div className="flex items-start gap-2">
      <Avatar />
      <div className="min-w-0 max-w-[88%]">
        <div
          dir="auto"
          className={`prose-chat rounded-2xl rounded-ss-sm border px-3 py-2 text-sm ${m.error ? "border-red-200 bg-red-50 text-red-700" : "border-slate-100 bg-white text-slate-800 shadow-sm"}`}
        >
          <ReactMarkdown>{m.content}</ReactMarkdown>
        </div>
        {(hasSources || m.trace) && (
          <div className="mt-1 flex gap-3 px-1 text-[11px] text-brand-700">
            {hasSources && (
              <button className="hover:underline" onClick={() => setShowSources(!showSources)}>
                {showSources ? "הסתר מקורות" : `הצג מקורות (${m.sources!.length})`}
              </button>
            )}
            {m.trace && (
              <button className="hover:underline" onClick={() => setShowTrace(!showTrace)}>
                {showTrace ? "הסתר" : "איך עניתי?"}
              </button>
            )}
          </div>
        )}
        {showSources && hasSources && (
          <div className="mt-1 space-y-1">
            {m.sources!.map((s) => (
              <SourceCard key={s.n} source={s} />
            ))}
          </div>
        )}
        {showTrace && m.trace && <TraceView trace={m.trace} />}
      </div>
    </div>
  );
}
