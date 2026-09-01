import { Navigate, Route, Routes } from "react-router-dom";
import { Dashboard } from "./features/dashboard/Dashboard";
import { RelationalPage } from "./features/relational/RelationalPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/relational" element={<RelationalPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}