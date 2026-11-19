"""生图输出比例：默认 1:1，用户可选预设。"""

from __future__ import annotations

DEFAULT_ASPECT_RATIO = "1:1"

# id 与 Grsai 一致：GPT 系在 grsai._aspect_for_gpt 映射像素；Banana 系传比例 + imageSize
ASPECT_RATIO_OPTIONS: list[dict[str, str]] = [
    {"id": "1:1", "label_zh": "1:1 方图（默认）"},
    {"id": "3:4", "label_zh": "3:4 竖图"},
    {"id": "4:3", "label_zh": "4:3 横图"},
    {"id": "9:16", "label_zh": "9:16 竖屏"},
    {"id": "16:9", "label_zh": "16:9 横屏"},
    {"id": "2:3", "label_zh": "2:3 竖图"},
    {"id": "3:2", "label_zh": "3:2 横图"},
]

_ALLOWED_IDS = frozenset(o["id"] for o in ASPECT_RATIO_OPTIONS)


def aspect_ratio_catalog() -> list[dict[str, str]]:
    return [dict(o) for o in ASPECT_RATIO_OPTIONS]


def aspect_ratio_label_zh(aspect_id: str) -> str:
    aid = (aspect_id or DEFAULT_ASPECT_RATIO).strip()
    for o in ASPECT_RATIO_OPTIONS:
        if o["id"] == aid:
            return o["label_zh"]
    return aid


def resolve_aspect_ratio(value: str | None) -> str:
    """非法值回退默认 1:1。"""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    aid = (value or "").strip() if isinstance(value, str) else str(value or "").strip()
    if aid in _ALLOWED_IDS:
        return aid
    return DEFAULT_ASPECT_RATIO


def merge_user_aspect_into_plan(plan: dict, job_plan_json: dict | None) -> dict:
    """策划完成后写入用户选择的比例（覆盖模板内默认 1:1）。"""
    src = job_plan_json or {}
    ar = resolve_aspect_ratio(src.get("aspect_ratio"))
    plan["aspect_ratio"] = ar
    plan["aspect_ratio_label_zh"] = aspect_ratio_label_zh(ar)
    return plan


def is_square_aspect(aspect_ratio: str) -> bool:
    ar = resolve_aspect_ratio(aspect_ratio)
    if ar == "1:1":
        return True
    if "x" in ar.lower():
        parts = ar.lower().split("x", 1)
        if len(parts) == 2 and parts[0] == parts[1]:
            return True
    return False