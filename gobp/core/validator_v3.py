"""
GoBP Validator v3.

Schema v3 có 2 templates:
  Template 1 — Mọi node: name + group + description + code + history[]
  Template 2 — ErrorCase: thêm severity field

Validator đơn giản hơn v2 vì không có typed fields.
"""

from __future__ import annotations

from typing import Any

# Group taxonomy từ SCHEMA.md
# Dùng để infer group khi không có
_DEFAULT_GROUPS: dict[str, str] = {
    "Idea": "Document > Idea",
    "Spec": "Document > Spec",
    "Document": "Document > Document",
    "Lesson": "Document > Lesson",
    "Entity": "Dev > Domain > Entity",
    "ValueObject": "Dev > Domain > ValueObject",
    "DomainEvent": "Dev > Domain > DomainEvent",
    "Aggregate": "Dev > Domain > Aggregate",
    "Flow": "Dev > Application > Flow",
    "Feature": "Dev > Application > Feature",
    "Command": "Dev > Application > Command",
    "UseCase": "Dev > Application > UseCase",
    "Engine": "Dev > Infrastructure > Engine",
    "Repository": "Dev > Infrastructure > Repository",
    "APIContract": "Dev > Infrastructure > API > APIContract",
    "APIEndpoint": "Dev > Infrastructure > API > APIEndpoint",
    "APIRequest": "Dev > Infrastructure > API > APIRequest",
    "APIResponse": "Dev > Infrastructure > API > APIResponse",
    "APIMiddleware": "Dev > Infrastructure > API > APIMiddleware",
    "APIVersion": "Dev > Infrastructure > API > APIVersion",
    "Webhook": "Dev > Infrastructure > API > Webhook",
    "AuthFlow": "Dev > Infrastructure > Security > AuthFlow",
    "AuthZ": "Dev > Infrastructure > Security > AuthZ",
    "Permission": "Dev > Infrastructure > Security > Permission",
    "Policy": "Dev > Infrastructure > Security > Policy",
    "Token": "Dev > Infrastructure > Security > Token",
    "Encryption": "Dev > Infrastructure > Security > Encryption",
    "Secret": "Dev > Infrastructure > Security > Secret",
    "SecurityAudit": "Dev > Infrastructure > Security > Audit",
    "ThreatModel": "Dev > Infrastructure > Security > ThreatModel",
    "Vulnerability": "Dev > Infrastructure > Security > Vulnerability",
    "RateLimitPolicy": "Dev > Infrastructure > Security > RateLimitPolicy",
    "DBSchema": "Dev > Infrastructure > Database > Schema",
    "Table": "Dev > Infrastructure > Database > Table",
    "Column": "Dev > Infrastructure > Database > Column",
    "View": "Dev > Infrastructure > Database > View",
    "Migration": "Dev > Infrastructure > Database > Migration",
    "DBIndex": "Dev > Infrastructure > Database > Index",
    "NamedQuery": "Dev > Infrastructure > Database > Query",
    "ConnectionPool": "Dev > Infrastructure > Database > ConnectionPool",
    "Seed": "Dev > Infrastructure > Database > Seed",
    "EventBus": "Dev > Infrastructure > Messaging > EventBus",
    "Queue": "Dev > Infrastructure > Messaging > Queue",
    "Message": "Dev > Infrastructure > Messaging > Message",
    "DeadLetterQueue": "Dev > Infrastructure > Messaging > DeadLetterQueue",
    "Topic": "Dev > Infrastructure > Messaging > Topic",
    "Worker": "Dev > Infrastructure > Messaging > Worker",
    "Metric": "Dev > Infrastructure > Observability > Metric",
    "SLO": "Dev > Infrastructure > Observability > SLO",
    "LogSpec": "Dev > Infrastructure > Observability > Log",
    "TraceSpec": "Dev > Infrastructure > Observability > Trace",
    "Alert": "Dev > Infrastructure > Observability > Alert",
    "CacheLayer": "Dev > Infrastructure > Cache > CacheLayer",
    "CacheKey": "Dev > Infrastructure > Cache > CacheKey",
    "StorageBucket": "Dev > Infrastructure > Storage > Bucket",
    "MediaProcessing": "Dev > Infrastructure > Storage > Media",
    "CDN": "Dev > Infrastructure > Storage > CDN",
    "EnvConfig": "Dev > Infrastructure > Config > EnvConfig",
    "FeatureFlag": "Dev > Infrastructure > Config > FeatureFlag",
    "Environment": "Dev > Infrastructure > Deployment > Environment",
    "ServiceDefinition": "Dev > Infrastructure > Deployment > Service",
    "Pipeline": "Dev > Infrastructure > Deployment > Pipeline",
    "LoadBalancer": "Dev > Infrastructure > Network > LoadBalancer",
    "ServiceMesh": "Dev > Infrastructure > Network > ServiceMesh",
    "DNSRecord": "Dev > Infrastructure > Network > DNS",
    "ExternalService": "Dev > Infrastructure > ThirdParty > ExternalService",
    "SDK": "Dev > Infrastructure > ThirdParty > SDK",
    "Screen": "Dev > Frontend > Screen",
    "Component": "Dev > Frontend > Component",
    "Interface": "Dev > Code > Interface",
    "Enum": "Dev > Code > Enum",
    "Module": "Dev > Code > Module",
    "Invariant": "Constraint > Invariant",
    "BusinessRule": "Constraint > BusinessRule",
    "ErrorDomain": "Error > ErrorDomain",
    "ErrorCase": "Error > ErrorCase",
    "TestSuite": "Test > TestSuite",
    "TestKind": "Test > TestKind",
    "TestCase": "Test > TestCase",
    "Session": "Meta > Session",
    "Wave": "Meta > Wave",
    "Task": "Meta > Task",
    "Reflection": "Meta > Reflection",
}

