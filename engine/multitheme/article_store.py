"""JSON-based article database for persistence across builds."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from .utils import create_slug


class ArticleStore:
    """Manages a persistent JSON database of articles.

    Articles are identified by their slug (derived from title).
    New articles are merged in; existing articles are never deleted.
    """

    def __init__(self, data_dir):
        """Initialize the store.

        Args:
            data_dir: Path to data/ directory containing articles.json
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / 'articles.json'
        self.articles = self._load()

    def _load(self):
        """Load articles from disk."""
        if not self.db_path.exists():
            return {}
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # data is a dict keyed by slug
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError):
            return {}

    def save(self):
        """Persist articles to disk."""
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.articles, f, indent=2, ensure_ascii=False)

    def merge(self, new_articles):
        """Merge new articles into the store.

        New articles (by slug) are added. Existing articles are updated
        only if they have a newer date.

        Args:
            new_articles: list of article dicts from source handlers.

        Returns:
            Number of new articles added.
        """
        added = 0
        for article in new_articles:
            slug = create_slug(article['title'])
            if not slug:
                continue

            article['slug'] = slug

            if slug not in self.articles:
                self.articles[slug] = article
                added += 1
            else:
                # Update if same slug but potentially fresher data
                existing = self.articles[slug]
                if article.get('pub_date_raw', '') > existing.get('pub_date_raw', ''):
                    self.articles[slug] = article

        return added

    def get_recent(self, max_age_days=30, limit=20):
        """Get recent articles sorted by date (newest first).

        Args:
            max_age_days: Maximum age in days for articles to include.
            limit: Maximum number of articles to return.

        Returns:
            List of article dicts.
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        cutoff_str = cutoff.isoformat()

        recent = [
            a for a in self.articles.values()
            if a.get('pub_date_raw', '') >= cutoff_str
        ]

        recent.sort(key=lambda x: x.get('pub_date_raw', ''), reverse=True)
        return recent[:limit]

    def get_all(self):
        """Get all articles sorted by date (newest first)."""
        all_articles = list(self.articles.values())
        all_articles.sort(key=lambda x: x.get('pub_date_raw', ''), reverse=True)
        return all_articles
