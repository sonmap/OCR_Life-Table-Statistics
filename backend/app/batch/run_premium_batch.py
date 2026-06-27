from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from app.actuarial.life_table import LifeTable
from app.actuarial.premium import PremiumInput, calculate_premium


def run_batch(life_table_path: str | Path, policies_path: str | Path, output_path: str | Path) -> pd.DataFrame:
    life_table = LifeTable.from_csv(life_table_path)
    policies = _read_table(policies_path)
    results = []

    for _, row in policies.iterrows():
        inp = PremiumInput(
            age=int(row["age"]),
            term=int(row.get("term", 20)),
            sum_assured=float(row.get("sum_assured", 1.0)),
            interest_rate=float(row.get("interest_rate", 0.03)),
            product_type=str(row.get("product_type", "term_life")),
        )
        result = calculate_premium(inp, life_table)
        flat = {
            "policy_id": row.get("policy_id", ""),
            "age": inp.age,
            "term": inp.term,
            "product_type": inp.product_type,
            "sum_assured": inp.sum_assured,
            "interest_rate": inp.interest_rate,
            "net_single_premium": result["amounts"]["net_single_premium"],
            "level_annual_premium": result["amounts"]["level_annual_premium"],
            "net_single_premium_rate": result["rates"]["net_single_premium_rate"],
            "level_annual_premium_rate": result["rates"]["level_annual_premium_rate"],
        }
        if "excel_premium" in row and not pd.isna(row["excel_premium"]):
            flat["excel_premium"] = float(row["excel_premium"])
            flat["diff_vs_excel"] = round(flat["level_annual_premium"] - flat["excel_premium"], 6)
        results.append(flat)

    out = pd.DataFrame(results)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return out


def _read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xlsm"}:
        return pd.read_excel(path)
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run premium batch simulation")
    parser.add_argument("--life-table", required=True)
    parser.add_argument("--policies", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    out = run_batch(args.life_table, args.policies, args.output)
    print(out.to_string(index=False))
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
