import { useState } from "react";
import type { Hit, Trace } from "../types";
import { Explain, fmt } from "./Explain";

type Tab = "bm25" | "vector" | "rrf" | "prompt";

export const TAB_HELP: Record<Tab, { title: string; text: string }> = {
  bm25: {
    title: "BM25 - חיפוש לפי מילות מפתח",
    text: "נותן ציון לכל קטע לפי כמה ממילות השאלה מופיעות בו. מילה נדירה שווה יותר (IDF), חזרות נוספות מוסיפות פחות ופחות, וקטעים ארוכים נענשים קלות. מצוין לשמות ומספרים מדויקים, עיוור למילים נרדפות.",
  },
  vector: {
    title: "חיפוש וקטורי - לפי משמעות",
    text: "השאלה וכל קטע הפכו ל-embeddings (רשימות של מספרים). קטעים שהוקטור שלהם מצביע לכיוון דומה (cosine similarity) קרובים במשמעות, גם בלי מילים משותפות.",
  },
  rrf: {
    title: "RRF - איחוד שתי הרשימות",
    text: "אי אפשר להשוות ציון BM25 לציון cosine, ולכן RRF מתעלם מהציונים ומשתמש רק בדירוג: כל רשימה נותנת לקטע 1/(k+דירוג) נקודות. קטעים ששני המנועים אוהבים עולים לראש. אלה הקטעים שנשלחים ל-LLM.",
  },
  prompt: {
    title: "הפרומפט שה-LLM ראה בפועל",
    text: "הקטעים שנשלפו מוזנים לתוך <context> עם מספרים, כדי שהמודל יוכל לצטט [1], [2]. הוראות המערכת (לענות רק מתוך ההקשר, ולומר שלא מצא אם אין תשובה) נשלחות בנפרד.",
  },
};

function HitRow({ h, showFor, k }: { h: Hit; showFor: Tab; k: number }) {
  return (
    <li className="rounded-md border border-slate-200 bg-white p-1.5">
      <div dir="ltr" className="flex items-center gap-1.5 text-[11px]">
        <span className="rounded bg-slate-200 px-1 font-mono text-slate-800">#{h.rank ?? "-"}</span>
        <span className="truncate font-medium text-slate-700">
          {h.filename} <span className="text-slate-400">#{h.chunk_index}</span>
        </span>
        <span className="ml-auto shrink-0 font-mono text-slate-500">
          {showFor === "bm25" && `score ${fmt(h.score, 2)}`}
          {showFor === "vector" && `cos ${fmt(h.score, 3)}`}
          {showFor === "rrf" && `${fmt(h.rrf_score, 4)}`}
        </span>
      </div>
      {showFor === "rrf" && h.contributions && (
        <div dir="ltr" className="mt-1 flex flex-wrap gap-1 font-mono text-[10px]">
          {Object.entries(h.contributions).map(([name, c]) => (
            <span key={name} className="rounded bg-brand-50 px-1 text-brand-700">
              {name} rank {c.rank}: 1/({k}+{c.rank}) = {c.score.toFixed(5)}
            </span>
          ))}
        </div>
      )}
      <p dir="ltr" className="mt-1 line-clamp-2 text-start text-[11px] text-slate-400">
        {h.snippet}
      </p>
    </li>
  );
}

export function TraceView({ trace }: { trace: Trace }) {
  const [tab, setTab] = useState<Tab>("rrf");
  const tabs: [Tab, string][] = [
    ["bm25", `BM25 (${trace.bm25.length})`],
    ["vector", `וקטורי (${trace.vector.length})`],
    ["rrf", `RRF ← ${trace.fused.length} נבחרו`],
    ["prompt", "פרומפט"],
  ];
  const list = tab === "bm25" ? trace.bm25 : tab === "vector" ? trace.vector : trace.fused;

  return (
    <div className="mt-2 space-y-2 rounded-lg border border-slate-200 bg-slate-50 p-2">
      {trace.standalone_query !== trace.original_query && (
        <Explain title="שאלת ההמשך נוסחה מחדש לחיפוש">
          “{trace.original_query}” ← <b>“{trace.standalone_query}”</b>. שאלת המשך כזו חסרת משמעות למנוע חיפוש לבדה, ולכן ה-LLM מנסח אותה מחדש לפי היסטוריית השיחה לפני החיפוש.
        </Explain>
      )}
      <div className="flex flex-wrap gap-1">
        {tabs.map(([id, label]) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`rounded-md px-2 py-1 text-[11px] font-medium ${tab === id ? "bg-brand-500 text-white" : "border border-slate-200 bg-slate-100 text-slate-600"}`}
          >
            {label}
          </button>
        ))}
      </div>
      <Explain title={TAB_HELP[tab].title}>{TAB_HELP[tab].text}</Explain>
      {tab === "prompt" ? (
        <pre dir="ltr" className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-slate-900 p-2 text-start text-[10px] text-slate-100">
          {trace.prompt}
        </pre>
      ) : (
        <ul className="max-h-64 space-y-1 overflow-auto">
          {list.map((h) => (
            <HitRow key={h.chunk_id} h={h} showFor={tab} k={trace.params.rrf_k} />
          ))}
        </ul>
      )}
      <div dir="ltr" className="font-mono text-[10px] text-slate-400">
        {Object.entries(trace.timings_ms).map(([k, v]) => `${k}: ${v}`).join(" · ")} · llm {trace.models.llm} · embeddings {trace.models.embedding} ({trace.models.dims}d)
      </div>
    </div>
  );
}
