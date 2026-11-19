"""成图内文字语言约束：默认禁止中文（营销文案/贴纸等）。"""

from __future__ import annotations

# 并入各计划 negative_prompt / Avoid 段
DEFAULT_NO_CHINESE_NEGATIVE = (
    "Chinese text, Chinese characters, hanzi, 汉字, 中文, CJK captions, random Asian glyphs, "
    "bilingual Chinese-Spanish ad copy, Chinese watermarks, Chinese subtitles"
)

ON_IMAGE_TEXT_MANDATE_ES_MX = (
    "ON-IMAGE TEXT POLICY — CRITICAL: Do NOT render Chinese (中文/汉字) anywhere. "
    "Marketing typography must be Spanish (México), SHORT and high-contrast — each frame needs "
    "a focal message (not pure visual-only art). Hero: up to 2 headline lines + 3 icon bullets; "
    "other frames: 1–3 short callouts (2–6 words) OR compact spec/step tags. "
    "Reproduce packaging label text EXACTLY from reference only. No English marketing unless user asked."
)

ON_IMAGE_TEXT_MANDATE_DEFAULT = (
    "ON-IMAGE TEXT POLICY — CRITICAL: Do NOT render Chinese (中文/汉字) in the output. "
    "Do not add Chinese headlines, stickers, UI, or captions. "
    "Reproduce reference packaging label wording only when it is part of the SKU; "
    "do not add new non-label text in Chinese."
)


def merge_image_text_negative(existing: str | None) -> str:
    base = (existing or "").strip()
    if not base:
        return DEFAULT_NO_CHINESE_NEGATIVE
    low = base.lower()
    if "chinese text" in low or "chinese characters" in low:
        return base
    return f"{base}, {DEFAULT_NO_CHINESE_NEGATIVE}".strip(", ")


def _coerce_str(val) -> str:
    if val is None:
        return ""
    if isinstance(val, (list, tuple)):
        return " ".join(str(x).strip() for x in val if x is not None and str(x).strip())
    return str(val).strip()


def on_image_text_mandate_for_plan(plan: dict) -> str:
    custom = _coerce_str(plan.get("on_image_text_mandate_en"))
    if custom:
        return custom
    locale = (plan.get("locale") or "").strip().lower()
    if locale in ("es-mx", "es_mx", "es-mx-listing"):
        return ON_IMAGE_TEXT_MANDATE_ES_MX
    from generation.services.listing_bundle import is_listing_ecommerce_plan

    if is_listing_ecommerce_plan(plan):
        return ON_IMAGE_TEXT_MANDATE_ES_MX
    return ON_IMAGE_TEXT_MANDATE_DEFAULT
