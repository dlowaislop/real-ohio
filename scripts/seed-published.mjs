// One-time migration for the publish-state change (Nov 15, 2026).
// Before this change, publishing in /masthead wrote status "published"
// into the draft article file itself. After it, publish state lives only
// in data/published.json (gitignored) and the draft file is left alone.
// Run this ONCE on popcorn, BEFORE git pull, if any articles were
// published with the old server: it records the current file statuses
// into data/published.json so those articles stay published after the
// pull reverts their files to drafts.
//
//   cd /root/work/real-ohio
//   bun scripts/seed-published.mjs
//
// Safe to run again or on a fresh checkout: it only adds entries for
// articles whose file status is "published" and never removes any.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const ARTICLES_DIR = path.join(ROOT, "articles");
const PUBLISHED_PATH = path.join(ROOT, "data", "published.json");

let state = {};
try {
  state = JSON.parse(fs.readFileSync(PUBLISHED_PATH, "utf8"));
} catch { /* no state yet */ }

let seeded = 0;
for (const f of fs.readdirSync(ARTICLES_DIR).filter((x) => x.endsWith(".json"))) {
  const a = JSON.parse(fs.readFileSync(path.join(ARTICLES_DIR, f), "utf8"));
  if (a.status === "published" && !state[a.slug]) {
    state[a.slug] = { published: true, by: "seed-published.mjs", at: new Date().toISOString() };
    seeded++;
  }
}
fs.mkdirSync(path.join(ROOT, "data"), { recursive: true });
fs.writeFileSync(PUBLISHED_PATH, JSON.stringify(state, null, 2) + "\n");
const published = Object.entries(state).filter(([, v]) => v.published).map(([s]) => s);
console.log(`Seeded ${seeded} article(s). Published now: ${published.length ? published.join(", ") : "(none)"}`);
