"""LaMa inference on masked crops with soft blending."""

from __future__ import annotations

import logging

import cv2
import numpy as np

from app.processing.plugins.lama.model_manager import LamaModelManager
from app.processing.plugins.lama.utils import (
    blend_crop,
    color_correct,
    dilate_mask,
    expand_bbox,
    mask_bbox,
    prepare_tensors,
)

logger = logging.getLogger(__name__)


def inpaint_frame_with_lama(
    frame_bgr: np.ndarray,
    mask: np.ndarray,
    manager: LamaModelManager,
    *,
    padding: int = 64,
    blend_strength: float = 1.0,
    feather_radius: int = 12,
    prefer_gpu: bool = True,
) -> tuple[np.ndarray, dict]:
    """
    Inpaint only the padded bbox around the mask using LaMa, then blend back.

    Returns (processed_bgr, stats).
    """
    if mask.dtype != np.uint8:
        mask = (mask > 0).astype(np.uint8) * 255
    if int(np.count_nonzero(mask)) == 0:
        return frame_bgr, {"skipped": True, "device": manager.status["device"]}

    manager.ensure_model(prefer_gpu=prefer_gpu)
    device = manager.status["device"]

    work_mask = dilate_mask(mask, max(0, padding // 4))
    bbox = mask_bbox(work_mask)
    if bbox is None:
        return frame_bgr, {"skipped": True, "device": device}

    h, w = frame_bgr.shape[:2]
    x1, y1, x2, y2 = expand_bbox(*bbox, width=w, height=h, padding=padding)
    crop_bgr = frame_bgr[y1:y2, x1:x2]
    crop_mask = work_mask[y1:y2, x1:x2]
    if crop_bgr.size == 0:
        return frame_bgr, {"skipped": True, "device": device}

    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    # Ensure dimensions divisible by 8
    ch, cw = crop_rgb.shape[:2]
    pad_h = (8 - ch % 8) % 8
    pad_w = (8 - cw % 8) % 8
    if pad_h or pad_w:
        crop_rgb = cv2.copyMakeBorder(
            crop_rgb, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT_101
        )
        crop_mask = cv2.copyMakeBorder(
            crop_mask, 0, pad_h, 0, pad_w, cv2.BORDER_CONSTANT, value=0
        )

    img_t, mask_t = prepare_tensors(crop_rgb, crop_mask, device)
    output = manager.predict(img_t, mask_t)
    # output: (1,3,H,W) in 0..1
    arr = output[0].detach().float().cpu().permute(1, 2, 0).numpy()
    arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    if pad_h or pad_w:
        arr = arr[:ch, :cw]
        crop_mask = crop_mask[:ch, :cw]
        crop_bgr = crop_bgr[:ch, :cw]

    inpainted_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    inpainted_bgr = color_correct(crop_bgr, inpainted_bgr, crop_mask)
    # Use original (non-dilated) mask crop for final blend region focus
    blend_mask = mask[y1 : y1 + ch, x1 : x1 + cw]
    if blend_mask.shape[:2] != inpainted_bgr.shape[:2]:
        blend_mask = cv2.resize(
            blend_mask,
            (inpainted_bgr.shape[1], inpainted_bgr.shape[0]),
            interpolation=cv2.INTER_NEAREST,
        )
    # Expand blend slightly for seamlessness
    blend_mask = dilate_mask(blend_mask, max(2, feather_radius // 2))

    result = blend_crop(
        frame_bgr,
        inpainted_bgr,
        blend_mask,
        x1=x1,
        y1=y1,
        x2=x1 + inpainted_bgr.shape[1],
        y2=y1 + inpainted_bgr.shape[0],
        blend_strength=blend_strength,
        feather_radius=feather_radius,
    )
    # Hard guarantee: outside original mask stays identical
    outside = mask == 0
    result[outside] = frame_bgr[outside]

    return result, {
        "skipped": False,
        "device": manager.status["device"],
        "crop": [x1, y1, x2, y2],
        "crop_pixels": int(inpainted_bgr.shape[0] * inpainted_bgr.shape[1]),
    }
