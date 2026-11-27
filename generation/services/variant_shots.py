"""多色号 / 多 SKU：为套图镜头分配主推变体。"""

from __future__ import annotations


def variants_catalog_text(variants: list) -> str:
    lines: list[str] = []
    for i, v in enumerate(variants):
        if not isinstance(v, dict):
            continue
        label = (v.get("variant_label") or v.get("colorway_en") or f"Variant {i + 1}").strip()
        style = (v.get("style_en") or "").strip()
        size = (v.get("size_or_fit_en") or "").strip()
        lock = (v.get("identity_lock_en") or v.get("visual_identity") or "").strip()[:400]
        pos = (v.get("in_frame_position") or "").strip()
        src = v.get("source_image_index")
        chunk = f"{i + 1}) {label}"
        if style:
            chunk += f", style={style}"
        if size:
            chunk += f", size={size}"
        if src is not None:
            chunk += f" [ref image index {src}]"
        if pos:
            chunk += f" [in reference photo: {pos}]"
        if lock:
            chunk += f" — {lock}"
        lines.append(chunk)
    return " | ".join(lines)[:3500]


def _pick_showcase_shot(shots: list) -> dict | None:
    if not shots:
        return None
    preferred = {2, 8, 9, 7}
    for shot in shots:
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        if idx in preferred:
            return shot
    return shots[min(1, len(shots) - 1)]


def sync_product_variants_from_references(plan: dict, attachment_count: int) -> dict:
    """用户上传 N 张参考图但分析只识别出更少 SKU 时，按上传数量补齐 variants。"""
    if attachment_count <= 1:
        return plan
    analysis = plan.setdefault("product_analysis", {})
    variants = analysis.get("product_variants")
    if not isinstance(variants, list):
        variants = []
    if len(variants) >= attachment_count:
        for i, v in enumerate(variants[:attachment_count]):
            if isinstance(v, dict) and v.get("source_image_index") is None:
                v["source_image_index"] = i
        analysis["product_variants"] = variants
        return plan
    while len(variants) < attachment_count:
        i = len(variants)
        variants.append(
            {
                "variant_label": f"Variant {i + 1}",
                "source_image_index": i,
                "style_en": f"SKU or colorway from reference image {i + 1}",
                "identity_lock_en": f"Match reference image index {i} packaging, color, and shape exactly.",
            }
        )
    analysis["product_variants"] = variants
    return plan


def white_bg_variant_lineup_en(count: int) -> str:
    """同一链接的多个款式：白底图是一张照片里的整排，不是只留一个主商品。"""
    n = max(2, int(count or 2))
    return (
        f"Pure #FFFFFF seamless studio catalog photograph of ALL {n} style variants "
        "of this ONE product, one unit of each, standing UPRIGHT in a single row. "
        "Each unit copies one attached reference: packaging, color, cap, and shape. "
        "Do not drop a variant, do not clone one style to fill the row, and do not invent an extra style. "
        "Front view, eye-level, even softbox light, soft contact shadow. "
        "No props, no people, no lifestyle background, no marketing text, no icons. "
        "One photograph of the row. Not a panel collage, not a nine-grid, not a single centered SKU."
    )


