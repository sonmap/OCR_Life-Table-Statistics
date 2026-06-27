from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any

from .formula_repair import repair_latex


@dataclass(frozen=True)
class ActuarialFormulaExample:
    formula_code: str
    category: str
    formula_name: str
    latex: str
    python_function: str | None
    description: str
    variables: list[str]
    keywords: list[str]
    aliases: list[str]


@dataclass
class FormulaParseResult:
    formula_code: str
    formula_name: str
    category: str
    latex: str
    python_function: str | None
    variables: list[str]
    confidence: float
    status: str
    validation_message: str
    metadata: dict[str, Any]


FORMULA_EXAMPLES: list[ActuarialFormulaExample] = [
    ActuarialFormulaExample("DISCOUNT_FACTOR", "interest", "Discount factor", r"v = \frac{1}{1+i}", "discount_factor", "Discount factor from effective annual interest rate i.", ["v", "i"], ["discount", "interest", "v", "i"], ["v=1/(1+i)"]),
    ActuarialFormulaExample("SURVIVAL_PROBABILITY", "life_table", "k-year survival probability", r"{}_kp_x = \frac{l_{x+k}}{l_x}", "survival_probability", "Probability that a life aged x survives k years.", ["k", "p_x", "l_x", "l_{x+k}"], ["survival", "p_x", "l_x", "l_{x+k}"], ["kpx", "{}_kp_x", "l x+k / l x"]),
    ActuarialFormulaExample("DEATH_PROBABILITY", "life_table", "One-year death probability", r"q_x = \frac{d_x}{l_x} = 1 - p_x", "death_probability", "Probability that a life aged x dies within one year.", ["q_x", "d_x", "l_x", "p_x"], ["death", "q_x", "d_x", "l_x"], ["qx", "d_x/l_x", "1-p_x"]),
    ActuarialFormulaExample("DEFERRED_DEATH_PROBABILITY", "life_table", "Deferred death probability", r"{}_kp_x q_{x+k} = \frac{l_{x+k}-l_{x+k+1}}{l_x}", "deferred_death_probability", "Probability that a life aged x survives k years and dies during year k+1.", ["k", "p_x", "q_{x+k}", "l_x", "l_{x+k}", "l_{x+k+1}"], ["deferred", "kpx", "q_x+k", "l_x+k"], ["k p x q x+k", "{}_kp_x q_{x+k}"]),

    ActuarialFormulaExample("COMMUTATION_D", "commutation", "Commutation function D_x", r"D_x = v^x l_x", "commutation_D", "Discounted number of lives at age x.", ["D_x", "v", "x", "l_x"], ["D_x", "v^x", "l_x", "commutation"], ["Dx", "D x", "v x l x"]),
    ActuarialFormulaExample("COMMUTATION_C", "commutation", "Commutation function C_x", r"C_x = v^{x+1}d_x", "commutation_C", "One-year discounted death count.", ["C_x", "v", "x", "d_x"], ["C_x", "v", "d_x"], ["Cx", "C x"]),
    ActuarialFormulaExample("COMMUTATION_N", "commutation", "Commutation function N_x", r"N_x = \sum_{y=x}^{\infty}D_y", "commutation_N", "Reverse cumulative sum of D_y.", ["N_x", "D_y", "y", "x"], ["N_x", "sum", "D_y", "annuity"], ["Nx", "N x", "sum D_y"]),
    ActuarialFormulaExample("COMMUTATION_M", "commutation", "Commutation function M_x", r"M_x = \sum_{y=x}^{\infty}v^{y+1}d_y", "commutation_M", "Commutation function for insurance benefits.", ["M_x", "v", "y", "d_y"], ["M_x", "sum", "v", "d_y", "insurance"], ["Mx", "M x", "sum v y+1 d y"]),
    ActuarialFormulaExample("COMMUTATION_R", "commutation", "Commutation function R_x", r"R_x = \sum_{y=x}^{\infty}(y+1)v^{y+1}d_y", "commutation_R", "Auxiliary commutation column for increasing insurance.", ["R_x", "y", "v", "d_y"], ["R_x", "increasing", "benefit", "d_y"], ["Rx", "increasing insurance"]),

    ActuarialFormulaExample("PURE_ENDOWMENT", "premium", "Pure n-year endowment", r"A^1_{x:\overline{n}|} = {}_nE_x = v^n{}_np_x = \frac{D_{x+n}}{D_x}", "pure_endowment", "Present value of payment 1 at time n if alive.", ["A^1", "n", "E_x", "v", "p_x", "D_x"], ["pure endowment", "D_x+n", "D_x", "nE_x"], ["nEx", "D x+n / D x"]),
    ActuarialFormulaExample("WHOLE_LIFE_INSURANCE", "premium", "Whole life insurance", r"A_x = \sum_{k=0}^{\infty}v^{k+1}{}_kp_xq_{x+k} = \frac{M_x}{D_x}", "whole_life_insurance", "Net single premium for whole life insurance.", ["A_x", "v", "k", "p_x", "q_{x+k}", "M_x", "D_x"], ["whole life", "A_x", "M_x", "D_x", "q_x+k"], ["Ax", "M_x/D_x", "whole life insurance"]),
    ActuarialFormulaExample("TERM_INSURANCE", "premium", "n-year term insurance", r"A^1_{x:\overline{n}|} = \sum_{k=0}^{n-1}v^{k+1}{}_kp_xq_{x+k} = \frac{M_x-M_{x+n}}{D_x}", "term_life_net_single_premium", "Net single premium for n-year term insurance.", ["A^1", "x", "n", "M_x", "M_{x+n}", "D_x"], ["term", "insurance", "M_x-M_x+n", "D_x"], ["A1 x:n", "M_x - M_{x+n}"]),
    ActuarialFormulaExample("ENDOWMENT_INSURANCE", "premium", "n-year endowment insurance", r"A_{x:\overline{n}|} = A^1_{x:\overline{n}|} + A^1_{x:\overline{n}|}", "endowment_insurance", "Endowment insurance equals term insurance plus pure endowment.", ["A", "x", "n"], ["endowment", "term", "pure endowment"], ["endowment insurance"]),
    ActuarialFormulaExample("INCREASING_INSURANCE", "premium", "Increasing whole life insurance", r"IA_x = \sum_{k=0}^{\infty}(k+1)v^{k+1}{}_kp_xq_{x+k} = \frac{R_x-xM_x}{D_x}", "increasing_whole_life_insurance", "Whole life insurance with linearly increasing benefit.", ["IA_x", "R_x", "M_x", "D_x"], ["increasing", "IA", "R_x", "xM_x"], ["IAx", "increasing benefit"]),
    ActuarialFormulaExample("DECREASING_TERM_INSURANCE", "premium", "Decreasing term insurance", r"DA^1_{x:\overline{n}|} = (n+1)A^1_{x:\overline{n}|} - IA^1_{x:\overline{n}|}", "decreasing_term_insurance", "Decreasing-benefit term insurance.", ["DA", "IA", "n", "A"], ["decreasing", "DA", "IA", "term"], ["DA1", "decreasing benefit"]),

    ActuarialFormulaExample("WHOLE_LIFE_ANNUITY_DUE", "annuity", "Whole life annuity-due", r"\ddot{a}_x = \sum_{k=0}^{\infty}v^k{}_kp_x = \frac{N_x}{D_x}", "whole_life_annuity_due", "Present value of whole life annuity-due.", ["a_x", "N_x", "D_x"], ["annuity", "due", "N_x", "D_x"], ["äx", "annuity due"]),
    ActuarialFormulaExample("TEMPORARY_ANNUITY_DUE", "annuity", "Temporary life annuity-due", r"\ddot{a}_{x:\overline{n}|} = \sum_{k=0}^{n-1}v^k{}_kp_x = \frac{N_x-N_{x+n}}{D_x}", "temporary_annuity_due", "Present value of n-year temporary life annuity-due.", ["a", "x", "n", "N_x", "N_{x+n}", "D_x"], ["temporary", "annuity", "N_x-N_x+n"], ["a x:n", "N_x - N_{x+n}"]),
    ActuarialFormulaExample("ANNUITY_IMMEDIATE", "annuity", "Whole life annuity-immediate", r"a_x = \ddot{a}_x - 1", "whole_life_annuity_immediate", "Annuity-immediate equals annuity-due less the first payment.", ["a_x", "ddot_a_x"], ["annuity immediate", "annuity due"], ["a_x = äx - 1"]),

    ActuarialFormulaExample("LEVEL_PREMIUM_TERM", "level_premium", "Level annual premium for term insurance", r"P^1_{x:\overline{n}|} = \frac{A^1_{x:\overline{n}|}}{\ddot{a}_{x:\overline{n}|}}", "level_premium_term", "Level annual net premium for n-year term insurance.", ["P", "A", "a"], ["premium", "level", "term", "annuity"], ["P1 x:n", "annual premium"]),
    ActuarialFormulaExample("LEVEL_PREMIUM_ENDOWMENT", "level_premium", "Level annual premium for endowment insurance", r"P_{x:\overline{n}|} = \frac{A_{x:\overline{n}|}}{\ddot{a}_{x:\overline{n}|}}", "level_premium_endowment", "Level annual net premium for n-year endowment insurance.", ["P", "A", "a", "x", "n"], ["premium", "level", "endowment"], ["P x:n", "endowment premium"]),
    ActuarialFormulaExample("PREMIUM_IDENTITY_ENDOWMENT", "level_premium", "Endowment premium identity", r"P_{x:\overline{n}|} = \frac{1}{\ddot{a}_{x:\overline{n}|}} - d", "endowment_premium_identity", "Premium identity derived from A = 1 - d a-double-dot.", ["P", "a", "d"], ["premium", "identity", "d", "annuity"], ["1/a - d"]),

    ActuarialFormulaExample("TERM_RESERVE_PROSPECTIVE", "reserve", "Prospective reserve for term insurance", r"{}_tV^1_{x:\overline{n}|} = A^1_{x+t:\overline{n-t}|} - P^1_{x:\overline{n}|}\ddot{a}_{x+t:\overline{n-t}|}", "term_life_reserve", "Prospective reserve at policy duration t for term insurance.", ["t", "V", "A", "P", "a", "x", "n"], ["reserve", "prospective", "term", "V"], ["tV1", "term reserve"]),
    ActuarialFormulaExample("ENDOWMENT_RESERVE_PROSPECTIVE", "reserve", "Prospective reserve for endowment insurance", r"{}_tV_{x:\overline{n}|} = A_{x+t:\overline{n-t}|} - P_{x:\overline{n}|}\ddot{a}_{x+t:\overline{n-t}|}", "endowment_reserve", "Prospective reserve at policy duration t for endowment insurance.", ["t", "V", "A", "P", "a", "x", "n"], ["reserve", "prospective", "endowment"], ["tV endowment"]),
    ActuarialFormulaExample("ENDOWMENT_RESERVE_IDENTITY", "reserve", "Endowment reserve identity", r"{}_tV_{x:\overline{n}|} = 1 - \frac{\ddot{a}_{x+t:\overline{n-t}|}}{\ddot{a}_{x:\overline{n}|}}", "endowment_reserve_identity", "Simplified reserve identity for endowment insurance.", ["t", "V", "a", "x", "n"], ["reserve", "identity", "annuity"], ["1 - a future / a issue"]),
    ActuarialFormulaExample("RETROSPECTIVE_RESERVE_TERM", "reserve", "Retrospective reserve identity for term insurance", r"v^t{}_tp_x{}_tV^1_{x:\overline{n}|} = -\left[A^1_{x:\overline{t}|} - P^1_{x:\overline{n}|}\ddot{a}_{x:\overline{t}|}\right]", "retrospective_term_reserve", "Retrospective identity connecting past accumulated value and prospective reserve.", ["v", "t", "p_x", "V", "A", "P", "a"], ["retrospective", "reserve", "term"], ["v^t tpx tV"]),

    ActuarialFormulaExample("MTHLY_INSURANCE_INTERPOLATION", "payment_frequency", "m-thly insurance interpolation", r"A^{(m)1}_{x:\overline{n}|} = \frac{i}{i^{(m)}}A^1_{x:\overline{n}|}", "mthly_insurance_interpolation", "Case interpolation formula for m-payment-per-year insurance.", ["A", "m", "i", "i^{(m)}"], ["mthly", "interpolation", "i/i"], ["A(m)", "i / i(m)"]),
    ActuarialFormulaExample("MTHLY_ANNUITY_INTERPOLATION", "payment_frequency", "m-thly annuity interpolation", r"\ddot{a}^{(m)}_{x:\overline{n}|} = \alpha(m)\ddot{a}_{x:\overline{n}|} - \beta(m)(1-A^1_{x:\overline{n}|})", "mthly_annuity_interpolation", "Case interpolation formula for m-payment-per-year annuity-due.", ["a", "m", "alpha", "beta", "A"], ["mthly", "annuity", "alpha", "beta"], ["a(m)", "alpha beta"]),

    ActuarialFormulaExample("SELECT_SURVIVAL_PROBABILITY", "select_mortality", "Select survival probability", r"{}_kp_{[x]+s} = \prod_{j=0}^{k-1}p_{[x]+s+j}", "select_survival_probability", "Survival probability under select mortality notation.", ["k", "p", "[x]", "s"], ["select", "mortality", "[x]", "p"], ["p_[x]+s", "select p"]),
    ActuarialFormulaExample("MORTALITY_TREND_FORCE", "mortality_trend", "Time-dependent force of mortality", r"\mu_x^{(t)} = \mu_x^{(0)} + b_xt", "mortality_trend_force", "Simple linear calendar-time trend in force of mortality.", ["mu", "x", "t", "b_x"], ["mortality trend", "mu", "force", "b_x"], ["mu_x(t)", "mu x 0 plus b x t"]),
    ActuarialFormulaExample("TIME_DEPENDENT_D", "mortality_trend", "Time-dependent commutation D", r"D_x^{(t)} = D_x^{(0)}e^{-tB_x}", "time_dependent_commutation_D", "Commutation D under a mortality trend model.", ["D", "t", "B_x"], ["time dependent", "D", "trend", "B_x"], ["D(t)", "D0 exp"]),
]

