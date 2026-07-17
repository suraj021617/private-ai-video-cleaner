"""
AI inpainting worker stub (Phase 9).

Contract (planned):
  input:  frame BGR ndarray + binary mask + job options
  output: inpainted frame BGR ndarray

This module must not be imported by the request path until a model
runtime is configured. Feature-flagged via ProcessingStrategy.ai_inpaint.
"""


class AIInpaintWorker:
    """Reserved extension point for generative / model-based inpainting."""

    def process_frame(self, *_args, **_kwargs):  # noqa: ANN002, ANN003
        raise NotImplementedError(
            "AI inpainting is not implemented yet (Phase 9)."
        )
