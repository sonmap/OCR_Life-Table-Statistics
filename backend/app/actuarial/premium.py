from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .commutation import build_commutation_table, value_at
from .life_table import LifeTable

ProductType = Literal["whole_life", "term_life", "endowment", "annuity_due"]


@dataclass
class PremiumInput:
    age: int
    term: int
    sum_assured: float
    interest_rate: float
    product_type: ProductType


def calculate_premium(input_data: PremiumInput, life_table: LifeTable) -> dict:
    c = build_commutation_table(life_table, input_data.interest_rate)
    x = input_data.age
    n = input_data.term
    S = input_data.sum_assured

    Dx = value_at(c, "Dx", x)
    Dx_n = value_at(c, "Dx", x + n)
    Nx = value_at(c, "Nx", x)
    Nx_n = value_at(c, "Nx", x + n)
    Mx = value_at(c, "Mx", x)
    Mx_n = value_at(c, "Mx", x + n)

    if Dx <= 0:
        raise ValueError(f"D_x is zero at age {x}")

    annuity_due = max((Nx - Nx_n) / Dx, 0.0)
    whole_life_nsp = Mx / Dx
    term_life_nsp = max((Mx - Mx_n) / Dx, 0.0)
    pure_endowment_nsp = Dx_n / Dx if Dx_n else 0.0
    endowment_nsp = term_life_nsp + pure_endowment_nsp

    if input_data.product_type == "whole_life":
        net_single_premium_rate = whole_life_nsp
    elif input_data.product_type == "term_life":
        net_single_premium_rate = term_life_nsp
    elif input_data.product_type == "endowment":
        net_single_premium_rate = endowment_nsp
    elif input_data.product_type == "annuity_due":
        net_single_premium_rate = annuity_due
    else:
        raise ValueError(f"unsupported product_type: {input_data.product_type}")

    level_annual_premium_rate = net_single_premium_rate / annuity_due if annuity_due > 0 else 0.0

    return {
        "age": x,
        "term": n,
        "product_type": input_data.product_type,
        "sum_assured": S,
        "interest_rate": input_data.interest_rate,
        "commutation": {
            "Dx": Dx,
            "Dx_n": Dx_n,
            "Nx": Nx,
            "Nx_n": Nx_n,
            "Mx": Mx,
            "Mx_n": Mx_n,
        },
        "rates": {
            "whole_life_nsp": whole_life_nsp,
            "term_life_nsp": term_life_nsp,
            "pure_endowment_nsp": pure_endowment_nsp,
            "endowment_nsp": endowment_nsp,
            "annuity_due": annuity_due,
            "net_single_premium_rate": net_single_premium_rate,
            "level_annual_premium_rate": level_annual_premium_rate,
        },
        "amounts": {
            "net_single_premium": round(S * net_single_premium_rate, 2),
            "level_annual_premium": round(S * level_annual_premium_rate, 2),
        },
        "formula_mapping": {
            "D_x": "COMMUTATION_D",
            "N_x": "COMMUTATION_N",
            "M_x": "COMMUTATION_M",
            "term_life": "TERM_INSURANCE",
            "annuity_due": "ANNUITY_DUE",
        },
    }


def calculate_from_csv(life_table_path: str | Path, payload: dict) -> dict:
    table = LifeTable.from_csv(life_table_path)
    inp = PremiumInput(
        age=int(payload["age"]),
        term=int(payload.get("term", 20)),
        sum_assured=float(payload.get("sum_assured", 1.0)),
        interest_rate=float(payload.get("interest_rate", 0.03)),
        product_type=payload.get("product_type", "term_life"),
    )
    return calculate_premium(inp, table)
