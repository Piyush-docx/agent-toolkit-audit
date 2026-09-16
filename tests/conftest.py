"""Shared fixtures. `make_record` keeps each rule test to one readable line."""
import pytest

from agent.schema import AppRecord


@pytest.fixture
def make_record():
    def _make(**overrides) -> AppRecord:
        base = {"id": 1, "name": "Test App", "category": "CRM & Sales"}
        return AppRecord.model_validate({**base, **overrides})
    return _make
