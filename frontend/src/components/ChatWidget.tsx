import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { ChatMessage, Health } from "../types";
import { MessageList } from "./MessageList";
import { UploadPanel } from "./UploadPanel";

type Conn = "checking" | "ok" | "degraded" | "offline";

const DOT: Record<Conn, string> = {
  checking: "bg-slate-300 animate-pulse",
  ok: "bg-emerald-500",
  degraded: "bg-amber-500",
  offline: "bg-red-500",
};

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [conn, setConn] = useState<Conn>("checking");
  const [health, setHealth] = useState<Health | null>(null);

  // --- health ping: on open, then every 30 s while open
  const ping = useCallback(async () => {
    try {
      const h = await api.health();
      setHealth(h);
      setConn(h.status === "ok" ? "ok" : "degraded");
    } catch {
      setHealth(null);
      setConn("offline");
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    setConn("checking");
    ping();
    const t = setInterval(ping, 30000);
    return () => clearInterval(t);
  }, [open, ping]);

  // --- history: reload whenever the widget opens (also covers page refresh)
  useEffect(() => {
    if (!open) return;
    api
      .history()
      .then(setMessages)
      .catch(() => {
        /* offline: keep what we have */
      });
  }, [open]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const r = await api.send(text);
      setMessages((m) => [...m, { role: "assistant", content: r.answer, sources: r.sources, trace: r.trace }]);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `Something went wrong: ${e.message}`, error: true }]);
    } finally {
      setLoading(false);
      ping(); // refresh the chunk counter too
    }
  };

  const newChat = async () => {
    await api.reset();
    setMessages([]);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        aria-label="Open chat"
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-brand-600 text-2xl text-white shadow-lg hover:bg-brand-700"
      >
        💬
      </button>
    );
  }

  return (
    <div className="fixed bottom-5 right-5 z-50 flex h-[640px] max-h-[88vh] w-[400px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
      <header className="flex items-center gap-2 bg-brand-600 px-3 py-2 text-white">
        <span className={`h-2.5 w-2.5 rounded-full ring-2 ring-white/60 ${DOT[conn]}`} title={`Backend: ${conn}`} />
        <div className="leading-tight">
          <div className="text-sm font-semibold">DocuMind RAG</div>
          <div className="text-[10px] opacity-80">
            {conn === "offline" ? "backend unreachable" : health ? `${health.indexed_chunks} chunks indexed` : "connecting..."}
          </div>
        </div>
        <div className="ml-auto flex gap-1 text-sm">
          <button className="rounded px-2 py-1 hover:bg-white/20" onClick={() => setShowUpload(!showUpload)} title="Upload documents">
            📎
          </button>
          <button className="rounded px-2 py-1 hover:bg-white/20" onClick={newChat} title="New chat (fresh session)">
            ↻ New
          </button>
          <button className="rounded px-2 py-1 hover:bg-white/20" onClick={() => setOpen(false)} title="Close">
            ✕
          </button>
        </div>
      </header>

      {conn === "offline" && <div className="bg-red-50 px-3 py-2 text-xs text-red-700">Cannot reach the backend. Is `docker compose up` running?</div>}
      {health && !health.gemini_configured && (
        <div className="bg-amber-50 px-3 py-2 text-xs text-amber-800">GEMINI_API_KEY is not set - embeddings and answers will fail. Add it to .env and restart.</div>
      )}
      {showUpload && <UploadPanel onChanged={ping} />}

      <MessageList messages={messages} loading={loading} />

      <form
        className="flex items-end gap-2 border-t border-slate-200 bg-white p-2"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          maxLength={2000}
          rows={1}
          placeholder="Ask about your documents..."
          className="max-h-28 flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
        />
        <button className="btn-primary h-9" disabled={loading || !input.trim() || conn === "offline"}>
          Send
        </button>
      </form>
    </div>
  );
}