FORMULA_BY_CODE = {item.formula_code: item for item in FORMULA_EXAMPLES}


def get_formula_examples() -> list[dict[str, Any]]:
    return [asdict(item) for item in FORMULA_EXAMPLES]


def normalize_formula_text(text: str) -> str:
    s = text or ""
    for old, new in {
        "∞": r"\infty", "Σ": r"\sum", "∑": r"\sum", "µ": r"\mu", "μ": r"\mu",
        "¨a": r"\ddot{a}", "ä": r"\ddot{a}", "⌉": "|", "−": "-", "–": "-", "—": "-",
        "·": r"\cdot", "×": r"\times",
    }.items():
        s = s.replace(old, new)
    return re.sub(r"\s+", " ", s).strip()


def is_formula_like(line: str) -> bool:
    s = normalize_formula_text(line)
    tokens = ["=", r"\sum", r"\frac", r"\infty", "_", "^", "D_x", "N_x", "M_x", "C_x", "R_x", "A_", "P_", "V_", "l_x", "d_x", "q_x", "p_x", "annuity", "premium", "reserve"]
    if any(token.lower() in s.lower() for token in tokens):
        return True
    return bool(re.search(r"\b(D|N|M|A|P|V|l|d|q|p)\s*x\b", s))


def extract_formula_candidates(text: str, max_candidates: int = 50) -> list[str]:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    candidates: list[str] = []
    buffer: list[str] = []
    for line in lines:
        if is_formula_like(line):
            buffer.append(line)
        else:
            if buffer:
                candidates.append(" ".join(buffer))
                buffer = []
    if buffer:
        candidates.append(" ".join(buffer))
    return _dedupe(candidates)[:max_candidates]


