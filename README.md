# Real Ohio

**Real Ohio for Real Ohioans**

Real news, retold the Ohio way. Each story starts with what actually
happened — a 2–3 paragraph summary based on real reporting — then follows
it home to Ohio, where a fictional local family deals with the fallout.

Parody: the Ohio people in these stories are fictional. The underlying
news events are real and sourced.

- Site: https://ohio.randorando.win
- Config: `config.json` — site name, tagline, and domain live here.
  Change the domain in one place and rebuild; nothing else hard-codes it.
- Articles: `articles/*.json` — one JSON file per story.
- Site: `index.html` — the whole site, self-contained. Serve it statically.
  Regenerate it with `python3 build.py` after adding or editing an article.

## Adding a new article

1. Copy `articles/2026-11-15-faa-ground-stop-cruise-miss.json` to a new
   file named `articles/YYYY-MM-DD-<slug>.json`.
2. Fill in `headline`, `dek`, `real_summary` (2–3 paragraphs, faithful to
   the real reporting, with `source_name` / `source_url`), and
   `ohio_story` (the fictional Ohio angle — pick a real Ohio town, keep
   the people fictional, keep the local details specific).
3. Set `"status": "draft"` in the new file (or create it in `/masthead`,
   which does this for you), then edit and **Publish** it in `/masthead`.
   Or, for a file-only flow: set `"status": "published"`, run
   `python3 build.py`, check `index.html` locally, commit, and push.
4. On popcorn: `git pull` in the checkout and copy `index.html` to the
   web root (see `DEPLOY.md`). No rebuild, no restart, no backend.
   If you published from `/masthead` on popcorn instead, the public site
   is already rebuilt there — just commit and push from popcorn to
   keep GitHub in sync.

This is the same update flow as MuseCases Threads: articles live in
GitHub, the built `index.html` is committed, and popcorn serves the
static file.

## Drafts, editing, and publishing

Every article has a `status`: `draft` or `published`. New articles
start as drafts, and `build.py` only puts `published` articles into
`index.html` — drafts never appear on the public site.

Edit and publish in the admin UI at `/masthead`
(`https://ohio.randorando.win/masthead` once deployed):

- Log in with a CLI-created username/password (below).
- **Articles** lists drafts and published stories. **Edit** opens the
  full article — headline, deck, town, real summary, Ohio story,
  quotes, source. **Save draft** keeps it a draft; **Publish** puts
  it on the public site immediately; **Unpublish** pulls it back to
  draft; **Delete** removes it. **+ New draft** starts a blank one.
- After publishing from the admin UI, keep GitHub in sync (the
  MuseCases flow) from the popcorn checkout — the admin page shows
  the exact commands:
  `git add -A && git commit -m "Publish: <headline>" && git push`

### Admin users (CLI)

No signup on the site. Create/update/delete users from the command
line on the machine running the admin server (popcorn, in production):

```sh
bun scripts/users.mjs create alice            # prompts for a password (masked)
bun scripts/users.mjs create bob --password 'correct horse battery staple'
bun scripts/users.mjs update alice            # change password
bun scripts/users.mjs delete bob
bun scripts/users.mjs list
```

Usernames: 3–32 chars, lowercase letters/digits/`.`/`_`/`-`.
Passwords: at least 8 characters, stored only as scrypt hashes in
`data/users.json` (gitignored, never committed). Multiple users can
log in at the same time; the article records who last edited it.

### Admin server

`server.mjs` — Bun or Node, no dependencies, port 3016 by default
(`admin_port` in `config.json`, or `PORT` env). It serves `/masthead`
and `/api/*`, and rebuilds the public site (`python3 build.py`)
after every save / publish / unpublish / delete.

```sh
bun run server.mjs
# production (systemd, see DEPLOY.md): realohio.service, port 3016
```

## Changing the domain later

Edit `domain` and `base_url` in `config.json`, run `python3 build.py`,
commit, push, and update the Apache vhost / DNS (see `DEPLOY.md`).
