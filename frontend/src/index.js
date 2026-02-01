import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import App from "./App";

console.log("Frontend index.js mounting...");

const root = ReactDOM.createRoot(document.getElementById("root"));
try {
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
  console.log("Frontend mounted.");
} catch (e) {
  console.error("Frontend mount error:", e);
}
