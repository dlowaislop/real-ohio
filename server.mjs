// Real Ohio admin server — drafts, editing, publishing.
// Run: PORT=3016 bun run server.mjs   (or: bun run server.mjs)
// No dependencies, Bun or Node. Serves /masthead (the editor UI) and /api/*.
// Public site stays static: Apache serves index.html and proxies
// /masthead and /api to this server (see DEPLOY.md).
// Auth: cookie session, 12h. Only CLI-created users (scripts/users.mjs)
// can log in; there is no signup. Passwords are scrypt hashes in
// data/users.json (see server/auth.mjs).
// Writes: articles are articles/*.json with status "draft" | "published".
// After every write this server runs `python3 build.py`, which rebuilds
// the public index.html from published articles only — so publishing is
// what makes an article appear on the public site. Drafts never appear.
import { execFileSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { checkLogin } from "./server/auth.mjs";

const ROOT = path.dirname(fileURLToPath(import.meta.url)); // server.mjs lives at the repo root
const ARTICLES_DIR = path.join(ROOT, "articles");
const config = JSON.parse(fs.readFileSync(path.join(ROOT, "config.json"), "utf8"));
const PORT = Number(process.env.PORT || config.admin_port || 3016);
const ADMIN_PATH = config.admin_path || "/masthead";
const SESSION_TTL_MS = 12 * 60 * 60 * 1000;
const sessions = new Map(); // token -> { username, expires }

function slugOk(s) {
  return typeof s === "string" && /^[a-z0-9][a-z0-9-]{2,80}$/.test(s);
}
function articlePath(slug) {
  return path.join(ARTICLES_DIR, `${slug}.json`);
}
// Article files on disk are date-prefixed (2026-11-12-microsoft-365-outage.json)
// but the slug field inside is just "microsoft-365-outage" — and that is
// what the editor list sends back. So resolve by the slug field, not the
// filename, falling back to the plain <slug>.json name for older files.
function findArticlePath(slug) {
  if (fs.existsSync(articlePath(slug))) return articlePath(slug);
  for (const f of fs.readdirSync(ARTICLES_DIR).filter((x) => x.endsWith(".json"))) {
    try {
      const a = JSON.parse(fs.readFileSync(path.join(ARTICLES_DIR, f), "utf8"));
      if (a.slug === slug) return path.join(ARTICLES_DIR, f);
    } catch { /* skip unreadable files */ }
  }
  return null;
}
function listArticles() {
  return fs
    .readdirSync(ARTICLES_DIR)
    .filter((f) => f.endsWith(".json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(ARTICLES_DIR, f), "utf8")))
    .sort((a, b) => (a.date < b.date ? 1 : -1));
}
function rebuild() {
  execFileSync("python3", ["build.py"], { cwd: ROOT, stdio: "pipe" });
}
function sendJson(res, code, obj, extraHeaders = {}) {
  const body = JSON.stringify(obj);
  res.writeHead(code, { "content-type": "application/json", ...extraHeaders });
  res.end(body);
}
function parseCookies(req) {
  const out = {};
  for (const part of (req.headers.cookie || "").split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k) out[k] = decodeURIComponent(v.join("="));
  }
  return out;
}
function authedUser(req) {
  const token = parseCookies(req).realohio_session;
  if (!token) return null;
  const s = sessions.get(token);
  if (!s || s.expires < Date.now()) {
    sessions.delete(token);
    return null;
  }
  return s.username;
}
async function readBody(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  const text = Buffer.concat(chunks).toString("utf8");
  return text ? JSON.parse(text) : {};
}
function splitParas(text) {
  return String(text || "")
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}
function parseQuotes(text) {
  return String(text || "")
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      const i = line.indexOf("|");
      if (i < 0) return { speaker: "", quote: line };
      return { speaker: line.slice(0, i).trim(), quote: line.slice(i + 1).trim() };
    })
    .filter((q) => q.quote);
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  const pathname = url.pathname;

  // --- Admin UI ---
  if ((pathname === ADMIN_PATH || pathname === `${ADMIN_PATH}/`) && req.method === "GET") {
    const html = fs.readFileSync(path.join(ROOT, "server", "admin.html"), "utf8");
    res.writeHead(200, { "content-type": "text/html" });
    res.end(html);
    return;
  }

  if (!pathname.startsWith("/api/")) {
    sendJson(res, 404, { error: "not found" });
    return;
  }

  try {
    // --- Login (no auth needed) ---
    if (pathname === "/api/login" && req.method === "POST") {
      const { username, password } = await readBody(req);
      if (!username || !checkLogin(username, password || "")) {
        sendJson(res, 401, { error: "Invalid username or password." });
        return;
      }
      const token = randomBytes(32).toString("hex");
      sessions.set(token, { username, expires: Date.now() + SESSION_TTL_MS });
      sendJson(res, 200, { ok: true, username }, {
        "set-cookie": `realohio_session=${token}; HttpOnly; Path=/; SameSite=Lax; Max-Age=${SESSION_TTL_MS / 1000}`,
      });
      return;
    }
    if (pathname === "/api/logout" && req.method === "POST") {
      sessions.delete(parseCookies(req).realohio_session);
      sendJson(res, 200, { ok: true }, { "set-cookie": "realohio_session=; HttpOnly; Path=/; Max-Age=0" });
      return;
    }

    const user = authedUser(req);
    if (!user) {
      sendJson(res, 401, { error: "Please log in." });
      return;
    }
    if (pathname === "/api/me" && req.method === "GET") {
      sendJson(res, 200, { username: user });
      return;
    }

    // --- Articles ---
    if (pathname === "/api/articles" && req.method === "GET") {
      sendJson(res, 200, { articles: listArticles() });
      return;
    }
    if (pathname === "/api/articles" && req.method === "POST") {
      const body = await readBody(req);
      const slug = (body.slug || "").trim();
      if (!slugOk(slug)) {
        sendJson(res, 400, { error: "Slug must be lowercase letters, digits, dashes, e.g. 2026-11-20-my-story (use the article slug, not the filename date)." });
        return;
      }
      if (findArticlePath(slug)) {
        sendJson(res, 409, { error: `An article with slug "${slug}" already exists.` });
        return;
      }
      const now = new Date().toISOString();
      const article = {
        id: body.date ? `${body.date}-${slug}` : slug,
        slug,
        date: body.date || now.slice(0, 10),
        status: "draft",
        headline: body.headline || "Untitled draft",
        dek: body.dek || "",
        ohio_town: body.ohio_town || "",
        real_event_date: body.real_event_date || "",
        real_summary: splitParas(body.real_summary),
        ohio_story: splitParas(body.ohio_story),
        ohio_quotes: parseQuotes(body.ohio_quotes_text),
        source_name: body.source_name || "",
        source_url: body.source_url || "",
        source_note: body.source_note || "",
        disclaimer: "Parody: the Ohio family in this story is fictional. The underlying news event is real and sourced.",
        author: user,
        updated_at: now,
      };
      fs.mkdirSync(ARTICLES_DIR, { recursive: true });
      // Date-prefixed filename, matching the existing articles on disk.
      fs.writeFileSync(path.join(ARTICLES_DIR, `${article.date}-${slug}.json`), JSON.stringify(article, null, 2) + "\n");
      rebuild();
      sendJson(res, 201, { article });
      return;
    }

    const m = pathname.match(/^\/api\/articles\/([^/]+)(\/(publish|unpublish))?$/);
    if (m) {
      const slug = decodeURIComponent(m[1]);
      const action = m[3];
      const file = slugOk(slug) ? findArticlePath(slug) : null;
      if (!file) {
        sendJson(res, 404, { error: "No such article." });
        return;
      }
      if (req.method === "GET" && !action) {
        sendJson(res, 200, { article: JSON.parse(fs.readFileSync(file, "utf8")) });
        return;
      }
      if (req.method === "PUT" && !action) {
        const body = await readBody(req);
        const article = JSON.parse(fs.readFileSync(file, "utf8"));
        for (const k of ["headline", "dek", "ohio_town", "date", "real_event_date", "source_name", "source_url", "source_note"]) {
          if (typeof body[k] === "string") article[k] = body[k];
        }
        if (typeof body.real_summary === "string") article.real_summary = splitParas(body.real_summary);
        if (typeof body.ohio_story === "string") article.ohio_story = splitParas(body.ohio_story);
        if (typeof body.ohio_quotes_text === "string") article.ohio_quotes = parseQuotes(body.ohio_quotes_text);
        article.author = user;
        article.updated_at = new Date().toISOString();
        fs.writeFileSync(file, JSON.stringify(article, null, 2) + "\n");
        rebuild();
        sendJson(res, 200, { article });
        return;
      }
      if (req.method === "POST" && (action === "publish" || action === "unpublish")) {
        const article = JSON.parse(fs.readFileSync(file, "utf8"));
        if (action === "publish" && (!article.headline || !article.real_summary?.length || !article.ohio_story?.length)) {
          sendJson(res, 400, { error: "Cannot publish: fill in a headline, at least one real-summary paragraph, and at least one Ohio paragraph first." });
          return;
        }
        article.status = action === "publish" ? "published" : "draft";
        article.author = user;
        article.updated_at = new Date().toISOString();
        fs.writeFileSync(file, JSON.stringify(article, null, 2) + "\n");
        rebuild();
        sendJson(res, 200, { article });
        return;
      }
      if (req.method === "DELETE" && !action) {
        fs.unlinkSync(file);
        rebuild();
        sendJson(res, 200, { ok: true });
        return;
      }
    }

    sendJson(res, 404, { error: "not found" });
  } catch (e) {
    console.error(e);
    sendJson(res, 500, { error: e.message || "Server error." });
  }
});

server.listen(PORT, () => console.log(`Real Ohio admin listening on http://127.0.0.1:${PORT}${ADMIN_PATH}`));