def parse_formula_candidate(raw_text: str) -> FormulaParseResult:
    latex = repair_latex(normalize_formula_text(raw_text))
    code, confidence, matched = classify_formula(latex, raw_text)
    example = FORMULA_BY_CODE.get(code)
    warnings = validate_latex_structure(latex)
    status = "CANDIDATE" if confidence >= 0.45 and not warnings else "NEEDS_REVIEW"
    if example:
        variables = sorted(set(example.variables + extract_variables(latex)))
        formula_name = example.formula_name
        category = example.category
        function = example.python_function
        message = "matched actuarial formula"
    else:
        variables = extract_variables(latex)
        formula_name = "OCR Formula Candidate"
        category = "unknown"
        function = None
        message = "unclassified OCR formula candidate"
    if warnings:
        message += "; warnings=" + ",".join(warnings)
    return FormulaParseResult(code, formula_name, category, latex, function, variables, round(confidence, 3), status, message, {"raw_text": raw_text, "matched_keywords": matched, "warnings": warnings})


def classify_formula(latex: str, raw_text: str | None = None) -> tuple[str, float, list[str]]:
    haystack = normalize_formula_text((latex or "") + " " + (raw_text or "")).lower()
    compact = re.sub(r"\s+", "", haystack)
    best_code = "OCR_FORMULA"
    best_score = 0.0
    best_matched: list[str] = []
    for item in FORMULA_EXAMPLES:
        matched = []
        for keyword in item.keywords + item.aliases:
            key = normalize_formula_text(keyword).lower()
            key_compact = re.sub(r"\s+", "", key)
            if key and (key in haystack or key_compact in compact):
                matched.append(keyword)
        weak_hits = sum(1 for var in item.variables if normalize_formula_text(var).lower().replace("{}", "") in haystack)
        score = min(1.0, len(matched) * 0.18 + weak_hits * 0.04)
        if item.formula_code == "COMMUTATION_D" and all(t in haystack for t in ["d_x", "l_x", "v"]):
            score += 0.45
        if item.formula_code == "TERM_INSURANCE" and "m_x" in haystack and "m_{x+n}" in haystack and "d_x" in haystack:
            score += 0.45
        if item.formula_code == "TEMPORARY_ANNUITY_DUE" and "n_x" in haystack and "n_{x+n}" in haystack and "d_x" in haystack:
            score += 0.45
        if item.formula_code == "WHOLE_LIFE_INSURANCE" and "m_x" in haystack and "d_x" in haystack and "a_x" in haystack:
            score += 0.25
        score = min(score, 1.0)
        if score > best_score:
            best_code, best_score, best_matched = item.formula_code, score, matched
    return best_code, best_score, best_matched


