"""套图 index ↔ role 强制对齐，防止策划 JSON 漂移导致图4不是前后对比镜。"""

from __future__ import annotations

from generation.services.ecommerce_strategy import TK_MX_NINE_FRAME_MATRIX

_TK_BY_INDEX = {int(f["index"]): f for f in TK_MX_NINE_FRAME_MATRIX}


def enforce_tk_mx_shot_roles(plan: dict) -> dict:
    if (plan.get("plan_template") or "") != "tk_mx_ecommerce_9":
        return plan
    for shot in plan.get("shots") or []:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        frame = _TK_BY_INDEX.get(idx)
        if not frame:
            continue
        shot["role"] = frame["role"]
        if frame.get("frame_contract"):
            shot["frame_contract"] = frame["frame_contract"]
        shot.setdefault("marketing_pillar", frame.get("marketing_pillar"))
        shot.setdefault("consumer_question", frame.get("consumer_question"))
        shot.setdefault("visual_archetype", frame.get("visual_archetype"))
        shot.setdefault("scene_family", frame.get("scene_family"))
    plan["shots"] = plan.get("shots") or []
    return plan