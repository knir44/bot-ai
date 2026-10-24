import { ReactNode, useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";
import { Avatar } from "./Welcome";

const NEAR_BOTTOM_PX = 80;

export function MessageList({ messages, loading, header }: { messages: ChatMessage[]; loading: boolean; header?: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [atBottom, setAtBottom] = useState(true);

  const scrollToBottom = (smooth = true) => {
    const el = ref.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
  };

  const onScroll = () => {
    const el = ref.current;
    if (el) setAtBottom(el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX);
  };

  // גלילה אוטומטית להודעה חדשה, אבל רק אם המשתמש כבר בתחתית או שההודעה החדשה היא שלו.
  // לעולם לא "מושכים" למטה מי שגלל למעלה כדי לקרוא.
  useEffect(() => {
    const last = messages[messages.length - 1];
    if (atBottom || last?.role === "user") scrollToBottom();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, loading]);

  return (
    <div className="relative min-h-0 flex-1">
      <div ref={ref} onScroll={onScroll} className="h-full space-y-3 overflow-y-auto bg-gradient-to-b from-sky-50 to-white p-3">
        {header}
        {messages.map((m, i) => (
          <MessageBubble key={m.id ?? i} m={m} />
        ))}
        {loading && (
          <div className="flex items-start gap-2">
            <Avatar />
            <div className="rounded-2xl rounded-ss-sm border border-slate-100 bg-white px-3 py-2 text-sm text-slate-500 shadow-sm">
              מחפש במסמכים וחושב<span className="animate-pulse">...</span>
            </div>
          </div>
        )}
      </div>
      {!atBottom && (
        <button
          onClick={() => scrollToBottom()}
          aria-label="גלול למטה"
          className="absolute bottom-3 end-4 flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 shadow-md hover:bg-slate-50"
        >
          ↓
        </button>
      )}
    </div>
  );
}
