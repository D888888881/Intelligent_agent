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
        showcase["role"] = "multi_variant_showcase"
        showcase["use_all_reference_images"] = True
        showcase["variant_label"] = "All colorways / styles lineup"
        showcase["multi_variant_catalog_en"] = catalog
        showcase.pop("variant_identity_extra", None)
        showcase.pop("featured_variant_index", None)

    plan["multi_variant_listing"] = True
    plan["variant_count"] = n
    return plan
