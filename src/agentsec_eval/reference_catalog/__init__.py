"""Strict contracts for the full upstream reference ledger."""

from agentsec_eval.reference_catalog.enums import (
    GenerationDependency,
    NativeConversionDisposition,
    NativeOutputKind,
    RawReuseDisposition,
    RecordRole,
    ReuseClassification,
    RuntimeOwnership,
    SourceAssetKind,
    StateScope,
)
from agentsec_eval.reference_catalog.models import (
    CommitSha,
    CoverageSummary,
    EmbeddedDataSource,
    NonEmptyText,
    NonNegativeInt,
    PromptfooEntryMetadata,
    PromptfooSummary,
    RelativePosixPath,
    SaberSummary,
    Sha256Digest,
    SourceCoverage,
    UpstreamLedgerRecord,
)
from agentsec_eval.reference_catalog.validation import validate_records

__all__ = [
    "CommitSha",
    "CoverageSummary",
    "EmbeddedDataSource",
    "GenerationDependency",
    "NativeConversionDisposition",
    "NativeOutputKind",
    "NonEmptyText",
    "NonNegativeInt",
    "PromptfooEntryMetadata",
    "PromptfooSummary",
    "RawReuseDisposition",
    "RecordRole",
    "RelativePosixPath",
    "ReuseClassification",
    "RuntimeOwnership",
    "SaberSummary",
    "Sha256Digest",
    "SourceAssetKind",
    "SourceCoverage",
    "StateScope",
    "UpstreamLedgerRecord",
    "validate_records",
]
