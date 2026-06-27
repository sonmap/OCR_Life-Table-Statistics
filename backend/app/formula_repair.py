import re


CANONICAL_FORMULAS = {
    "COMMUTATION_D": r"D_x = v^x l_x",
    "COMMUTATION_N": r"N_x = \sum_{y=x}^{\infty} D_y",
    "COMMUTATION_M": r"M_x = \sum_{y=x}^{\infty} v^{y+1} d_y",
    "WHOLE_LIFE_INSURANCE": r"A_x = \frac{M_x}{D_x}",
    "TERM_INSURANCE": r"A^1_{x:\overline{n}|} = \frac{M_x - M_{x+n}}{D_x}",
    "ANNUITY_DUE": r"\ddot{a}_{x:\overline{n}|} = \frac{N_x - N_{x+n}}{D_x}",
}


def repair_latex(text: str) -> str:
    s = (text or "").strip()
    if not s:
        return ""
    s = s.replace("∞", r"\infty")
    s = s.replace("∑", r"\sum").replace("Σ", r"\sum")
    s = s.replace("−", "-").replace("–", "-").replace("—", "-")
    s = s.replace("×", r" \times ").replace("·", r" \cdot ")
    s = re.sub(r"\s+", " ", s)

    canonical = detect_known_formula(s)
    if canonical:
        return canonical

    s = _repair_commutation_symbols(s)
    s = _repair_sum_bounds(s)
    s = _repair_actuarial_terms(s)
    s = _repair_simple_fractions(s)
    s = _cleanup(s)
    return s


def detect_known_formula(text: str) -> str | None:
    compact = re.sub(r"\s+", "", text).lower()
    if all(token in compact for token in ["d", "v", "l"]):
        if re.search(r"d_?x|dx", compact) and re.search(r"v\^?x", compact):
            return CANONICAL_FORMULAS["COMMUTATION_D"]
    if "m" in compact and "d" in compact and ("sum" in compact or "\\sum" in compact):
        return CANONICAL_FORMULAS["COMMUTATION_M"]
    if "n" in compact and "d_y" in compact and ("sum" in compact or "\\sum" in compact):
        return CANONICAL_FORMULAS["COMMUTATION_N"]
    if "a" in compact and "m_x" in compact and "d_x" in compact:
        return CANONICAL_FORMULAS["WHOLE_LIFE_INSURANCE"]
    if "m_x-m" in compact and "d_x" in compact:
        return CANONICAL_FORMULAS["TERM_INSURANCE"]
    return None


def _repair_commutation_symbols(s: str) -> str:
    for sym in ["D", "N", "M", "A", "P", "V", "l", "d", "q", "p"]:
        s = re.sub(rf"\b{sym}\s*_\s*([A-Za-z0-9+\-]+)", rf"{sym}_{{\1}}", s)
    s = re.sub(r"\bD\s*x\b", "D_x", s)
    s = re.sub(r"\bN\s*x\b", "N_x", s)
    s = re.sub(r"\bM\s*x\b", "M_x", s)
    s = re.sub(r"\bl\s*x\b", "l_x", s)
    return s


def _repair_sum_bounds(s: str) -> str:
    s = re.sub(
        r"\\sum\s+([A-Za-z]\s*=\s*[^\s]+)\s+(\\infty|infty|oo|00|[A-Za-z0-9+\-]+)",
        lambda m: rf"\sum_{{{m.group(1).replace(' ', '')}}}^{{{_bound(m.group(2))}}}",
        s,
    )
    return s


def _bound(value: str) -> str:
    v = value.strip()
    return r"\infty" if v in {"infty", "oo", "00"} else v


def _repair_actuarial_terms(s: str) -> str:
    s = re.sub(r"\bk\s*p\s*x\b", r"{}_{k}p_x", s)
    s = re.sub(r"q\s*x\s*\+\s*k", r"q_{x+k}", s)
    s = re.sub(r"l\s*x\s*\+\s*k\s*\+\s*1", r"l_{x+k+1}", s)
    s = re.sub(r"l\s*x\s*\+\s*k", r"l_{x+k}", s)
    s = re.sub(r"v\s*\^?\s*x\s*\+\s*k\s*\+\s*1", r"v^{x+k+1}", s)
    s = re.sub(r"v\s*\^?\s*k\s*\+\s*1", r"v^{k+1}", s)
    return s


def _repair_simple_fractions(s: str) -> str:
    s = re.sub(r"\b(M_x\s*-\s*M_\{?x\+n\}?)\s*/\s*(D_x)\b", r"\\frac{\1}{\2}", s)
    s = re.sub(r"\b(N_x\s*-\s*N_\{?x\+n\}?)\s*/\s*(D_x)\b", r"\\frac{\1}{\2}", s)
    s = re.sub(r"\b(M_x)\s*/\s*(D_x)\b", r"\\frac{\1}{\2}", s)
    return s


def _cleanup(s: str) -> str:
    s = re.sub(r"\s*=\s*", " = ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()
