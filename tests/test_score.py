"""Accuracy scoring against ground truth (brief section 8)."""
import csv

import pytest

from agent import score
from agent.schema import AppRecord

LIST_FIELDS = {"auth_methods", "api_type"}


def _rec(id, name, category="X", **overrides):
    base = {"id": id, "name": name, "category": category}
    return AppRecord.model_validate({**base, **overrides})


def _write_gt(tmp_path, rows):
    path = tmp_path / "ground_truth.csv"
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "name", "field", "truth_value",
                                            "source_url", "notes"])
        w.writeheader()
        w.writerows(rows)
    return path


def _row(id, name, field, truth, source_url="", notes=""):
    return {"id": id, "name": name, "field": field, "truth_value": truth,
            "source_url": source_url, "notes": notes}


def test_scalar_field_exact_match(tmp_path, monkeypatch):
    records = {1: _rec(1, "Stripe", access="self_serve_free")}
    monkeypatch.setattr(score, "load_cached_record", lambda i: records.get(i))
    gt = _write_gt(tmp_path, [_row(1, "Stripe", "access", "self_serve_free")])
    result = score.score_v1(gt)
    assert result.per_field["access"].correct == 1
    assert result.per_field["access"].total == 1


def test_scalar_field_mismatch_is_a_miss(tmp_path, monkeypatch):
    records = {1: _rec(1, "Stripe", access="paid_plan")}
    monkeypatch.setattr(score, "load_cached_record", lambda i: records.get(1))
    gt = _write_gt(tmp_path, [_row(1, "Stripe", "access", "self_serve_free")])
    result = score.score_v1(gt)
    assert result.per_field["access"].correct == 0
    assert len(result.misses) == 1
    assert result.misses[0].field == "access"
    assert result.misses[0].truth == "self_serve_free"
    assert result.misses[0].answer == "paid_plan"


def test_list_field_exact_set_match(tmp_path, monkeypatch):
    records = {1: _rec(1, "Stripe", auth_methods=["oauth2", "api_key"])}
    monkeypatch.setattr(score, "load_cached_record", lambda i: records.get(1))
    gt = _write_gt(tmp_path, [_row(1, "Stripe", "auth_methods", "api_key,oauth2")])
    result = score.score_v1(gt)
    assert result.per_field["auth_methods"].correct == 1


def test_list_field_reports_jaccard_even_on_partial_match(tmp_path, monkeypatch):
    records = {1: _rec(1, "Stripe", auth_methods=["oauth2"])}
    monkeypatch.setattr(score, "load_cached_record", lambda i: records.get(1))
    gt = _write_gt(tmp_path, [_row(1, "Stripe", "auth_methods", "oauth2,api_key")])
    result = score.score_v1(gt)
    # exact-set fails (headline metric) but Jaccard is partial, not zero
    assert result.per_field["auth_methods"].correct == 0
    assert 0 < result.misses[0].jaccard < 1


def test_unknown_truth_and_unknown_answer_is_correct(tmp_path, monkeypatch):
    records = {1: _rec(1, "Stripe", webhooks="unknown")}
    monkeypatch.setattr(score, "load_cached_record", lambda i: records.get(1))
    gt = _write_gt(tmp_path, [_row(1, "Stripe", "webhooks", "unknown")])
    result = score.score_v1(gt)
    assert result.per_field["webhooks"].correct == 1


def test_unknown_answer_when_truth_is_known_is_wrong(tmp_path, monkeypatch):
    records = {1: _rec(1, "Stripe", webhooks="unknown")}
    monkeypatch.setattr(score, "load_cached_record", lambda i: records.get(1))
    gt = _write_gt(tmp_path, [_row(1, "Stripe", "webhooks", "yes")])
    result = score.score_v1(gt)
    assert result.per_field["webhooks"].correct == 0


def test_blank_truth_value_is_skipped_not_scored_as_wrong(tmp_path, monkeypatch):
    """A ground-truth row the human hasn't filled in yet must not count as a miss."""
    records = {1: _rec(1, "Stripe", access="self_serve_free")}
    monkeypatch.setattr(score, "load_cached_record", lambda i: records.get(1))
    gt = _write_gt(tmp_path, [_row(1, "Stripe", "access", "")])
    result = score.score_v1(gt)
    assert "access" not in result.per_field
    assert result.misses == []


def test_missing_cached_record_is_a_miss_not_a_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(score, "load_cached_record", lambda i: None)
    gt = _write_gt(tmp_path, [_row(1, "Ghost", "access", "self_serve_free")])
    result = score.score_v1(gt)
    assert result.per_field["access"].correct == 0
    assert result.per_field["access"].total == 1


def test_overall_accuracy_is_correct_over_total_across_all_fields(tmp_path, monkeypatch):
    records = {1: _rec(1, "Stripe", access="self_serve_free", webhooks="yes")}
    monkeypatch.setattr(score, "load_cached_record", lambda i: records.get(1))
    gt = _write_gt(tmp_path, [
        _row(1, "Stripe", "access", "self_serve_free"),   # correct
        _row(1, "Stripe", "webhooks", "no"),               # wrong
    ])
    result = score.score_v1(gt)
    assert result.overall.correct == 1
    assert result.overall.total == 2


def _full_evidence():
    from agent.schema import EVIDENCE_REQUIRED_FIELDS
    return [{"field": f, "url": "https://x", "quote": "q"}
            for f in EVIDENCE_REQUIRED_FIELDS]


def test_needs_human_and_evidence_support_rate_over_all_100(tmp_path, monkeypatch):
    all_records = [
        _rec(1, "A", needs_human=True, evidence=[], verdict="ready"),
        _rec(2, "B", needs_human=False, evidence=_full_evidence(), verdict="ready"),
    ]
    monkeypatch.setattr(score, "load_all_records", lambda: all_records)
    stats = score.population_stats()
    assert stats["apps_needing_human"] == 1
    assert stats["apps_total"] == 2
    assert stats["apps_with_evidence"] == 1
