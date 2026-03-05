"""Abstract base class for content source handlers."""

from abc import ABC, abstractmethod


class Source(ABC):
    """Base class for all content sources (RSS, YouTube, Google News)."""

    def __init__(self, source_config, site_config):
        """Initialize with source and site configuration.

        Args:
            source_config: dict with source-specific settings (name, url, etc.)
            site_config: dict with full site configuration
        """
        self.name = source_config.get('name', 'Unknown')
        self.limit = source_config.get('limit', 10)
        self.keywords = source_config.get('keywords', [])
        self.source_config = source_config
        self.site_config = site_config

    @abstractmethod
    def fetch(self):
        """Fetch articles from the source.

        Returns:
            list of dicts, each with keys:
                - title (str)
                - link (str): URL to original article
                - description (str): cleaned text summary
                - pub_date (str): formatted date string
                - pub_date_raw (str): ISO 8601 date for sorting
                - image (str or None): URL to thumbnail/image
                - source_name (str): name of the source
                - source_type (str): 'rss', 'youtube', or 'google_news'
                - video_id (str or None): YouTube video ID if applicable
        """
        pass

    def _matches_keywords(self, title, description=''):
        """Check if title or description matches any of the configured keywords."""
        if not self.keywords:
            return True
        text = f"{title} {description}".lower()
        return any(kw.lower() in text for kw in self.keywords)
