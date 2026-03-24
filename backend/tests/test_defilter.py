# backend/tests/test_defilter.py
import numpy as np
import pytest
from PIL import Image
from defilter import defilter_classical, grey_world_white_balance


def make_image(r: int, g: int, b: int, size: int = 64) -> Image.Image:
    """Create a solid-color test image."""
    array = np.full((size, size, 3), [r, g, b], dtype=np.uint8)
    return Image.fromarray(array)


def average_saturation(image: Image.Image) -> float:
    """Return mean saturation (0-255) of an image in HSV space."""
    import cv2
    array = np.array(image.convert("RGB"))
    hsv = cv2.cvtColor(array, cv2.COLOR_RGB2HSV)
    return float(hsv[:, :, 1].mean())


def test_defilter_returns_pil_image():
    img = make_image(200, 150, 100)
    result = defilter_classical(img)
    assert isinstance(result, Image.Image)
    assert result.mode == "RGB"


def test_defilter_reduces_saturation_of_oversaturated_image():
    # Warm orange image — high saturation
    img = make_image(255, 100, 0)
    original_sat = average_saturation(img)
    result = defilter_classical(img)
    result_sat = average_saturation(result)
    assert result_sat < original_sat


def test_defilter_preserves_image_dimensions():
    img = make_image(180, 160, 140, size=128)
    result = defilter_classical(img)
    assert result.size == img.size


def test_defilter_brightens_dark_midtones():
    # Dark grey image — gamma > 1 should brighten midtones
    img = make_image(80, 80, 80)
    result = defilter_classical(img)
    result_brightness = np.array(result).mean()
    original_brightness = np.array(img).mean()
    assert result_brightness > original_brightness


def test_grey_world_balances_red_shifted_image():
    # All-red image — grey world should shift R down and B up
    array = np.zeros((64, 64, 3), dtype=np.uint8)
    array[:, :, 0] = 200  # R=200, G=0, B=0
    result = grey_world_white_balance(array)
    # After balancing, R should be lower and channels more equal
    assert result[:, :, 0].mean() < 200
