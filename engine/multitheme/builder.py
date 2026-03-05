"""Main build orchestrator: fetch sources -> merge articles -> render site."""

import shutil
from pathlib import Path

from .config import load_config
from .article_store import ArticleStore
from .renderer import Renderer
from .sources.rss import RSSSource
from .sources.youtube import YouTubeSource
from .sources.google_news import GoogleNewsSource
from .utils import create_slug


# Map source type strings to handler classes
SOURCE_HANDLERS = {
    'rss': RSSSource,
    'youtube': YouTubeSource,
    'google_news': GoogleNewsSource,
}


def build(config_path, output_dir, engine_dir=None):
    """Run the full build pipeline.

    Args:
        config_path: Path to site.yaml
        output_dir: Path to output directory (e.g. docs/)
        engine_dir: Path to engine/ directory (auto-detected if None)
    """
    # Auto-detect engine directory
    if engine_dir is None:
        engine_dir = Path(__file__).parent.parent

    config_path = Path(config_path)
    output_dir = Path(output_dir)
    engine_dir = Path(engine_dir)

    # Determine data directory (sibling to config file)
    site_dir = config_path.parent
    data_dir = site_dir / 'data'

    print(f"Building site from {config_path}")

    # 1. Load config
    config = load_config(config_path)
    site = config['site']
    content = config.get('content', {})
    print(f"  Site: {site['title']}")
    print(f"  Template: {site.get('template', 'starter')}")

    # 2. Set up YouTube cache directory
    YouTubeSource.cache_dir = str(data_dir)

    # 3. Fetch from all sources
    print("\nFetching sources...")
    all_articles = []
    for source_config in config.get('sources', []):
        source_type = source_config.get('type', '')
        handler_class = SOURCE_HANDLERS.get(source_type)

        if not handler_class:
            print(f"  [!] Unknown source type: '{source_type}', skipping")
            continue

        try:
            handler = handler_class(source_config, config)
            articles = handler.fetch()
            all_articles.extend(articles)
        except Exception as e:
            print(f"  [!] Source '{source_config.get('name', '?')}' failed: {e}")

    print(f"\nTotal articles fetched: {len(all_articles)}")

    # 4. Merge into article store
    store = ArticleStore(data_dir)
    added = store.merge(all_articles)
    store.save()
    print(f"Articles in database: {len(store.articles)} ({added} new)")

    # 5. Prepare output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # 6. Render site
    template_name = site.get('template', 'starter')
    renderer = Renderer(template_name, engine_dir)

    max_age = content.get('max_article_age_days', 30)
    homepage_limit = content.get('articles_on_homepage', 20)

    recent_articles = store.get_recent(max_age_days=max_age, limit=homepage_limit)
    all_stored = store.get_all()

    print(f"\nRendering site...")
    print(f"  Recent articles for homepage: {len(recent_articles)}")
    print(f"  Total articles for sitemap: {len(all_stored)}")

    # 6a. Render homepage
    homepage_html = renderer.render_homepage(config, recent_articles)
    (output_dir / 'index.html').write_text(homepage_html, encoding='utf-8')
    print(f"  Generated: index.html")

    # 6b. Render individual article pages
    articles_dir = output_dir / 'articles'
    articles_dir.mkdir(exist_ok=True)
    for article in all_stored:
        slug = article.get('slug', create_slug(article['title']))
        article_dir = articles_dir / slug
        article_dir.mkdir(exist_ok=True)
        article_html = renderer.render_article(config, article)
        (article_dir / 'index.html').write_text(article_html, encoding='utf-8')
    print(f"  Generated: {len(all_stored)} article pages")

    # 6c. Render sitemap
    sitemap_xml = renderer.render_sitemap(config, all_stored)
    (output_dir / 'sitemap.xml').write_text(sitemap_xml, encoding='utf-8')
    print(f"  Generated: sitemap.xml")

    # 6d. Render robots.txt
    robots_txt = renderer.render_robots_txt(config)
    (output_dir / 'robots.txt').write_text(robots_txt, encoding='utf-8')
    print(f"  Generated: robots.txt")

    # 6e. Copy CNAME if configured
    cname = site.get('url', '').replace('https://', '').replace('http://', '')
    if cname:
        (output_dir / 'CNAME').write_text(cname, encoding='utf-8')
        print(f"  Generated: CNAME ({cname})")

    # 6f. Copy template assets
    assets_src = renderer.template_dir / 'assets'
    assets_dst = output_dir / 'assets'
    if assets_src.exists():
        if assets_dst.exists():
            shutil.rmtree(assets_dst)
        shutil.copytree(assets_src, assets_dst)
        print(f"  Copied: assets/")

    print(f"\nBuild complete! Output: {output_dir.absolute()}")
