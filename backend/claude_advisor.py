# backend/claude_advisor.py
import re
import base64
import io

import anthropic
from PIL import Image, ImageEnhance


def _image_to_base64_jpeg(image: Image.Image) -> str:
    """Encode PIL image as base64 JPEG string."""
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=85)
    return base64.standard_b64encode(buffer.getvalue()).decode()


def get_claude_corrections(
    original: Image.Image,
    processed: Image.Image,
) -> dict[str, float]:
    """
    Ask Claude to suggest remaining color corrections.
    Returns a dict of adjustment factors (e.g. {'brightness': 0.05}).
    Returns empty dict on any API failure (caller handles degradation).
    """
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": _image_to_base64_jpeg(original),
                            },
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": _image_to_base64_jpeg(processed),
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "The first image is Instagram-filtered. "
                                "The second is after classical de-filtering. "
                                "Describe what color adjustments (if any) are still needed "
                                "to make the second image look like a natural, unfiltered photo. "
                                "Be specific: e.g., 'reduce warmth by 20%', "
                                "'lower saturation by 10%', 'increase brightness slightly'. "
                                "If no adjustments are needed, say 'no adjustments needed'."
                            ),
                        },
                    ],
                }
            ],
        )
        text = response.content[0].text
        return parse_corrections(text)
    except Exception:
        return {}


def parse_corrections(text: str) -> dict[str, float]:
    """Parse Claude's free-text response into numeric adjustment factors."""
    adjustments: dict[str, float] = {}

    # Warmth: "reduce warmth by 20%" / "increase warmth by 15%"
    m = re.search(r"(reduce|increase)\s+warmth\s+by\s+(\d+)%", text, re.IGNORECASE)
    if m:
        sign = -1 if m.group(1).lower() == "reduce" else 1
        adjustments["warmth"] = sign * int(m.group(2)) / 100

    # Saturation: "lower/reduce/increase saturation by N%"
    m = re.search(
        r"(lower|reduce|increase)\s+saturation\s+by\s+(\d+)%", text, re.IGNORECASE
    )
    if m:
        sign = -1 if m.group(1).lower() in ("lower", "reduce") else 1
        adjustments["saturation"] = sign * int(m.group(2)) / 100

    # Brightness: "increase/reduce brightness slightly/moderately/significantly"
    m = re.search(
        r"(increase|reduce)\s+brightness\s*(slightly|moderately|significantly)?",
        text,
        re.IGNORECASE,
    )
    if m:
        sign = 1 if m.group(1).lower() == "increase" else -1
        magnitude_map = {
            "slightly": 0.05,
            "moderately": 0.10,
            "significantly": 0.20,
            None: 0.05,
        }
        word = m.group(2).lower() if m.group(2) else None
        adjustments["brightness"] = sign * magnitude_map[word]

    return adjustments


def apply_corrections(image: Image.Image, corrections: dict[str, float]) -> Image.Image:
    """Apply numeric correction factors to a PIL image via ImageEnhance."""
    result = image.copy()

    if "brightness" in corrections:
        result = ImageEnhance.Brightness(result).enhance(1 + corrections["brightness"])

    if "saturation" in corrections:
        result = ImageEnhance.Color(result).enhance(1 + corrections["saturation"])

    # warmth: shift color temperature via R/B channel adjustment
    if "warmth" in corrections:
        import numpy as np
        arr = np.array(result.convert("RGB")).astype(np.float32)
        factor = corrections["warmth"]
        arr[:, :, 0] = np.clip(arr[:, :, 0] * (1 + factor), 0, 255)   # R
        arr[:, :, 2] = np.clip(arr[:, :, 2] * (1 - factor), 0, 255)   # B (inverse)
        result = Image.fromarray(arr.astype(np.uint8))

    return result
