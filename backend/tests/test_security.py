"""Security step turns a model reply into findings, without calling Groq."""

from app.agent.nodes.security import findings_from_reply, security_audit


def test_none_means_no_matching_rule():
    assert findings_from_reply("NONE") == ["No rule from the rulebook matched this change."]


def test_security_audit_uses_the_supplied_reply():
    state = {
        "diff": "query = \"SELECT * FROM users WHERE name = '\" + user + \"'\"",
        "policy_context": "A03 Injection. Use parameterized APIs.",
        "code_context": "",
    }

    def fake_reply(diff: str, policy: str, code: str) -> str:
        assert "SELECT" in diff
        assert "A03" in policy
        assert code == ""
        return "A03 Injection | Use parameterized APIs. | username is pasted into the SQL string"

    result = security_audit(state, complete_fn=fake_reply)
    assert result["findings"] == [
        "A03 Injection | Use parameterized APIs. | username is pasted into the SQL string"
    ]
