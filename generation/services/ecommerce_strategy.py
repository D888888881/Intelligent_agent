"""电商主图策略：卖点 / 痛点 / 购买动机 → 9 张差异化视觉矩阵。"""

import json

from django.conf import settings

# 9 张图固定「营销职能」，避免只做角度微调
TK_MX_NINE_FRAME_MATRIX = [
    {
        "index": 1,
        "role": "hero_hook",
        "frame_contract": "fixed",
        "marketing_pillar": "购买动机",
        "consumer_question": "3 秒内抓住注意力：这对我有什么用？",
        "visual_archetype": "scroll_stopper_hero",
        "scene_family": "studio_hero",
    },
    {
        "index": 2,
        "role": "white_bg_catalog",
        "frame_contract": "fixed",
        "marketing_pillar": "平台合规",
        "consumer_question": "看清商品本体、规格与包装",
        "visual_archetype": "catalog_white_seamless",
        "scene_family": "pure_white",
    },
    {
        "index": 3,
        "role": "pain_empathy",
        "frame_contract": "creative_detail",
        "marketing_pillar": "痛点共鸣",
        "consumer_question": "使用前的困扰/问题状态是什么？（before 侧素材）",
        "visual_archetype": "before_use_problem_state",
        "scene_family": "relatable_home",
    },
    {
        "index": 4,
        "role": "usp_primary",
        "frame_contract": "fixed",
        "marketing_pillar": "核心卖点",
        "consumer_question": "使用前后对比：改善有多明显？",
        "visual_archetype": "before_after_transformation",
        "scene_family": "comparison_studio_single_frame",
    },
    {
        "index": 5,
        "role": "usp_secondary",
        "frame_contract": "fixed",
        "marketing_pillar": "次要卖点",
        "consumer_question": "比同类型普通产品好在哪里？",
        "visual_archetype": "same_category_product_comparison",
        "scene_family": "side_by_side_vs_generic",
    },
    {
        "index": 6,
        "role": "trust_quality",
        "frame_contract": "creative_detail",
        "marketing_pillar": "信任背书",
        "consumer_question": "质量/成分/工艺是否可靠？",
        "visual_archetype": "quality_proof_macro",
        "scene_family": "clinical_detail",
    },
    {
        "index": 7,
        "role": "ease_objection",
        "frame_contract": "creative_detail",
        "marketing_pillar": "消除顾虑",
        "consumer_question": "是否难用、耗时、不适合我？",
        "visual_archetype": "simple_steps_in_use",
        "scene_family": "hands_on_demo",
    },
    {
        "index": 8,
        "role": "value_stack",
        "frame_contract": "creative_detail",
        "marketing_pillar": "性价比/套装",
        "consumer_question": "买到什么、是否划算？",
        "visual_archetype": "bundle_flatlay_value",
        "scene_family": "topdown_kit",
    },
    {
        "index": 9,
        "role": "lifestyle_payoff",
        "frame_contract": "creative_detail",
        "marketing_pillar": "成交愿景",
        "consumer_question": "用完后的理想状态/身份认同",
        "visual_archetype": "aspirational_outcome",
        "scene_family": "lifestyle_mx_outdoor_or_vanity",
    },
]


