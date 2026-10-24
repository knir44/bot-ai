import { NavLink, Route, Routes } from "react-router-dom";
import { ChatWidget } from "./components/ChatWidget";
import { HomePage } from "./pages/HomePage";
import { LabPage } from "./pages/LabPage";

const link = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium ${isActive ? "bg-brand-500 text-white" : "text-slate-600 hover:bg-slate-100"}`;

export default function App() {
  return (
    <>
      <nav className="sticky top-0 z-40 flex items-center gap-2 border-b border-slate-200 bg-white/90 px-4 py-2 backdrop-blur">
        <span className="me-4 font-bold text-brand-700">🛰️ DocuMind</span>
        <NavLink to="/" end className={link}>
          בית
        </NavLink>
        <NavLink to="/lab" className={link}>
          מעבדת RAG
        </NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/lab" element={<LabPage />} />
      </Routes>
      <ChatWidget />
    </>
  );
}