def formula_to_function(code: str) -> str | None:
    item = FORMULA_BY_CODE.get(code)
    return item.python_function if item else None


def formula_name(code: str) -> str:
    item = FORMULA_BY_CODE.get(code)
    return item.formula_name if item else "OCR Formula Candidate"


def formula_category(code: str) -> str:
    item = FORMULA_BY_CODE.get(code)
    return item.category if item else "unknown"


def extract_variables(latex: str) -> list[str]:
    variables = set()
    for pat in [r"[A-Za-z]+_\{[^}]+\}", r"[A-Za-z]+_[A-Za-z0-9]+", r"\\mu_\{?[^}\s]+\}?", r"\\ddot\{a\}_\{[^}]+\}", r"\b[DNLMCARPV]_[A-Za-z0-9]+\b"]:
        variables.update(re.findall(pat, latex or ""))
    for token in ["i", "v", "d", "x", "n", "t", "k", "m"]:
        if re.search(rf"\b{token}\b", latex or ""):
            variables.add(token)
    return sorted(variables)


def validate_latex_structure(latex: str) -> list[str]:
    warnings: list[str] = []
    if latex.count("{") != latex.count("}"):
        warnings.append("unbalanced_braces")
    if r"\sum" in latex and not re.search(r"\\sum_\{[^}]+\}\^\{[^}]+\}", latex):
        warnings.append("sum_bounds_missing_or_broken")
    if "/" in latex and r"\frac" not in latex:
        warnings.append("slash_fraction_not_structured")
    if re.search(r"\b(A|P|V|D|N|M|l|q|p)\s+x\b", latex):
        warnings.append("subscript_may_be_missing")
    return warnings


def build_formula_dsl(result: FormulaParseResult | str) -> dict[str, Any]:
    if isinstance(result, str):
        result = parse_formula_candidate(result)
    return {
        "formula_code": result.formula_code,
        "formula_name": result.formula_name,
        "category": result.category,
        "latex": result.latex,
        "python_function": result.python_function,
        "variables": result.variables,
        "confidence": result.confidence,
        "status": result.status,
        "validation_message": result.validation_message,
        "metadata": result.metadata,
    }


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = re.sub(r"\W+", "", item.lower())[:200]
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out