def build_marketing_strategy(product_analysis: dict, user_prompt: str) -> dict:
    """基于商品分析 + 用户需求，生成 9 帧营销策略（优先 LLM）。"""
    from chat.services.openai_client import is_chat_configured, get_openai_client

    base = _strategy_fallback(product_analysis, user_prompt)
    if product_analysis.get("pain_points"):
        base["pain_points"] = product_analysis["pain_points"]
    if product_analysis.get("purchase_motivations"):
        base["purchase_motivations"] = product_analysis["purchase_motivations"]
    if not is_chat_configured():
        return base

    matrix_json = json.dumps(TK_MX_NINE_FRAME_MATRIX, ensure_ascii=False)
    system = (
        "你是 TikTok Shop 墨西哥站「电商主图分析大师」：先解剖商品再策划视觉。"
        "输出单个 JSON，无 markdown。"
        "顶层字段：product_summary_zh, target_buyer_zh, purchase_motivations[], pain_points[], "
        "core_usps[], objections[], trust_signals[], mexico_angle_zh, conversion_story_zh。"
        "shot_briefs：长度必须 9，与 matrix 的 index/role 一一对应；每项含 "
        "index, role, marketing_pillar, consumer_question, visual_archetype, scene_family, "
        "key_message_es（西语 3-8 词）, creative_direction_en（80+ 词，描述独特画面，禁止与其他帧同类）, "
        "diversity_lock（说明本帧与另外 8 帧在视觉叙事与机位上的差异）。"
        "creative_direction_en 必须包含明确的 product facing / camera angle（互不相同）。"
        "必须消费 product_analysis 中的 before_use_state、after_use_state、before_after_visual_en、same_category_comparison、"
        "key_ingredients/key_selling_points/visual_identity："
        "index 3 聚焦使用前问题态（可环境静物，不必正脸）；index 4 为单张图的使用前后对比（非多宫格，优先无大正脸）；"
        "index 5 为本品 vs 同品类无品牌/generic 替代品并排对比（禁止真实竞品商标）；"
        "index 6 必须描述可拍摄的材质/成分/工艺微观证据；index 8 套装/value 故事，避免与 index 2 雷同白底正面。"
        "人物：全组最多 2–3 帧出现人（含手），禁止每套 5 张都出人；index 2/5/6 无人。"
        "要求：9 帧不得都是正面同视角或同一 bathroom flatlay；必须覆盖动机/痛点/前后对比/品类对比/信任/顾虑/套装/愿景等任务。"
    )
    user = "\n".join(
        [
            f"user_prompt={user_prompt[:3000]}",
            f"product_analysis={json.dumps(product_analysis or {}, ensure_ascii=False)[:10000]}",
            f"fixed_matrix={matrix_json}",
        ]
    )
    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=settings.OPENAI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.75,
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
        briefs = data.get("shot_briefs") or []
        if len(briefs) != 9:
            data["shot_briefs"] = base.get("shot_briefs")
        return {**base, **data}
    except Exception:
        return base


def _strategy_fallback(product_analysis: dict, user_prompt: str) -> dict:
    usps = product_analysis.get("key_selling_points") or []
    pains = product_analysis.get("pain_points") or []
    if not pains:
        pains = ["日常困扰", "效果不稳定", "使用麻烦"]
    if not usps:
        usps = ["品质可靠", "易于使用", "性价比高"]

    headlines = product_analysis.get("spanish_headlines") or []
    h = lambda i: headlines[i % len(headlines)] if headlines else "Calidad premium"

    briefs = []
    for frame in TK_MX_NINE_FRAME_MATRIX:
        idx = frame["index"]
        role = frame["role"]
        creative = _fallback_creative_en(role, user_prompt, usps, pains, product_analysis)
        briefs.append(
            {
                **frame,
                "key_message_es": h(idx - 1) if role != "white_bg_catalog" else "",
                "creative_direction_en": creative,
                "diversity_lock": f"Unique marketing frame '{role}' — not a minor angle change of other shots.",
            }
        )

    return {
        "product_summary_zh": product_analysis.get("primary_function") or user_prompt[:200],
        "purchase_motivations": ["解决问题", "提升形象", "省时省心"],
        "pain_points": pains[:4] if isinstance(pains, list) else [str(pains)],
        "core_usps": usps[:4] if isinstance(usps, list) else [str(usps)],
        "shot_briefs": briefs,
    }


