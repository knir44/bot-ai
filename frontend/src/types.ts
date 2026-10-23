export interface Health {
  status: "ok" | "degraded";
  elasticsearch: boolean;
  postgres: boolean;
  gemini_configured: boolean;
  indexed_chunks: number;
  models: { llm: string; embedding: string; dims: number };
}

export interface Source {
  n: number;
  filename: string;
  chunk_index: number;
  content: string;
  rrf_score: number;
  bm25_rank: number | null;
  vector_rank: number | null;
}

export interface Contribution {
  rank: number;
  score: number;
}

/** A retrieved chunk. Different lists fill different fields. */
export interface Hit {
  chunk_id: string;
  filename: string;
  chunk_index: number;
  snippet?: string; // in chat traces
  content?: string; // in lab results
  score?: number;
  rank?: number;
  rrf_score?: number;
  contributions?: Record<string, Contribution>;
  bm25_score?: number | null;
  vector_score?: number | null;
  breakdown?: TermBreakdown[];
}

export interface TermBreakdown {
  term: string;
  score: number;
  idf: number | null;
  tf_norm: number | null;
  freq: number | null;
  docs_with_term: number | null;
  total_docs: number | null;
  field_length: number | null;
  avg_field_length: number | null;
  k1: number | null;
  b: number | null;
}

export interface Trace {
  original_query: string;
  standalone_query: string;
  params: { retrieve_k: number; top_k: number; rrf_k: number };
  bm25: Hit[];
  vector: Hit[];
  fused: Hit[];
  prompt: string;
  timings_ms: Record<string, number>;
  models: { llm: string; embedding: string; dims: number };
}

export interface ChatMessage {
  id?: number | string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[] | null;
  trace?: Trace | null;
  error?: boolean;
}

export interface DocInfo {
  doc_id: string;
  filename: string;
  chunks: number;
}

export interface LabResult {
  query: string;
  mode: string;
  params: { retrieve_k: number; top_k: number; rrf_k: number };
  bm25: Hit[];
  vector: Hit[];
  fused: Hit[];
  timings_ms: Record<string, number>;
}

export interface MapPoint {
  chunk_id: string;
  filename: string;
  chunk_index: number;
  snippet: string;
  x: number;
  y: number;
}

export interface EmbeddingMap {
  points: MapPoint[];
  query: { x: number; y: number } | null;
  note?: string;
}
