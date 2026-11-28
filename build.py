#!/usr/bin/env python3
"""Build Real Ohio's public site from config.json + articles/*.json.

Usage: python3 build.py
Reads config.json (domain, tagline) and every articles/*.json file,
newest first, and writes index.html, about.html, archive.html and
subscribe.html (plus page2.html, page3.html, ... when there are more
published articles than config articles_per_page), feed.xml, and
sitemap.xml (front pages + static pages + one URL per published
article, for search engines).
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
import datetime
import email.utils
import html
import json
import pathlib
import urllib.parse

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

def page_head(config, title, show_parody=True, description=None, canonical=None, link_prefix=""):
    # link_prefix is "../" on standalone article pages (stories/), where
    # the nav targets live one level up; "" everywhere else.
    parody = (
        '<div class="parody"><strong>Parody news.</strong> The news underneath is real. '
        "The Ohioans are not — they're fictional, and any resemblance to an actual Ohio family "
        "is a coincidence, probably from Findlay.</div>"
        if show_parody
        else ""
    )
    desc = description if description is not None else config['description']
    canon = f'\n<link rel="canonical" href="{html.escape(canonical)}">' if canonical else ""
    rss = f'\n<link rel="alternate" type="application/rss+xml" title="{html.escape(config["site_name"])}" href="{html.escape(config["base_url"])}/feed.xml">'
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — {html.escape(config['site_name'])}</title>
<meta name="description" content="{html.escape(desc)}">{canon}{rss}
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
  .pagination {{ text-align: center; font-family: system-ui, sans-serif; font-weight: 700; margin: 8px 0 32px; }}
  .pagination a {{ text-decoration: none; }}
  .pagination a:hover {{ text-decoration: underline; }}
  .story h2 a {{ color: inherit; text-decoration: none; }}
  .story h2 a:hover {{ text-decoration: underline; }}
  .back {{ font-family: system-ui, sans-serif; font-weight: 700; margin-bottom: 20px; }}
  .back a {{ text-decoration: none; }}
  .back a:hover {{ text-decoration: underline; }}
  .share {{ font-family: system-ui, sans-serif; font-size: .9rem; margin-top: 24px; }}
  .share a {{ margin: 0 4px; }}
  .share-btn {{ font: inherit; font-size: .9rem; font-weight: 700; padding: 4px 10px; border: 1.5px solid #1c1a17; border-radius: 4px; background: #fff; color: #1c1a17; cursor: pointer; margin: 0 4px; }}
  .price {{ font-size: 2rem; font-weight: 700; font-family: system-ui, sans-serif; }}
</style>
</head>
<body>
<header><h1>{html.escape(config['site_name'])}</h1><p>{html.escape(config['tagline'])}</p></header>
<nav><a href="{link_prefix}index.html">Latest</a><a href="{link_prefix}archive.html">News Archive</a><a href="{link_prefix}subscribe.html">Subscribe — {html.escape(ARCHIVE_PRICE)}</a><a href="{link_prefix}about.html">About</a></nav>
{parody}
"""

COPY_SCRIPT = """
<script>
function copyShareLink(btn) {
  var url = btn.getAttribute('data-url');
  function done() { var t = btn.textContent; btn.textContent = 'Copied!'; setTimeout(function() { btn.textContent = t; }, 2000); }
  function fallback() {
    var ta = document.createElement('textarea');
    ta.value = url; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); done(); } catch (e) {}
    document.body.removeChild(ta);
  }
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(url).then(done, fallback);
  } else { fallback(); }
}
</script>
"""

def page_foot(config):
    return f"""
<footer>{html.escape(config['tagline'])} &middot; {html.escape(config['base_url'])} &middot; <a href="{html.escape(config['base_url'])}/feed.xml">RSS</a></footer>
""" + COPY_SCRIPT + """
</body>
</html>
"""

