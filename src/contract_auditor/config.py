"""Runtime configuration, read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from contract_auditor.policy import CompliancePolicy


class ConfigError(RuntimeError):
    pass


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    gemini_model: str = "gemini-2.5-flash"
    max_upload_bytes: int = 10 * 1024 * 1024
    policy: CompliancePolicy = field(default_factory=CompliancePolicy)

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            gemini_api_key=os.environ.get("GEMINI_API_KEY") or None,
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            max_upload_bytes=_int_env("MAX_UPLOAD_MB", 10) * 1024 * 1024,
            policy=CompliancePolicy(
                max_payment_terms_days=_int_env("POLICY_MAX_PAYMENT_TERMS_DAYS", 30),
                max_lead_time_days=_int_env("POLICY_MAX_LEAD_TIME_DAYS", 21),
            ),
        )
