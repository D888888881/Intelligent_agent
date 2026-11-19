"""第三层：图片身份规划 Agent — 每镜职能 / 卖点 / 基础构图（冻结 role）。"""

from __future__ import annotations

from generation.services.pipeline.schemas import layer_snapshot
from generation.services.planner import build_plan


def _identity_roster(plan: dict) -> list[dict]:
    roster = []
    for shot in plan.get("shots") or []:
        roster.append(
            {
                "index": int(shot.get("index") or 0),
                "role": shot.get("role") or "",
                "frame_contract": shot.get("frame_contract") or "",
                "marketing_pillar": shot.get("marketing_pillar") or "",
                "visual_archetype": (shot.get("visual_archetype") or "")[:80],
            }
        )
    return sorted(roster, key=lambda x: x["index"])


def run_layer3_identity_planning(
    *,
    user_prompt: str,
    image_count: int,
    plan_template: str,
    product_analysis: dict,
    marketing_strategy: dict,
    reference_attachment_count: int = 0,
) -> tuple[dict, dict]:
    plan = build_plan(
        user_prompt,
        image_count,
        plan_template=plan_template,
        product_analysis=product_analysis,
        reference_attachment_count=reference_attachment_count,
        marketing_strategy=marketing_strategy,
        listing_finalize_stage="identity",
    )
    summary = {
        "plan_template": plan.get("plan_template"),
        "image_count": plan.get("image_count") or len(plan.get("shots") or []),
        "identity_roster": _identity_roster(plan),
    }
    return plan, layer_snapshot("L3_identity_planning", summary=summary)
