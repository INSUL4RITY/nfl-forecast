// Every home/away pairing of current teams must get two distinct identity colours (web/lib/format.ts teamPairColors).
// Run: node scripts/check_team_colors.js  (exit 1 and a list on failure). Used by tests/test_team_colors.py.
const path = require("path");
const fs = require("fs");
const web = path.join(__dirname, "..", "web");
const ts = require(path.join(web, "node_modules", "typescript"));
const src = fs.readFileSync(path.join(web, "lib", "format.ts"), "utf8");
const js = ts.transpileModule(src, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText;
const mod = { exports: {} };
new Function("module", "exports", "require", js)(mod, mod.exports, require);
const { teamPairColors, distinctColors } = mod.exports;
const teams = JSON.parse(fs.readFileSync(path.join(web, "public", "data", "teams.json"), "utf8"));
const OLD_NAMES = new Set(["OAK", "SD", "STL", "LAR"]);          // former names / aliases of current teams
const cur = Object.keys(teams).filter((k) => !OLD_NAMES.has(k));
const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
const bad = [];
let n = 0;
for (const H of cur) for (const A of cur) {
  if (H === A) continue;
  n++;
  const p = teamPairColors(teams[H], teams[A]);
  if (!distinctColors(rgb(p.home), rgb(p.away))) bad.push(`${A}@${H} ${p.away}/${p.home}`);
}
console.log(`${n} pairings, ${bad.length} with colours that look alike`);
if (bad.length) { console.log(bad.join("\n")); process.exit(1); }
