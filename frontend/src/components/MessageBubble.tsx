import { useState } from "react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "../types";
import { SourceCard } from "./SourceCard";
import { TraceView } from "./TraceView";

export function MessageBubble({ m }: { m: ChatMessage }) {
  const [showSources, setShowSources] = useState(false);
  const [showTrace, setShowTrace] = useState(false);

  if (m.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-brand-600 px-3 py-2 text-sm text-white">{m.content}</div>
      </div>
    );
  }
  const hasSources = !!m.sources?.length;
  return (
    <div className="flex justify-start">
      <div className="max-w-[92%]">
        <div className={`prose-chat rounded-2xl rounded-bl-sm px-3 py-2 text-sm ${m.error ? "bg-red-50 text-red-700" : "border border-slate-200 bg-white text-slate-800"}`}>
          <ReactMarkdown>{m.content}</ReactMarkdown>
        </div>
        {(hasSources || m.trace) && (
          <div className="mt-1 flex gap-3 px-1 text-[11px] text-brand-700">
            {hasSources && (
              <button className="hover:underline" onClick={() => setShowSources(!showSources)}>
                {showSources ? "Hide" : "Show"} sources ({m.sources!.length})
              </button>
            )}
            {m.trace && (
              <button className="hover:underline" onClick={() => setShowTrace(!showTrace)}>
                {showTrace ? "Hide" : "How did I answer?"}
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
