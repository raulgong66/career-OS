"""Apply recommendations to artifact models for tailoring."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .optimizer import Recommendation


class RecommendationApplier:
    """Apply ADD recommendations to artifact models."""

    def apply_add_recommendations(
        self,
        artifact: dict[str, Any],
        recommendations: list[Recommendation],
    ) -> dict[str, Any]:
        """Apply ADD recommendations to a deep-copied artifact.

        Args:
            artifact: The original artifact data.
            recommendations: List of Recommendation objects.

        Returns:
            A deep-copied artifact with ADD recommendations applied as sourceRefs.
        """
        # Deep-copy to avoid modifying the original
        tailored_artifact = copy.deepcopy(artifact)

        # Filter for ADD recommendations only
        add_recs = [r for r in recommendations if r.operation == "ADD"]

        if not add_recs:
            return tailored_artifact

        # Ensure sourceRefs exists
        if "sourceRefs" not in tailored_artifact:
            tailored_artifact["sourceRefs"] = []

        # Apply each ADD recommendation
        for rec in add_recs:
            # Create a sourceRef for the recommended element
            source_ref = {
                "id": rec.id,
                "type": rec.type,
            }
            tailored_artifact["sourceRefs"].append(source_ref)

        return tailored_artifact
