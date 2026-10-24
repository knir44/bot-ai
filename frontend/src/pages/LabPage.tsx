import { useState } from "react";
import { api } from "../api";
import { EmbeddingMapView } from "../components/EmbeddingMap";
import { Explain, fmt } from "../components/Explain";
import { TAB_HELP } from "../components/TraceView";
import type { EmbeddingMap, Hit, LabResult, TermBreakdown } from "../types";

// מסמכי הדוגמה באנגלית, ולכן רוב השאילתות באנגלית. הדוגמה האחרונה בעברית בכוונה: היא מראה מה קורה כשאין מילים משותפות.
const EXAMPLES: { label: string; q: string; hint: string }[] = [
  { label: "שם מדויק", q: "Apollo 13 oxygen tank explosion", hint: "BM25 אמור לזרוח כאן: מילים נדירות ומדויקות." },
  { label: "ניסוח אחר", q: "Which robot flew a small aircraft on another planet?", hint: "אין אף מילה משותפת עם 'Ingenuity helicopter', ולכן כאן ה-embeddings אמורים לנצח." },
  { label: "מושג", q: "Which telescope sees the earliest galaxies using heat radiation?", hint: "'heat radiation' הוא אינפרא-אדום: התאמה סמנטית ולא מילולית." },
  { label: "מלכודת", q: "Apollo 11 oxygen tank", hint: "מערבב שתי משימות. ראה איזה מנוע עוקב אחרי 'Apollo 11' ואיזה אחרי 'oxygen tank'." },
  { label: "שאלה בעברית", q: "איזה רובוט הטיס מסוק על מאדים?", hint: "שאלה בעברית מול מסמכים באנגלית: ל-BM25 אין מה למצוא (אפס מילים משותפות), אבל החיפוש הווקטורי הוא רב-לשוני וימצא." },
];

type Overlap = "both" | "bm25" | "vector";

function overlapOf(id: string, r: LabResult): Overlap {
  const inB = r.bm25.some((h) => h.chunk_id === id);
  const inV = r.vector.some((h) => h.chunk_id === id);
  return inB && inV ? "both" : inB ? "bm25" : "vector";
}

const BORDER: Record<Overlap, string> = { both: "border-s-emerald-400", bm25: "border-s-amber-400", vector: "border-s-sky-400" };

