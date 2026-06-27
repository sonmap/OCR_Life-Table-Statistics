from __future__ import annotations

from .commutation import build_commutation_table, value_at
from .life_table import LifeTable


def term_life_reserve(life_table: LifeTable, interest_rate: float, age: int, term: int, policy_year: int) -> dict:
    """Prospective reserve sample for term life insurance.

    tV = A^1_{x+t:n-t} - P^1_{x:n} * a_due_{x+t:n-t}
    """
    if policy_year < 0 or policy_year > term:
        raise ValueError("policy_year must be between 0 and term")

    c = build_commutation_table(life_table, interest_rate)
    x = age
    n = term
    t = policy_year

    Dx = value_at(c, "Dx", x)
    Mx = value_at(c, "Mx", x)
    Mx_n = value_at(c, "Mx", x + n)
    Nx = value_at(c, "Nx", x)
    Nx_n = value_at(c, "Nx", x + n)

    annuity_issue = (Nx - Nx_n) / Dx if Dx else 0.0
    term_nsp_issue = (Mx - Mx_n) / Dx if Dx else 0.0
    annual_premium = term_nsp_issue / annuity_issue if annuity_issue else 0.0

    Dxt = value_at(c, "Dx", x + t)
    Mxt = value_at(c, "Mx", x + t)
    Mxn = value_at(c, "Mx", x + n)
    Nxt = value_at(c, "Nx", x + t)
    Nxn = value_at(c, "Nx", x + n)

    future_nsp = (Mxt - Mxn) / Dxt if Dxt else 0.0
    future_annuity = (Nxt - Nxn) / Dxt if Dxt else 0.0
    reserve = future_nsp - annual_premium * future_annuity

    return {
        "age": age,
        "term": term,
        "policy_year": policy_year,
        "annual_premium_rate": annual_premium,
        "future_nsp_rate": future_nsp,
        "future_annuity_due": future_annuity,
        "reserve_rate": reserve,
    }
