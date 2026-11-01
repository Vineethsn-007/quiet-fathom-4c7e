import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Overview from "./pages/Overview";
import Explorer from "./pages/Explorer";
import Accuracy from "./pages/Accuracy";
import Revisions from "./pages/Revisions";
import Methodology from "./pages/Methodology";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/explorer" element={<Explorer />} />
        <Route path="/accuracy" element={<Accuracy />} />
        <Route path="/revisions" element={<Revisions />} />
        <Route path="/methodology" element={<Methodology />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
