"""Silver-to-gold quality gate.

Validates Pydantic schemas and null-rate thresholds on assembled records
before they are written to the gold layer. Hard-stops (sys.exit 1) when
thresholds are breached and halt_on_failure is True.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Type

from pydantic import BaseModel, ValidationError


@dataclass
class FieldCheck:
    """Null-rate threshold for a single field path."""

    field_path: str  # dot-separated: "description.pt", "title.en"
    max_null_rate: float  # 0.0 – 1.0 inclusive


@dataclass
class QualityReport:
    total: int
    schema_errors: list[str] = field(default_factory=list)
    null_rate_violations: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.schema_errors and not self.null_rate_violations

    def print_summary(self, label: str) -> None:
        status = "PASS" if self.passed else "FAIL"
        print(f"[quality-gate] {label}: {status} ({self.total} records)")
        for msg in self.schema_errors:
            print(f"  schema    : {msg}")
        for msg in self.null_rate_violations:
            print(f"  null-rate : {msg}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_nested(obj: Any, dotted: str) -> Any:
    """Resolve a dot-separated path from a plain dict (not a Pydantic model)."""
    for part in dotted.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


def check_null_rate(records: list[dict], field_path: str) -> float:
    """Return the fraction of records where *field_path* is None."""
    if not records:
        return 0.0
    nulls = sum(1 for r in records if _get_nested(r, field_path) is None)
    return nulls / len(records)


# ---------------------------------------------------------------------------
# Main gate
# ---------------------------------------------------------------------------


def run_quality_gate(
    records: list[dict],
    schema_class: Type[BaseModel],
    checks: list[FieldCheck],
    label: str = "output",
    halt_on_failure: bool = False,
) -> QualityReport:
    """Validate *records* against *schema_class* and *checks*.

    Args:
        records: Plain dicts to validate (gold-layer records before writing).
        schema_class: Pydantic model class for structural validation.
        checks: Null-rate thresholds to enforce.
        label: Human-readable name used in log output.
        halt_on_failure: When True, call sys.exit(1) on any violation.

    Returns:
        A :class:`QualityReport` describing the outcome.
    """
    report = QualityReport(total=len(records))

    # --- Schema validation --------------------------------------------------
    for i, rec in enumerate(records):
        try:
            schema_class.model_validate(rec)
        except ValidationError as exc:
            report.schema_errors.append(
                f"record[{i}] id={rec.get('id', '?')}: {exc.error_count()} error(s)"
            )

    # --- Null-rate checks ---------------------------------------------------
    for chk in checks:
        rate = check_null_rate(records, chk.field_path)
        if rate > chk.max_null_rate:
            report.null_rate_violations.append(
                f"{chk.field_path}: {rate:.0%} null (threshold {chk.max_null_rate:.0%})"
            )

    report.print_summary(label)

    if halt_on_failure and not report.passed:
        sys.exit(1)

    return report
