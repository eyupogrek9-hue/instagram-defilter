# Instagram De-Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python/FastAPI API that accepts an Instagram post URL and returns a de-filtered version of the image using classical image processing + Claude vision, with a React web frontend and Expo mobile app showing side-by-side comparisons.

**Architecture:** FastAPI backend orchestrates Instagram scraping (instaloader), classical de-filtering (OpenCV + Pillow), and a Claude vision secondary pass. React and Expo frontends call the same `/defilter` endpoint and display original vs processed side-by-side.

**Tech Stack:** Python 3.11, FastAPI, instaloader, OpenCV, Pillow, Anthropic SDK (claude-opus-4-6), pytest; React 19 + Vite + Tailwind CSS 4; Expo (React Native)

---

## File Map

### Backend (`backend/`)

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, `/defilter` endpoint, error mapping |
| `scraper.py` | Instagram URL scraping via instaloader |
| `defilter.py` | Classical image processing (CLAHE, white balance, saturation) |
| `claude_advisor.py` | Claude vision call, correction parsing, Pillow application |
| `requirements.txt` | Python dependencies |
| `Procfile` | Railway deployment command |
| `tests/test_defilter.py` | Unit tests for classical processing |
| `tests/test_scraper.py` | Unit tests for scraper + URL parsing |
| `tests/test_claude_advisor.py` | Unit tests for correction parsing + application |
| `tests/test_api.py` | Integration tests for the FastAPI endpoint |

### Frontend (`frontend/`)

| File | Responsibility |
|---|---|
| `src/App.tsx` | Single-page app: URL input, API call, side-by-side result |
| `src/env.d.ts` | VITE_API_URL type declaration |
| `index.html` | Vite entry |
| `package.json` | Dependencies |
| `vite.config.ts` | Vite + React config |
| `vercel.json` | SPA rewrite rule |

### Mobile (`mobile/`)

| File | Responsibility |
|---|---|
| `App.tsx` | Full screen: URL input, API call, side-by-side result, save to camera roll |
| `package.json` | Expo dependencies |
| `app.json` | Expo config |

---

## Task 1: Backend project setup

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/Procfile`
- Create: `backend/tests/__init__.py`

- [ ] **Step 1: Create backend directory and requirements.txt**

```
backend/requirements.txt
```

```
fastapi==0.115.6
uvicorn[standard]==0.32.1
instaloader==4.13.1
opencv-python-headless==4.10.0.84
Pillow==11.0.0
anthropic==0.40.0
httpx==0.27.2
pytest==8.3.4
pytest-asyncio==0.24.0
python-multipart==0.0.18
```

- [ ] **Step 2: Create Procfile**

```
backend/Procfile
```

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 3: Create tests directory**

```bash
mkdir -p backend/tests && touch backend/tests/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
cd backend && pip install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "chore: backend project setup"
```

---

## Task 2: Instagram scraper

**Files:**
- Create: `backend/scraper.py`
- Create: `backend/tests/test_scraper.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_scraper.py -v
```

Expected: FAIL — `scraper` module not found.

- [ ] **Step 3: Implement scraper.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_scraper.py -v
```

Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/scraper.py backend/tests/test_scraper.py
git commit -m "feat: Instagram scraper with URL parsing and error handling"
```

---

## Task 3: Classical de-filter engine

**Files:**
- Create: `backend/defilter.py`
- Create: `backend/tests/test_defilter.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_defilter.py -v
```

Expected: FAIL — `defilter` module not found.

- [ ] **Step 3: Implement defilter.py**

```python
# backend/defilter.py
import cv2
import numpy as np
from PIL import Image


def grey_world_white_balance(img: np.ndarray) -> np.ndarray:
    """Apply Grey World assumption white balance correction."""
    result = img.astype(np.float32)
    avg_r = result[:, :, 0].mean()
    avg_g = result[:, :, 1].mean()
    avg_b = result[:, :, 2].mean()
    avg = (avg_r + avg_g + avg_b) / 3

    if avg_r > 0:
        result[:, :, 0] = np.clip(result[:, :, 0] * (avg / avg_r), 0, 255)
    if avg_g > 0:
        result[:, :, 1] = np.clip(result[:, :, 1] * (avg / avg_g), 0, 255)
    if avg_b > 0:
        result[:, :, 2] = np.clip(result[:, :, 2] * (avg / avg_b), 0, 255)

    return result.astype(np.uint8)


