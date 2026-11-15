#!/usr/bin/env python3
"""Build Real Ohio's index.html from config.json + articles/*.json.

Usage: python3 build.py
Reads config.json (domain, tagline) and every articles/*.json file,
newest first, and writes a self-contained index.html.
No dependencies, no network.
"""
import html
import json
import pathlib

ROOT = pathlib.Path(__file__).parent

def load_config():
    return json.loads((ROOT / "config.json").read_text())

def load_articles():
    articles = []
    for path in sorted((ROOT / "articles").glob("*.json")):
        articles.append(json.loads(path.read_text()))
    # Drafts never appear on the public site — only published articles.
    articles = [a for a in articles if a.get("status", "published") == "published"]
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles

def paras(items):
    return "".join(f"<p>{html.escape(p)}</p>" for p in items)

def render(config, articles):
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
      <div class="kicker">Real news &middot; {html.escape(a['date'])} &middot; {html.escape(a['ohio_town'])}</div>
      <h2>{html.escape(a['headline'])}</h2>
      <p class="dek">{html.escape(a['dek'])}</p>
      {figures}
      <h3>What actually happened</h3>
      {paras(a['real_summary'])}
      <p class="source">Based on {html.escape(a['source_name'])} reporting, {html.escape(a['real_event_date'])}. <a href="{html.escape(a['source_url'])}">Read the real story</a>.</p>
      <h3>Meanwhile, in Ohio</h3>
      {paras(a['ohio_story'])}
      {quotes}
      <p class="disclaimer">{html.escape(a['disclaimer'])}</p>
    </article>""")
    stories = "\n".join(cards)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(config['site_name'])} — {html.escape(config['tagline'])}</title>
<meta name="description" content="{html.escape(config['description'])}">
<style>
  body {{ margin: 0; background: #f7f3ea; color: #1c1a17; font-family: Georgia, 'Times New Roman', serif; line-height: 1.6; }}
  header {{ background: #bb0000; color: #fff; padding: 28px 20px 22px; text-align: center; border-bottom: 6px solid #1c1a17; }}
  header h1 {{ margin: 0; font-size: clamp(2.6rem, 8vw, 4.5rem); letter-spacing: -0.02em; line-height: 1; }}
  header p {{ margin: 8px 0 0; font-family: system-ui, sans-serif; font-size: 1.05rem; font-style: italic; }}
  .parody {{ background: #fff3cd; border-bottom: 2px solid #1c1a17; text-align: center; padding: 10px 16px; font-family: system-ui, sans-serif; font-size: .9rem; }}
  main {{ max-width: 760px; margin: 0 auto; padding: 28px 20px 60px; }}
  .story {{ background: #fff; border: 2px solid #1c1a17; box-shadow: 5px 5px 0 #1c1a17; padding: 28px; margin-bottom: 32px; }}
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
</style>
</head>
<body>
<header><h1>{html.escape(config['site_name'])}</h1><p>{html.escape(config['tagline'])}</p></header>
<div class="parody"><strong>Parody news.</strong> The news underneath is real. The Ohioans are not — they're fictional, and any resemblance to an actual Ohio family is a coincidence, probably from Findlay.</div>
<main>
{stories}
</main>
<footer>{html.escape(config['site_name'])} — {html.escape(config['tagline'])} &middot; {html.escape(config['base_url'])} &middot; Real events, fictional Ohioans.</footer>
</body>
</html>
"""

if __name__ == "__main__":
    config = load_config()
    articles = load_articles()
    (ROOT / "index.html").write_text(render(config, articles))
    print(f"Built index.html: {len(articles)} article(s), domain {config['domain']}")
