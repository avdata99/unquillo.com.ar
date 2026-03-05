"""Jinja2 rendering engine for generating static HTML pages."""

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .utils import create_slug, truncate


def _jinja_truncate(text, length=250):
    """Jinja2 filter to truncate text with ellipsis."""
    return truncate(text, length)


class Renderer:
    """Renders site pages using Jinja2 templates."""

    def __init__(self, template_name, engine_dir):
        """Initialize renderer with a template.

        Args:
            template_name: Name of the template directory (e.g. 'municipal')
            engine_dir: Path to the engine/ directory
        """
        self.engine_dir = Path(engine_dir)
        self.template_dir = self.engine_dir / 'templates' / template_name

        if not self.template_dir.exists():
            raise FileNotFoundError(
                f"Template '{template_name}' not found at {self.template_dir}"
            )

        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True,
        )
        self.env.globals['now'] = datetime.now
        self.env.filters['truncate_text'] = _jinja_truncate

    def render_homepage(self, config, articles):
        """Render the homepage (index.html).

        Args:
            config: Site configuration dict.
            articles: List of recent articles for the homepage.

        Returns:
            Rendered HTML string.
        """
        template = self.env.get_template('index.html')
        return template.render(
            site=config['site'],
            content=config.get('content', {}),
            articles=articles,
            build_date=datetime.now().strftime('%d/%m/%Y %H:%M'),
        )

    def render_article(self, config, article):
        """Render an individual article page.

        Args:
            config: Site configuration dict.
            article: Article dict.

        Returns:
            Rendered HTML string.
        """
        template = self.env.get_template('article.html')
        return template.render(
            site=config['site'],
            article=article,
            build_date=datetime.now().strftime('%d/%m/%Y %H:%M'),
        )

    def render_sitemap(self, config, articles):
        """Render sitemap.xml.

        Args:
            config: Site configuration dict.
            articles: List of ALL articles (not just recent).

        Returns:
            Rendered XML string.
        """
        base_url = config['site']['url'].rstrip('/')
        today = datetime.now().strftime('%Y-%m-%d')

        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        # Homepage
        xml += f'  <url>\n'
        xml += f'    <loc>{base_url}/</loc>\n'
        xml += f'    <lastmod>{today}</lastmod>\n'
        xml += f'    <changefreq>daily</changefreq>\n'
        xml += f'    <priority>1.0</priority>\n'
        xml += f'  </url>\n'

        # Article pages
        for article in articles:
            slug = article.get('slug', create_slug(article['title']))
            xml += f'  <url>\n'
            xml += f'    <loc>{base_url}/articles/{slug}/</loc>\n'
            xml += f'    <lastmod>{today}</lastmod>\n'
            xml += f'    <changefreq>weekly</changefreq>\n'
            xml += f'    <priority>0.8</priority>\n'
            xml += f'  </url>\n'

        xml += '</urlset>'
        return xml

    def render_robots_txt(self, config):
        """Render robots.txt.

        Args:
            config: Site configuration dict.

        Returns:
            robots.txt content string.
        """
        base_url = config['site']['url'].rstrip('/')
        return (
            f"User-agent: *\n"
            f"Allow: /\n"
            f"\n"
            f"Sitemap: {base_url}/sitemap.xml\n"
        )

    def get_asset_files(self):
        """Return list of asset files in the template's assets/ directory."""
        assets_dir = self.template_dir / 'assets'
        if not assets_dir.exists():
            return []
        return list(assets_dir.rglob('*'))