def defilter_classical(image: Image.Image) -> Image.Image:
    """
    Apply classical de-filtering to remove Instagram-style color grading.

    Steps:
    1. CLAHE on luminance channel (LAB) — normalize contrast
    2. Grey World white balance — correct color temperature shifts
    3. Reduce saturation by 15% — counter Instagram's saturation boost
    4. Gamma correction (gamma=1.15) — brighten midtones, counter contrast boost
    """
    img_array = np.array(image.convert("RGB"))

    # Step 1: CLAHE on L channel in LAB space
    lab = cv2.cvtColor(img_array, cv2.COLOR_RGB2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_channel = clahe.apply(l_channel)
    lab = cv2.merge([l_channel, a_channel, b_channel])
    img_array = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    # Step 2: White balance
    img_array = grey_world_white_balance(img_array)

    # Step 3: Reduce saturation
    hsv = cv2.cvtColor(img_array, cv2.COLOR_RGB2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 0.85, 0, 255)
    img_array = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

    # Step 4: Contrast flattening via gamma correction (pull midtones toward linear)
    # gamma > 1 brightens midtones, counteracting the typical Instagram contrast boost
    gamma = 1.15
    inv_gamma = 1.0 / gamma
    lut = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)], dtype=np.uint8)
    img_array = cv2.LUT(img_array, lut)

    return Image.fromarray(img_array)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_defilter.py -v
```

Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/defilter.py backend/tests/test_defilter.py
git commit -m "feat: classical de-filter engine (CLAHE + white balance + saturation)"
```

---

## Task 4: Claude vision advisor

**Files:**
- Create: `backend/claude_advisor.py`
- Create: `backend/tests/test_claude_advisor.py`

