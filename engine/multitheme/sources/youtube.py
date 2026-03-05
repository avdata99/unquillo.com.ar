"""YouTube feed source handler with automatic channel_id resolution."""

import json
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path

from .base import Source
from ..utils import clean_html, format_iso_date, parse_iso_date, truncate


class YouTubeSource(Source):
    """Fetch videos from YouTube channel feeds."""

    # Cache file path (set by builder before fetching)
    cache_dir = None

    def fetch(self):
        """Fetch videos from a YouTube channel."""
        channel = self.source_config.get('channel', '')
        channel_id = self.source_config.get('channel_id', '')
        max_desc = self.site_config.get('content', {}).get('max_description_length', 250)

        # Resolve channel_id if not provided directly
        if not channel_id:
            if not channel:
                print(f"  [!] YouTube source '{self.name}' has no channel or channel_id, skipping")
                return []
            channel_id = self._resolve_channel_id(channel)
            if not channel_id:
                print(f"  [!] Could not resolve channel_id for '{channel}', skipping")
                return []

        feed_url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'

        try:
            print(f"  Fetching YouTube: {self.name} ({channel or channel_id})")
            content = self._download(feed_url)
            return self._parse(content, max_desc)
        except Exception as e:
            print(f"  [!] Error fetching YouTube '{self.name}': {e}")
            return []

    def _resolve_channel_id(self, channel):
        """Resolve a YouTube handle or URL to a channel_id.

        Checks cache first, then scrapes the channel page.
        """
        # Normalize: extract handle from URL if needed
        handle = channel.strip('/')
        if 'youtube.com' in handle:
            # Extract @handle from URL
            match = re.search(r'youtube\.com/(@[^/\s?]+)', handle)
            if match:
                handle = match.group(1)
            else:
                # Try channel URL format
                match = re.search(r'youtube\.com/channel/([^/\s?]+)', handle)
                if match:
                    return match.group(1)

        if not handle.startswith('@'):
            handle = f'@{handle}'

        # Check cache
        cached_id = self._get_cached_id(handle)
        if cached_id:
            print(f"    Using cached channel_id for {handle}")
            return cached_id

        # Scrape channel page
        print(f"    Resolving channel_id for {handle}...")
        try:
            req = urllib.request.Request(
                f'https://www.youtube.com/{handle}',
                headers={
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                }
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                page_content = response.read().decode('utf-8')

            # Look for channel_id in page source
            match = re.search(r'channel_id=([^"&\s]+)', page_content)
            if not match:
                match = re.search(r'"channelId"\s*:\s*"([^"]+)"', page_content)

            if match:
                channel_id = match.group(1)
                self._cache_id(handle, channel_id)
                print(f"    Resolved: {handle} -> {channel_id}")
                return channel_id

        except Exception as e:
            print(f"    [!] Error resolving {handle}: {e}")

        return None

    def _get_cached_id(self, handle):
        """Look up channel_id in cache file."""
        cache_file = self._cache_file()
        if not cache_file or not cache_file.exists():
            return None
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            return cache.get(handle)
        except (json.JSONDecodeError, IOError):
            return None

    def _cache_id(self, handle, channel_id):
        """Save channel_id to cache file."""
        cache_file = self._cache_file()
        if not cache_file:
            return

        cache = {}
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        cache[handle] = channel_id
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2)

    def _cache_file(self):
        """Return path to the youtube_channels.json cache file."""
        if self.cache_dir:
            return Path(self.cache_dir) / 'youtube_channels.json'
        return None

    def _download(self, url):
        """Download feed content from URL."""
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8')

    def _parse(self, content, max_desc):
        """Parse YouTube Atom feed XML into article dicts."""
        xml_start = content.find('<?xml')
        if xml_start > 0:
            content = content[xml_start:]

        root = ET.fromstring(content)

        ns = {
            'atom': 'http://www.w3.org/2005/Atom',
            'media': 'http://search.yahoo.com/mrss/',
            'yt': 'http://www.youtube.com/xml/schemas/2015'
        }

        articles = []
        # YouTube RSS returns max 15 entries; scan all of them for keyword matches
        for entry in root.findall('atom:entry', ns):
            title_elem = entry.find('atom:title', ns)
            title = title_elem.text if title_elem is not None else ''

            desc_elem = entry.find('.//media:description', ns)
            raw_desc = desc_elem.text if desc_elem is not None else ''

            if not self._matches_keywords(title, raw_desc):
                continue

            link_elem = entry.find('atom:link[@rel="alternate"]', ns)
            link = link_elem.get('href') if link_elem is not None else ''

            published_elem = entry.find('atom:published', ns)
            published = published_elem.text if published_elem is not None else ''

            author_elem = entry.find('atom:author/atom:name', ns)
            author = author_elem.text if author_elem is not None else self.name

            thumbnail_elem = entry.find('.//media:thumbnail', ns)
            thumbnail = thumbnail_elem.get('url') if thumbnail_elem is not None else None

            description = clean_html(raw_desc)

            video_id_elem = entry.find('yt:videoId', ns)
            video_id = video_id_elem.text if video_id_elem is not None else ''

            if not thumbnail and video_id:
                thumbnail = f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'

            dt = parse_iso_date(published)

            articles.append({
                'title': title,
                'link': link,
                'description': description,
                'pub_date': format_iso_date(published),
                'pub_date_raw': dt.isoformat(),
                'image': thumbnail,
                'source_name': author,
                'source_type': 'youtube',
                'video_id': video_id,
            })

            if len(articles) >= self.limit:
                break

        print(f"    Found {len(articles)} videos")
        return articles
