from __future__ import annotations

import pandas as pd

from .life_table import LifeTable


def build_commutation_table(life_table: LifeTable, interest_rate: float) -> pd.DataFrame:
    """Build actuarial commutation columns D_x, N_x, M_x.

    v = 1 / (1+i)
    D_x = v^x l_x
    N_x = sum_{y=x}^{omega} D_y
    M_x = sum_{y=x}^{omega} v^{y+1} d_y
    """
    df = life_table.rows.copy()
    v = 1.0 / (1.0 + interest_rate)
    df["v_power_x"] = df["age"].apply(lambda x: v ** int(x))
    df["Dx"] = df["v_power_x"] * df["lx"]
    df["Mx_term"] = df["age"].apply(lambda y: v ** (int(y) + 1)) * df["dx"]
    df["Nx"] = df["Dx"][::-1].cumsum()[::-1]
    df["Mx"] = df["Mx_term"][::-1].cumsum()[::-1]
    return df[["age", "lx", "dx", "qx", "Dx", "Nx", "Mx"]]


def value_at(commutation: pd.DataFrame, column: str, age: int) -> float:
    row = commutation[commutation["age"] == age]
    if row.empty:
        return 0.0
    return float(row.iloc[0][column])


def commutation_D(life_table: LifeTable, interest_rate: float, age: int) -> float:
    return value_at(build_commutation_table(life_table, interest_rate), "Dx", age)


def commutation_N(life_table: LifeTable, interest_rate: float, age: int) -> float:
    return value_at(build_commutation_table(life_table, interest_rate), "Nx", age)


def commutation_M(life_table: LifeTable, interest_rate: float, age: int) -> float:
    return value_at(build_commutation_table(life_table, interest_rate), "Mx", age)
