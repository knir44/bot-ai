import { ReactNode } from "react";

/** תיבת "מה אני רואה כאן?". מטרת האפליקציה היא ללמד, ולכן יש כאלה בכל מקום. */
export function Explain({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-brand-200 bg-brand-50 p-2.5 text-xs leading-relaxed text-slate-600">
      <div className="mb-0.5 font-semibold text-brand-700">{title}</div>
      {children}
    </div>
  );
}

export const fmt = (n: number | null | undefined, digits = 3) => (n === null || n === undefined ? "-" : n.toFixed(digits));
