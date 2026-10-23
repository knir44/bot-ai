import { ReactNode } from "react";

/** A small "what am I looking at?" box. The app's job is teaching, so these are everywhere. */
export function Explain({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-brand-100 bg-brand-50 p-2.5 text-xs leading-relaxed text-slate-700">
      <div className="mb-0.5 font-semibold text-brand-700">{title}</div>
      {children}
    </div>
  );
}

export const fmt = (n: number | null | undefined, digits = 3) => (n === null || n === undefined ? "-" : n.toFixed(digits));
