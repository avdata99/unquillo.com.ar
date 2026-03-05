"""Download, resize, and cache article images as local thumbnails.

Images are stored in {output_dir}/img/ with filenames derived from
a SHA-256 hash of the original URL, avoiding any collision issues.
Already-cached images are skipped on subsequent builds.
"""

import hashlib
import io
import urllib.request
from pathlib import Path

from PIL import Image

# Thumbnail constraints
MAX_WIDTH = 400
MAX_HEIGHT = 300
JPEG_QUALITY = 80


def process_articles(articles, output_dir):
    """Download and cache images for a list of articles.

    Modifies each article's 'image' field in-place to point to the
    local thumbnail path (/img/xxx.jpg).
    Articles without images are skipped.

    Args:
        articles: list of article dicts (modified in-place)
        output_dir: Path to the site output directory (e.g. docs/)
    """
    output_dir = Path(output_dir)
    img_dir = output_dir / 'img'
    img_dir.mkdir(parents=True, exist_ok=True)

    total = sum(1 for a in articles if a.get('image'))
    cached = 0
    downloaded = 0
    failed = 0

    print(f"\nCaching images...")
    print(f"  Articles with images: {total}")

    for article in articles:
        original_url = article.get('image_original') or article.get('image')
        if not original_url:
            continue

        # YouTube thumbnails are already served from a fast CDN, skip
        if article.get('source_type') == 'youtube':
            continue

        filename = _url_to_filename(original_url)
        local_path = img_dir / filename

        # Preserve original URL for future re-downloads
        article['image_original'] = original_url

        if local_path.exists():
            cached += 1
            article['image'] = f'/img/{filename}'
            continue

        print(f"    Downloading: {original_url[:80]}...")
        image_data = _download_image(original_url)
        if not image_data:
            failed += 1
            print(f"    [!] Failed to download")
            continue

        thumbnail_data = _create_thumbnail(image_data)
        if not thumbnail_data:
            failed += 1
            print(f"    [!] Failed to process image")
            continue

        local_path.write_bytes(thumbnail_data)
        size_kb = len(thumbnail_data) / 1024
        article['image'] = f'/img/{filename}'
        downloaded += 1
        print(f"    [ok] {filename} ({size_kb:.1f} KB)")

    print(f"  Results: {downloaded} downloaded, {cached} cached, {failed} failed")


def _url_to_filename(url):
    """Convert a URL to a unique filename using SHA-256 hash."""
    url_hash = hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]
    return f'{url_hash}.jpg'


def _download_image(url, timeout=15):
    """Download image data from a URL. Returns bytes or None."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        })
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()
    except Exception:
        return None


def _create_thumbnail(image_data):
    """Resize image to thumbnail and convert to JPEG. Returns bytes or None."""
    try:
        img = Image.open(io.BytesIO(image_data))
        img = img.convert('RGB')
        img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        return buffer.getvalue()
    except Exception:
        return None