function BreakdownTable({ rows }: { rows: TermBreakdown[] }) {
  if (!rows.length) return null;
  return (
    <div className="mt-1 overflow-x-auto rounded border border-slate-200 bg-slate-50 p-1.5">
      <table dir="ltr" className="w-full text-[10px]">
        <thead className="text-left text-slate-400">
          <tr>
            <th>term*</th>
            <th>freq</th>
            <th>n / N</th>
            <th>idf</th>
            <th>tf part</th>
            <th>idf×tf</th>
          </tr>
        </thead>
        <tbody className="font-mono text-slate-600">
          {rows.map((t) => (
            <tr key={t.term}>
              <td>{t.term}</td>
              <td>{fmt(t.freq, 0)}</td>
              <td>
                {fmt(t.docs_with_term, 0)} / {fmt(t.total_docs, 0)}
              </td>
              <td>{fmt(t.idf, 2)}</td>
              <td>{fmt(t.tf_norm, 2)}</td>
              <td>{fmt(t.score, 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-1 text-[10px] text-slate-400">
        *אחרי stemming. n = כמה קטעים מכילים את המונח, N = כל הקטעים. tf part = freq / (freq + k1·(1 − b + b·len/avglen)). כאן{" "}
        <span dir="ltr">
          len = {fmt(rows[0].field_length, 0)}, avglen = {fmt(rows[0].avg_field_length, 0)}, k1 = {fmt(rows[0].k1, 1)}, b = {fmt(rows[0].b, 2)}
        </span>
        .
      </p>
    </div>
  );
}

function HitCard({ h, kind, overlap, hover, setHover, k }: { h: Hit; kind: "bm25" | "vector" | "rrf"; overlap: Overlap; hover: string | null; setHover: (s: string | null) => void; k: number }) {
  const [why, setWhy] = useState(false);
  return (
    <li
      onMouseEnter={() => setHover(h.chunk_id)}
      onMouseLeave={() => setHover(null)}
      className={`rounded-md border border-s-4 bg-white p-2 text-xs ${BORDER[overlap]} ${hover === h.chunk_id ? "ring-2 ring-brand-400" : "border-slate-200"}`}
    >
      <div dir="ltr" className="flex items-center gap-1.5">
        <span className="rounded bg-slate-200 px-1.5 font-mono text-[11px] text-slate-800">#{h.rank ?? "·"}</span>
        <span className="truncate font-medium text-slate-700">
          {h.filename} <span className="text-slate-400">#{h.chunk_index}</span>
        </span>
        <span className="ml-auto shrink-0 font-mono text-slate-500">
          {kind === "bm25" && fmt(h.score, 2)}
          {kind === "vector" && `cos ${fmt(h.score, 3)}`}
          {kind === "rrf" && fmt(h.rrf_score, 5)}
        </span>
      </div>
      {kind === "rrf" && h.contributions && (
        <div dir="ltr" className="mt-1 flex flex-wrap gap-1 font-mono text-[10px]">
          {Object.entries(h.contributions).map(([name, c]) => (
            <span key={name} className="rounded bg-brand-50 px-1 text-brand-700">
              {name} #{c.rank} → 1/({k}+{c.rank}) = {c.score.toFixed(5)}
            </span>
          ))}
        </div>
      )}
      <p dir="ltr" className="mt-1 line-clamp-3 text-start text-slate-400">
        {h.content}
      </p>
      {kind === "bm25" && h.breakdown && (
        <>
          <button className="mt-1 text-[11px] text-brand-700 hover:underline" onClick={() => setWhy(!why)}>
            {why ? "הסתר" : "מדוע ציון BM25 כזה?"}
          </button>
          {why && <BreakdownTable rows={h.breakdown} />}
        </>
      )}
    </li>
  );
}

export function LabPage() {
  const [query, setQuery] = useState(EXAMPLES[1].q);
  const [rrfK, setRrfK] = useState(60);
  const [result, setResult] = useState<LabResult | null>(null);
  const [map, setMap] = useState<EmbeddingMap | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [hint, setHint] = useState<string>(EXAMPLES[1].hint);

  const run = async (q = query) => {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.labSearch({ query: q, explain: true, rrf_k: rrfK, top_k: 5, retrieve_k: 10 }));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const plot = async () => {
    setBusy(true);
    setError(null);
    try {
      setMap(await api.embeddingMap(query.trim() || undefined));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const cols: { key: "bm25" | "vector" | "fused"; kind: "bm25" | "vector" | "rrf"; help: keyof typeof TAB_HELP }[] = [
    { key: "bm25", kind: "bm25", help: "bm25" },
    { key: "vector", kind: "vector", help: "vector" },
    { key: "fused", kind: "rrf", help: "rrf" },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-5 p-4 pb-24">
      <section className="card space-y-3 p-4">
        <h2 className="text-lg font-semibold text-slate-800">אותה שאלה, שלוש דרכי חיפוש</h2>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((e) => (
            <button
              key={e.label}
              className="btn-ghost text-xs"
              onClick={() => {
                setQuery(e.q);
                setHint(e.hint);
                run(e.q);
              }}
            >
              {e.label}
            </button>
          ))}
        </div>
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            setHint("");
            run();
          }}
        >
          <input
            dir="auto"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            maxLength={2000}
            className="min-w-[240px] flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 outline-none focus:border-brand-400"
          />
          <label className="flex items-center gap-2 text-xs text-slate-500" title="קבוע ההחלקה של RRF">
            <span dir="ltr">RRF k =</span>
            <b dir="ltr" className="w-8 font-mono text-slate-700">
              {rrfK}
            </b>
            <input type="range" min={0} max={200} value={rrfK} onChange={(e) => setRrfK(Number(e.target.value))} className="accent-teal-400" />
          </label>
          <button className="btn-primary" disabled={busy || !query.trim()}>
            {busy ? "מחפש..." : "חפש"}
          </button>
        </form>
        {hint && <p className="text-xs text-slate-500">💡 {hint}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <Explain title="איך קוראים את הדף?">
          כל עמודה היא דירוג עצמאי של אותם קטעים. הפס הצבעוני בצד מראה הסכמה: <b className="text-emerald-600">ירוק</b> = נמצא בשני המנועים, <b className="text-amber-600">צהוב</b> = רק BM25, <b className="text-sky-600">כחול</b> = רק החיפוש
          הווקטורי. רחף מעל קטע כדי למצוא אותו בשאר העמודות. אפשר להזיז את הסליידר <b>RRF k</b> ולחפש שוב: ב-k=0 מקום ראשון בכל אחת מהרשימות שולט, וב-k גדול קטעים שמופיעים בשתי הרשימות מנצחים.
        </Explain>
      </section>

      {result && (
        <section className="grid gap-3 md:grid-cols-3">
          {cols.map((c) => (
            <div key={c.key} className="space-y-2">
              <h3 className="text-sm font-semibold text-slate-800">{TAB_HELP[c.help].title}</h3>
              <p className="text-[11px] leading-snug text-slate-500">{TAB_HELP[c.help].text}</p>
              <ul className="space-y-1.5">
                {result[c.key].map((h) => (
                  <HitCard key={h.chunk_id} h={h} kind={c.kind} overlap={overlapOf(h.chunk_id, result)} hover={hover} setHover={setHover} k={result.params.rrf_k} />
                ))}
                {result[c.key].length === 0 && <li className="text-xs text-slate-400">אין תוצאות.</li>}
              </ul>
            </div>
          ))}
          <p dir="ltr" className="font-mono text-[11px] text-slate-400 md:col-span-3">
            {Object.entries(result.timings_ms).map(([k, v]) => `${k}: ${v}`).join(" · ")}
          </p>
        </section>
      )}

      <section className="card space-y-3 p-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-slate-800">מפת Embeddings</h2>
          <button className="btn-ghost text-xs" disabled={busy} onClick={plot}>
            הצג קטעים (+ השאלה שלי)
          </button>
        </div>
        <Explain title="מה זה?">
          כל קטע הוא נקודה במרחב של 768 מימדים. PCA מכווץ אותו לשני מימדים כדי שנוכל להסתכל עליו. מידע הולך לאיבוד, ולכן זו אינטואיציה ולא מדידה מדויקת: קטעים באותו נושא אמורים להתקבץ, והשאלה שלך (★) אמורה לנחות ליד הקטעים שעונים עליה.
        </Explain>
        {map && <EmbeddingMapView data={map} />}
      </section>
    </div>
  );
}
