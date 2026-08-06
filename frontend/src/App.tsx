import { Navigate, Route, Routes } from "react-router-dom";
import { Dashboard } from "./features/dashboard/Dashboard";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}