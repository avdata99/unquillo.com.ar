"""Google News RSS source handler."""

import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET

from .base import Source
from ..utils import clean_html, format_rss_date, parse_rss_date, truncate


class GoogleNewsSource(Source):
    """Fetch articles from Google News RSS search."""

    def fetch(self):
        """Fetch articles from Google News RSS."""
        query = self.source_config.get('query', '')
        if not query:
            print(f"  [!] Google News source '{self.name}' has no query, skipping")
            return []

        lang = self.site_config.get('site', {}).get('language', 'es')
        country = self.site_config.get('site', {}).get('country', 'AR')
        max_desc = self.site_config.get('content', {}).get('max_description_length', 250)

        encoded_query = urllib.parse.quote(query)
        url = (
            f'https://news.google.com/rss/search?q={encoded_query}'
            f'&hl={lang}&gl={country}&ceid={country}:{lang}'
        )

        try:
            print(f"  Fetching Google News: {self.name} (q={query})")
            content = self._download(url)
            return self._parse(content, max_desc)
        except Exception as e:
            print(f"  [!] Error fetching Google News '{self.name}': {e}")
            return []

    def _download(self, url):
        """Download feed content from URL."""
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8')

    def _parse(self, content, max_desc):
        """Parse Google News RSS XML into article dicts."""
        xml_start = content.find('<?xml')
        if xml_start > 0:
            content = content[xml_start:]

        root = ET.fromstring(content)
        articles = []

        for item in root.findall('.//item'):
            title_elem = item.find('title')
            title = clean_html(title_elem.text if title_elem is not None else '')

            if not self._matches_keywords(title):
                continue

            link_elem = item.find('link')
            link = link_elem.text if link_elem is not None else ''

            # Google News wraps the real URL; the link itself redirects
            # We use it as-is since it redirects to the source

            desc_elem = item.find('description')
            description = clean_html(desc_elem.text if desc_elem is not None else '')

            pub_date_elem = item.find('pubDate')
            pub_date_raw = pub_date_elem.text if pub_date_elem is not None else ''

            # Extract source from title (Google News format: "Title - Source")
            source_name = self.name
            source_elem = item.find('source')
            if source_elem is not None and source_elem.text:
                source_name = source_elem.text

            dt = parse_rss_date(pub_date_raw)

            articles.append({
                'title': title,
                'link': link,
                'description': description,
                'pub_date': format_rss_date(pub_date_raw),
                'pub_date_raw': dt.isoformat(),
                'image': None,
                'source_name': source_name,
                'source_type': 'google_news',
                'video_id': None,
            })

            if len(articles) >= self.limit:
                break

        print(f"    Found {len(articles)} articles")
        return articles