def share_row(config, a):
    """Share links for an article. Facebook, X, and Threads all offer a
    web share/intent URL. TikTok and Instagram do not, so they are
    covered by the Copy link button — copy the link and paste it into
    the app."""
    url = f"{config['base_url']}/stories/{a['id']}.html"
    enc_url = urllib.parse.quote(url, safe="")
    enc_text = urllib.parse.quote(a['headline'], safe="")
    return f"""
      <p class="share">Share:
        <a href="https://www.facebook.com/sharer/sharer.php?u={enc_url}" target="_blank" rel="noopener">Facebook</a>
        <a href="https://twitter.com/intent/tweet?url={enc_url}&amp;text={enc_text}" target="_blank" rel="noopener">X</a>
        <a href="https://www.threads.net/intent/post?text={enc_text}%20{enc_url}" target="_blank" rel="noopener">Threads</a>
        <button type="button" class="share-btn" data-url="{html.escape(url)}" onclick="copyShareLink(this)" title="Copy the link to paste into TikTok or Instagram">Copy link</button>
      </p>"""

def figure(a, src, prefix=""):
    return f'<figure><img src="{html.escape(prefix + src)}" alt="{html.escape(a["headline"])}"></figure>'

def render_card(config, a, link_headline=False, asset_prefix=""):
    # asset_prefix is "../" on standalone article pages (stories/),
    # where the images live one level up; "" on the front pages.
    quotes = "".join(
        f'<blockquote><p>“{html.escape(q["quote"])}”</p>'
        f'<cite>— {html.escape(q["speaker"])}</cite></blockquote>'
        for q in a.get("ohio_quotes", [])
    )
    # Images are spread through the article, not stacked at the top:
    # the first (real event) goes after "What actually happened", the
    # second (the Ohioan) after "Meanwhile, in Ohio". Any further
    # images follow the quotes, in order.
    images = a.get("images", [])
    first = figure(a, images[0], asset_prefix) if len(images) > 0 else ""
    second = figure(a, images[1], asset_prefix) if len(images) > 1 else ""
    rest = "".join(figure(a, src, asset_prefix) for src in images[2:])
    headline = html.escape(a['headline'])
    if link_headline:
        headline = f'<a href="stories/{html.escape(a["id"])}.html">{headline}</a>'
    return f"""
    <article class="story" id="{html.escape(a['slug'])}">
      <div class="kicker">Real news about Real Ohioans &middot; {html.escape(a['date'])} &middot; {html.escape(a['ohio_town'])}</div>
      <h2>{headline}</h2>
      <p class="dek">{html.escape(a['dek'])}</p>
      <h3>What actually happened</h3>
      {paras(a['real_summary'])}
      {first}
      <h3>Meanwhile, in Ohio</h3>
      {paras(a['ohio_story'])}
      {second}
      {quotes}
      {rest}
      {share_row(config, a)}
    </article>"""

def page_filename(n):
    # Page 1 is index.html; later pages are page2.html, page3.html, ...
    return "index.html" if n == 1 else f"page{n}.html"

def render_index_page(config, page_articles, page, total_pages):
    stories = "\n".join(render_card(config, a, link_headline=True) for a in page_articles)
    links = []
    if page > 1:
        links.append(f'<a href="{page_filename(page - 1)}">&larr; Newer stories</a>')
    if page < total_pages:
        links.append(f'<a href="{page_filename(page + 1)}">Older stories &rarr;</a>')
    pagination = ""
    if total_pages > 1:
        pagination = (
            '<nav class="pagination">' + " &middot; ".join(links)
            + f' &middot; <span class="muted">Page {page} of {total_pages}</span></nav>'
        )
    # The archive plug only goes on the last page — earlier pages point
    # at the next page of real stories instead.
    archive_card = ""
    if page == total_pages:
        archive_card = f"""<div class="card"><h2>Looking for older stories?</h2>
<p>They're all in the <a href="archive.html">News Archive</a> — {html.escape(ARCHIVE_TOTAL)} stories and counting, going back to 2019. Archive access is for subscribers (<a href="subscribe.html">Subscribe — {html.escape(ARCHIVE_PRICE)}</a>).</p></div>"""
    title = config['tagline'] if page == 1 else f"{config['tagline']} · Page {page}"
    return page_head(config, title, show_parody=False) + f"""<main>
{stories}
{pagination}
{archive_card}
</main>
""" + page_foot(config)

