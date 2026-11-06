"""Refactor step returns the model's rewrite, without calling Groq."""

from app.agent.nodes.refactor import refactor_code, strip_code_fences


def test_strip_code_fences():
    assert strip_code_fences("```python\nprint(1)\n```") == "print(1)"


def test_refactor_uses_the_supplied_rewrite():
    state = {
        "diff": 'query = "SELECT * FROM users WHERE name = \'" + user + "\'"',
        "findings": ["A03 Injection | do not concatenate SQL | username is pasted in"],
        "test_errors": [],
        "iteration": 0,
    }

    def fake_reply(diff: str, findings: list[str], errors: list[str]) -> str:
        assert "SELECT" in diff
        assert "A03" in findings[0]
        assert errors == []
        return "```python\nquery = \"SELECT * FROM users WHERE name = ?\"\n```"

    result = refactor_code(state, complete_fn=fake_reply)
    assert result["iteration"] == 1
    assert result["refactored_code"] == 'query = "SELECT * FROM users WHERE name = ?"'


def test_clear_finding_keeps_the_original_diff():
    state = {
        "diff": "return 1",
        "findings": ["No rule from the rulebook matched this change."],
        "iteration": 0,
    }
    result = refactor_code(state, complete_fn=lambda *_args: "should not be used")
    assert result["refactored_code"] == "return 1"
