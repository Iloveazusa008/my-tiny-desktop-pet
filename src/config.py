from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    anim = cfg.setdefault("animation", {})
    for key, value in list(anim.items()):
        if not value:  # talk/error 等素材未提供时留空，跳过
            continue
        if isinstance(value, list):  # idle_random 等列表型路径
            anim[key] = [str(ROOT / v) if not Path(v).is_absolute() else v for v in value]
            continue
        p = Path(value)
        if not p.is_absolute():
            anim[key] = str(ROOT / p)
    return cfg
