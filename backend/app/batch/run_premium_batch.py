from __future__ import annotations

import argparse
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd

from app.actuarial.commutation import build_commutation_table
from app.actuarial.life_table import LifeTable
from app.actuarial.premium import PremiumInput, calculate_premium

_WORKER_CACHE: dict[str, Any] = {}


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
        flat = _flatten_result(row, inp, result)
        results.append(flat)

    out = pd.DataFrame(results)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return out


def run_grouped_batch(life_table_path: str | Path, policies_path: str | Path, output_path: str | Path) -> pd.DataFrame:
    """Calculate duplicate premium keys once, then map results back to all rows."""
    life_table = LifeTable.from_csv(life_table_path)
    policies = _read_table(policies_path)
    key_cols = _key_columns(policies)
    unique_cases = policies[key_cols].drop_duplicates().reset_index(drop=True)

    results = []
    for _, row in unique_cases.iterrows():
        inp = PremiumInput(
            age=int(row["age"]),
            term=int(row.get("term", 20)),
            sum_assured=float(row.get("sum_assured", 1.0)),
            interest_rate=float(row.get("interest_rate", 0.03)),
            product_type=str(row.get("product_type", "term_life")),
        )
        result = calculate_premium(inp, life_table)
        results.append(_flatten_result(row, inp, result))

    unique_result = pd.DataFrame(results)
    out = policies.merge(unique_result, on=key_cols, how="left")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return out


def run_parallel_grouped_batch(
    life_table_path: str | Path,
    policies_path: str | Path,
    output_path: str | Path,
    chunk_size: int = 50000,
    worker_count: int | None = None,
) -> pd.DataFrame:
    """Memory-first grouped calculation using process parallelism.

    Use this for large jobs. It follows the target design:
    SQL/CSV load once -> memory cache -> grouped keys -> chunk parallel calc -> output file.
    DB insert should be performed by a separate loader after this step.
    """
    policies = _read_table(policies_path)
    key_cols = _key_columns(policies)
    unique_cases = policies[key_cols].drop_duplicates().reset_index(drop=True)
    cache = _build_memory_cache(life_table_path, unique_cases["interest_rate"].tolist())
    workers = worker_count or max(1, (os.cpu_count() or 4) - 2)

    chunks = list(_split_dataframe(unique_cases, chunk_size))
    result_chunks: list[tuple[int, pd.DataFrame]] = []
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker, initargs=(cache,)) as executor:
        futures = [executor.submit(_calculate_chunk, chunk_id, chunk) for chunk_id, chunk in chunks]
        for future in as_completed(futures):
            result_chunks.append(future.result())

    result_chunks.sort(key=lambda x: x[0])
    unique_result = pd.concat([df for _, df in result_chunks], ignore_index=True) if result_chunks else pd.DataFrame()
    out = policies.merge(unique_result, on=key_cols, how="left")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return out


def _calculate_chunk(chunk_id: int, chunk: pd.DataFrame) -> tuple[int, pd.DataFrame]:
    rows = []
    for row in chunk.itertuples(index=False):
        rows.append(_calculate_from_cache(row))
    return chunk_id, pd.DataFrame(rows)


def _calculate_from_cache(row: Any) -> dict[str, Any]:
    age = int(row.age)
    term = int(row.term)
    amount = float(row.sum_assured)
    rate = float(row.interest_rate)
    product_type = str(row.product_type)
    comm = _WORKER_CACHE["commutation"][str(rate)]

    dx = float(comm["Dx"].get(age, 0.0))
    dxn = float(comm["Dx"].get(age + term, 0.0))
    nx = float(comm["Nx"].get(age, 0.0))
    nxn = float(comm["Nx"].get(age + term, 0.0))
    mx = float(comm["Mx"].get(age, 0.0))
    mxn = float(comm["Mx"].get(age + term, 0.0))
    if dx <= 0:
        raise ValueError(f"D_x is zero at age {age}")

    annuity_due = max((nx - nxn) / dx, 0.0)
    term_life_nsp = max((mx - mxn) / dx, 0.0)
    pure_endowment_nsp = dxn / dx if dxn else 0.0
    whole_life_nsp = mx / dx
    endowment_nsp = term_life_nsp + pure_endowment_nsp

    if product_type == "whole_life":
        net_rate = whole_life_nsp
    elif product_type == "endowment":
        net_rate = endowment_nsp
    elif product_type == "annuity_due":
        net_rate = annuity_due
    else:
        net_rate = term_life_nsp

    annual_rate = net_rate / annuity_due if annuity_due > 0 else 0.0
    return {
        "age": age,
        "term": term,
        "product_type": product_type,
        "sum_assured": amount,
        "interest_rate": rate,
        "net_single_premium": round(amount * net_rate, 2),
        "level_annual_premium": round(amount * annual_rate, 2),
        "net_single_premium_rate": net_rate,
        "level_annual_premium_rate": annual_rate,
    }


def _build_memory_cache(life_table_path: str | Path, interest_rates: list[float]) -> dict[str, Any]:
    life_table = LifeTable.from_csv(life_table_path)
    commutation = {}
    for rate in sorted(set(float(x) for x in interest_rates)):
        table = build_commutation_table(life_table, rate).set_index("age")
        commutation[str(rate)] = {
            "Dx": table["Dx"].to_dict(),
            "Nx": table["Nx"].to_dict(),
            "Mx": table["Mx"].to_dict(),
        }
    return {"commutation": commutation}


def _init_worker(cache: dict[str, Any]) -> None:
    global _WORKER_CACHE
    _WORKER_CACHE = cache


def _split_dataframe(df: pd.DataFrame, chunk_size: int):
    for start in range(0, len(df), chunk_size):
        yield start // chunk_size, df.iloc[start:start + chunk_size].copy()


def _key_columns(df: pd.DataFrame) -> list[str]:
    keys = ["age", "term", "sum_assured", "interest_rate", "product_type"]
    missing = [x for x in keys if x not in df.columns]
    if missing:
        raise ValueError(f"policies missing columns: {missing}")
    return keys


def _flatten_result(row: Any, inp: PremiumInput, result: dict[str, Any]) -> dict[str, Any]:
    flat = {
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
    if hasattr(row, "get") and "policy_id" in row:
        flat["policy_id"] = row.get("policy_id", "")
    if hasattr(row, "get") and "excel_premium" in row and not pd.isna(row["excel_premium"]):
        flat["excel_premium"] = float(row["excel_premium"])
        flat["diff_vs_excel"] = round(flat["level_annual_premium"] - flat["excel_premium"], 6)
    return flat


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
    parser.add_argument("--mode", choices=["inline", "grouped", "parallel"], default="inline")
    parser.add_argument("--chunk-size", type=int, default=50000)
    parser.add_argument("--workers", type=int, default=None)
    args = parser.parse_args()

    if args.mode == "parallel":
        out = run_parallel_grouped_batch(args.life_table, args.policies, args.output, args.chunk_size, args.workers)
    elif args.mode == "grouped":
        out = run_grouped_batch(args.life_table, args.policies, args.output)
    else:
        out = run_batch(args.life_table, args.policies, args.output)
    print(out.head(20).to_string(index=False))
    print(f"Rows: {len(out)}")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()
