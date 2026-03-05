"""Utility functions for slug generation, HTML cleaning, and date formatting."""

import html
import re
import unicodedata
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
    """Extract the URL of the first image from HTML content."""
    if not html_content:
        return None
    img_match = re.search(
        r'src=["\']([^"\']+\.(?:jpg|jpeg|png|gif|webp))["\']',
        html_content, re.IGNORECASE
    )
    if img_match:
        return img_match.group(1)
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
