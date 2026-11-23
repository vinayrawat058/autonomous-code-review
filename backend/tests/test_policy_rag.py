"""Policy vector search returns relevant OWASP sections, not the whole book."""

from pathlib import Path

from app.rag.policy import index_policies, retrieve_policy_context

POLICIES = Path(__file__).resolve().parents[1] / "data" / "policies"

SQL_DIFF = """\
+ query = "SELECT * FROM users WHERE name = '" + user + "'"
+ return query
"""


def test_index_policies_writes_sections():
    written = index_policies(str(POLICIES), force=True)
    assert written >= 5


def test_retrieve_prefers_injection_for_sql_diff():
    index_policies(str(POLICIES), force=True)
    context = retrieve_policy_context(SQL_DIFF, str(POLICIES))
    assert "Injection" in context or "parameterized" in context.lower()
    # Should be a slice of the rulebook, not every OWASP item.
    assert "SSRF" not in context or context.count("##") <= 6