def _fallback_before_scene(analysis: dict, pain_fallback: str) -> str:
    before = (analysis.get("before_use_state") or pain_fallback or "problem before use")[:300]
    return (
        f"BEFORE-use problem state (single photograph, no product hero yet or product small): "
        f"{before}. Relatable Mexican home context, muted tones, empathy-first, not a packshot."
    )


def _fallback_before_after(analysis: dict, usp_fallback: str) -> str:
    before = (analysis.get("before_use_state") or "before condition")[:200]
    after = (analysis.get("after_use_state") or "improved after use")[:200]
    visual = (analysis.get("before_after_visual_en") or "").strip()
    extra = visual if visual else (
        f"One cohesive studio/lifestyle photo expressing transformation from '{before}' to '{after}' "
        f"while hero product {usp_fallback} is prominent; use lighting/color/contrast or split visual weight, "
        f"NOT a multi-panel collage grid."
    )
    return f"Before/after transformation in ONE frame: {extra}"


def _fallback_category_compare(analysis: dict, usp_fallback: str) -> str:
    comp = analysis.get("same_category_comparison") or {}
    if isinstance(comp, dict):
        generic = (comp.get("generic_alternative_en") or "plain unbranded generic same-category product")[:200]
        shot = (comp.get("comparison_shot_en") or "").strip()
        adv = comp.get("our_advantages_en") or []
        adv_txt = "; ".join(str(x) for x in adv[:4]) if adv else usp_fallback
    else:
        generic = "plain unbranded generic alternative"
        shot = ""
        adv_txt = usp_fallback
    if not shot:
        shot = (
            f"Single studio photograph: our branded SKU on the right looking premium, "
            f"generic alternative ({generic}) on the left looking dull; same surface and lighting; "
            f"highlights advantages: {adv_txt}. No competitor logos or trademarked brands."
        )
    return shot


def _fallback_creative_en(role: str, user_prompt: str, usps: list, pains: list, analysis: dict) -> str:
    fn = (analysis.get("primary_function") or user_prompt)[:400]
    usp1 = usps[0] if usps else "quality"
    usp2 = usps[1] if len(usps) > 1 else "easy to use"
    pain1 = pains[0] if pains else "daily frustration"
    templates = {
        "hero_hook": (
            f"TikTok scroll-stopper hero: product as star (prefer NO model face) with bold Spanish headline space, "
            f"emotional lighting, dynamic composition, communicates {usp1}, not a plain packshot."
        ),
        "white_bg_catalog": (
            "Pure #FFFFFF seamless catalog shot, front-facing product only, even softbox, "
            "full margins for TikTok Shop compliance."
        ),
        "pain_empathy": _fallback_before_scene(analysis, pain1),
        "usp_primary": _fallback_before_after(analysis, usp1),
        "usp_secondary": _fallback_category_compare(analysis, usp2),
        "trust_quality": (
            "Macro trust shot: visible paste/stick/cream texture, smear or cross-section, "
            "ingredient or certification callout from label, clinical sharpness, cool neutral background, NO face."
        ),
        "ease_objection": (
            "Hands-only demo: ONE simple step, cropped above wrists, product in hand, "
            "communicates 'easy and fast'; not the same gesture as other frames."
        ),
        "value_stack": (
            "Value story: kit contents from package_includes on shelf or angled layout (avoid duplicate top-down grid), "
            "value-for-money narrative, warm surface."
        ),
        "lifestyle_payoff": (
            f"Aspirational AFTER-use payoff WITHOUT portrait: {(analysis.get('after_use_state') or fn)[:200]}. "
            f"Product in Mexico lifestyle context (window, café, outdoor), no applying gesture."
        ),
    }
    return templates.get(role, f"Unique e-commerce visual for {role}. {fn}")


def strategy_brief_by_index(strategy: dict) -> dict[int, dict]:
    out = {}
    for brief in strategy.get("shot_briefs") or []:
        try:
            out[int(brief["index"])] = brief
        except (KeyError, TypeError, ValueError):
            continue
    return out
