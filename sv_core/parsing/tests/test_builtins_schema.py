"""builtins.to_schema() 단위 테스트."""

import pytest

from sv_core.parsing.builtins import to_schema


@pytest.fixture(scope="module")
def schema():
    return to_schema()


def test_returns_dict(schema):
    assert isinstance(schema, dict)


def test_version_is_string(schema):
    assert isinstance(schema["version"], str)
    assert len(schema["version"]) > 0


def test_fields_contains_required(schema):
    assert "현재가" in schema["fields"]
    assert "거래량" in schema["fields"]


def test_functions_contains_rsi(schema):
    assert "RSI" in schema["functions"]
    rsi = schema["functions"]["RSI"]
    assert "min_args" in rsi
    assert "max_args" in rsi
    assert "return_type" in rsi


def test_patterns_contains_golden_cross(schema):
    assert "골든크로스" in schema["patterns"]
    assert "definition" in schema["patterns"]["골든크로스"]


def test_compound_fields_present(schema):
    assert "compound_fields" in schema
    assert isinstance(schema["compound_fields"], dict)
