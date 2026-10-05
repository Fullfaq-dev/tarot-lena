import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { consumeRobokassaReturn } from "./payReturn";
import "./styles.css";

consumeRobokassaReturn();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