def apply_white_bg_all_references(plan: dict, attachment_count: int) -> dict:
    """白底 catalog 镜头需展示全部款式时，上传全部参考图（受 showcase 上限约束）。"""
    if attachment_count <= 1:
        return plan
    shots = plan.get("shots") or []
    catalog = (plan.get("variants_catalog_en") or "").strip()
    if not catalog:
        variants = (plan.get("product_analysis") or {}).get("product_variants") or []
        if isinstance(variants, list) and variants:
            catalog = variants_catalog_text(variants)
            plan["variants_catalog_en"] = catalog
    lineup = white_bg_variant_lineup_en(attachment_count)
    for shot in shots:
        role = (shot.get("role") or "").strip()
        try:
            idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            idx = 0
        if role != "white_bg_catalog" and idx != 2:
            continue
        shot["role"] = "white_bg_catalog"
        shot["use_all_reference_images"] = True
        shot["variant_label"] = "All colorways / styles lineup"
        shot.pop("featured_variant_index", None)
        shot.pop("variant_identity_extra", None)
        if catalog:
            shot["multi_variant_catalog_en"] = catalog
        shot["prompt_en"] = lineup
        shot["product_pose_lock_en"] = (
            "INDEX 2 — Every uploaded style stands upright on pure white, in one row. "
            "Not one centered SKU."
        )
        shot["orientation_lock"] = (
            "Each variant faces the camera upright, 0° tilt, arranged left to right in one row."
        )
        shot["scene_zh"] = "纯白底，同一产品的全部款式并排"
        shot["composition_zh"] = f"白底上一字排开 {attachment_count} 个不同款式，无文案"
        mandate = (shot.get("composition_mandate") or "").strip()
        extra = (
            f"WHITE BG MULTI-SKU: include all {attachment_count} distinct product variants "
            f"from the {attachment_count} reference images in one clean catalog row. "
            "Each SKU is a different style. No missing variant, no cloned duplicate, no panel collage."
        )
        if "WHITE BG MULTI-SKU" not in mandate:
            shot["composition_mandate"] = f"{mandate} {extra}".strip() if mandate else extra
    plan["multi_variant_listing"] = True
    plan["variant_count"] = max(int(plan.get("variant_count") or 0), attachment_count)
    plan["variant_family_lock_en"] = (
        f"These {attachment_count} uploads are style variants of ONE product on ONE listing. "
        "They are not unrelated products. The white catalog frame shows every style together. "
        "Each other frame features one of those styles and keeps the same product type."
    )
    return plan


def apply_multi_reference_listing_rules(plan: dict, attachment_count: int) -> dict:
    plan = sync_product_variants_from_references(plan, attachment_count)
    plan = assign_shot_variants(plan)
    plan = apply_white_bg_all_references(plan, attachment_count)
    if attachment_count > 1:
        plan["reference_image_count"] = attachment_count
    return plan


def assign_shot_variants(plan: dict) -> dict:
    analysis = plan.get("product_analysis") or {}
    variants = analysis.get("product_variants") or []
    if not isinstance(variants, list) or len(variants) <= 1:
        return plan

    shots = plan.get("shots") or []
    n = len(variants)
    catalog = variants_catalog_text(variants)
    plan["variants_catalog_en"] = catalog

    showcase = _pick_showcase_shot(shots)

    for i, shot in enumerate(shots):
        if showcase is not None and shot is showcase:
            continue
        v = variants[i % n]
        if not isinstance(v, dict):
            continue
        shot["variant_index"] = i % n
        try:
            shot["featured_variant_index"] = int(v.get("source_image_index", i % n))
        except (TypeError, ValueError):
            shot["featured_variant_index"] = i % n
        label = (v.get("variant_label") or v.get("colorway_en") or v.get("style_en") or "").strip()
        if label:
            shot["variant_label"] = label
        style = (v.get("style_en") or "").strip()
        if style and style not in label:
            shot["variant_style_en"] = style
        size = (v.get("size_or_fit_en") or "").strip()
        if size:
            shot["variant_size_en"] = size
        lock = (v.get("identity_lock_en") or "").strip()
        if lock:
            shot["variant_identity_extra"] = lock[:700]
        pos = (v.get("in_frame_position") or "").strip()
        if pos:
            shot["variant_in_frame_position"] = pos[:200]

    if showcase is not None:
        try:
            showcase_idx = int(showcase.get("index") or 0)
        except (TypeError, ValueError):
            showcase_idx = 0
        if showcase_idx != 2 and (showcase.get("role") or "") != "white_bg_catalog":
            showcase["role"] = "multi_variant_showcase"
        showcase["use_all_reference_images"] = True
        showcase["variant_label"] = "All colorways / styles lineup"
        showcase["multi_variant_catalog_en"] = catalog
        showcase.pop("variant_identity_extra", None)
        showcase.pop("featured_variant_index", None)

    plan["multi_variant_listing"] = True
    plan["variant_count"] = n
    return plan
