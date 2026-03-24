# backend/tests/test_scraper.py
import pytest
from unittest.mock import patch, MagicMock
from scraper import extract_shortcode, get_image_from_url


def test_extract_shortcode_standard_url():
    url = "https://www.instagram.com/p/ABC123xyz/"
    assert extract_shortcode(url) == "ABC123xyz"


def test_extract_shortcode_no_trailing_slash():
    url = "https://www.instagram.com/p/ABC123xyz"
    assert extract_shortcode(url) == "ABC123xyz"


def test_extract_shortcode_invalid_url():
    assert extract_shortcode("https://example.com") is None
    assert extract_shortcode("not a url") is None


def test_get_image_raises_valueerror_for_invalid_url():
    with pytest.raises(ValueError, match="Could not extract shortcode"):
        get_image_from_url("https://example.com/not-instagram")


def test_get_image_raises_filenot_found_for_missing_post():
    import instaloader
    with patch("scraper.instaloader.Post.from_shortcode") as mock_post:
        mock_post.side_effect = instaloader.exceptions.QueryReturnedNotFoundException(
            "https://instagram.com/p/NOTEXIST/", "Not found"
        )
        with pytest.raises(FileNotFoundError):
            get_image_from_url("https://www.instagram.com/p/NOTEXIST/")


def test_get_image_raises_permissionerror_for_private_post():
    import instaloader
    with patch("scraper.instaloader.Post.from_shortcode") as mock_post:
        mock_post.side_effect = instaloader.exceptions.LoginRequiredException(
            "https://instagram.com/p/PRIVATE/", "Login required"
        )
        with pytest.raises(PermissionError):
            get_image_from_url("https://www.instagram.com/p/PRIVATE/")
