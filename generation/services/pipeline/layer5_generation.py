"""第五层：图片生成准备 — 模型策略、分镜规范化、生图 manifest。"""

from __future__ import annotations

from Intelligent_agent.model_catalog import resolve_image_model
from generation.services.model_strategy import tune_plan_for_image_model
from generation.services.pipeline.schemas import layer_snapshot
from generation.services.prompt_builder import build_shot_generation_prompt
from generation.services.shot_plan import normalize_shot_list
from generation.services.visual_batch_variance import resolve_visual_batch_index


def run_layer5_generation_prepare(
    plan: dict,
    *,
    job,
    product_analysis: dict | None,
    selected_image_model: str | None,
    attachments,
    user_prompt: str,
    image_count: int,
) -> tuple[dict, int, dict]:
    plan["user_prompt"] = user_prompt
    plan["visual_batch_index"] = resolve_visual_batch_index(job, product_analysis=product_analysis)
    model = resolve_image_model(selected_image_model or plan.get("image_model"))
    plan["image_model"] = model
    plan = tune_plan_for_image_model(
        plan,
        model,
        has_reference=bool(attachments),
    )
    shots = normalize_shot_list(plan.get("shots") or [], image_count, user_prompt)
    plan["shots"] = shots
    if shots:
        image_count = len(shots)

    manifest = []
    for shot in shots:
        idx = int(shot.get("index") or 0)
        final_prompt = build_shot_generation_prompt(shot, plan, attach_reference=True)
        manifest.append(
            {
                "index": idx,
                "role": shot.get("role") or "",
                "reference_mode": shot.get("reference_mode") or plan.get("default_reference_mode"),
                "prompt_chars": len(final_prompt or ""),
            }
        )

    summary = {
        "image_model": model,
        "shot_count": len(shots),
        "generation_manifest": manifest,
        "awaiting_generation_confirm": bool(plan.get("awaiting_generation_confirm")),
    }
    return (
        plan,
        image_count,
        layer_snapshot("L5_generation_prepare", summary=summary),
    )