def render_index(config, articles):
    """Split published articles into pages of config articles_per_page.

    Returns a list of (filename, html) — page 1 is index.html, later
    pages are page2.html, page3.html, ... — and deletes any stale
    page*.html left over from when more articles were published.
    """
    per_page = int(config.get("articles_per_page", 5))
    chunks = [articles[i:i + per_page] for i in range(0, len(articles), per_page)] or [[]]
    total_pages = len(chunks)
    for stale in ROOT.glob("page*.html"):
        stale.unlink()
    return [
        (page_filename(n), render_index_page(config, chunk, n, total_pages))
        for n, chunk in enumerate(chunks, start=1)
    ]

def render_about(config):
    return page_head(config, "About Real Ohio", show_parody=False) + f"""<main>
<div class="card">
<h2>About Real Ohio</h2>
<p>Real Ohio was founded in 2019 by a group of Ohio journalists who were tired of reading news that never described the impact on our state. We took on a mission to bring everyone not only the news, but also the local perspective.</p>
<p>Every story here starts with what actually happened — the facts, as reported — and then follows it home to Ohio: what it means for a family in Lima, a shop owner in Defiance, a choir singer in Hamilton. A national story is only half a story if it never lands where you live.</p>
<p>We want news to connect with our readers at a human level. A gas price is a number until a family in Mansfield starts doing the math out loud; a hurricane is a headline until it's a roof in Dover; a software outage is a status page until a family in Dublin discovers just how much of life runs through Outlook. That's the part we try never to leave out.</p>
<p>We hope this helps bring our community closer together — neighbors reading the same stories, recognizing their own towns in them, and talking about them at the kitchen table instead of scrolling past. That's the whole idea.</p>
<p class="muted"><a href="index.html">Read the latest stories</a> &middot; <a href="subscribe.html">Subscribe — {html.escape(ARCHIVE_PRICE)}</a></p>
</div>
</main>
""" + page_foot(config)

def render_article_page(config, article, newer=None, older=None):
    """One standalone page per article, at stories/<slug>.html.

    Same card as the front page (images spread through the story), but
    the headline is not a link to itself. Each page carries its own
    <title>, meta description, and canonical URL, and links to the
    next/previous story — that is the SEO point of these pages.
    """
    links = []
    if newer:
        links.append(f'<a href="{html.escape(newer["id"])}.html">&larr; Newer: {html.escape(newer["headline"])}</a>')
    if older:
        links.append(f'<a href="{html.escape(older["id"])}.html">Older: {html.escape(older["headline"])} &rarr;</a>')
    nav = ""
    if links:
        nav = '<nav class="pagination">' + " &middot; ".join(links) + "</nav>"
    canonical = f"{config['base_url']}/stories/{article['id']}.html"
    return page_head(config, article['headline'], show_parody=False,
                     description=article.get('dek') or None,
                     canonical=canonical, link_prefix="../") + f"""<main>
<p class="back"><a href="../index.html">&larr; Back to the latest stories</a></p>
{render_card(config, article, asset_prefix="../")}
{nav}
</main>
""" + page_foot(config)

def render_article_pages(config, articles):
    """Write stories/<slug>.html for every published article and delete
    stale ones (e.g. after an unpublish). Returns the filenames written.
    """
    out_dir = ROOT / "stories"
    out_dir.mkdir(exist_ok=True)
    for stale in out_dir.glob("*.html"):
        stale.unlink()
    written = []
    for i, a in enumerate(articles):
        newer = articles[i - 1] if i > 0 else None
        older = articles[i + 1] if i + 1 < len(articles) else None
        # Datestamped filename: stories/2026-11-15-faa-ground-stop-cruise-miss.html
        # (id is the date-prefixed slug, matching the article JSON filenames).
        filename = f"{a['id']}.html"
        (out_dir / filename).write_text(render_article_page(config, a, newer, older))
        written.append(filename)
    return written

