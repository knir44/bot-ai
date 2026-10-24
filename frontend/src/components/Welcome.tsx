import { useState } from "react";

/** הודעת הפתיחה הקבועה. היא קיימת רק בממשק: לא נשמרת ב-Postgres, ונשארת גם אחרי "שיחה חדשה". */
export const WELCOME_TEXT =
  "שלום! אני DocuMind, עוזר הידע שלך 🛰️ מאגר הידע שלי כבר טעון במסמכים על חקר החלל (הם באנגלית, אבל אפשר לשאול אותי גם בעברית), ואני עונה רק על סמך המסמכים ומציין מאיפה לקחתי כל תשובה. אפשר גם להעלות מסמכים משלך דרך 📎. ומתחת לכל תשובה לחיצה על «איך עניתי?» תראה לך איך המערכת מצאה אותה. מה תרצה לדעת?";

export function Avatar() {
  return <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-lg shadow-sm ring-2 ring-teal-300">🛰️</div>;
}

export function Welcome() {
  // שעת פתיחת הווידג'ט, כמו תווית "נשלח ב-17:36" בצ'אט שירות אמיתי.
  const [time] = useState(() => new Date().toLocaleTimeString("he-IL", { hour: "2-digit", minute: "2-digit" }));
  return (
    <div className="flex items-start gap-2">
      <Avatar />
      <div className="min-w-0">
        <div className="rounded-2xl rounded-ss-sm border border-slate-100 bg-white px-3 py-2 text-sm leading-relaxed text-slate-800 shadow-sm">{WELCOME_TEXT}</div>
        <div className="mt-1 px-1 text-[11px] text-slate-400">DocuMind · {time}</div>
      </div>
    </div>
  );
}
