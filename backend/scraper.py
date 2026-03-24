# backend/scraper.py
import re
import instaloader
import httpx


def extract_shortcode(url: str) -> str | None:
    """Extract Instagram post shortcode from URL."""
    match = re.search(r'instagram\.com/p/([A-Za-z0-9_-]+)', url)
    return match.group(1) if match else None


def get_image_from_url(url: str) -> tuple[bytes, str, bool]:
    """
    Fetch image bytes, CDN URL, and carousel flag from an Instagram post URL.

    Returns: (image_bytes, cdn_url, is_carousel)
    Raises:
        ValueError: URL is not a valid Instagram post URL
        FileNotFoundError: Post does not exist or was deleted
        PermissionError: Post is private or requires login
        RuntimeError: Instagram rate-limited the request
        Exception: Any other fetch failure
    """
    shortcode = extract_shortcode(url)
    if not shortcode:
        raise ValueError(f"Could not extract shortcode from URL: {url}")

    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        quiet=True,
    )

    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
    except instaloader.exceptions.QueryReturnedNotFoundException:
        raise FileNotFoundError(f"Post not found: {shortcode}")
    except instaloader.exceptions.LoginRequiredException:
        raise PermissionError("Post is private or requires login")
    except instaloader.exceptions.TooManyRequestsException:
        raise RuntimeError("Rate limited by Instagram")

    is_carousel = post.typename == "GraphSidecar"
    cdn_url = post.url  # first image for carousels

    response = httpx.get(cdn_url, follow_redirects=True, timeout=30)
    response.raise_for_status()

    return response.content, cdn_url, is_carousel
