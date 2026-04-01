"""Configuration helpers for the cognitive reaction test application."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json

PROTOCOL_VERSION = "1.0.0"
APP_TITLE = "Test de réactions complexes"

DEFAULT_CONFIG_PATH = Path("hardware_config.json")
DEFAULT_RESULTS_DIR = Path("results")
DEFAULT_REPORTS_DIR = Path("reports")


@dataclass
class InputBinding:
    mode: str = "button"  # button|axis|keyboard
    joystick_id: int | None = None
    control: int | None = None  # button index or axis index
    threshold: float = 0.5
    keyboard_key: str | None = None


@dataclass
class HardwareConfig:
    manette_gauche: InputBinding
    manette_droite: InputBinding
    pedale_gauche: InputBinding
    pedale_droite: InputBinding
    debug_keyboard_mode: bool = True
    neutral_interval_seconds: float = 0.0


def default_config() -> HardwareConfig:
    return HardwareConfig(
        manette_gauche=InputBinding(mode="keyboard", keyboard_key="a"),
        manette_droite=InputBinding(mode="keyboard", keyboard_key="l"),
        pedale_gauche=InputBinding(mode="keyboard", keyboard_key="q"),
        pedale_droite=InputBinding(mode="keyboard", keyboard_key="p"),
        debug_keyboard_mode=True,
        neutral_interval_seconds=0.0,
    )


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> HardwareConfig:
    if not path.exists():
        cfg = default_config()
        save_config(cfg, path)
        return cfg
    payload = json.loads(path.read_text(encoding="utf-8"))

    def read_binding(name: str) -> InputBinding:
        return InputBinding(**payload[name])

    return HardwareConfig(
        manette_gauche=read_binding("manette_gauche"),
        manette_droite=read_binding("manette_droite"),
        pedale_gauche=read_binding("pedale_gauche"),
        pedale_droite=read_binding("pedale_droite"),
        debug_keyboard_mode=payload.get("debug_keyboard_mode", True),
        neutral_interval_seconds=payload.get("neutral_interval_seconds", 0.0),
    )


def save_config(cfg: HardwareConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    data = asdict(cfg)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
