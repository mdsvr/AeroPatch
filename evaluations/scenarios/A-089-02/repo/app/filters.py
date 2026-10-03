"""Turn search criteria into SQL fragments for the product catalogue."""

FILTERABLE = ("name", "category", "supplier")
SORTABLE = {"name": "name", "price": "price_cents", "newest": "id DESC"}


def build_filter(**criteria):
    """Return a WHERE clause for the given column=value criteria ('' when there are none)."""
    clauses = []
    for column, value in sorted(criteria.items()):
        if column not in FILTERABLE:
            raise ValueError(f"cannot filter on {column!r}")
        if value is None:
            continue
        clauses.append(f"{column} = '{value}'")
    if not clauses:
        return ""
    return " WHERE " + " AND ".join(clauses)


def order_clause(sort="name"):
    """Return an ORDER BY clause for one of the SORTABLE keys."""
    try:
        return " ORDER BY " + SORTABLE[sort]
    except KeyError:
        raise ValueError(f"cannot sort by {sort!r}") from None
