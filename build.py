#!/usr/bin/env python3
"""Build Real Ohio's public site from config.json + articles/*.json.

Usage: python3 build.py
Reads config.json (domain, tagline) and every articles/*.json file,
newest first, and writes index.html, archive.html and subscribe.html.
No dependencies, no network.

The News Archive is a gag, by design: there is no archive behind it.
archive.html is a fake login gate (any login attempt fails client-side,
nothing is sent or stored) over a locked index that makes the site look
like it has thousands of back stories. subscribe.html is a fake
$19.99/month signup form: it collects nothing, sends nothing, stores
nothing — pressing Register always shows
"Error processing transaction, please try again later."
Both pages are pure static HTML/JS with no form action, no fetch, and
no backend. Do not "fix" them into a real login or a real checkout.
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).parent

ARCHIVE_PRICE = "$19.99/month"
# Fake archive volume, part of the gag: makes the site look like it has
# a deep back catalog. These counts are invented, not article counts.
ARCHIVE_TOTAL = "3,214"

def load_config():
    return json.loads((ROOT / "config.json").read_text())

def load_published_override():
    # Popcorn-local publish state (data/published.json, gitignored):
    # slug -> {"published": bool, ...}. Publishing in /masthead updates
    # only this file, never the draft — so GitHub keeps the drafts and
    # the live site is built from the override. No override for a slug
    # means: fall back to the status in the draft file.
    try:
        return json.loads((ROOT / "data" / "published.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def load_articles():
    articles = []
    for path in sorted((ROOT / "articles").glob("*.json")):
        articles.append(json.loads(path.read_text()))
    override = load_published_override()
    # Drafts never appear on the public site — only published articles.
    def is_published(a):
        entry = override.get(a.get("slug"))
        if isinstance(entry, dict) and isinstance(entry.get("published"), bool):
            return entry["published"]
        return a.get("status", "published") == "published"
    articles = [a for a in articles if is_published(a)]
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles

def paras(items):
    return "".join(f"<p>{html.escape(p)}</p>" for p in items)

def page_head(config, title, show_parody=True):
    parody = (
        '<div class="parody"><strong>Parody news.</strong> The news underneath is real. '
        "The Ohioans are not — they're fictional, and any resemblance to an actual Ohio family "
        "is a coincidence, probably from Findlay.</div>"
        if show_parody
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — {html.escape(config['site_name'])}</title>
<meta name="description" content="{html.escape(config['description'])}">
<style>
  body {{ margin: 0; background: #f7f3ea; color: #1c1a17; font-family: Georgia, 'Times New Roman', serif; line-height: 1.6; }}
  header {{ background: #bb0000; color: #fff; padding: 28px 20px 22px; text-align: center; border-bottom: 6px solid #1c1a17; }}
  header h1 {{ margin: 0; font-size: clamp(2.6rem, 8vw, 4.5rem); letter-spacing: -0.02em; line-height: 1; }}
  header p {{ margin: 8px 0 0; font-family: system-ui, sans-serif; font-size: 1.05rem; font-style: italic; }}
  nav {{ background: #1c1a17; text-align: center; padding: 10px 16px; font-family: system-ui, sans-serif; }}
  nav a {{ color: #fff; text-decoration: none; font-weight: 700; margin: 0 14px; }}
  nav a:hover {{ text-decoration: underline; }}
  .parody {{ background: #fff3cd; border-bottom: 2px solid #1c1a17; text-align: center; padding: 10px 16px; font-family: system-ui, sans-serif; font-size: .9rem; }}
  main {{ max-width: 760px; margin: 0 auto; padding: 28px 20px 60px; }}
  .story, .card {{ background: #fff; border: 2px solid #1c1a17; box-shadow: 5px 5px 0 #1c1a17; padding: 28px; margin-bottom: 32px; }}
  .story img {{ max-width: 100%; height: auto; display: block; margin: 12px 0; }}
  .kicker {{ font-family: system-ui, sans-serif; font-size: .8rem; letter-spacing: .08em; text-transform: uppercase; color: #bb0000; font-weight: 700; }}
  h2 {{ font-size: 1.9rem; line-height: 1.2; margin: .4em 0 .3em; }}
  .dek {{ font-size: 1.15rem; color: #555; font-style: italic; }}
  h3 {{ font-family: system-ui, sans-serif; font-size: .95rem; text-transform: uppercase; letter-spacing: .06em; border-top: 2px solid #1c1a17; padding-top: 14px; margin-top: 24px; }}
  blockquote {{ border-left: 4px solid #bb0000; margin: 20px 0; padding: 4px 0 4px 16px; font-style: italic; }}
  blockquote cite {{ font-style: normal; font-family: system-ui, sans-serif; font-size: .9rem; }}
  .source, .disclaimer {{ font-family: system-ui, sans-serif; font-size: .85rem; color: #666; }}
  .disclaimer {{ border-top: 1px solid #ddd; padding-top: 12px; }}
  footer {{ text-align: center; font-family: system-ui, sans-serif; font-size: .85rem; color: #666; padding: 0 20px 40px; }}
  a {{ color: #bb0000; }}
  nav a {{ color: #fff; }}
  label {{ display: block; font-family: system-ui, sans-serif; font-weight: 700; font-size: .9rem; margin: 14px 0 4px; }}
  input {{ width: 100%; box-sizing: border-box; padding: 9px 10px; font: inherit; border: 1.5px solid #999; border-radius: 4px; }}
  button {{ font: inherit; font-weight: 700; padding: 9px 16px; border: 2px solid #1c1a17; border-radius: 4px; background: #bb0000; color: #fff; cursor: pointer; margin-top: 16px; }}
  .error {{ color: #bb0000; font-weight: 700; font-family: system-ui, sans-serif; }}
  .muted {{ color: #666; font-size: .9rem; font-family: system-ui, sans-serif; }}
  .locked {{ border-top: 1px solid #ddd; padding: 12px 0; font-family: system-ui, sans-serif; }}
  .locked .lock {{ float: right; }}
  .price {{ font-size: 2rem; font-weight: 700; font-family: system-ui, sans-serif; }}
</style>
</head>
<body>
<header><h1>{html.escape(config['site_name'])}</h1><p>{html.escape(config['tagline'])}</p></header>
<nav><a href="index.html">Latest</a><a href="archive.html">News Archive</a><a href="subscribe.html">Subscribe — {html.escape(ARCHIVE_PRICE)}</a></nav>
{parody}
"""

