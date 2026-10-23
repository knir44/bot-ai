import type { ChatMessage, DocInfo, EmbeddingMap, Health, LabResult, Source, Trace } from "./types";

const BASE = "/api/v1";
const STORAGE_KEY = "documind.session";

export interface Session {
  session_id: string;
  token: string;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// --- session persistence (per-browser convenience; the server is the source of truth) ---
export function loadSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Session) : null;
  } catch {
    return null;
  }
}

function saveSession(s: Session | null) {
  try {
    if (s) localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* private mode etc. - the app still works, just without persistence */
  }
}

async function parse(res: Response) {
  if (res.ok) return res.json();
  let detail = res.statusText;
  try {
    const body = await res.json();
    detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    /* non-JSON error body */
  }
  throw new ApiError(res.status, detail);
}

export async function createSession(): Promise<Session> {
  const s: Session = await parse(await fetch(`${BASE}/chat/session`, { method: "POST" }));
  saveSession(s);
  return s;
}

export async function ensureSession(): Promise<Session> {
  return loadSession() ?? createSession();
}

/** Authenticated request. If the stored session is unknown/expired, mint a new one and retry once. */
type Init = RequestInit | ((s: Session) => { path?: string; init: RequestInit });

async function authed(path: string, initOrBuilder: Init = {}, retry = true): Promise<any> {
  const s = await ensureSession();
  // A builder lets callers put the (possibly re-minted) session id into the path/body.
  const built = typeof initOrBuilder === "function" ? initOrBuilder(s) : { init: initOrBuilder };
  const init = built.init;
  path = built.path ?? path;
  const headers = new Headers(init.headers);
  headers.set("X-Session-Id", s.session_id);
  headers.set("X-Session-Token", s.token);
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (retry && (res.status === 401 || res.status === 404 || res.status === 409)) {
    saveSession(null);
    return authed(path, initOrBuilder, false);
  }
  return parse(res);
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: (): Promise<Health> => fetch(`${BASE}/health`).then(parse),

  async history(): Promise<ChatMessage[]> {
    const data = await authed("", (s) => ({ path: `/chat/history?session_id=${encodeURIComponent(s.session_id)}`, init: {} }));
    return data.messages;
  },

  async send(message: string): Promise<{ answer: string; sources: Source[]; trace: Trace | null }> {
    // The body must carry the same session id as the headers, even if authed() had to mint a new session.
    return authed("/chat/message", (s) => ({ init: json({ session_id: s.session_id, message }) }));
  },

  async reset(): Promise<Session> {
    try {
      await authed("/chat/reset", { method: "POST" }, false);
    } catch {
      /* old session may already be gone - we still want a fresh one */
    }
    return createSession();
  },

  listDocuments: (): Promise<{ documents: DocInfo[] }> => authed("/documents"),
  deleteDocument: (id: string) => authed(`/documents/${id}`, { method: "DELETE" }),
  upload(file: File) {
    const form = new FormData();
    form.append("file", file);
    return authed("/documents/upload", { method: "POST", body: form });
  },

  seed: (): Promise<{ ingested: { filename: string; chunks: number }[] }> => authed("/lab/seed", { method: "POST" }),
  clearCorpus: () => authed("/lab/corpus", { method: "DELETE" }),
  labSearch: (body: {
    query: string;
    mode?: string;
    explain?: boolean;
    rrf_k?: number;
    retrieve_k?: number;
    top_k?: number;
  }): Promise<LabResult> => authed("/lab/search", json(body)),
  embeddingMap: (q?: string): Promise<EmbeddingMap> => authed(`/lab/embedding-map${q ? `?q=${encodeURIComponent(q)}` : ""}`),
};
