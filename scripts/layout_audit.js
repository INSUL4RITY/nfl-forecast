// Layout audit for the nflcast site. Paste into the browser console on the site's origin (local build or live), or run via
// the browser tool. For every page it loads the page in a hidden same-origin iframe at each width (media queries apply to
// the iframe width), opens every <details> (collapsed content is only measurable when open), and reports:
//   page-hscroll         the page scrolls sideways
//   overflows-container  an element sticks out of its panel/card/column (and is not inside a horizontal scroll area)
// Usage: await nflcastLayoutAudit({ base: "/nfl-forecast", widths: [1280, 375] })  -> { checked, issues, byKind }
// (base = "" for a local build served at the root.) Results are also kept in window.__layoutAudit while it runs.
async function nflcastLayoutAudit({ base = "", widths = [1280, 375], limit = Infinity, pages = null } = {}) {
  const get = async (p) => (await fetch(`${base}${p}`)).json();
  if (!pages) {
    const m = await get("/data/manifest.json");
    pages = ["/", "/performance/", "/methodology/", "/ratings/", "/about/"];
    for (const w of m.weeks) {
      pages.push(`/week/${w.season}/${w.week}/`);
      const doc = await get(`/data/weeks/${w.season}-${String(w.week).padStart(2, "0")}.json`);
      for (const g of doc.games) pages.push(`/game/${g.game_id}/`);
    }
  }
  pages = pages.slice(0, limit);
  const CONTAINER = ".panel, .card, .pick-sec, .pick-box, .two-col > *, .three-col > *, .grid > *";
  const state = (window.__layoutAudit = { total: pages.length * widths.length, checked: 0, issues: [] });
  const frame = document.createElement("iframe");
  frame.style.cssText = "position:fixed;left:-10000px;top:0;height:900px;border:0;visibility:hidden";
  document.body.appendChild(frame);
  try {
    for (const width of widths) {
      frame.style.width = `${width}px`;
      for (const p of pages) {
        await new Promise((res) => { frame.onload = res; frame.src = `${base}${p}`; });
        const doc = frame.contentDocument, win = frame.contentWindow;
        doc.querySelectorAll("details").forEach((d) => { d.open = true; });   // collapsed content is only measurable when open
        const vw = win.innerWidth;
        if (doc.documentElement.scrollWidth > vw + 1)
          state.issues.push({ page: p, width, kind: "page-hscroll", detail: `${doc.documentElement.scrollWidth}px > ${vw}px` });
        const rects = new Map();
        const rectOf = (a) => { if (!rects.has(a)) rects.set(a, a.getBoundingClientRect()); return rects.get(a); };
        const seen = new Set();
        for (const el of doc.querySelectorAll("main *")) {
          const a = el.parentElement && el.parentElement.closest(CONTAINER);
          if (!a) continue;
          const r = el.getBoundingClientRect();
          if (!r.width || !r.height) continue;
          const ar = rectOf(a);
          const by = Math.round(Math.max(r.right - ar.right, ar.left - r.left));
          if (by <= 2) continue;
          let inScroller = false;                                           // styles checked only for overflowing elements
          for (let b = el.parentElement; b && b !== a; b = b.parentElement) {
            const o = win.getComputedStyle(b).overflowX;
            if (o === "auto" || o === "scroll" || o === "hidden") { inScroller = true; break; }
          }
          if (inScroller) continue;
          const head = (a.querySelector("h2,h3")?.textContent || "").slice(0, 40);
          const key = `${el.tagName}|${a.className}|${head}`;
          if (seen.has(key)) continue;
          seen.add(key);
          state.issues.push({ page: p, width, kind: "overflows-container", detail: `<${el.tagName.toLowerCase()}> "${el.textContent.trim().slice(0, 40)}" sticks out ${by}px of ${a.className || a.tagName} "${head}"` });
        }
        state.checked++;
      }
    }
  } finally {
    frame.remove();
  }
  const byKind = {};
  for (const i of state.issues) {
    const k = `${i.width}px ${i.kind}: ${i.detail.replace(/"[^"]*" sticks/, "… sticks").replace(/\d+px/g, "Npx")}`;
    byKind[k] = (byKind[k] || 0) + 1;
  }
  state.done = true;
  return { checked: state.checked, issues: state.issues.length, byKind, sample: state.issues.slice(0, 15) };
}
