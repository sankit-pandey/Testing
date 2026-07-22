"""Strategy factory — Design ref: `LOCKED_Design_v1.0.md` §3, §13;
`Technical_Design_Document.md` §2.0. Story 2.1.
"""
from app.pipeline.strategy import BaseStrategy, NoOpStrategy


class UnsupportedArtifactTypeError(Exception):
    """Raised for an `artifact_type` with no registered strategy."""


class StrategyFactory:
    @staticmethod
    def create(artifact_type: str) -> BaseStrategy:
        if artifact_type == "IFU":
            from app.strategies.ifu.strategy import IFUStrategy

            return IFUStrategy()
        if artifact_type == "UI_RESOURCE":
            from app.strategies.ui_resource.strategy import UIResourceStrategy

            return UIResourceStrategy()
        if artifact_type == "VIDEO":
            raise UnsupportedArtifactTypeError(
                "VIDEO is design-locked (LOCKED §4.2) but deferred — out of scope for "
                "this implementation phase (Implementation_Plan.md Story 5.4)."
            )
        if artifact_type == "NOOP":
            return NoOpStrategy()
        raise UnsupportedArtifactTypeError(f"No strategy registered for artifact_type='{artifact_type}'")
