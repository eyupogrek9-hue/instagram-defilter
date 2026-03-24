# Instagram De-Filter — Design Spec

**Date:** 2026-03-24
**Status:** Approved

---

## Overview

Instagram De-Filter removes color grading and tonal effects applied by Instagram filters from photos. The user pastes an Instagram post URL, and the app returns a side-by-side comparison of the original filtered image and the de-filtered result. The system uses classical image processing for the core correction and Claude vision as a secondary pass to improve naturalness.

---

## Accuracy Goal

The target is: **the output looks roughly natural to a human observer** — colors appear plausible for an unfiltered photo. Pixel-perfect reversal is explicitly out of scope. The classical pass is a general heuristic and results will vary across filter styles (e.g., heavy matte/desaturated filters vs warm-vignette filters). The Claude vision pass compensates for cases where the classical corrections undershoot or overshoot.

---

## Architecture

```
instagram-defilter/
  backend/          → Python + FastAPI
  frontend/         → React + Vite + Tailwind CSS
  mobile/           → Expo (React Native)
```

---

## Backend — Python + FastAPI

### Endpoint

```
POST /defilter
Content-Type: application/json

Body:  { "url": "https://www.instagram.com/p/<shortcode>/" }

Response (200):
{
  "original_url": "https://cdn.instagram.com/...",
  "processed_image": "<base64-encoded PNG>",
  "claude_pass_applied": true   // false if Claude step failed/was skipped
}

Response (400): { "error": "Invalid or malformed Instagram URL" }
Response (403): { "error": "Post is private or account is private" }
Response (404): { "error": "Post not found or has been deleted" }
Response (429): { "error": "Rate limited by Instagram — try again later" }
Response (502): { "error": "Could not fetch image from Instagram" }
Response (503): { "error": "Anthropic API unavailable — classical corrections applied only" }
```

### Processing Pipeline

1. **Scrape** — `instaloader` fetches the highest-resolution image from the given Instagram post URL. Only public posts are supported. Returns the CDN image URL for the frontend to display as the "original".

2. **Classical de-filter** — OpenCV + Pillow apply:
   - Histogram normalization (CLAHE on luminance channel in LAB color space)
   - White balance correction (Grey World assumption)
   - Saturation reduction (bring towards neutral if oversaturated)
   - Contrast flattening (stretch midtones toward linear response)

3. **Claude vision check** — Send both the original and the classically-corrected image to `claude-opus-4-6` with a structured prompt: *"The first image is Instagram-filtered. The second is after classical de-filtering. Describe what color adjustments (if any) are still needed to make the second image look like a natural, unfiltered photo. Be specific: e.g., 'reduce warmth by 20%', 'lower saturation by 10%', 'increase brightness slightly'."*

4. **Apply Claude corrections** — Parse the response and apply the described adjustments via Pillow's `ImageEnhance`. If the Claude API call fails, times out, or returns a response that cannot be parsed into adjustment instructions, the classically-corrected image is returned as-is with `claude_pass_applied: false` in the response. The endpoint does not fail — it degrades gracefully.

5. **Return** — Respond with `original_url` (Instagram CDN URL) and the final processed image encoded as base64 PNG.

### Dependencies

- `fastapi`, `uvicorn`
- `instaloader`
- `opencv-python`, `Pillow`
- `anthropic` (Anthropic Python SDK)

### Configuration

Environment variables:
- `ANTHROPIC_API_KEY` — Anthropic API key

### Deployment

Railway. `Procfile`: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## Frontend — React + Vite + Tailwind CSS

Single page:

1. **URL input** — Text field for the Instagram post URL + Submit button
2. **Loading state** — Spinner while the backend processes
3. **Side-by-side result** — Original (left) and de-filtered (right), with labels
4. **Download button** — Downloads the de-filtered image as PNG
5. **Error state** — Shows error message if URL is invalid, post is private, or post not found
6. **Carousel notice** — If the response indicates a carousel post, show a small notice: "Only the first image was processed"

Environment variable: `VITE_API_URL` pointing to the Railway backend URL.

Deployed on Vercel.

---

## Mobile App — Expo (React Native)

Same flow as the web frontend:

1. URL text input + Submit button
2. Loading indicator
3. Side-by-side image comparison (scrollable if needed on small screens)
4. "Save to camera roll" button using `expo-media-library`

Environment variable: `EXPO_PUBLIC_API_URL` pointing to the Railway backend URL.

Distributed via Expo Go for development; EAS Build for production distribution.

---

## Limitations

- **Public posts only** — Instagram blocks scraping of private accounts. The app shows a clear error for private posts.
- **Destructive filters** — Heavy blur, grain, or glow effects baked into a filter cannot be fully reversed. The output will look better but not perfect.
- **Rate limiting** — Instagram may rate-limit or block repeated scraping requests. The API returns a 429 for these cases.
- **Single image per post** — For carousel posts, only the first image is processed. The frontend shows a notice when this occurs.
- **General heuristic, not filter-specific** — The classical de-filter applies the same corrections regardless of which Instagram filter was used. Results vary significantly: simple warm/cool tints correct well; heavy matte, fade, or vignette effects correct partially.
