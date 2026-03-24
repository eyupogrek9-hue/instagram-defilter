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
