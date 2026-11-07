"""How this sample project runs SQL — nearby code for the review agent."""


def run_query(sql: str, params: tuple | None = None):
    """Always pass user values in params, never paste them into sql."""
    return {"sql": sql, "params": params or ()}


def find_user_by_name(name: str):
    return run_query("SELECT * FROM users WHERE name = ?", (name,))
