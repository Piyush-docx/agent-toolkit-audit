"""Accuracy scoring against human ground truth (brief section 8).

Only v1 exists in this submission -- Loops A-E (verify.py) were scoped out
under time pressure, so there is no v2 to compare against. score_v1() scores
whatever ground_truth.csv rows the human has actually filled in (a partial
sample is fine; blank truth_value rows are skipped, not scored as misses).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from agent.normalise import norm_field
from agent.research import load_apps, load_cached_record
from agent.schema import AppRecord

GROUND_TRUTH_PATH = Path("data/ground_truth.csv")
LIST_FIELDS = {"auth_methods", "api_type"}


@dataclass
class FieldStats:
    correct: int = 0
    total: int = 0

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0


@dataclass
class Miss:
    id: int
    name: str
    field: str
    truth: str
    answer: str
    jaccard: Optional[float] = None
    cause: str = "other"


@dataclass
class ScoreResult:
    per_field: dict[str, FieldStats] = field(default_factory=dict)
    overall: FieldStats = field(default_factory=FieldStats)
    misses: list[Miss] = field(default_factory=list)


def _jaccard(a: tuple, b: tuple) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 1.0


def _predicted_value(record: Optional[AppRecord], field_name: str):
    """The record's answer for `field_name`, normalised the same way as truth."""
    if record is None:
        return () if field_name in LIST_FIELDS else "unknown"
    raw = getattr(record, field_name, None)
    if field_name in LIST_FIELDS:
        values = [getattr(v, "value", v) for v in (raw or [])]
        return norm_field(field_name, values) if values else ()
    value = getattr(raw, "value", raw)
    return norm_field(field_name, value if value is not None else "unknown")


def score_v1(ground_truth_path: Path = GROUND_TRUTH_PATH) -> ScoreResult:
    result = ScoreResult()
    with Path(ground_truth_path).open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        truth_raw = row["truth_value"].strip()
        if not truth_raw:
            continue  # human hasn't labelled this row yet -- not a miss

        field_name = row["field"]
        app_id = int(row["id"])
        record = load_cached_record(app_id)
        truth = norm_field(field_name, truth_raw)
        predicted = _predicted_value(record, field_name)

        stats = result.per_field.setdefault(field_name, FieldStats())
        stats.total += 1
        result.overall.total += 1

        correct = predicted == truth
        if correct:
            stats.correct += 1
            result.overall.correct += 1
        else:
            jaccard = (_jaccard(predicted, truth)
                      if field_name in LIST_FIELDS else None)
            result.misses.append(Miss(
                id=app_id, name=row["name"], field=field_name,
                truth=",".join(truth) if field_name in LIST_FIELDS else truth,
                answer=(",".join(predicted) if field_name in LIST_FIELDS
                        else predicted),
                jaccard=jaccard,
            ))

    return result


def load_all_records() -> list[AppRecord]:
    return [r for r in (load_cached_record(a["id"]) for a in load_apps())
            if r is not None]


def population_stats() -> dict:
    """Evidence-support rate and needs_human count across all researched apps."""
    records = load_all_records()
    return {
        "apps_total": len(records),
        "apps_needing_human": sum(1 for r in records if r.needs_human),
        "apps_with_evidence": sum(1 for r in records if r.evidence),
    }
