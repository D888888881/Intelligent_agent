"""成图内文字语言约束：默认禁止中文（营销文案/贴纸等）。"""

from __future__ import annotations

# 并入各计划 negative_prompt / Avoid 段
DEFAULT_NO_CHINESE_NEGATIVE = (
    "Chinese text, Chinese characters, hanzi, 汉字, 中文, CJK captions, random Asian glyphs, "
    "bilingual Chinese-Spanish ad copy, Chinese watermarks, Chinese subtitles"
)

ON_IMAGE_TEXT_MANDATE_ES_MX = (
    "ON-IMAGE TEXT POLICY — CRITICAL: Do NOT render Chinese (中文/汉字) anywhere. "
    "Index 2 (white catalog) and Index 4 (before/after visual): ZERO added marketing text. "
    "All other TK frames (1,3,5,6,7,8,9): a LARGE Spanish (México) text panel for ONE benefit — "
    "bold headline, a two-line introduction, and three proof lines about that same benefit. "
    "The panel covers about one third of the image. The photo fills the rest. Do not leave an empty card. "
    "Do not repeat another frame's wording and do not print Step 1 / Step 2. "
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
