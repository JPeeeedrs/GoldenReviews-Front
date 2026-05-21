import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import TopicAnalysis from "../topics_analizers/topic_analysis.jsx";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <TopicAnalysis />
  </StrictMode>
);
