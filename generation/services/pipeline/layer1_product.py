"""第一层：产品理解 Agent — 识图结构化产品身份。"""

from __future__ import annotations

from generation.services.pipeline.schemas import layer_snapshot
from generation.services.planner import analyze_product_for_plan


def vision_prompt_for_job(*, job_prompt: str, plan_template: str) -> str:
    if plan_template == "reference_guided":
        return (
            f"{job_prompt}\n\n"
            "[系统提示] 参考图导演模式：请描述每张上传图（按顺序）是产品 SKU、版式/首图、模特场景、尺码表或其他，"
            "并提取产品 identity；若有多 SKU 再建立 product_variants。"
        ).strip()
    return job_prompt


def vision_prompt_multi_sku(job_prompt: str) -> str:
    return (
        f"{job_prompt}\n\n"
        "[系统提示] 这几张图是同一个商品链接下的不同款式或颜色，不是互不相关的商品。"
        "顶层字段写这一个产品的作用和卖点；product_variants 按上传顺序每张图一条，"
        "source_image_index 从 0 起，写清这一款和其它款看得见的差别。"
        "画面不是口红、鞋或内衣时，不要把品类写成那些。"
    ).strip()


def run_layer1_product_understanding(
    attachments,
    job_prompt: str,
    *,
    plan_template: str,
    vision_model: str | None = None,
    multi_reference: bool = False,
) -> tuple[dict, dict]:
    """返回 (product_analysis, layer_snapshot)。"""
    vision_prompt = vision_prompt_for_job(job_prompt=job_prompt, plan_template=plan_template)
    if multi_reference and plan_template != "reference_guided":
        vision_prompt = vision_prompt_multi_sku(job_prompt)

    analysis = {}
    if attachments:
        analysis = analyze_product_for_plan(
            attachments,
            vision_prompt,
            vision_model=vision_model,
        )
        from generation.services.product_usage_semantics import normalize_product_usage_analysis

        analysis = normalize_product_usage_analysis(analysis, job_prompt)

    summary = {
        "has_analysis": bool(analysis),
        "product_name_en": (analysis.get("product_name_en") or "")[:120],
        "category": (analysis.get("category") or "")[:80],
        "variant_count": len(analysis.get("product_variants") or []),
        "has_identity_lock": bool(analysis.get("identity_lock_en")),
        "pain_points": len(analysis.get("pain_points") or []),
        "key_selling_points": len(analysis.get("key_selling_points") or []),
    }
    return analysis, layer_snapshot("L1_product_understanding", summary=summary)
