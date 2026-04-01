"""Scoring and statistics functions."""
from __future__ import annotations

from statistics import mean, median, pstdev


def classify_trial(expected: str, response: str | None, rt_ms: float | None) -> str:
    if response is None:
        return "omission"
    if response == expected:
        return "correct"
    return "erreur"


def trial_error_rate_percent(rows: list[dict]) -> float:
    if not rows:
        return 100.0
    err_like = sum(1 for r in rows if r["status"] in ("erreur", "omission"))
    return (err_like / len(rows)) * 100.0


def compute_metrics(rows: list[dict]) -> dict:
    total = len(rows)
    br = sum(1 for r in rows if r["status"] == "correct")
    er = sum(1 for r in rows if r["status"] == "erreur")
    om = sum(1 for r in rows if r["status"] == "omission")
    perf = (br / total * 100.0) if total else 0.0
    rts = [r["reaction_time_ms"] for r in rows if r["reaction_time_ms"] is not None and r["status"] == "correct"]
    return {
        "nb_signaux": total,
        "performance_pct": perf,
        "br": br,
        "er": er,
        "om": om,
        "mean_ms": mean(rts) if rts else None,
        "median_ms": median(rts) if rts else None,
        "std_ms": pstdev(rts) if len(rts) > 1 else 0.0 if len(rts) == 1 else None,
    }


def compute_by_rhythm(rows: list[dict]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    out["global"] = compute_metrics(rows)
    for rhythm in ("lent", "modere", "rapide"):
        out[rhythm] = compute_metrics([r for r in rows if r.get("rhythm") == rhythm])
    return out