def page_foot(config):
    return f"""
<footer>{html.escape(config['site_name'])} — {html.escape(config['tagline'])} &middot; {html.escape(config['base_url'])} &middot; Real events, fictional Ohioans.</footer>
</body>
</html>
"""

def render_index(config, articles):
    cards = []
    for a in articles:
        quotes = "".join(
            f'<blockquote><p>“{html.escape(q["quote"])}”</p>'
            f'<cite>— {html.escape(q["speaker"])}</cite></blockquote>'
            for q in a.get("ohio_quotes", [])
        )
        figures = "".join(
            f'<figure><img src="{html.escape(src)}" alt="{html.escape(a["headline"])}"></figure>'
            for src in a.get("images", [])
        )
        cards.append(f"""
    <article class="story" id="{html.escape(a['slug'])}">
      <div class="kicker">Real news about Real Ohioans &middot; {html.escape(a['date'])} &middot; {html.escape(a['ohio_town'])}</div>
      <h2>{html.escape(a['headline'])}</h2>
      <p class="dek">{html.escape(a['dek'])}</p>
      {figures}
      <h3>What actually happened</h3>
      {paras(a['real_summary'])}
      <h3>Meanwhile, in Ohio</h3>
      {paras(a['ohio_story'])}
      {quotes}
    </article>""")
    stories = "\n".join(cards)
    return page_head(config, config['tagline'], show_parody=False) + f"""<main>
{stories}
<div class="card"><h2>Looking for older stories?</h2>
<p>They're all in the <a href="archive.html">News Archive</a> — {html.escape(ARCHIVE_TOTAL)} stories and counting, going back to 2019. Archive access is for subscribers (<a href="subscribe.html">Subscribe — {html.escape(ARCHIVE_PRICE)}</a>).</p></div>
</main>
""" + page_foot(config)

