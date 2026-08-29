import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { I18nProvider } from "./context/I18nContext";
import { ThemeProvider } from "./context/ThemeContext";
import "./styles/global.css";
import "./styles/masteacon-shell.css";
import "./styles/masteacon-auth.css";
import "./styles/masteacon-landing.css";
import "./styles/masteacon-overview.css";
import "./styles/masteacon-library.css";
import "./styles/masteacon-chat.css";
import "./styles/masteacon-agent.css";
import "./styles/masteacon-workspaces.css";
import "./styles/masteacon-observability.css";
import "./styles/masteacon-polish.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider>
      <I18nProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </I18nProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
