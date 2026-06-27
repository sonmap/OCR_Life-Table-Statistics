from __future__ import annotations

from dataclasses import dataclass, asdict
import json


@dataclass(frozen=True)
class FormulaExample:
    formula_code: str
    formula_name: str
    formula_family: str
    latex: str
    python_function: str | None
    variables: list[str]
    description: str
    tags: list[str]


FORMULA_EXAMPLES: list[FormulaExample] = [
    FormulaExample("DISCOUNT_FACTOR", "Discount factor", "interest", "v = 1 / (1+i)", "discount_factor", ["v", "i"], "Discount factor from annual effective interest rate.", ["interest", "discount"]),
    FormulaExample("DISCOUNT_RATE", "Discount rate", "interest", "d = i / (1+i)", "discount_rate", ["d", "i"], "Annual effective discount rate.", ["interest", "discount"]),
    FormulaExample("LIFE_TABLE_DEATHS", "Life-table deaths", "life_table", "d_x = l_x - l_{x+1}", "life_table_deaths", ["d_x", "l_x", "l_{x+1}"], "Deaths between exact ages x and x+1.", ["life_table", "mortality"]),
    FormulaExample("ONE_YEAR_DEATH_PROBABILITY", "One-year death probability", "life_table", "q_x = d_x / l_x", "one_year_death_probability", ["q_x", "d_x", "l_x"], "Probability of death within one year.", ["life_table", "mortality"]),
    FormulaExample("ONE_YEAR_SURVIVAL_PROBABILITY", "One-year survival probability", "life_table", "p_x = 1 - q_x = l_{x+1} / l_x", "one_year_survival_probability", ["p_x", "q_x", "l_{x+1}", "l_x"], "Probability of survival for one year.", ["life_table", "survival"]),
    FormulaExample("N_YEAR_SURVIVAL_PROBABILITY", "n-year survival probability", "life_table", "{}_n p_x = l_{x+n} / l_x", "n_year_survival_probability", ["{}_n p_x", "l_{x+n}", "l_x"], "Probability that a life aged x survives n years.", ["life_table", "survival"]),
    FormulaExample("N_YEAR_DEATH_PROBABILITY", "n-year death probability", "life_table", "{}_n q_x = 1 - {}_n p_x", "n_year_death_probability", ["{}_n q_x", "{}_n p_x"], "Probability that a life aged x dies within n years.", ["life_table", "mortality"]),
    FormulaExample("DEFERRED_DEATH_PROBABILITY", "Deferred death probability", "life_table", "{}_{k|}q_x = {}_k p_x q_{x+k}", "deferred_death_probability", ["{}_{k|}q_x", "{}_k p_x", "q_{x+k}"], "Survive k years then die in the next year.", ["deferred", "mortality"]),
    FormulaExample("COMMUTATION_D", "Commutation function D_x", "commutation", "D_x = v^x l_x", "commutation_D", ["D_x", "v", "l_x"], "Discounted number of lives at age x.", ["commutation", "D"]),
    FormulaExample("COMMUTATION_C", "Commutation function C_x", "commutation", "C_x = v^{x+1} d_x", "commutation_C", ["C_x", "v", "d_x"], "Discounted deaths between ages x and x+1.", ["commutation", "C"]),
    FormulaExample("COMMUTATION_N", "Commutation function N_x", "commutation", "N_x = sum_{y=x}^{infinity} D_y", "commutation_N", ["N_x", "D_y"], "Reverse cumulative sum of D_y.", ["commutation", "N", "annuity"]),
    FormulaExample("COMMUTATION_M", "Commutation function M_x", "commutation", "M_x = sum_{y=x}^{infinity} C_y", "commutation_M", ["M_x", "C_y"], "Reverse cumulative sum of discounted deaths.", ["commutation", "M"]),
]


def examples_as_dicts() -> list[dict]:
    return [asdict(item) for item in FORMULA_EXAMPLES]


def examples_as_json() -> str:
    return json.dumps(examples_as_dicts(), ensure_ascii=False, indent=2)


def find_examples(keyword: str) -> list[FormulaExample]:
    q = (keyword or "").lower()
    if not q:
        return FORMULA_EXAMPLES
    return [item for item in FORMULA_EXAMPLES if q in item.formula_code.lower() or q in item.formula_name.lower() or q in item.formula_family.lower() or any(q in tag.lower() for tag in item.tags)]
