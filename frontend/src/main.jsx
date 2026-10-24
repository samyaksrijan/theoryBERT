import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { MotionConfig } from "motion/react";
import "@fontsource-variable/manrope";
import "@fontsource-variable/dm-sans";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/instrument-serif/400-italic.css";
import App from "./App";
import { Startup } from "./components/Brand";
import "./styles.css";
import "./readability.css";
import "./workspace-theme.css";
import "./landing.css";
import "./brand.css";

createRoot(document.getElementById("root")).render(
  <BrowserRouter>
    <MotionConfig reducedMotion="user">
      <Startup>
        <App />
      </Startup>
    </MotionConfig>
  </BrowserRouter>,
);
