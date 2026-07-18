"""LaMa inpainting plugin package."""

from app.processing.plugins.lama.model_manager import LamaModelManager, get_model_manager
from app.processing.plugins.lama.predict import inpaint_frame_with_lama

__all__ = [
    "LamaModelManager",
    "get_model_manager",
    "inpaint_frame_with_lama",
]
