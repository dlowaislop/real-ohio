# Real Ohio — deploy to popcorn

Static site, same pattern as Rando / MuseCases Threads: one
self-contained `index.html`, no build step on the server, no backend,
no systemd service. Apache serves it directly.

Target domain (configurable — see `config.json`):
`www.realohio.us.com`

`ohio.randorando.win` was the original domain, retired Nov 16, 2026 —
see "Retiring ohio.randorando.win" below.

## 1. GitHub repo (one-time)

Create a private repo `dlowaislop/real-ohio` and push this directory.
The local copy lives at `~/workspace/real-ohio/`.

## 2. DNS (your step, in Cloudflare)

Create an A record for `www.realohio.us.com` pointing at popcorn's
public IP. Leave it DNS-only (grey cloud) while you get the
certificate, then flip it to proxied (orange cloud). Set SSL/TLS →
Overview to **Full (strict)** once the certificate is in place.

## 3. Checkout on popcorn

```sh
cd /root/work
git clone git@github.com:dlowaislop/real-ohio.git
# or, if the checkout already exists:
cd /root/work/real-ohio && git pull --ff-only
```

The generated pages (`index.html`, `archive.html`, `subscribe.html`)
are build output and are not in the repo — generate them after
cloning (and after any pull that changes `build.py`):

```sh
cd /root/work/real-ohio && python3 build.py
```

## 4. Copy the files to the web root

```sh
sudo mkdir -p /var/www/real-ohio
sudo cp /root/work/real-ohio/index.html /root/work/real-ohio/about.html /root/work/real-ohio/archive.html /root/work/real-ohio/subscribe.html /root/work/real-ohio/feed.xml /root/work/real-ohio/sitemap.xml /root/work/real-ohio/robots.txt /root/work/real-ohio/google89288fdd33347992.html /var/www/real-ohio/
sudo cp /root/work/real-ohio/page*.html /var/www/real-ohio/ 2>/dev/null || true  # paginated pages, if any
sudo cp -r /root/work/real-ohio/stories /var/www/real-ohio/  # standalone article pages
sudo cp -r /root/work/real-ohio/images /var/www/real-ohio/   # article photos, if present
sudo chown -R root:root /var/www/real-ohio
sudo chmod 644 /var/www/real-ohio/*.html
```

`archive.html` / `subscribe.html` are the fake News Archive login and
fake $19.99/month signup (see README — client-side only, nothing is
sent, stored, or charged; Register always errors).

## 5. Apache vhost

Create `/etc/apache2/sites-available/real-ohio.conf`:

```apache
<VirtualHost *:80>
    ServerName www.realohio.us.com
    DocumentRoot /var/www/real-ohio

    <Directory /var/www/real-ohio>
        Require all granted
        Options -Indexes
    </Directory>
</VirtualHost>
```

Enable and reload:

```sh
sudo a2ensite real-ohio
sudo apachectl configtest
sudo systemctl reload apache2
```

## 6. HTTPS (recommended)

```sh
sudo certbot --apache -d www.realohio.us.com
```

Certbot works behind Cloudflare's proxy — the HTTP-01 challenge
comes in over port 80, which Cloudflare passes through. One
exception: if the record is proxied with "Always Use HTTPS" and
"Full (strict)" before popcorn has any valid cert, the challenge
gets redirected to HTTPS and fails (chicken-and-egg). Flip the
record to DNS-only for the issuance, then flip it back. Renewals
work unattended behind the proxy once a valid cert is in place.

## 7. Verify

```sh
curl -s -o /dev/null -w "%{http_code}\n" https://www.realohio.us.com/
```

Expect `200`.

## Updating later (same as MuseCases)

Add or edit an article in `articles/`, run `python3 build.py`,
commit and push to GitHub, then on popcorn:

```sh
cd /root/work/real-ohio && git pull --ff-only
```

A pull no longer touches the live site by itself, and publishing in
`/masthead` no longer dirties the checkout: the generated pages are
untracked build output, and publish state is gitignored, so after a
publish the tree stays clean and the next pull just works. To refresh
the live site after a pull that changes code or `build.py`, either
do any save/publish/unpublish in `/masthead` — the admin server
rebuilds and copies `index.html` / `archive.html` / `subscribe.html`,
the paginated `page2.html` / `page3.html` / ... pages, and `images/`
to `/var/www/real-ohio/` (config `web_root`) — or run manually:

