"""Closed project-native vocabularies for scenario assets."""

from enum import StrEnum


class ScenarioDomain(StrEnum):
    CODING_CLI = "coding_cli"
    LOCAL_MCP = "local_mcp"
    OFFICE_BUSINESS = "office_business"
    WEB_RAG = "web_rag"
    MEMORY = "memory"
    AGENT_SABOTAGE = "agent_sabotage"


class ScenarioVariant(StrEnum):
    ATTACKED = "attacked"
    NO_ATTACK_CONTROL = "no_attack_control"
    BENIGN_CONTROL = "benign_control"


class EntryPoint(StrEnum):
    USER_REQUEST = "user_request"
    ISSUE = "issue"
    README = "readme"
    SOURCE_COMMENT = "source_comment"
    BUILD_LOG = "build_log"
    TOOL_RESULT = "tool_result"
    MCP_TOOL_DEFINITION = "mcp_tool_definition"


class AttackDeliveryMode(StrEnum):
    DIRECT_USER_REQUEST = "direct_user_request"
    INDIRECT_CONTEXT = "indirect_context"


class CapabilityProvider(StrEnum):
    TOOL = "tool"
    SERVICE = "service"
    MCP = "mcp"


class CapabilityKind(StrEnum):
    FILESYSTEM_READ = "filesystem_read"
    FILESYSTEM_WRITE = "filesystem_write"
    SHELL_EXECUTION = "shell_execution"
    GIT = "git"
    LOCAL_HTTP = "local_http"
    NETWORK = "network"
    PACKAGE_MANAGER = "package_manager"
    MCP_CLIENT = "mcp_client"


class EnvironmentRole(StrEnum):
    AGENT_WORKSPACE = "agent_workspace"
    PRIVATE_VERIFIER = "private_verifier"
    SYNTHETIC_SECRET_STORE = "synthetic_secret_store"
    MOCK_RECEIVER = "mock_receiver"
    LOCAL_SERVICE = "local_service"
    RESET_BASELINE = "reset_baseline"


class FixtureRole(StrEnum):
    NORMAL_TASK_INPUT = "normal_task_input"
    ATTACK_CHANNEL = "attack_channel"
    PROTECTED_ASSET = "protected_asset"
    PRIVATE_VERIFIER_MATERIAL = "private_verifier_material"
    RESET_SNAPSHOT = "reset_snapshot"


class Visibility(StrEnum):
    AGENT_VISIBLE = "agent_visible"
    VERIFIER_PRIVATE = "verifier_private"
    HARNESS_INTERNAL = "harness_internal"


class ObservationLevel(StrEnum):
    BLACK_BOX = "black_box"
    INSTRUMENTED = "instrumented"
    ENVIRONMENT_CONFIRMED = "environment_confirmed"


class ProbeOracleCategory(StrEnum):
    UTILITY = "utility"
    ATTACK_PROGRESS = "attack_progress"
    SECURITY_EFFECT = "security_effect"
    HARNESS_INTEGRITY = "harness_integrity"
    RESET = "reset"
    REPRODUCIBILITY = "reproducibility"


class OracleExpectation(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    EQUALS = "equals"
    UNCHANGED = "unchanged"
    ORDERED = "ordered"


class ReviewStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class ReuseMode(StrEnum):
    REFERENCE_ONLY = "reference_only"
    ASSET_IMPORT = "asset_import"
    CODE_INTERNALIZATION = "code_internalization"
    UPSTREAM_REPLAY = "upstream_replay"


class LineageTransformation(StrEnum):
    SEMANTIC_RECONSTRUCTION = "semantic_reconstruction"
    DIRECT_IMPORT = "direct_import"
    PROJECT_AUTHORED = "project_authored"
    OMITTED = "omitted"


class ConversionLossKind(StrEnum):
    RIGHTS_BLOCKED = "rights_blocked"
    EXECUTABLE_OMITTED = "executable_omitted"
    NON_AUTHORITATIVE = "non_authoritative"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class ResetAction(StrEnum):
    RESTORE_FIXTURE_SNAPSHOT = "restore_fixture_snapshot"
    CLEAR_LOCAL_RECEIVER = "clear_local_receiver"
    RESET_SERVICE_STATE = "reset_service_state"
    REMOVE_GENERATED_ARTIFACTS = "remove_generated_artifacts"
