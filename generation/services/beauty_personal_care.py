"""美妆 + 个人护理 / 洗护：共享动作池（通用 8 + 美妆增量）判定。"""

from __future__ import annotations

import re

# 护肤彩妆 + 洗发沐浴洁面身体乳等个护洗护（中英）
_BEAUTY_PERSONAL_CARE_KW = re.compile(
    r"("
    r"mud\s*mask|clay\s*mask|mud\s*stick|face\s*mask|acne\s*patch|pimple\s*patch|"
    r"hydrocolloid|skincare|serum|cleanser|toner|moisturizer|sunscreen|"
    r"shampoo|conditioner|hair\s*mask|hair\s*care|body\s*wash|shower\s*gel|"
    r"shower\s*cream|body\s*lotion|body\s*milk|body\s*cream|hand\s*wash|"
    r"bar\s*soap|liquid\s*soap|personal\s*care|bath\s*&\s*body|"
    r"泥膜|泥膜棒|面膜|痘痘贴|痘贴|护肤|精华|洁面|水乳|防晒|美妆|"
    r"洗发水|洗发露|洗发|护发素|护发|发膜|润发|"
    r"沐浴露|沐浴乳|沐浴|洗澡|身体乳|润肤乳|身体霜|护手霜|"
    r"洗手液|香皂|皂|洗护|个护|个人护理|头发护理"
    r")",
    re.I,
)


def text_matches_beauty_personal_care(text: str) -> bool:
    return bool(_BEAUTY_PERSONAL_CARE_KW.search(text or ""))


def plan_uses_beauty_action_pool(plan: dict) -> bool:
    """是否走美妆/个护动作库（含 L2 category、创意引擎、L3.5）。"""
    cs = plan.get("category_strategy") or {}
    if (cs.get("category_bucket") or "").strip() == "beauty_skincare":
        return True
    analysis = plan.get("product_analysis") or {}
    blob = " ".join(
        [
            str(analysis.get("category") or ""),
            str(analysis.get("product_name_en") or ""),
            str(analysis.get("primary_function") or ""),
            str(plan.get("user_prompt") or ""),
        ]
    )
    return text_matches_beauty_personal_care(blob)


# 供 _normalize_category_bucket 等模块直接匹配 category 字段
BEAUTY_PERSONAL_CARE_PATTERN = _BEAUTY_PERSONAL_CARE_KW