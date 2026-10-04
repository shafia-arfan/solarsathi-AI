"""simulation/checks.py - validates AI report text against the real numbers (anti-hallucination)."""
import re

NUM = re.compile(r"-?\d+(?:\.\d+)?")
TIME = re.compile(r"\b\d{1,2}:\d{2}\b")          # clock times like 19:00 are not measurements


def _numeric_leaves(obj):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield float(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _numeric_leaves(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _numeric_leaves(v)


def check_report(report: str, facts: dict, required_flags=(), ignore_small_ints=True):
    """Return a list of problems (empty list = report looks grounded).
    - every number in the text must match a number in `facts` (1% or 0.06 tolerance)
    - every flag in required_flags must be mentioned (e.g. 'LOW_SOC' or 'low soc')
    Limitation: whole numbers 1-24 and years are ignored (hours, counts)."""
    problems = []
    if not report or len(report.strip()) < 50:
        return ["Report is empty or too short"]
    allowed = list(_numeric_leaves(facts))
    for tok in NUM.findall(TIME.sub(" ", report)):
        x = float(tok)
        if ignore_small_ints and x.is_integer() and (1 <= abs(x) <= 24 or 2000 <= abs(x) <= 2100):
            continue
        if not any(abs(x - a) <= max(0.06, 0.01 * abs(a)) for a in allowed):
            problems.append(f"Number {tok} not found in facts")
    low = report.lower()
    for flag in required_flags:
        if flag.lower() not in low and flag.lower().replace("_", " ") not in low:
            problems.append(f"Missing warning: {flag}")
    return problems
