import { Link } from "react-router-dom";

const STEPS = [
  ["1. חלוקה (Chunking)", "המסמכים נחתכים לקטעים חופפים של כ-800 תווים, כך שכל קטע עוסק בנושא אחד."],
  ["2. Embedding ואינדוקס", "כל קטע הופך לוקטור של 768 מספרים (Gemini) ונשמר ב-Elasticsearch לצד הטקסט שלו."],
  ["3. שליפה (Retrieval)", "השאלה מחופשת פעמיים: BM25 (מילות מפתח) ו-kNN (משמעות). יוצאות שתי רשימות מדורגות."],
  ["4. איחוד (RRF)", "Reciprocal Rank Fusion מאחד את הרשימות לפי דירוג בלבד: ציון = Σ 1/(60 + דירוג)."],
  ["5. יצירה (Generation)", "חמשת הקטעים המובילים נכנסים לפרומפט, ו-Gemini עונה רק מהם ומצטט [1], [2]..."],
];

export function HomePage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6 pb-28">
      <section className="space-y-3">
        <h1 className="text-3xl font-bold text-slate-800">DocuMind RAG</h1>
        <p className="leading-relaxed text-slate-600">
          מערכת Retrieval-Augmented Generation שנבנתה כדי <b className="text-brand-700">להראות איך היא עובדת</b>. פתח את בועת הצ'אט (בפינה השמאלית-תחתונה), טען את מסמכי הדוגמה בנושא חקר החלל, שאל שאלה, ואז לחץ על <i>«איך עניתי?»</i> מתחת לכל תשובה
          כדי לראות כל שלב.
        </p>
        <Link to="/lab" className="btn-primary inline-flex">
          פתח את מעבדת ה-RAG ←
        </Link>
      </section>

      <section className="card divide-y divide-slate-200">
        {STEPS.map(([title, text]) => (
          <div key={title} className="flex gap-4 p-3 text-sm">
            <div className="w-40 shrink-0 font-semibold text-brand-700">{title}</div>
            <div className="text-slate-600">{text}</div>
          </div>
        ))}
      </section>

      <section className="text-sm text-slate-600">
        <h2 className="mb-1 font-semibold text-slate-800">דברים לנסות</h2>
        <ul className="list-disc space-y-1 ps-5">
          <li>
            שאל <i dir="ltr">“Which robot flew a small aircraft on another planet?”</i> - אין אף מילה משותפת עם התשובה, ולכן הווקטורים ימצאו אותה ו-BM25 לא.
          </li>
          <li>
            שאל <i dir="ltr">“Lovell Swigert Haise”</i> - שמות הם הטריטוריה של BM25.
          </li>
          <li>שאל בעברית: «איזה רובוט הטיס מסוק על מאדים?». המסמכים באנגלית, והחיפוש הווקטורי הרב-לשוני עדיין ימצא אותם.</li>
          <li>שאל שאלת המשך («מתי זה שוגר?») והסתכל איך השאלה נוסחה מחדש.</li>
          <li>העלה PDF משלך ושאל עליו.</li>
        </ul>
      </section>
    </div>
  );
}
