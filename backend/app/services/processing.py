"""
Processing orchestration.

Phase 7: classic OpenCV + FFmpeg strategies.
Phase 9: AI inpainting worker behind the same ProcessingStrategy interface.
"""

from app.schemas.enums import ProcessingStrategy


class ProcessingService:
    """Selects and runs a cleaning strategy for a job."""

    def resolve_strategy(self, name: ProcessingStrategy) -> str:
        # Concrete runners land in later phases.
        return name.value
