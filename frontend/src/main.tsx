import React from "react";
import ReactDOM from "react-dom/client";

// Bundled Noto Sans fonts (Latin + Devanagari subsets for offline operation)
import "@fontsource/noto-sans/400.css";
import "@fontsource/noto-sans/500.css";
import "@fontsource/noto-sans/600.css";
import "@fontsource/noto-sans/700.css";
import "@fontsource/noto-sans-devanagari/400.css";
import "@fontsource/noto-sans-devanagari/500.css";
import "@fontsource/noto-sans-devanagari/600.css";
import "@fontsource/noto-sans-devanagari/700.css";

// UX4G Design System 3.0 styles, EduTrace tokens, and runtime
import "ux4g-web-components/styles.css";
import "./styles/tokens.css";
import "ux4g-web-components/design-system";

import { applyDomSettings, loadInitialSettings } from "./context/accessibilityUtils";

// Initialize UX4G theme and DOM settings immediately before mount
applyDomSettings(loadInitialSettings());

import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

