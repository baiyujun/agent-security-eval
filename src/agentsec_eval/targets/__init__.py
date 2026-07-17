"""Inspect-independent interfaces for external evaluation targets."""

from agentsec_eval.targets.http_session import JsonHttpTargetAdapter
from agentsec_eval.targets.protocol import (
    JsonRequestTransport,
    TargetAdapter,
    TargetSession,
    TargetToolCall,
    TargetTurnResult,
)

__all__ = [
    "JsonHttpTargetAdapter",
    "JsonRequestTransport",
    "TargetAdapter",
    "TargetSession",
    "TargetToolCall",
    "TargetTurnResult",
]
