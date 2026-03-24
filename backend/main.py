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
