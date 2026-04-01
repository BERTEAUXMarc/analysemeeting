"""Generic utility functions for date/time and storage."""
from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
import csv
import json


def parse_birth_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def compute_age_on_date(birth_date: date, when: date) -> int:
    years = when.year - birth_date.year
    if (when.month, when.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def timestamp_for_filename(now: datetime | None = None) -> str:
    now = now or datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")


def ensure_dirs(*paths: Path) -> None:
    for p in paths:
        p.mkdir(parents=True, exist_ok=True)


def save_trials_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