def render_feed(config, articles):
    """RSS 2.0 feed of the published articles, at feed.xml. Each item
    links to the article's standalone story page; pubDate is the
    article date at midnight UTC."""
    items = []
    for a in articles:
        url = f"{config['base_url']}/stories/{a['id']}.html"
        pub = datetime.datetime.combine(
            datetime.date.fromisoformat(a['date']), datetime.time.min,
            tzinfo=datetime.timezone.utc)
        items.append(f"""<item>
<title>{html.escape(a['headline'])}</title>
<link>{html.escape(url)}</link>
<guid>{html.escape(url)}</guid>
<pubDate>{email.utils.format_datetime(pub)}</pubDate>
<description>{html.escape(a['dek'])}</description>
</item>""")
    items_text = "\n".join(items)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{html.escape(config['site_name'])}</title>
<link>{html.escape(config['base_url'])}</link>
<description>{html.escape(config['description'])}</description>
<language>en-us</language>
{items_text}
</channel>
</rss>
"""

def render_sitemap(config, articles):
    """Sitemap XML for search engines, at sitemap.xml. Lists the front
    pages, the static pages, and every published article's standalone
    page, with lastmod dates. Regenerated on every build so it always
    matches the published set (popcorn's published.json is the source
    of truth — a local build without it only sees drafts marked
    published in their own files)."""
    base = config['base_url']
    per_page = int(config.get("articles_per_page", 5))
    chunks = [articles[i:i + per_page] for i in range(0, len(articles), per_page)] or [[]]
    urls = []
    # Front pages: page 1 is the site root.
    for n, chunk in enumerate(chunks, start=1):
        loc = base + "/" if n == 1 else f"{base}/page{n}.html"
        lastmod = chunk[0]["date"] if chunk else None
        urls.append((loc, lastmod, "1.0" if n == 1 else "0.7"))
    for page in ("about.html", "archive.html", "subscribe.html"):
        urls.append((f"{base}/{page}", None, "0.5"))
    for a in articles:
        urls.append((f"{base}/stories/{a['id']}.html", a["date"], "0.8"))
    entries = "".join(
        "  <url>\n"
        f"    <loc>{html.escape(loc)}</loc>\n"
        + (f"    <lastmod>{lastmod}</lastmod>\n" if lastmod else "")
        + f"    <priority>{prio}</priority>\n"
        "  </url>\n"
        for loc, lastmod, prio in urls
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}</urlset>\n"
    )

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
    pages = render_index(config, articles)
    for filename, text in pages:
        (ROOT / filename).write_text(text)
    story_pages = render_article_pages(config, articles)
    (ROOT / "about.html").write_text(render_about(config))
    (ROOT / "archive.html").write_text(render_archive(config))
    (ROOT / "subscribe.html").write_text(render_subscribe(config))
    (ROOT / "feed.xml").write_text(render_feed(config, articles))
    (ROOT / "sitemap.xml").write_text(render_sitemap(config, articles))
    print(f"Built index.html: {len(articles)} article(s), domain {config['domain']}")
    print(f"Built feed.xml: {len(articles)} item(s)")
    print(f"Built sitemap.xml: {len(articles)} article URL(s) + front pages")
    if len(pages) > 1:
        print(f"Paginated into {len(pages)} pages ({config.get('articles_per_page', 5)} per page): " + ", ".join(f for f, _ in pages))
    print(f"Built {len(story_pages)} standalone article page(s) in stories/")
    print("Built about.html, archive.html and subscribe.html (fake archive / fake $19.99/month signup — client-side only, nothing sent or stored)")