```sh
cd /root/work/real-ohio && python3 build.py
sudo cp index.html archive.html subscribe.html feed.xml sitemap.xml robots.txt google89288fdd33347992.html page*.html /var/www/real-ohio/
```

No restart needed for content or `build.py` changes; restart
`realohio` only when `server.mjs` changes.

One exception: if you edit a draft's text in `/masthead` on popcorn
and don't push it, that article file is a local change and a later
pull can still complain about it — commit or stash it first.

## Admin server — drafts, editing, publishing (port 3016)

The public site is static, but `/masthead` needs the small admin server
(`server.mjs`, Bun, no dependencies). It serves the editor UI and the
`/api/*` endpoints, and rebuilds `index.html` after every save/publish.

Create `/etc/systemd/system/realohio.service`:

```ini
[Unit]
Description=Real Ohio admin server
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/root/work/real-ohio
Environment=PORT=3016
ExecStart=/usr/local/bin/bun run server.mjs
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Set `ExecStart` to the path returned by `command -v bun` on the host.
Then:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now realohio
sudo systemctl status realohio
curl http://127.0.0.1:3016/api/me   # expect 401 "Please log in." — server is up
```

### Apache proxy for /masthead and /api

Add to the `real-ohio.conf` vhost (inside `<VirtualHost *:80>`,
and in the certbot TLS vhost too), then reload Apache:

```apache
ProxyPreserveHost On
ProxyPass        /masthead  http://127.0.0.1:3016/masthead nocanon
ProxyPassReverse /masthead  http://127.0.0.1:3016/masthead
ProxyPass        /api    http://127.0.0.1:3016/api nocanon
ProxyPassReverse /api    http://127.0.0.1:3016/api
```

Enable proxy modules once if not already enabled:

```sh
sudo a2enmod proxy proxy_http
sudo systemctl reload apache2
```

Admin URL: `https://www.realohio.us.com/masthead`

### Create the first admin user(s)

On popcorn, in the checkout (users live in `data/users.json`,
gitignored — never committed, never in GitHub):

```sh
cd /root/work/real-ohio
bun scripts/users.mjs create dave        # prompts for a password (masked)
bun scripts/users.mjs create alice
bun scripts/users.mjs list
bun scripts/users.mjs update dave        # change a password
bun scripts/users.mjs delete alice
```

Log in at `/masthead` with that username/password. Sessions last 12h.

### Workflow

1. New article → draft (in `/masthead`, or a `status: "draft"` JSON file).
2. Edit in `/masthead` until it reads right.
3. **Publish** — the public `index.html` on popcorn rebuilds immediately.

Publishing is popcorn-local by design: GitHub stores the drafts only.
Publishing records the article in `data/published.json` (gitignored)
and rebuilds the site — it never changes the draft file, so there is
nothing to commit or push after you publish. If you edit a draft's
text in `/masthead` and want that edit in GitHub, commit and push the
article file from the checkout on popcorn.

## Retiring ohio.randorando.win

The original domain was retired Nov 16, 2026 in favor of
`www.realohio.us.com`. Once the new domain is live and verified,
remove the old pieces:

- **DNS:** delete the A record for `ohio.randorando.win`.
- **Popcorn vhost:** remove any `ServerAlias ohio.randorando.win`
  from `/etc/apache2/sites-available/real-ohio.conf`, then reload
  Apache. (The `/masthead` and `/api` proxy directives stay — they
  live in that vhost and now serve the new name.)
- **Popcorn certificate:** delete the old Let's Encrypt cert:

  ```sh
  sudo certbot delete --cert-name ohio.randorando.win
  ```

  Skip the delete if you want to keep a redirect from the old name —
  in that case keep the DNS, the alias, and the cert.

## Changing the domain later

1. Edit `domain` and `base_url` in `config.json`.
2. Run `python3 build.py`, commit, push, deploy as above.
3. Update DNS to the new name and change `ServerName` in the vhost
   (or add a second vhost), then `sudo certbot --apache -d <new-domain>`.
