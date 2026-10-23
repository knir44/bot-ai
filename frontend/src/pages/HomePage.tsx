import { Link } from "react-router-dom";

const STEPS = [
  ["1. Chunk", "Documents are cut into ~800-character overlapping pieces, so each piece is about one thing."],
  ["2. Embed + index", "Each chunk becomes a 768-number vector (Gemini) and is stored in Elasticsearch next to its text."],
  ["3. Retrieve", "A question is searched twice: BM25 (keywords) and kNN (meaning). Two ranked lists."],
  ["4. Fuse (RRF)", "Reciprocal Rank Fusion merges the lists using ranks only: score = Σ 1/(60 + rank)."],
  ["5. Generate", "The top 5 chunks go into a prompt; Gemini answers using only them and cites [1], [2]..."],
];

export function HomePage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6 pb-28">
      <section className="space-y-2">
        <h1 className="text-3xl font-bold">DocuMind RAG</h1>
        <p className="text-slate-600">
          A Retrieval-Augmented Generation system built to <b>show its work</b>. Open the chat bubble (bottom-right), load the sample Space Exploration corpus, ask a question, then press <i>“How did I answer?”</i>
          under any reply to see every step.
        </p>
        <Link to="/lab" className="btn-primary inline-flex">
          Open the RAG Lab →
        </Link>
      </section>

      <section className="card divide-y divide-slate-100">
        {STEPS.map(([title, text]) => (
          <div key={title} className="flex gap-4 p-3 text-sm">
            <div className="w-32 shrink-0 font-semibold text-brand-700">{title}</div>
            <div className="text-slate-600">{text}</div>
          </div>
        ))}
      </section>

      <section className="text-sm text-slate-600">
        <h2 className="mb-1 font-semibold text-slate-800">Things to try</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            Ask <i>“Which robot flew a small aircraft on another planet?”</i> - no word overlaps with the answer, so vectors find it, BM25 does not.
          </li>
          <li>
            Ask <i>“Lovell Swigert Haise”</i> - names are BM25 territory.
          </li>
          <li>Ask a follow-up (“When did it launch?”) and look at how the question was rewritten.</li>
          <li>Upload your own PDF and ask about it.</li>
        </ul>
      </section>
    </div>
  );
}
