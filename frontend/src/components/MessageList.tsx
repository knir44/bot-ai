import { useEffect, useRef, useState } from "react";
import type { ChatMessage } from "../types";
import { MessageBubble } from "./MessageBubble";

const NEAR_BOTTOM_PX = 80;

export function MessageList({ messages, loading }: { messages: ChatMessage[]; loading: boolean }) {
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

  // Auto-scroll on new content - but only if the user is already at the bottom,
  // or the newest message is their own. Never yank someone who scrolled up to read.
  useEffect(() => {
    const last = messages[messages.length - 1];
    if (atBottom || last?.role === "user") scrollToBottom();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, loading]);

  return (
    <div className="relative min-h-0 flex-1">
      <div ref={ref} onScroll={onScroll} className="h-full space-y-3 overflow-y-auto bg-slate-50 p-3">
        {messages.length === 0 && !loading && (
          <p className="pt-6 text-center text-sm text-slate-400">
            Load the sample corpus (paperclip icon), then ask something like
            <br />
            <i>“Which robot flew a helicopter on Mars?”</i>
          </p>
        )}
        {messages.map((m, i) => (
          <MessageBubble key={m.id ?? i} m={m} />
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-3 py-2 text-sm text-slate-400">
              Retrieving &amp; thinking<span className="animate-pulse">...</span>
            </div>
          </div>
        )}
      </div>
      {!atBottom && (
        <button
          onClick={() => scrollToBottom()}
          aria-label="Scroll to bottom"
          className="absolute bottom-3 right-4 flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 shadow-md hover:bg-slate-100"
        >
          ↓
        </button>
      )}
    </div>
  );
}