_VALID_SEVERITIES = {"fatal", "error", "warning", "info"}


class ValidatorV3:
    """
    Schema v3 validator — 2 templates.

    Template 1 (mọi node):
        name (required)
        group (required)
        description (required, not empty)
        code (optional)
        history[] (optional, append-only)

    Template 2 (ErrorCase only):
        + severity: fatal|error|warning|info
    """

    def validate(self, node: dict[str, Any]) -> list[str]:
        """
        Validate node theo schema v3.

        Returns:
            List of error strings. Empty list = valid.
        """
        errors: list[str] = []

        # Template 1: base fields
        if not node.get("name", "").strip():
            errors.append("name is required and cannot be empty")

        if not node.get("group", "").strip():
            errors.append("group is required and cannot be empty")

        desc = node.get("description", "")
        if isinstance(desc, dict):
            # v2 compat: {info, code}
            desc = desc.get("info", "") or ""
        if not str(desc).strip():
            errors.append("description is required and cannot be empty")

        # history[] validation (nếu có)
        history = node.get("history", [])
        if history is not None:
            if not isinstance(history, list):
                errors.append("history must be a list")
            else:
                for i, entry in enumerate(history):
                    if not isinstance(entry, dict):
                        errors.append(f"history[{i}] must be a dict")
                    elif not entry.get("description", "").strip():
                        errors.append(f"history[{i}].description is required")

        # Template 2: ErrorCase additional field
        node_type = node.get("type", "")
        if node_type == "ErrorCase":
            severity = node.get("severity", "")
            if severity not in _VALID_SEVERITIES:
                errors.append(
                    f"ErrorCase.severity must be one of: "
                    f"{sorted(_VALID_SEVERITIES)}, got: '{severity}'"
                )

        return errors

    def auto_fix(self, node: dict[str, Any]) -> dict[str, Any]:
        """
        Auto-fix những lỗi có thể fix mà không cần human.

        Fixes:
        - Infer group từ type nếu thiếu
        - Convert description dict → plain text
        - Set empty defaults cho code, history
        """
        node = dict(node)

        # Infer group từ type
        if not node.get("group") and node.get("type"):
            default_group = _DEFAULT_GROUPS.get(str(node["type"]))
            if default_group:
                node["group"] = default_group

        # Convert v2 description {info, code} → v3 plain text
        desc = node.get("description")
        if isinstance(desc, dict):
            info = desc.get("info", "") or ""
            code = desc.get("code", "") or ""
            node["description"] = info
            if code and not node.get("code"):
                node["code"] = code

        # Set defaults
        if "code" not in node:
            node["code"] = ""
        if "history" not in node:
            node["history"] = []

        return node

    def is_valid(self, node: dict[str, Any]) -> bool:
        """Convenience method — True nếu không có errors."""
        return len(self.validate(node)) == 0


# Module-level instance
validator_v3 = ValidatorV3()
