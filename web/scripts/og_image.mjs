// Builds web/public/og.png (1200x630), the social preview image (Open Graph / Twitter). Run: node scripts/og_image.mjs
import { writeFileSync } from "node:fs";
import React from "react";
import { ImageResponse } from "next/dist/compiled/@vercel/og/index.node.js";

const h = React.createElement;
const BG = "#0e131b", SURFACE = "#161d29", INK = "#e8edf5", INK2 = "#a9b4c6", RULE = "#283142", BLUE = "#3d6db5";
const lines = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((i) =>
  h("div", { key: i, style: { position: "absolute", left: 90 + i * 102, top: 0, width: 2, height: 630, background: RULE } }));
const mark = h("svg", { width: 88, height: 88, viewBox: "0 0 28 28" },
  h("rect", { x: 1, y: 1, width: 26, height: 26, rx: 6, fill: "#1f4e8c" }),
  h("path", { d: "M7 5v18M14 5v18M21 5v18", stroke: BLUE, strokeWidth: 1.5 }),
  h("path", { d: "M5 19l6-5 5 3 7-9", stroke: "#fff", strokeWidth: 2.4, fill: "none", strokeLinecap: "round", strokeLinejoin: "round" }));
const trend = h("svg", { width: 1200, height: 630, viewBox: "0 0 1200 630", style: { position: "absolute", left: 0, top: 0 } },
  h("path", { d: "M60 560 L300 470 L470 505 L690 380 L880 410 L1140 250", stroke: BLUE, strokeWidth: 6, fill: "none",
    strokeLinecap: "round", strokeLinejoin: "round", opacity: 0.55 }));
const el = h("div", { style: { width: 1200, height: 630, display: "flex", position: "relative", background: BG, fontFamily: "Geist" } },
  ...lines, trend,
  h("div", { style: { position: "absolute", left: 80, top: 90, display: "flex", flexDirection: "column", gap: 26 } },
    h("div", { style: { display: "flex", alignItems: "center", gap: 28 } }, mark,
      h("div", { style: { display: "flex", flexDirection: "column" } },
        h("div", { style: { fontSize: 76, fontWeight: 800, letterSpacing: 6, color: INK } }, "INSULARITY"),
        h("div", { style: { fontSize: 40, color: INK2, marginTop: -4 } }, "NFL Forecast"))),
    h("div", { style: { fontSize: 36, color: INK, maxWidth: 900, lineHeight: 1.3, marginTop: 30 } },
      "Model lines, totals and win probabilities for every NFL game, set against the market line."),
    h("div", { style: { display: "flex", fontSize: 26, color: INK2, background: SURFACE, border: `2px solid ${RULE}`,
      borderRadius: 14, padding: "12px 22px", marginTop: 10 } },
      "Timestamped before kickoff · validated openly · for analysis and education only")));
const res = new ImageResponse(el, { width: 1200, height: 630 });
writeFileSync(new URL("../public/og.png", import.meta.url), Buffer.from(await res.arrayBuffer()));
console.log("wrote public/og.png");