- [ ] **Step 1: Write failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_claude_advisor.py -v
```

Expected: FAIL — `claude_advisor` module not found.

- [ ] **Step 3: Implement claude_advisor.py**

```python
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
    Raises on any API failure — caller (main.py) handles degradation.
    """
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
        import cv2
        arr = np.array(result.convert("RGB")).astype(np.float32)
        factor = corrections["warmth"]
        arr[:, :, 0] = np.clip(arr[:, :, 0] * (1 + factor), 0, 255)   # R
        arr[:, :, 2] = np.clip(arr[:, :, 2] * (1 - factor), 0, 255)   # B (inverse)
        result = Image.fromarray(arr.astype(np.uint8))

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_claude_advisor.py -v
```

Expected: 8 PASSED.

- [ ] **Step 5: Commit**

```bash
git add backend/claude_advisor.py backend/tests/test_claude_advisor.py
git commit -m "feat: Claude vision advisor with correction parsing and application"
```

---

## Task 5: FastAPI endpoint

**Files:**
- Create: `backend/main.py`
- Create: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api.py
import base64
import io
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np


def make_image_bytes() -> bytes:
    array = np.full((64, 64, 3), 128, dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(array).save(buf, format="JPEG")
    return buf.getvalue()


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_defilter_success(client):
    with (
        patch("main.get_image_from_url", return_value=(make_image_bytes(), "https://cdn.ig.com/test.jpg", False)),
        patch("main.get_claude_corrections", return_value={"brightness": 0.05}),
    ):
        response = client.post("/defilter", json={"url": "https://www.instagram.com/p/ABC123/"})
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "https://cdn.ig.com/test.jpg"
    assert data["processed_image"]  # non-empty base64 string
    assert data["claude_pass_applied"] is True


def test_defilter_invalid_url(client):
    with patch("main.get_image_from_url", side_effect=ValueError("bad url")):
        response = client.post("/defilter", json={"url": "https://example.com"})
    assert response.status_code == 400


def test_defilter_private_post(client):
    with patch("main.get_image_from_url", side_effect=PermissionError("private")):
        response = client.post("/defilter", json={"url": "https://www.instagram.com/p/PRIV/"})
    assert response.status_code == 403


def test_defilter_post_not_found(client):
    with patch("main.get_image_from_url", side_effect=FileNotFoundError("gone")):
        response = client.post("/defilter", json={"url": "https://www.instagram.com/p/GONE/"})
    assert response.status_code == 404


def test_defilter_rate_limited(client):
    with patch("main.get_image_from_url", side_effect=RuntimeError("Rate limited")):
        response = client.post("/defilter", json={"url": "https://www.instagram.com/p/RL/"})
    assert response.status_code == 429


def test_defilter_claude_failure_degrades_gracefully(client):
    with (
        patch("main.get_image_from_url", return_value=(make_image_bytes(), "https://cdn.ig.com/test.jpg", False)),
        patch("main.get_claude_corrections", side_effect=Exception("API down")),
    ):
        response = client.post("/defilter", json={"url": "https://www.instagram.com/p/ABC123/"})
    assert response.status_code == 200
    assert response.json()["claude_pass_applied"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_api.py -v
```

Expected: FAIL — `main` module not found.

- [ ] **Step 3: Implement main.py**

```python
# backend/main.py
import io
import base64

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image

from scraper import get_image_from_url
from defilter import defilter_classical
from claude_advisor import get_claude_corrections, apply_corrections

app = FastAPI(title="Instagram De-Filter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class DefilterRequest(BaseModel):
    url: str


class DefilterResponse(BaseModel):
    original_url: str
    processed_image: str        # base64-encoded PNG
    claude_pass_applied: bool
    is_carousel: bool           # true if post had multiple images (only first processed)


@app.post("/defilter", response_model=DefilterResponse)
def defilter(request: DefilterRequest) -> DefilterResponse:
    # Scrape
    try:
        image_bytes, original_url, is_carousel = get_image_from_url(request.url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid or malformed Instagram URL")
    except PermissionError:
        raise HTTPException(status_code=403, detail="Post is private or account is private")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Post not found or has been deleted")
    except RuntimeError:
        raise HTTPException(status_code=429, detail="Rate limited by Instagram — try again later")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not fetch image from Instagram")

    # Load image
    original_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # Classical de-filter
    processed = defilter_classical(original_image)

    # Claude vision pass (graceful degradation on failure)
    claude_applied = False
    try:
        corrections = get_claude_corrections(original_image, processed)
        if corrections:
            processed = apply_corrections(processed, corrections)
            claude_applied = True
    except Exception:
        pass

    # Encode result as base64 PNG
    buf = io.BytesIO()
    processed.save(buf, format="PNG")
    processed_b64 = base64.standard_b64encode(buf.getvalue()).decode()

    return DefilterResponse(
        original_url=original_url,
        processed_image=processed_b64,
        claude_pass_applied=claude_applied,
        is_carousel=is_carousel,
    )


@app.get("/health")
def health() -> dict:
    return {"status": "healthy"}
```

- [ ] **Step 4: Run all backend tests**

```bash
cd backend && python -m pytest tests/ -v
```

Expected: All tests PASSED (scraper + defilter + claude_advisor + api).

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_api.py
git commit -m "feat: FastAPI /defilter endpoint with full pipeline"
```

---

## Task 6: Web frontend

**Files:**
- Create: `frontend/` (full Vite project)
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/env.d.ts`
- Create: `frontend/vercel.json`

- [ ] **Step 1: Scaffold Vite + React + Tailwind CSS 4**

```bash
cd instagram-defilter
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 2: Configure Tailwind in vite.config.ts**

```typescript
// frontend/vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

- [ ] **Step 3: Add Tailwind import to src/index.css**

```css
/* frontend/src/index.css */
@import "tailwindcss";
```

- [ ] **Step 4: Create env type declaration**

```typescript
// frontend/src/env.d.ts
/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_API_URL: string
}
interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

- [ ] **Step 5: Implement App.tsx**

```tsx
// frontend/src/App.tsx
import { useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL

interface Result {
  original_url: string
  processed_image: string
  claude_pass_applied: boolean
  is_carousel: boolean
}

export default function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setResult(null)
    setError('')

    try {
      const res = await fetch(`${API_URL}/defilter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail ?? 'Something went wrong')
      } else {
        setResult(data)
      }
    } catch {
      setError('Could not reach the server')
    } finally {
      setLoading(false)
    }
  }

  function handleDownload() {
    if (!result) return
    const link = document.createElement('a')
    link.href = `data:image/png;base64,${result.processed_image}`
    link.download = 'defiltered.png'
    link.click()
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-start p-8">
      <div className="w-full max-w-2xl">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Instagram De-Filter</h1>
        <p className="text-gray-500 mb-6 text-sm">Paste an Instagram post URL to remove the filter.</p>

        <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
          <input
            type="url"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://www.instagram.com/p/..."
            required
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Processing…' : 'De-filter'}
          </button>
        </form>

        {error && (
          <p className="text-red-600 text-sm mb-4">{error}</p>
        )}

        {result && (
          <div>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Original</p>
                <img src={result.original_url} alt="Original" className="w-full rounded-lg" />
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase mb-1">De-filtered</p>
                <img
                  src={`data:image/png;base64,${result.processed_image}`}
                  alt="De-filtered"
                  className="w-full rounded-lg"
                />
              </div>
            </div>
            {result.is_carousel && (
              <p className="text-xs text-amber-600 mb-2">Only the first image was processed (carousel post)</p>
            )}
            <div className="flex items-center justify-between">
              <p className="text-xs text-gray-400">
                {result.claude_pass_applied ? '✓ Claude corrections applied' : 'Classical corrections only'}
              </p>
              <button
                onClick={handleDownload}
                className="text-sm text-blue-600 hover:underline font-medium"
              >
                Download de-filtered image
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Add vercel.json**

```json
{ "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }] }
```

- [ ] **Step 7: Verify build**

```bash
cd frontend && npm run build
```

Expected: Build completes with no TypeScript errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: React web frontend with side-by-side de-filter UI"
```

---

## Task 7: Mobile app (Expo)

**Files:**
- Create: `mobile/` (Expo project)
- Create: `mobile/App.tsx`

- [ ] **Step 1: Create Expo project and install dependencies**

```bash
cd instagram-defilter
npx create-expo-app mobile --template blank-typescript
cd mobile
npx expo install expo-media-library expo-file-system
```

- [ ] **Step 2: Implement App.tsx**

```tsx
// mobile/App.tsx
import { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, Image,
  ScrollView, ActivityIndicator, StyleSheet, Alert, Platform,
} from 'react-native'
import * as MediaLibrary from 'expo-media-library'
import * as FileSystem from 'expo-file-system'

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? ''

interface Result {
  original_url: string
  processed_image: string
  claude_pass_applied: boolean
  is_carousel: boolean
}

export default function App() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Result | null>(null)
  const [error, setError] = useState('')

  async function handleSubmit() {
    if (!url.trim()) return
    setLoading(true)
    setResult(null)
    setError('')
    try {
      const res = await fetch(`${API_URL}/defilter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail ?? 'Something went wrong')
      } else {
        setResult(data)
      }
    } catch {
      setError('Could not reach the server')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave() {
    if (!result) return
    const { status } = await MediaLibrary.requestPermissionsAsync()
    if (status !== 'granted') {
      Alert.alert('Permission needed', 'Allow access to save photos.')
      return
    }
    const path = `${FileSystem.cacheDirectory}defiltered.png`
    await FileSystem.writeAsStringAsync(path, result.processed_image, {
      encoding: FileSystem.EncodingType.Base64,
    })
    await MediaLibrary.saveToLibraryAsync(path)
    Alert.alert('Saved', 'De-filtered image saved to camera roll.')
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Instagram De-Filter</Text>
      <Text style={styles.subtitle}>Paste an Instagram post URL</Text>

      <TextInput
        style={styles.input}
        value={url}
        onChangeText={setUrl}
        placeholder="https://www.instagram.com/p/..."
        autoCapitalize="none"
        keyboardType="url"
      />

      <TouchableOpacity
        style={[styles.button, loading && styles.buttonDisabled]}
        onPress={handleSubmit}
        disabled={loading}
      >
        {loading
          ? <ActivityIndicator color="#fff" />
          : <Text style={styles.buttonText}>De-filter</Text>}
      </TouchableOpacity>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      {result && (
        <View style={styles.results}>
          <View style={styles.imageRow}>
            <View style={styles.imageCol}>
              <Text style={styles.label}>ORIGINAL</Text>
              <Image source={{ uri: result.original_url }} style={styles.image} />
            </View>
            <View style={styles.imageCol}>
              <Text style={styles.label}>DE-FILTERED</Text>
              <Image
                source={{ uri: `data:image/png;base64,${result.processed_image}` }}
                style={styles.image}
              />
            </View>
          </View>
          <TouchableOpacity style={styles.saveButton} onPress={handleSave}>
            <Text style={styles.saveText}>Save to Camera Roll</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, padding: 20, paddingTop: 60, backgroundColor: '#f9f9f9' },
  title: { fontSize: 24, fontWeight: 'bold', color: '#111', marginBottom: 4 },
  subtitle: { fontSize: 14, color: '#888', marginBottom: 20 },
  input: {
    borderWidth: 1, borderColor: '#ddd', borderRadius: 10,
    paddingHorizontal: 14, paddingVertical: 10, fontSize: 14,
    backgroundColor: '#fff', marginBottom: 12,
  },
  button: {
    backgroundColor: '#2563eb', borderRadius: 10, paddingVertical: 12,
    alignItems: 'center', marginBottom: 12,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: '#fff', fontWeight: '600', fontSize: 15 },
  error: { color: '#dc2626', fontSize: 13, marginBottom: 12 },
  results: { marginTop: 8 },
  imageRow: { flexDirection: 'row', gap: 8 },
  imageCol: { flex: 1 },
  label: { fontSize: 10, fontWeight: '700', color: '#888', marginBottom: 4, letterSpacing: 1 },
  image: { width: '100%', aspectRatio: 1, borderRadius: 8, backgroundColor: '#eee' },
  saveButton: { marginTop: 12, padding: 12, backgroundColor: '#f0f0f0', borderRadius: 10, alignItems: 'center' },
  saveText: { fontSize: 14, color: '#2563eb', fontWeight: '600' },
})
```

- [ ] **Step 3: Verify the app runs**

Start the backend locally: `cd backend && uvicorn main:app --reload`
Then: `cd mobile && EXPO_PUBLIC_API_URL=http://localhost:8000 npx expo start`

Open in Expo Go. Paste a public Instagram URL. Verify side-by-side result appears.

- [ ] **Step 4: Commit**

```bash
git add mobile/
git commit -m "feat: Expo mobile app with side-by-side de-filter and save to camera roll"
```

---

## Task 8: Deployment config

**Files:**
- Create: `backend/railway.toml`
- Create: `backend/.env.example`

- [ ] **Step 1: Create railway.toml**

```toml
# backend/railway.toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
```

- [ ] **Step 2: Create .env.example**

```bash
# backend/.env.example
ANTHROPIC_API_KEY=your_key_here
```

- [ ] **Step 3: Create root .gitignore**

```
# .gitignore
__pycache__/
*.pyc
.env
*.db
backend/.venv/
frontend/node_modules/
frontend/dist/
mobile/node_modules/
mobile/.expo/
```

- [ ] **Step 4: Commit**

```bash
git add backend/railway.toml backend/.env.example .gitignore
git commit -m "chore: deployment config for Railway and Vercel"
```

---

## Deployment Steps (not automated — do these manually)

**Backend (Railway):**
1. Create GitHub repo `instagram-defilter` and push: `git remote add origin https://TOKEN@github.com/eyupogrek9-hue/instagram-defilter.git && git push -u origin master`
2. Railway: New Project → Deploy from GitHub → root directory: `backend`
3. Add env var: `ANTHROPIC_API_KEY`
4. Note the Railway URL (e.g., `https://instagram-defilter-production.up.railway.app`)

**Frontend (Vercel):**
1. Vercel: New Project → Import `instagram-defilter` → root directory: `frontend`
2. Add env var: `VITE_API_URL = https://instagram-defilter-production.up.railway.app`
3. Deploy

**Mobile:**
1. Set `EXPO_PUBLIC_API_URL` in `mobile/app.json` or `.env`
2. Run `npx expo start` for development, `eas build` for production
