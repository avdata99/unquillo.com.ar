"""Utility functions for slug generation, HTML cleaning, and date formatting."""

import html
import re
import unicodedata
import urllib.request
from datetime import datetime


def create_slug(text):
    """Create a URL-friendly slug from text.

    Converts "Mi Título Con Ñ" -> "mi-titulo-con-n"
    """
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    text = text[:100].strip('-')
    return text


def clean_html(text):
    """Remove HTML tags and decode entities."""
    if not text:
        return ''
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_first_image(html_content):
    """Extract the URL of the first image from HTML content.

    Tries multiple strategies, from most specific to most permissive:
    1. img src with known image extensions
    2. img src with any URL (CDN images often lack extensions)
    3. Any URL that looks like an image (in attributes, og:image, etc.)
    """
    if not html_content:
        return None
    # 1. img src with known image extension
    img_match = re.search(
        r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|gif|webp)(?:\?[^"\']*)?)["\']',
        html_content, re.IGNORECASE
    )
    if img_match:
        return img_match.group(1)
    # 2. Any img src (CDN URLs without extensions)
    img_match = re.search(
        r'<img[^>]+src=["\']([^"\']+://[^"\']+)["\']',
        html_content, re.IGNORECASE
    )
    if img_match:
        url = img_match.group(1)
        if _looks_like_image_url(url):
            return url
    # 3. og:image or twitter:image meta tags
    og_match = re.search(
        r'content=["\']([^"\']+://[^"\']+)["\'][^>]*property=["\']og:image["\']',
        html_content, re.IGNORECASE
    ) or re.search(
        r'property=["\']og:image["\'][^>]*content=["\']([^"\']+://[^"\']+)["\']',
        html_content, re.IGNORECASE
    )
    if og_match:
        return og_match.group(1)
    # 4. Last resort: any img src at all
    img_match = re.search(
        r'<img[^>]+src=["\']([^"\']{10,})["\']',
        html_content, re.IGNORECASE
    )
    if img_match:
        return img_match.group(1)
    return None


def _looks_like_image_url(url):
    """Check if a URL likely points to an image (even without extension)."""
    skip_patterns = ['.js', '.css', '.svg', 'data:image/svg',
                     'pixel', 'tracking', 'beacon', '1x1',
                     'spacer', 'blank']
    url_lower = url.lower()
    return not any(p in url_lower for p in skip_patterns)


def extract_media_image(item):
    """Extract image from RSS media elements (media:content, media:thumbnail, enclosure)."""
    # media:thumbnail
    for ns in ['http://search.yahoo.com/mrss/', 'http://www.rssboard.org/media-rss']:
        thumb = item.find(f'{{{ns}}}thumbnail')
        if thumb is not None:
            url = thumb.get('url')
            if url:
                return url
        # media:content with medium="image"
        content = item.find(f'{{{ns}}}content')
        if content is not None and content.get('medium') == 'image':
            url = content.get('url')
            if url:
                return url
        # media:content without medium but with image type
        if content is not None and 'image' in (content.get('type', '')):
            url = content.get('url')
            if url:
                return url

    # enclosure with image type
    enclosure = item.find('enclosure')
    if enclosure is not None and 'image' in (enclosure.get('type', '')):
        url = enclosure.get('url')
        if url:
            return url

    return None


def fetch_og_image(url, timeout=10):
    """Fetch a URL and extract the og:image meta tag from the HTML."""
    if not url:
        return None
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=timeout) as response:
            # Read only first 50KB to find og:image quickly
            content = response.read(51200).decode('utf-8', errors='ignore')
        # og:image
        og_match = re.search(
            r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            content, re.IGNORECASE
        ) or re.search(
            r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
            content, re.IGNORECASE
        )
        if og_match:
            return og_match.group(1)
    except Exception:
        pass
    return None


def format_rss_date(date_str):
    """Format RSS date (RFC 822) to dd/mm/yyyy."""
    if not date_str:
        return ''
    try:
        dt = datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S')
        return dt.strftime('%d/%m/%Y')
    except (ValueError, IndexError):
        return date_str


def format_iso_date(date_str):
    """Format ISO 8601 date to dd/mm/yyyy.

    YouTube uses: 2026-02-09T21:35:27+00:00
    """
    if not date_str:
        return ''
    try:
        date_clean = date_str.split('+')[0].split('Z')[0]
        dt = datetime.strptime(date_clean, '%Y-%m-%dT%H:%M:%S')
        return dt.strftime('%d/%m/%Y')
    except (ValueError, IndexError):
        return date_str


def parse_iso_date(date_str):
    """Parse ISO 8601 date string to datetime object."""
    if not date_str:
        return datetime.min
    try:
        date_clean = date_str.split('+')[0].split('Z')[0]
        return datetime.strptime(date_clean, '%Y-%m-%dT%H:%M:%S')
    except (ValueError, IndexError):
        return datetime.min


def parse_rss_date(date_str):
    """Parse RSS date (RFC 822) to datetime object."""
    if not date_str:
        return datetime.min
    try:
        return datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S')
    except (ValueError, IndexError):
        return datetime.min


def truncate(text, max_length):
    """Truncate text to max_length, adding ellipsis if needed."""
    if not text or len(text) <= max_length:
        return text
    return text[:max_length] + '...'
