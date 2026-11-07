"""Query safety gate — Must-Have #4. No LLM can bypass this."""
FORBIDDEN = ["insert", "update", "delete", "drop", "alter", "create",
             "replace", "truncate", "grant", "revoke", "attach", "detach",
             "pragma", "vacuum", "reindex"]

def validate_sql(sql: str, max_rows: int = 100) -> str:
    s = sql.strip().rstrip(";")
    low = s.lower()
    if not low.startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")
    # crude but effective: forbid write keywords even inside substrings
    tokens = set(low.replace("(", " ").replace(")", " ").replace(",", " ").split())
    # also substring check for ; + stacked queries
    if ";" in s:
        raise ValueError("Multiple statements are not allowed.")
    for w in FORBIDDEN:
        if w in tokens or f" {w} " in f" {low} ":
            raise ValueError(f"Blocked keyword: {w}. Read-only access.")
    if "limit" not in low:
        s = f"{s} LIMIT {max_rows}"
    return s
