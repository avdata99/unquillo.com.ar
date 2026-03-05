"""WordPress-specific utilities for extracting data via the WP REST API.

Many RSS feeds come from WordPress sites that expose a REST API at
/wp-json/wp/v2/posts/{id}. WordPress feeds include the post ID in a
<post-id xmlns="com-wordpress:feed-additions:1"> element, which we can
use to query the API for richer data like featured images.
"""

import json
import urllib.request
import urllib.parse

# WordPress feed-additions namespace
WP_NS = 'com-wordpress:feed-additions:1'


def extract_wp_post_id(item):
    """Extract the WordPress post ID from an RSS <item> element.

    Returns the post ID string, or None if not a WordPress feed.
    """
    post_id_elem = item.find(f'{{{WP_NS}}}post-id')
    if post_id_elem is not None and post_id_elem.text:
        return post_id_elem.text.strip()
    return None


def extract_wp_site_url(feed_link):
    """Derive the WordPress site base URL from an article link.

    Given 'https://elmilenio.info/2026/03/nota/', returns 'https://elmilenio.info'.
    """
    if not feed_link:
        return None
    parsed = urllib.parse.urlparse(feed_link)
    if parsed.scheme and parsed.netloc:
        return f'{parsed.scheme}://{parsed.netloc}'
    return None


def fetch_wp_featured_image(site_url, post_id, timeout=10):
    """Fetch the featured image URL from the WordPress REST API.

    Queries: {site_url}/wp-json/wp/v2/posts/{post_id}
    Looks for 'featured_image_urls' (Flavor 1: jetpack/some themes)
    and falls back to fetching the media endpoint via 'featured_media'.

    Returns the image URL string, or None.
    """
    if not site_url or not post_id:
        return None

    api_url = f'{site_url}/wp-json/wp/v2/posts/{post_id}'

    try:
        post_data = _fetch_json(api_url, timeout)
        if not post_data:
            return None

        # Strategy 1: featured_image_urls (Jetpack / some themes inject this)
        featured_urls = post_data.get('featured_image_urls')
        if isinstance(featured_urls, dict):
            # Try 'full' first, then any available size
            for size_key in ('full', 'large', 'medium_large', 'medium'):
                size_data = featured_urls.get(size_key)
                if isinstance(size_data, list) and size_data:
                    return size_data[0]
            # Any key will do
            for size_data in featured_urls.values():
                if isinstance(size_data, list) and size_data:
                    return size_data[0]

        # Strategy 2: featured_media ID -> /wp-json/wp/v2/media/{id}
        media_id = post_data.get('featured_media')
        if media_id and int(media_id) > 0:
            return _fetch_media_url(site_url, media_id, timeout)

    except Exception:
        pass

    return None


def _fetch_media_url(site_url, media_id, timeout=10):
    """Fetch image URL from the WordPress media endpoint."""
    media_url = f'{site_url}/wp-json/wp/v2/media/{media_id}'
    try:
        media_data = _fetch_json(media_url, timeout)
        if not media_data:
            return None

        # source_url is the direct link to the image
        source_url = media_data.get('source_url')
        if source_url:
            return source_url

        # Alternative: media_details.sizes
        sizes = media_data.get('media_details', {}).get('sizes', {})
        for size_key in ('full', 'large', 'medium_large', 'medium'):
            size_info = sizes.get(size_key, {})
            if size_info.get('source_url'):
                return size_info['source_url']

    except Exception:
        pass
    return None


def _fetch_json(url, timeout=10):
    """Fetch a URL and parse the response as JSON."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        'Accept': 'application/json',
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))
