import { useState } from "react";
import type { Source } from "../types";
import { fmt } from "./Explain";

export function SourceCard({ source }: { source: Source }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-slate-200 bg-white text-xs">
      <button className="flex w-full items-center gap-2 px-2 py-1.5 text-start" onClick={() => setOpen(!open)}>
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded bg-brand-500 font-semibold text-white">{source.n}</span>
        <span dir="ltr" className="truncate font-medium text-slate-700">
          {source.filename} <span className="text-slate-400">#{source.chunk_index}</span>
        </span>
        <span dir="ltr" className="ms-auto shrink-0 text-slate-400">
          BM25 #{source.bm25_rank ?? "-"} · vec #{source.vector_rank ?? "-"} · RRF {fmt(source.rrf_score, 4)}
        </span>
      </button>
      {open && (
        <p dir="ltr" className="border-t border-slate-200 px-2 py-1.5 text-start text-slate-500">
          {source.content}
        </p>
      )}
    </div>
  );
}
