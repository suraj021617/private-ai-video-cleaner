"""LaMa crop, pad, feather-blend, and color-match utilities."""

from __future__ import annotations

import cv2
import numpy as np


def dilate_mask(mask: np.ndarray, padding: int) -> np.ndarray:
    if padding <= 0:
        return (mask > 0).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (padding * 2 + 1, padding * 2 + 1)
    )
    dilated = cv2.dilate((mask > 0).astype(np.uint8) * 255, kernel, iterations=1)
    return dilated


def mask_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def expand_bbox(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    *,
    width: int,
    height: int,
    padding: int,
) -> tuple[int, int, int, int]:
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(width, x2 + padding)
    y2 = min(height, y2 + padding)
    # Snap crop size to multiples of 8 for LaMa
    cw = x2 - x1
    ch = y2 - y1
    cw8 = ((cw + 7) // 8) * 8
    ch8 = ((ch + 7) // 8) * 8
    if x1 + cw8 > width:
        x1 = max(0, width - cw8)
        x2 = width
    else:
        x2 = x1 + cw8
    if y1 + ch8 > height:
        y1 = max(0, height - ch8)
        y2 = height
    else:
        y2 = y1 + ch8
    # Ensure at least 8x8
    if x2 - x1 < 8:
        x2 = min(width, x1 + 8)
        x1 = max(0, x2 - 8)
    if y2 - y1 < 8:
        y2 = min(height, y1 + 8)
        y1 = max(0, y2 - 8)
    return x1, y1, x2, y2


def feather_mask(mask: np.ndarray, radius: int = 8) -> np.ndarray:
    """Return float32 alpha mask in [0,1] with soft edges."""
    binary = (mask > 0).astype(np.uint8) * 255
    if radius <= 0:
        return binary.astype(np.float32) / 255.0
    k = radius * 2 + 1
    blurred = cv2.GaussianBlur(binary, (k, k), 0)
    return blurred.astype(np.float32) / 255.0


def color_correct(
    original_crop: np.ndarray, inpainted_crop: np.ndarray, mask: np.ndarray
) -> np.ndarray:
    """
    Match mean/std of inpainted pixels to surrounding original context
    to reduce color seams.
    """
    out = inpainted_crop.astype(np.float32)
    orig = original_crop.astype(np.float32)
    inside = mask > 0
    outside = ~inside
    if not np.any(inside) or not np.any(outside):
        return inpainted_crop
    for c in range(3):
        src = out[:, :, c][inside]
        ref = orig[:, :, c][outside]
        src_mean, src_std = float(src.mean()), float(src.std()) + 1e-6
        ref_mean, ref_std = float(ref.mean()), float(ref.std()) + 1e-6
        corrected = (out[:, :, c] - src_mean) * (ref_std / src_std) + ref_mean
        out[:, :, c][inside] = corrected[inside]
    return np.clip(out, 0, 255).astype(np.uint8)


def blend_crop(
    original: np.ndarray,
    inpainted_crop: np.ndarray,
    mask_crop: np.ndarray,
    *,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    blend_strength: float = 1.0,
    feather_radius: int = 12,
) -> np.ndarray:
    """Soft-blend inpainted crop back into the full frame."""
    result = original.copy()
    strength = float(np.clip(blend_strength, 0.0, 1.0))
    alpha = feather_mask(mask_crop, radius=feather_radius) * strength
    alpha3 = alpha[:, :, None]
    crop = result[y1:y2, x1:x2].astype(np.float32)
    inp = inpainted_crop.astype(np.float32)
    if inp.shape[:2] != crop.shape[:2]:
        inp = cv2.resize(inp, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_LINEAR)
    if alpha3.shape[:2] != crop.shape[:2]:
        alpha_resized = cv2.resize(alpha, (crop.shape[1], crop.shape[0]), interpolation=cv2.INTER_LINEAR)
        alpha3 = alpha_resized[:, :, None]
    blended = crop * (1.0 - alpha3) + inp * alpha3
    result[y1:y2, x1:x2] = np.clip(blended, 0, 255).astype(np.uint8)
    return result


def prepare_tensors(
    image_rgb: np.ndarray, mask: np.ndarray, device: str
):
    """Prepare CHW float tensors for LaMa JIT model."""
    import torch

    img = image_rgb.astype(np.float32) / 255.0
    if mask.ndim == 3:
        mask = mask[:, :, 0]
    m = (mask > 0).astype(np.float32)
    # LaMa expects masked pixels zeroed in the image
    img = img * (1 - m[:, :, None])
    img_t = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0).to(device)
    mask_t = torch.from_numpy(m).unsqueeze(0).unsqueeze(0).to(device)
    return img_t, mask_t
