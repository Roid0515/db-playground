import { Navigate, Route, Routes } from "react-router-dom";
import { ComparisonPage } from "./features/comparison/ComparisonPage";
import { Dashboard } from "./features/dashboard/Dashboard";
import { MongoPage } from "./features/mongo/MongoPage";
import { NotesPage } from "./features/notes/NotesPage";
import { PerformancePage } from "./features/performance/PerformancePage";
import { RelationalPage } from "./features/relational/RelationalPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/relational" element={<RelationalPage />} />
      <Route path="/mongodb" element={<MongoPage />} />
      <Route path="/comparison" element={<ComparisonPage />} />
      <Route path="/performance" element={<PerformancePage />} />
      <Route path="/notes" element={<NotesPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}