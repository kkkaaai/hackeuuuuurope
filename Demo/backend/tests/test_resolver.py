"""Tests for the template resolver."""

from engine.resolver import resolve_templates


def _make_state(**overrides):
    base = {
        "results": {
            "n1": {"results": [{"title": "HN Post"}], "summary": "hello"},
            "n2": {"summary": "world", "count": 5},
        },
        "user": {"name": "Alice", "email": "alice@test.com"},
        "memory": {"preferences": {"theme": "dark"}, "lang": "en"},
    }
    base.update(overrides)
    return base


class TestResolveTemplates:
    def test_whole_ref_preserves_type(self):
        """A whole-string {{ref}} should return the raw value, not stringified."""
        state = _make_state()
        result = resolve_templates({"data": "{{n1.results}}"}, state)
        assert result["data"] == [{"title": "HN Post"}]
        assert isinstance(result["data"], list)

    def test_mixed_string_interpolation(self):
        state = _make_state()
        result = resolve_templates({"msg": "Summary: {{n1.summary}}"}, state)
        assert result["msg"] == "Summary: hello"

    def test_nested_path(self):
        state = _make_state()
        result = resolve_templates({"val": "{{memory.preferences.theme}}"}, state)
        assert result["val"] == "dark"

    def test_memory_namespace(self):
        state = _make_state()
        result = resolve_templates({"lang": "{{memory.lang}}"}, state)
        assert result["lang"] == "en"

    def test_user_namespace(self):
        state = _make_state()
        result = resolve_templates({"who": "{{user.name}}"}, state)
        assert result["who"] == "Alice"

    def test_missing_ref_whole_returns_none(self):
        state = _make_state()
        result = resolve_templates({"x": "{{n99.missing}}"}, state)
        assert result["x"] is None

    def test_missing_ref_mixed_returns_empty_string(self):
        state = _make_state()
        result = resolve_templates({"x": "prefix-{{n99.missing}}-suffix"}, state)
        assert result["x"] == "prefix--suffix"

    def test_no_templates_passthrough(self):
        state = _make_state()
        result = resolve_templates({"plain": "just text"}, state)
        assert result["plain"] == "just text"

    def test_multiple_templates_in_one_string(self):
        state = _make_state()
        result = resolve_templates(
            {"both": "{{n1.summary}} and {{n2.summary}}"}, state
        )
        assert result["both"] == "hello and world"

    def test_non_string_values_pass_through(self):
        state = _make_state()
        result = resolve_templates({"num": 42, "flag": True}, state)
        assert result["num"] == 42
        assert result["flag"] is True

    def test_numeric_value_in_mixed_string(self):
        state = _make_state()
        result = resolve_templates({"msg": "count={{n2.count}}"}, state)
        assert result["msg"] == "count=5"
