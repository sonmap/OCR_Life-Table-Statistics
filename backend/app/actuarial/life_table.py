from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class LifeTable:
    rows: pd.DataFrame

    @classmethod
    def from_csv(cls, path: str | Path) -> "LifeTable":
        df = pd.read_csv(path)
        required = {"age", "lx"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"life table missing columns: {missing}")
        df = df.sort_values("age").reset_index(drop=True)
        if "dx" not in df.columns:
            df["dx"] = df["lx"] - df["lx"].shift(-1).fillna(0)
        if "qx" not in df.columns:
            df["qx"] = df["dx"] / df["lx"].replace(0, pd.NA)
        return cls(df)

    def lx(self, age: int) -> float:
        row = self.rows[self.rows["age"] == age]
        if row.empty:
            return 0.0
        return float(row.iloc[0]["lx"])

    def dx(self, age: int) -> float:
        row = self.rows[self.rows["age"] == age]
        if row.empty:
            return 0.0
        return float(row.iloc[0]["dx"])

    def max_age(self) -> int:
        return int(self.rows["age"].max())
