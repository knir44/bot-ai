import { useMemo, useState } from "react";
import type { EmbeddingMap as MapData } from "../types";

const PALETTE = ["#4f46e5", "#0891b2", "#059669", "#d97706", "#dc2626", "#7c3aed", "#db2777", "#65a30d", "#0d9488", "#9333ea"];
const W = 640;
const H = 380;
const PAD = 24;

/** 2-D scatter of chunk embeddings (PCA projection done by the backend). Pure SVG, no chart library. */
export function EmbeddingMapView({ data }: { data: MapData }) {
  const [hover, setHover] = useState<string | null>(null);

  const { files, scale } = useMemo(() => {
    const all = [...data.points.map((p) => ({ x: p.x, y: p.y })), ...(data.query ? [data.query] : [])];
    const xs = all.map((p) => p.x);
    const ys = all.map((p) => p.y);
    const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
    return {
      files: Array.from(new Set(data.points.map((p) => p.filename))).sort(),
      scale: {
        x: (v: number) => PAD + ((v - minX) / (maxX - minX || 1)) * (W - 2 * PAD),
        y: (v: number) => H - PAD - ((v - minY) / (maxY - minY || 1)) * (H - 2 * PAD),
      },
    };
  }, [data]);

  if (!data.points.length) return <p className="text-sm text-slate-500">{data.note ?? "No chunks to plot yet."}</p>;
  const color = (f: string) => PALETTE[files.indexOf(f) % PALETTE.length];
  const hovered = data.points.find((p) => p.chunk_id === hover);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full rounded-lg border border-slate-200 bg-white">
        {data.points.map((p) => (
          <circle
            key={p.chunk_id}
            cx={scale.x(p.x)}
            cy={scale.y(p.y)}
            r={hover === p.chunk_id ? 8 : 5.5}
            fill={color(p.filename)}
            fillOpacity={0.8}
            stroke="white"
            strokeWidth={1.5}
            onMouseEnter={() => setHover(p.chunk_id)}
            onMouseLeave={() => setHover(null)}
          />
        ))}
        {data.query && (
          <g transform={`translate(${scale.x(data.query.x)},${scale.y(data.query.y)})`}>
            <path d="M0,-11 L3.2,-3.5 11,-3.5 4.8,1.5 7,9.5 0,5 -7,9.5 -4.8,1.5 -11,-3.5 -3.2,-3.5Z" fill="#111827" stroke="white" strokeWidth={1.5} />
            <text y={-15} textAnchor="middle" className="fill-slate-900 text-[11px] font-semibold">
              your query
            </text>
          </g>
        )}
      </svg>
      <div className="mt-2 flex min-h-[2.5rem] flex-wrap gap-x-3 gap-y-1 text-[11px]">
        {files.map((f) => (
          <span key={f} className="flex items-center gap-1">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: color(f) }} />
            {f}
          </span>
        ))}
      </div>
      <p className="min-h-[2.5rem] text-xs text-slate-600">
        {hovered ? (
          <>
            <b>
              {hovered.filename} #{hovered.chunk_index}
            </b>
            : {hovered.snippet}...
          </>
        ) : (
          "Hover a dot to read the chunk."
        )}
      </p>
    </div>
  );
}
