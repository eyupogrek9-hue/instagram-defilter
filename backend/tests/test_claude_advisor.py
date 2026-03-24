# backend/tests/test_claude_advisor.py
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np
from claude_advisor import parse_corrections, apply_corrections, get_claude_corrections


def make_grey_image(size: int = 64) -> Image.Image:
    array = np.full((size, size, 3), 128, dtype=np.uint8)
    return Image.fromarray(array)


def test_parse_corrections_reduce_warmth():
    corrections = parse_corrections("reduce warmth by 20%")
    assert "warmth" in corrections
    assert corrections["warmth"] == pytest.approx(-0.20)


def test_parse_corrections_increase_brightness_slightly():
    corrections = parse_corrections("increase brightness slightly")
    assert "brightness" in corrections
    assert corrections["brightness"] > 0


def test_parse_corrections_lower_saturation():
    corrections = parse_corrections("lower saturation by 10%")
    assert "saturation" in corrections
    assert corrections["saturation"] == pytest.approx(-0.10)


def test_parse_corrections_no_adjustment():
    corrections = parse_corrections("no adjustments needed")
    assert corrections == {}


def test_parse_corrections_empty_string():
    corrections = parse_corrections("")
    assert corrections == {}


def test_apply_corrections_returns_pil_image():
    img = make_grey_image()
    result = apply_corrections(img, {"brightness": 0.1})
    assert isinstance(result, Image.Image)


def test_apply_corrections_empty_dict_returns_unchanged():
    img = make_grey_image()
    result = apply_corrections(img, {})
    assert list(result.getdata()) == list(img.getdata())


def test_get_claude_corrections_returns_empty_on_api_failure():
    with patch("claude_advisor.anthropic.Anthropic") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API unavailable")
        img = make_grey_image()
        result = get_claude_corrections(img, img)
    assert result == {}
