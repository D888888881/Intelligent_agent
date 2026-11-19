"""第四层：套图创意 Agent — 批次视觉概念、flex 变体、机位、USP 文案（不改 role）。"""

from __future__ import annotations

from generation.services.pipeline.schemas import layer_snapshot
from generation.services.talent_diversity import apply_talent_diversity, resolve_talent_rotation_index


def _creative_summary(plan: dict) -> dict:
    return {
        "creative_concept_id": plan.get("creative_concept_id"),
        "creative_concept_label_zh": plan.get("creative_concept_label_zh"),
        "creative_dimension_matrix": plan.get("creative_dimension_matrix"),
        "creative_history_count": len(plan.get("creative_history") or []),
        "visual_batch_index": plan.get("visual_batch_index"),
        "visual_batch_pack_name": plan.get("visual_batch_pack_name"),
        "frame3_variant_id": plan.get("frame3_variant_id"),
        "frame4_variant_id": plan.get("frame4_variant_id"),
        "frame5_variant_id": plan.get("frame5_variant_id"),
        "frame9_variant_id": plan.get("frame9_variant_id"),
        "listing_story_theme_en": (plan.get("listing_story_theme_en") or "")[:120],
        "camera_batch_preset_id": plan.get("camera_batch_preset_id"),
        "human_presence_summary": plan.get("human_presence_summary"),
        "action_plugin": (plan.get("action_planning") or {}).get("plugin"),
        "action_ids": [
            s.get("primary_action_id")
            for s in (plan.get("shots") or [])
            if s.get("primary_action_id")
        ],
    }


def run_layer4_bundle_creative(plan: dict, *, job) -> tuple[dict, dict]:
    from generation.services.job_references import job_attachments
    from generation.services.variant_shots import apply_multi_reference_listing_rules
    from generation.services.detail_shot_diversity import apply_detail_shot_diversity
    from generation.services.tk_mx_listing import apply_tk_mx_listing_plan
    from generation.services.camera_diversity import apply_camera_diversity
    from generation.services.listing_usp_distribution import apply_listing_usp_distribution

    roles_before = {
        int(s.get("index") or 0): (s.get("role") or "")
        for s in plan.get("shots") or []
    }

    from generation.services.creative_engine import apply_creative_engine, finalize_creative_set_record

    plan = apply_creative_engine(plan, job=job)
    plan = apply_multi_reference_listing_rules(plan, len(job_attachments(job)))
    plan = apply_detail_shot_diversity(plan, job=job)
    batch_idx = int(plan.get("visual_batch_index") or 0)
    conv_rot = resolve_talent_rotation_index(job)
    talent_rot = (batch_idx + conv_rot) % max(1, 12)
    plan = apply_talent_diversity(plan, rotation_index=talent_rot)
    plan = apply_tk_mx_listing_plan(plan)
    plan = apply_camera_diversity(plan, merge=True)
    plan = apply_listing_usp_distribution(plan)
    plan = finalize_creative_set_record(plan)

    roles_after = {
        int(s.get("index") or 0): (s.get("role") or "")
        for s in plan.get("shots") or []
    }
    identity_preserved = roles_before == roles_after

    summary = _creative_summary(plan)
    summary["identity_roles_preserved"] = identity_preserved
    return plan, layer_snapshot(
        "L4_bundle_creative",
        status="ok" if identity_preserved else "warn",
        summary=summary,
    )
