import { useState } from "react";
import { api } from "../api";
import { EmbeddingMapView } from "../components/EmbeddingMap";
import { Explain, fmt } from "../components/Explain";
import { TAB_HELP } from "../components/TraceView";
import type { EmbeddingMap, Hit, LabResult, TermBreakdown } from "../types";

const EXAMPLES: { label: string; q: string; hint: string }[] = [
  { label: "Exact name", q: "Apollo 13 oxygen tank explosion", hint: "BM25 should shine: rare exact tokens." },
  { label: "Paraphrase", q: "Which robot flew a small aircraft on another planet?", hint: "No shared words with 'Ingenuity helicopter' - embeddings should win." },
  { label: "Concept", q: "Which telescope sees the earliest galaxies using heat radiation?", hint: "'heat radiation' = infrared; a semantic match." },
  { label: "Trap", q: "Apollo 11 oxygen tank", hint: "Mixes two missions: see which retriever follows 'Apollo 11' and which follows 'oxygen tank'." },
];

type Overlap = "both" | "bm25" | "vector";

function overlapOf(id: string, r: LabResult): Overlap {
  const inB = r.bm25.some((h) => h.chunk_id === id);
  const inV = r.vector.some((h) => h.chunk_id === id);
  return inB && inV ? "both" : inB ? "bm25" : "vector";
}

const BORDER: Record<Overlap, string> = { both: "border-l-emerald-500", bm25: "border-l-amber-500", vector: "border-l-sky-500" };

function BreakdownTable({ rows }: { rows: TermBreakdown[] }) {
  if (!rows.length) return null;
  return (
    <div className="mt-1 overflow-x-auto rounded border border-slate-200 bg-slate-50 p-1.5">
      <table className="w-full text-[10px]">
        <thead className="text-left text-slate-500">
          <tr>
            <th>term*</th>
            <th>freq</th>
            <th>n / N</th>
            <th>idf</th>
            <th>tf part</th>
            <th>idf×tf</th>
          </tr>
        </thead>
        <tbody className="font-mono">
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
      <p className="mt-1 text-[10px] text-slate-500">
        *stemmed. n = chunks containing the term, N = all chunks. tf part = freq / (freq + k1·(1 − b + b·len/avglen)), here len = {fmt(rows[0].field_length, 0)}, avglen = {fmt(rows[0].avg_field_length, 0)}, k1 = {fmt(rows[0].k1, 1)}, b = {fmt(rows[0].b, 2)}.
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
      className={`rounded-md border border-l-4 bg-white p-2 text-xs ${BORDER[overlap]} ${hover === h.chunk_id ? "ring-2 ring-brand-500" : "border-slate-200"}`}
    >
      <div className="flex items-center gap-1.5">
        <span className="rounded bg-slate-800 px-1.5 font-mono text-[11px] text-white">#{h.rank ?? "·"}</span>
        <span className="truncate font-medium">
          {h.filename} <span className="text-slate-400">#{h.chunk_index}</span>
        </span>
        <span className="ml-auto shrink-0 font-mono text-slate-500">
          {kind === "bm25" && fmt(h.score, 2)}
          {kind === "vector" && `cos ${fmt(h.score, 3)}`}
          {kind === "rrf" && fmt(h.rrf_score, 5)}
        </span>
      </div>
      {kind === "rrf" && h.contributions && (
        <div className="mt-1 flex flex-wrap gap-1 font-mono text-[10px]">
          {Object.entries(h.contributions).map(([name, c]) => (
            <span key={name} className="rounded bg-brand-50 px-1 text-brand-700">
              {name} #{c.rank} → 1/({k}+{c.rank}) = {c.score.toFixed(5)}
            </span>
          ))}
        </div>
      )}
      <p className="mt-1 line-clamp-3 text-slate-500">{h.content}</p>
      {kind === "bm25" && h.breakdown && (
        <>
          <button className="mt-1 text-[11px] text-brand-700 hover:underline" onClick={() => setWhy(!why)}>
            {why ? "Hide" : "Why this BM25 score?"}
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
        <h2 className="text-lg font-semibold">Search the same question three ways</h2>
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
          <input value={query} onChange={(e) => setQuery(e.target.value)} maxLength={2000} className="min-w-[240px] flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <label className="flex items-center gap-2 text-xs text-slate-600" title="RRF smoothing constant">
            RRF k = <b className="w-8 font-mono">{rrfK}</b>
            <input type="range" min={0} max={200} value={rrfK} onChange={(e) => setRrfK(Number(e.target.value))} />
          </label>
          <button className="btn-primary" disabled={busy || !query.trim()}>
            {busy ? "Searching..." : "Search"}
          </button>
        </form>
        {hint && <p className="text-xs text-slate-500">💡 {hint}</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <Explain title="How to read this page">
          Each column is an independent ranking of the same chunks. The coloured edge shows agreement: <b className="text-emerald-700">green</b> = found by both retrievers, <b className="text-amber-600">amber</b> = BM25 only,{" "}
          <b className="text-sky-600">blue</b> = vector only. Hover a chunk to find it in the other columns. Drag the <b>RRF k</b> slider and search again: with k=0 the #1 of either list dominates; with a large k, chunks that appear in both lists win.
        </Explain>
      </section>

      {result && (
        <section className="grid gap-3 md:grid-cols-3">
          {cols.map((c) => (
            <div key={c.key} className="space-y-2">
              <h3 className="text-sm font-semibold">{TAB_HELP[c.help].title}</h3>
              <p className="text-[11px] leading-snug text-slate-500">{TAB_HELP[c.help].text}</p>
              <ul className="space-y-1.5">
                {result[c.key].map((h) => (
                  <HitCard key={h.chunk_id} h={h} kind={c.kind} overlap={overlapOf(h.chunk_id, result)} hover={hover} setHover={setHover} k={result.params.rrf_k} />
                ))}
                {result[c.key].length === 0 && <li className="text-xs text-slate-400">No results.</li>}
              </ul>
            </div>
          ))}
          <p className="font-mono text-[11px] text-slate-400 md:col-span-3">
            {Object.entries(result.timings_ms).map(([k, v]) => `${k}: ${v}`).join(" · ")}
          </p>
        </section>
      )}

      <section className="card space-y-3 p-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Embedding map</h2>
          <button className="btn-ghost text-xs" disabled={busy} onClick={plot}>
            Plot chunks (+ my query)
          </button>
        </div>
        <Explain title="What is this?">
          Every chunk is a point in 768-dimensional space. PCA squashes that to 2-D so we can look at it - information is lost, so read it as intuition: chunks about the same topic should cluster, and your query (★) should land near the chunks that answer it.
        </Explain>
        {map && <EmbeddingMapView data={map} />}
      </section>
    </div>
  );
}
