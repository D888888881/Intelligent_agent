"""按 Grsai 生图模型（Banana / GPT Image）调整参考图策略与构图 prompt。"""

from __future__ import annotations

from generation.services.camera_diversity import apply_camera_diversity

BANANA_STRICT_NEGATIVE = (
    "redesigned packaging, different label artwork, wrong bottle color, wrong cap color, "
    "altered brand graphics, simplified label, generic mockup, different SKU, color shift"
)

GPT_IMAGE_NEGATIVE_EXTRA = (
    "tiny product, product lost in background, same angle as other photos, duplicate composition, "
    "identical camera position, flat layout, product smaller than 40 percent of frame"
)

# 历史：曾仅白底带参考；GPT Image 在无图时会以 violation 拒答「请上传参考图」，有参考时应全镜头带图。
GPT_REF_ROLES = frozenset({"white_bg_catalog"})

def model_family(model_id: str | None) -> str:
    m = (model_id or "").lower()
    if m.startswith("gpt-image"):
        return "gpt_image"
    if "banana" in m or m.startswith("nano-"):
        return "banana"
    return "other"


def tune_plan_for_image_model(
    plan: dict,
    image_model: str | None,
    *,
    has_reference: bool = False,
) -> dict:
    """根据模型改写 reference 策略与镜头构图约束。"""
    family = model_family(image_model)
    plan["image_model_family"] = family
    plan["reference_attachment_present"] = bool(has_reference or plan.get("reference_attachment_present"))
    shots = plan.get("shots") or []

    if family == "banana":
        plan["reference_policy"] = "banana_strict_all"
        plan["default_reference_mode"] = "identity"
        neg = (plan.get("negative_prompt") or "").strip()
        plan["negative_prompt"] = f"{neg}, {BANANA_STRICT_NEGATIVE}".strip(", ")
        for shot in shots:
            shot["reference_mode"] = "identity"
            shot.setdefault(
                "negative_extra",
                "wrong packaging print, bottle color mismatch, label redesign",
            )
        plan = apply_camera_diversity(plan)
        shots = plan.get("shots") or []
    elif family == "gpt_image":
        if has_reference:
            plan["reference_policy"] = "gpt_all_with_ref"
            plan["default_reference_mode"] = "identity"
        else:
            plan["reference_policy"] = "gpt_text_only"
            plan["default_reference_mode"] = "none"
        neg = (plan.get("negative_prompt") or "").strip()
        plan["negative_prompt"] = f"{neg}, {GPT_IMAGE_NEGATIVE_EXTRA}".strip(", ")
        for shot in shots:
            role = shot.get("role") or ""
            if has_reference:
                shot["reference_mode"] = "identity"
            elif role in GPT_REF_ROLES:
                shot["reference_mode"] = "identity"
            else:
                shot["reference_mode"] = "none"
            shot.setdefault(
                "prompt_en",
                (shot.get("prompt_en") or "")
                + " Product must be the clear visual hero with professional e-commerce layout; "
                "rotate the product to the mandated orientation — never clone the reference photo pose.",
            )
        plan = apply_camera_diversity(plan)
        shots = plan.get("shots") or []
    else:
        plan.setdefault("reference_policy", "default")

    plan["shots"] = shots
    return plan


def reference_prefix_for_model(
    model_id: str | None,
    *,
    has_reference: bool,
    purpose: str = "generation",
) -> str:
    if not has_reference:
        return ""
    family = model_family(model_id)
    if purpose == "slot_refine":
        if family == "banana":
            return (
                "BANANA IN-PLACE RETOUCH — Image 2 is the full listing frame (BASE CANVAS). Image 1 is SKU packshot for "
                "packaging, label, logo, and colors only — never replace the scene with image 1's studio pose. "
                "Edit image 2 in place; keep its camera, layout, lighting, and on-image text unless the edit request says otherwise. "
                "Do not redesign the product graphics. Apply only the edit request below. "
                "If the edit fixes wrong product in the scene, swap that item to match image 1 SKU while keeping image 2 people and layout. "
            )
        if family == "gpt_image":
            return (
                "SLOT RETOUCH — images[0]=SKU product photo; images[1]=current listing frame (BASE CANVAS). "
                "Retouch the listing frame (image index 1) in place per the edit request. "
                "Preserve that frame's scene, camera, layout, and marketing copy unless the edit request explicitly changes them. "
                "Match packaging and colors to image index 0. "
                "Generate one photorealistic listing image now; do not respond with text-only refusals. "
                "If the edit request changes object size or fixes product mismatch, the output must visibly differ from the input frame — not a duplicate. "
                "For product correction edits, render the SKU from image index 0 inside the lifestyle frame of image index 1. "
            )
        return (
            "Slot retouch: reference 1 = product identity, reference 2 = frame to edit; "
            "keep composition unless edit says otherwise. "
        )
    if family == "banana":
        return (
            "BANANA / SKU LOCK — Reference is ONLY for packaging graphics, label text, logo, and exact colors "
            "(hue, cap color, print pattern). DO NOT copy the reference photo's camera angle, crop, or product rotation. "
            "You MUST rotate the product to the MANDATORY PRODUCT ORIENTATION in this prompt. "
            "FORBIDDEN: redesigning label art, wrong bottle color, or cloning reference pose. "
            "Change background, lighting, camera position, and props as directed below. "
            "When humans or hands appear, follow HUMAN CAST in the prompt — unique face/skin per frame; "
            "include fair, olive, and brown skin tones across the set; never reuse the same model identity. "
        )
    if family == "gpt_image":
        return (
            "IMAGE GENERATION TASK — Reference image is attached (images field). Generate ONE 1024×1024 image now. "
            "Do not respond with text asking the user to upload photos — output the image directly. "
            "Match packaging, logo, label wording, and colors from reference — but NEVER copy reference angle or orientation. "
            "Rotate product to the MANDATORY PRODUCT ORIENTATION below; each listing frame uses a different facing direction. "
            "When humans or hands appear, follow HUMAN CAST — distinct photorealistic models per frame; "
            "use reference for SKU only, not for copying faces or poses from the reference photo. "
            "vary skin tone (light/fair, medium olive, brown); do not default to one repeated East-Asian-looking face. "
        )
    return (
        "Use reference ONLY for product identity (shape, label, colors). "
        "New scene and camera as described. "
    )
