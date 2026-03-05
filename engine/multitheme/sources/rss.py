"""RSS/Atom feed source handler."""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from .base import Source
from ..utils import (
    clean_html, extract_first_image, format_rss_date,
    parse_rss_date, truncate
)


class RSSSource(Source):
    """Fetch and parse standard RSS feeds."""

    def fetch(self):
        """Fetch articles from an RSS feed URL."""
        url = self.source_config.get('url')
        if not url:
            print(f"  [!] RSS source '{self.name}' has no URL, skipping")
            return []

        max_desc = self.site_config.get('content', {}).get('max_description_length', 250)

        try:
            print(f"  Fetching RSS: {self.name} ({url})")
            content = self._download(url)
            return self._parse(content, max_desc)
        except Exception as e:
            print(f"  [!] Error fetching RSS '{self.name}': {e}")
            return []

    def _download(self, url):
        """Download feed content from URL."""
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8')

    def _parse(self, content, max_desc):
        """Parse RSS XML content into article dicts."""
        # Clean XML preamble
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

            desc_elem = item.find('description')
            description = clean_html(desc_elem.text if desc_elem is not None else '')

            pub_date_elem = item.find('pubDate')
            pub_date_raw = pub_date_elem.text if pub_date_elem is not None else ''

            # Extract image from content:encoded or description
            content_elem = item.find(
                './/{http://purl.org/rss/1.0/modules/content/}encoded'
            )
            html_content = content_elem.text if content_elem is not None else ''
            image = extract_first_image(html_content) or extract_first_image(
                desc_elem.text if desc_elem is not None else ''
            )

            # Parse date for sorting
            dt = parse_rss_date(pub_date_raw)

            articles.append({
                'title': title,
                'link': link,
                'description': description,
                'pub_date': format_rss_date(pub_date_raw),
                'pub_date_raw': dt.isoformat(),
                'image': image,
                'source_name': self.name,
                'source_type': 'rss',
                'video_id': None,
            })

            if len(articles) >= self.limit:
                break

        print(f"    Found {len(articles)} articles")
        return articles
