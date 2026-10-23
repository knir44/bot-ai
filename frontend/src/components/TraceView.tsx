import { useState } from "react";
import type { Hit, Trace } from "../types";
import { Explain, fmt } from "./Explain";

type Tab = "bm25" | "vector" | "rrf" | "prompt";

export const TAB_HELP: Record<Tab, { title: string; text: string }> = {
  bm25: {
    title: "BM25 - keyword search",
    text: "Scores chunks by how many query words they contain, weighting rare words more (IDF), with diminishing returns for repeats and a penalty for long chunks. Great at exact names and numbers; blind to synonyms.",
  },
  vector: {
    title: "Vector search - meaning",
    text: "The question and every chunk were turned into embeddings (lists of numbers). Chunks whose vectors point in a similar direction (cosine similarity) have a similar meaning, even without shared words.",
  },
  rrf: {
    title: "RRF - fusing both lists",
    text: "BM25 and cosine scores cannot be compared, so RRF ignores scores and uses only ranks: each list gives a chunk 1/(k+rank) points. Chunks both retrievers like rise to the top. These are the chunks sent to the LLM.",
  },
  prompt: {
    title: "The prompt the LLM actually saw",
    text: "The retrieved chunks are pasted into <context> with numbers, so the model can cite [1], [2]. The system instructions (answer only from context, say it does not know otherwise) are sent separately.",
  },
};

function HitRow({ h, showFor, k }: { h: Hit; showFor: Tab; k: number }) {
  return (
    <li className="rounded-md border border-slate-200 bg-white p-1.5">
      <div className="flex items-center gap-1.5 text-[11px]">
        <span className="rounded bg-slate-800 px-1 font-mono text-white">#{h.rank ?? "-"}</span>
        <span className="truncate font-medium">
          {h.filename} <span className="text-slate-400">#{h.chunk_index}</span>
        </span>
        <span className="ml-auto shrink-0 font-mono text-slate-500">
          {showFor === "bm25" && `score ${fmt(h.score, 2)}`}
          {showFor === "vector" && `cos ${fmt(h.score, 3)}`}
          {showFor === "rrf" && `${fmt(h.rrf_score, 4)}`}
        </span>
      </div>
      {showFor === "rrf" && h.contributions && (
        <div className="mt-1 flex flex-wrap gap-1 font-mono text-[10px]">
          {Object.entries(h.contributions).map(([name, c]) => (
            <span key={name} className="rounded bg-brand-50 px-1 text-brand-700">
              {name} rank {c.rank}: 1/({k}+{c.rank}) = {c.score.toFixed(5)}
            </span>
          ))}
        </div>
      )}
      <p className="mt-1 line-clamp-2 text-[11px] text-slate-500">{h.snippet}</p>
    </li>
  );
}

export function TraceView({ trace }: { trace: Trace }) {
  const [tab, setTab] = useState<Tab>("rrf");
  const tabs: [Tab, string][] = [
    ["bm25", `BM25 (${trace.bm25.length})`],
    ["vector", `Vector (${trace.vector.length})`],
    ["rrf", "RRF → top " + trace.fused.length],
    ["prompt", "Prompt"],
  ];
  const list = tab === "bm25" ? trace.bm25 : tab === "vector" ? trace.vector : trace.fused;

  return (
    <div className="mt-2 space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-2">
      {trace.standalone_query !== trace.original_query && (
        <Explain title="Follow-up rewritten for search">
          “{trace.original_query}” → <b>“{trace.standalone_query}”</b>. A follow-up like this is meaningless to a search engine on its own, so the LLM first rewrites it using the chat history.
        </Explain>
      )}
      <div className="flex gap-1">
        {tabs.map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`rounded-md px-2 py-1 text-[11px] font-medium ${tab === id ? "bg-brand-600 text-white" : "border border-slate-200 bg-white text-slate-600"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <Explain title={TAB_HELP[tab].title}>{TAB_HELP[tab].text}</Explain>
      {tab === "prompt" ? (
        <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-slate-900 p-2 text-[10px] text-slate-100">{trace.prompt}</pre>
      ) : (
        <ul className="max-h-64 space-y-1 overflow-auto">
          {list.map((h) => (
            <HitRow key={h.chunk_id} h={h} showFor={tab} k={trace.params.rrf_k} />
          ))}
        </ul>
      )}
      <div className="font-mono text-[10px] text-slate-400">
        {Object.entries(trace.timings_ms).map(([k, v]) => `${k}: ${v}`).join(" · ")} · llm {trace.models.llm} · embeddings {trace.models.embedding} ({trace.models.dims}d)
      </div>
    </div>
  );
}
