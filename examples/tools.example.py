"""Example tools file for probe.py (set "tools_file" in the experiment and "tools": true on a variant).

Each tool is a plain Python function plus a JSON Schema for its arguments. Keep tools as small as a
competent builder would write in an afternoon; the point is to see whether one simple tool closes a
gap the plain baseline could not.
"""

PLANS = {
    "Starter": {"monthly": 19, "max_invoices": 50, "included_users": 1, "extra_user": None},
    "Team": {"monthly": 79, "max_invoices": 500, "included_users": 5, "extra_user": 9},
}


def quote(plan, users, invoices_per_month):
    p = PLANS.get(plan)
    if p is None:
        return {"error": f"{plan} has no list price (Enterprise is quote only)."}
    if invoices_per_month > p["max_invoices"]:
        return {"fits": False, "reason": f"{plan} allows up to {p['max_invoices']} invoices per month."}
    extra = max(0, users - p["included_users"])
    if extra and p["extra_user"] is None:
        return {"fits": False, "reason": f"{plan} is for {p['included_users']} user only."}
    return {"fits": True, "monthly_usd": p["monthly"] + extra * (p["extra_user"] or 0), "billing": "annual",
            "note": "excludes sales tax"}


TOOLS = [
    {
        "name": "quote",
        "description": "Monthly price of a plan for a given number of users and invoices per month. Use it for any price calculation.",
        "parameters": {
            "type": "object",
            "properties": {
                "plan": {"type": "string", "enum": ["Starter", "Team", "Enterprise"]},
                "users": {"type": "integer"},
                "invoices_per_month": {"type": "integer"},
            },
            "required": ["plan", "users", "invoices_per_month"],
        },
        "fn": quote,
    }
]