def render_archive(config):
    # Locked teaser rows: invented parody headlines, members-only, no
    # full text anywhere — the point is the volume, not the stories.
    teasers = [
        ("November 2026", "The Great Lima Pothole Census of 2026"),
        ("October 2026", "Dayton Man Ranks Every Sheet Pan in the County"),
        ("September 2026", "Toledo Family Loses Remote, Finds It in the Couch, Loses It Again"),
        ("August 2026", "Akron Dad Declares War on a Single Dandelion"),
        ("July 2026", "Canton Porch Declared a Historic Landmark by the Porch"),
        ("June 2026", "Youngstown Reunion Potluck Ends in a Tie, Again"),
    ]
    rows = "".join(
        f'<div class="locked"><span class="lock">🔒 Members only</span><strong>{html.escape(t)}</strong><div class="muted">{html.escape(d)}</div></div>'
        for d, t in teasers
    )
    years = "".join(
        f'<div class="locked"><strong>{y}</strong><span class="lock">{n} stories</span></div>'
        for y, n in [("2026", "312"), ("2025", "588"), ("2024", "601"), ("2023", "574"), ("2022", "559"), ("2021", "580")]
    )
    return page_head(config, "News Archive") + f"""<main>
<div class="card">
<h2>News Archive</h2>
<p class="dek">Every story we've ever run — {html.escape(ARCHIVE_TOTAL)} stories and counting, going back to 2019.</p>
<p>Log in with your archive account to browse the full archive.</p>
<form id="archive-login">
<label>Username <input name="username" autocomplete="username" required></label>
<label>Password <input name="password" type="password" autocomplete="current-password" required></label>
<p class="error" id="archive-error" hidden></p>
<button type="submit">Log in to the Archive</button>
</form>
<p class="muted">Don't have an archive account? <a href="subscribe.html">Subscribe — {html.escape(ARCHIVE_PRICE)}</a></p>
</div>
<div class="card">
<h2 style="margin-top:0">Browse the archive</h2>
{years}
<h3>Recently archived</h3>
{rows}
<p class="muted">Full stories are for subscribers only. Log in above, or <a href="subscribe.html">subscribe for {html.escape(ARCHIVE_PRICE)}</a>.</p>
</div>
</main>
<script>
// Fake archive login: no archive exists, nothing is sent or stored.
document.getElementById("archive-login").addEventListener("submit", function (e) {{
  e.preventDefault();
  var err = document.getElementById("archive-error");
  err.textContent = "Unable to sign in to the archive right now. Please try again later.";
  err.hidden = false;
}});
</script>
""" + page_foot(config)

def render_subscribe(config):
    return page_head(config, "Subscribe") + f"""<main>
<div class="card">
<h2>Subscribe to Real Ohio</h2>
<p class="dek">Full access to the News Archive — {html.escape(ARCHIVE_TOTAL)} stories and counting — plus every new story, the moment it lands.</p>
<p class="price">{html.escape(ARCHIVE_PRICE)}</p>
<p class="muted">Billed monthly. Cancel anytime (in theory).</p>
<form id="subscribe-form" autocomplete="off">
<label>Username <input name="username" autocomplete="off" required></label>
<label>Password <input name="password" type="password" autocomplete="new-password" required></label>
<label>Email address <input name="email" type="email" autocomplete="off" required></label>
<label>Billing name <input name="billing_name" autocomplete="off" required></label>
<label>Billing address <input name="billing_address" autocomplete="off" required></label>
<label>City <input name="city" autocomplete="off" required></label>
<label>State <input name="state" autocomplete="off" required></label>
<label>ZIP code <input name="zip" autocomplete="off" required></label>
<label>Credit card number <input name="card_number" inputmode="numeric" autocomplete="off" required></label>
<label>Expiry date <input name="card_expiry" placeholder="MM / YY" autocomplete="off" required></label>
<label>Security code (CVC) <input name="card_cvc" inputmode="numeric" autocomplete="off" required></label>
<p class="error" id="subscribe-error" hidden></p>
<button type="submit">Register — {html.escape(ARCHIVE_PRICE)}</button>
</form>
<p class="muted"><a href="archive.html">Back to the News Archive</a> &middot; <a href="index.html">Back to the latest stories</a></p>
</div>
</main>
<script>
// Fake checkout: nothing is sent, stored, or charged. Registering
// always fails with the same message, by design.
document.getElementById("subscribe-form").addEventListener("submit", function (e) {{
  e.preventDefault();
  var err = document.getElementById("subscribe-error");
  err.textContent = "Error processing transaction, please try again later.";
  err.hidden = false;
}});
</script>
""" + page_foot(config)

if __name__ == "__main__":
    config = load_config()
    articles = load_articles()
    (ROOT / "index.html").write_text(render_index(config, articles))
    (ROOT / "archive.html").write_text(render_archive(config))
    (ROOT / "subscribe.html").write_text(render_subscribe(config))
    print(f"Built index.html: {len(articles)} article(s), domain {config['domain']}")
    print("Built archive.html and subscribe.html (fake archive / fake $19.99/month signup — client-side only, nothing sent or stored)")
