import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { DocInfo } from "../types";

const ALLOWED = [".pdf", ".txt", ".docx"];
const MAX_MB = 10;

export function UploadPanel({ onChanged }: { onChanged?: () => void }) {
  const [docs, setDocs] = useState<DocInfo[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      setDocs((await api.listDocuments()).documents);
    } catch {
      /* השרת לא זמין: הכותרת של הווידג'ט כבר מראה את זה */
    }
  }, []);
  useEffect(() => {
    refresh();
  }, [refresh]);

  const done = (ok: boolean, text: string) => {
    setMsg({ ok, text });
    setBusy(null);
    refresh();
    onChanged?.();
  };

  const upload = async (file: File) => {
    const ext = "." + (file.name.split(".").pop() ?? "").toLowerCase();
    if (!ALLOWED.includes(ext)) return setMsg({ ok: false, text: "מותר להעלות רק קבצי PDF, TXT ו-DOCX." });
    if (file.size > MAX_MB * 1024 * 1024) return setMsg({ ok: false, text: `הקובץ גדול מ-${MAX_MB}MB.` });
    setBusy(`מחלק ל-chunks ויוצר embeddings עבור ${file.name}...`);
    setMsg(null);
    try {
      const r = await api.upload(file);
      done(true, `${r.filename}: ${r.chunks} קטעים נוספו לאינדקס (${r.elapsed_ms} אלפיות שנייה).`);
    } catch (e: any) {
      done(false, e.message);
    }
  };

  const seed = async () => {
    setBusy("יוצר embeddings למסמכי הדוגמה (כ-40 קטעים)...");
    setMsg(null);
    try {
      const r = await api.seed();
      done(true, `נטענו ${r.ingested.length} מסמכי דוגמה (חקר החלל).`);
    } catch (e: any) {
      done(false, e.message);
    }
  };

  const clearAll = async () => {
    if (!window.confirm("למחוק את כל הקטעים מהאינדקס?")) return;
    await api.clearCorpus();
    setMsg({ ok: true, text: "האינדקס נוקה." });
    refresh();
    onChanged?.();
  };

  const remove = async (d: DocInfo) => {
    await api.deleteDocument(d.doc_id);
    refresh();
    onChanged?.();
  };

  return (
    <div className="space-y-2 border-b border-slate-200 bg-white p-3 text-xs">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files[0];
          if (f) upload(f);
        }}
        onClick={() => input.current?.click()}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-3 text-center text-slate-600 ${drag ? "border-brand-400 bg-brand-50" : "border-slate-300 hover:bg-slate-100"}`}
      >
        גרור לכאן קובץ PDF / TXT / DOCX או לחץ לבחירה
        <input
          ref={input}
          type="file"
          hidden
          accept={ALLOWED.join(",")}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) upload(f);
            e.target.value = "";
          }}
        />
      </div>
      <div className="flex gap-2">
        <button className="btn-ghost flex-1" disabled={!!busy} onClick={seed}>
          טען מסמכי דוגמה
        </button>
        <button className="btn-ghost" disabled={!!busy || docs.length === 0} onClick={clearAll}>
          נקה הכל
        </button>
      </div>
      {busy && <div className="animate-pulse text-brand-700">{busy}</div>}
      {msg && <div className={msg.ok ? "text-emerald-600" : "text-red-600"}>{msg.text}</div>}
      {docs.length > 0 && (
        <ul className="max-h-24 space-y-0.5 overflow-auto">
          {docs.map((d) => (
            <li key={d.doc_id} className="flex items-center gap-2 text-slate-600">
              <span dir="ltr" className="truncate">
                {d.filename}
              </span>
              <span className="text-slate-400">{d.chunks} קטעים</span>
              <button className="ms-auto text-slate-400 hover:text-red-600" onClick={() => remove(d)} aria-label={`מחק ${d.filename}`}>
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
