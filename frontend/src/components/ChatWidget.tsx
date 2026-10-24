import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import type { ChatMessage, Health } from "../types";
import { MessageList } from "./MessageList";
import { UploadPanel } from "./UploadPanel";
import { Welcome } from "./Welcome";

type Conn = "checking" | "ok" | "degraded" | "offline";

const DOT: Record<Conn, string> = {
  checking: "bg-white/60 animate-pulse",
  ok: "bg-emerald-300",
  degraded: "bg-amber-300",
  offline: "bg-red-400",
};

const CONN_LABEL: Record<Conn, string> = {
  checking: "בודק חיבור לשרת...",
  ok: "מחובר",
  degraded: "חיבור חלקי",
  offline: "השרת לא זמין",
};

const GRADIENT = "bg-gradient-to-br from-teal-500 to-sky-500";

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [conn, setConn] = useState<Conn>("checking");
  const [health, setHealth] = useState<Health | null>(null);

  // בדיקת חיבור (health) פעם אחת בלבד, בכל פתיחה של הווידג'ט. בלי polling ובלי בדיקה אחרי כל הודעה:
  // אם השרת נופל באמצע, כשל בשליחת הודעה מעדכן את המצב ל"לא זמין" בלי קריאה נוספת.
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
  }, [open, ping]);

  // היסטוריה: נטענת בכל פתיחה (מכסה גם רענון דף)
  useEffect(() => {
    if (!open) return;
    api
      .history()
      .then(setMessages)
      .catch(() => {
        /* השרת לא זמין: משאירים מה שיש */
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
      setConn((c) => (c === "offline" ? "ok" : c));
      setMessages((m) => [...m, { role: "assistant", content: r.answer, sources: r.sources, trace: r.trace }]);
    } catch (e: any) {
      if (e instanceof TypeError) setConn("offline"); // fetch נכשל ברמת הרשת: השרת לא ענה
      setMessages((m) => [...m, { role: "assistant", content: `משהו השתבש: ${e.message}`, error: true }]);
    } finally {
      setLoading(false);
    }
  };

  const newChat = async () => {
    await api.reset();
    setMessages([]);
  };

  // הווידג'ט בפינה השמאלית-תחתונה: באתר בעברית הפינה הימנית שמורה לתוכן.
  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        aria-label="פתח צ'אט"
        className={`fixed bottom-5 left-5 z-50 flex items-center gap-2 rounded-full ${GRADIENT} px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-teal-500/30 transition hover:scale-105`}
      >
        <span className="text-lg">🛰️</span> שאל אותי
      </button>
    );
  }

  return (
    <div className="fixed bottom-5 left-5 z-50 flex h-[640px] max-h-[88vh] w-[400px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-400/30">
      <header className={`flex items-center gap-3 ${GRADIENT} px-4 py-3 text-white`}>
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/25 text-xl">🛰️</div>
        <div className="leading-tight">
          <div className="text-base font-bold">DocuMind</div>
          <div className="flex items-center gap-1.5 text-[11px] text-white/85">
            <span className={`h-2 w-2 rounded-full ${DOT[conn]}`} />
            {CONN_LABEL[conn]}
          </div>
        </div>
        <div className="ms-auto flex gap-1 text-sm">
          <button className="rounded-lg px-2 py-1 hover:bg-white/20" onClick={() => setShowUpload(!showUpload)} title="העלאת מסמכים משלך">
            📎
          </button>
          <button className="rounded-lg px-2 py-1 hover:bg-white/20" onClick={newChat} title="שיחה חדשה (סשן חדש)">
            ↻ חדשה
          </button>
          <button className="rounded-lg px-2 py-1 hover:bg-white/20" onClick={() => setOpen(false)} title="סגירה">
            ✕
          </button>
        </div>
      </header>

      {conn === "offline" && <div className="bg-red-50 px-3 py-2 text-xs text-red-700">אי אפשר להתחבר לשרת. האם הפקודה docker compose up רצה?</div>}
      {health && !health.gemini_configured && (
        <div className="bg-amber-50 px-3 py-2 text-xs text-amber-800">GEMINI_API_KEY לא הוגדר, ולכן ההטמעות והתשובות ייכשלו. הוסף אותו לקובץ .env והפעל מחדש.</div>
      )}
      {showUpload && <UploadPanel />}

      <MessageList messages={messages} loading={loading} header={<Welcome />} />

      <div className="border-t border-slate-100 bg-white p-3">
        <form
          className="flex items-end gap-2 rounded-3xl border border-slate-200 bg-slate-50 p-1.5 transition focus-within:border-teal-400 focus-within:bg-white focus-within:shadow-sm"
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
        >
          <textarea
            dir="auto"
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
            placeholder="כתוב שאלה..."
            className="max-h-24 flex-1 resize-none bg-transparent px-3 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-400"
          />
          <button
            aria-label="שלח"
            disabled={loading || !input.trim() || conn === "offline"}
            className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${GRADIENT} text-white transition hover:scale-105 disabled:opacity-40 disabled:hover:scale-100`}
          >
            <span className="rotate-180">➤</span>
          </button>
        </form>
        <p className="mt-2 text-center text-[10px] text-slate-400">התשובות נוצרות על ידי AI מתוך המסמכים שבמאגר, ומומלץ לוודא לפני שנסמכים עליהן.</p>
      </div>
    </div>
  );
}
