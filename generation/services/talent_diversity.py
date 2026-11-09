"""套图人物/模特差异化：肤色、年龄、气质轮换，避免九图与连续任务「同一张 AI 脸」。"""

from __future__ import annotations

import re

# 含人物或需手部肤色的镜头 role（与 TK 矩阵对齐，可扩展）
HUMAN_FULL_BODY_ROLES = frozenset(
    {
        "pain_empathy",
        "lifestyle_payoff",
        "usp_primary",
        "hero_hook",
    }
)
HUMAN_HANDS_ROLES = frozenset({"ease_objection"})

# 每组 9 个互异 profile；整组轮换以区分「上一套图 vs 下一套图」
TALENT_ROTATION_GROUPS: list[list[dict]] = [
    [
        {
            "id": "A1",
            "gender": "female",
            "profile_en": (
                "Woman, late 20s, light fair skin, auburn wavy shoulder-length hair, soft oval face, "
                "subtle freckles, slim build, casual home loungewear."
            ),
        },
        {
            "id": "A2",
            "gender": "male",
            "profile_en": (
                "Man, early 30s, medium olive Latino skin, short black hair, light stubble, "
                "athletic build, plain white tee."
            ),
        },
        {
            "id": "A3",
            "gender": "female",
            "profile_en": (
                "Woman, mid 30s, brown skin, black hair in low bun, warm smile lines, "
                "curvy build, modern Mexico City casual style."
            ),
        },
        {
            "id": "A4",
            "gender": "female",
            "profile_en": (
                "Woman, early 40s, deep brown skin, natural curly hair, strong cheekbones, "
                "confident expression, smart-casual blouse."
            ),
        },
        {
            "id": "A5",
            "gender": "male",
            "profile_en": (
                "Man, late 20s, light tan skin, blond short hair, clean-shaven, lean build, "
                "outdoor activewear."
            ),
        },
        {
            "id": "A6",
            "gender": "female",
            "profile_en": (
                "Woman, early 30s, medium mestizo skin, straight dark brown hair past shoulders, "
                "minimal makeup, relatable mom-next-door vibe."
            ),
        },
        {
            "id": "A7",
            "gender": "female",
            "profile_en": (
                "Hands only: light fair skin, neat short nails, no jewelry, natural veins visible."
            ),
        },
        {
            "id": "A8",
            "gender": "male",
            "profile_en": (
                "Hands only: medium olive skin, masculine hands, short trimmed nails."
            ),
        },
        {
            "id": "A9",
            "gender": "female",
            "profile_en": (
                "Woman, late 20s, porcelain light skin, straight black bob, elegant features, "
                "aspirational lifestyle outfit for LATAM urban setting."
            ),
        },
    ],
    [
        {
            "id": "B1",
            "gender": "male",
            "profile_en": (
                "Man, mid 30s, medium brown skin, fade haircut, friendly expression, "
                "casual button-down, average build."
            ),
        },
        {
            "id": "B2",
            "gender": "female",
            "profile_en": (
                "Woman, early 30s, fair light skin, honey blonde hair in ponytail, blue-gray eyes, "
                "fitness-casual look."
            ),
        },
        {
            "id": "B3",
            "gender": "female",
            "profile_en": (
                "Woman, late 20s, golden tan skin, long dark hair, bright eyes, "
                "youthful TikTok-creator energy, simple tank top."
            ),
        },
        {
            "id": "B4",
            "gender": "male",
            "profile_en": (
                "Man, early 40s, light olive skin, salt-and-pepper short hair, "
                "trustworthy dad vibe, polo shirt."
            ),
        },
        {
            "id": "B5",
            "gender": "female",
            "profile_en": (
                "Woman, mid 30s, deep ebony skin, short natural afro, radiant smile, "
                "professional casual blazer."
            ),
        },
        {
            "id": "B6",
            "gender": "female",
            "profile_en": (
                "Woman, early 20s, very fair skin, light brown hair, delicate features, "
                "student-at-home aesthetic."
            ),
        },
        {
            "id": "B7",
            "gender": "female",
            "profile_en": (
                "Hands only: brown skin, feminine hands, soft pink nails."
            ),
        },
        {
            "id": "B8",
            "gender": "any",
            "profile_en": (
                "Hands only: light tan skin, young adult hands, no tattoos."
            ),
        },
        {
            "id": "B9",
            "gender": "male",
            "profile_en": (
                "Man, late 20s, fair skin with light stubble, brown hair, confident lifestyle pose, "
                "weekend casual for Mexico urban park."
            ),
        },
    ],
]

TALENT_NEGATIVE = (
    "same person face across frames, identical model in multiple shots, clone face, "
    "duplicate AI face, recurring stock model, default East Asian face unless cast specifies, "
    "same skin tone and hair on every human, waxy plastic skin"
)

VALID_SKIN_CAST_PRESETS = frozenset({"caucasian", "diverse", "black_only"})

# 默认白种人模特池（女性为主；男性向商品再按 gender 过滤）
CAUCASIAN_CAST_GROUP: list[dict] = [
    {
        "id": "C1",
        "gender": "female",
        "skin_bucket": "caucasian",
        "profile_en": (
            "Woman, mid 20s, Caucasian fair skin, light brown hair, soft features, "
            "casual white tee, natural daylight bathroom."
        ),
    },
    {
        "id": "C2",
        "gender": "female",
        "skin_bucket": "caucasian",
        "profile_en": (
            "Woman, early 30s, Caucasian porcelain skin, blonde ponytail, blue eyes, "
            "minimal makeup, clean vanity setting."
        ),
    },
    {
        "id": "C3",
        "gender": "female",
        "skin_bucket": "caucasian",
        "profile_en": (
            "Woman, late 20s, Caucasian light freckled skin, auburn hair, friendly expression, "
            "home loungewear."
        ),
    },
    {
        "id": "C4",
        "gender": "female",
        "skin_bucket": "caucasian",
        "profile_en": (
            "Woman, early 40s, Caucasian fair skin, shoulder-length dark blonde hair, "
            "smart casual, relatable mom aesthetic."
        ),
    },
    {
        "id": "C5",
        "gender": "female",
        "skin_bucket": "caucasian",
        "profile_en": (
            "Woman, mid 20s, Caucasian very fair skin, straight black bob, elegant features, "
            "urban lifestyle outfit."
        ),
    },
    {
        "id": "C6",
        "gender": "female",
        "skin_bucket": "caucasian",
        "profile_en": (
            "Hands only: Caucasian fair skin, feminine hands, nude manicure, applying skincare."
        ),
    },
    {
        "id": "C7",
        "gender": "female",
        "skin_bucket": "caucasian",
        "profile_en": (
            "Hands only: Caucasian light skin, young adult hands, short neat nails."
        ),
    },
    {
        "id": "C8",
        "gender": "male",
        "skin_bucket": "caucasian",
        "profile_en": (
            "Man, late 20s, Caucasian fair skin, light brown hair, clean-shaven, casual shirt."
        ),
    },
    {
        "id": "C9",
        "gender": "female",
        "skin_bucket": "caucasian",
        "profile_en": (
            "Woman, early 20s, Caucasian fair skin, honey hair, student-at-home skincare routine look."
        ),
    },
]

BLACK_CAST_GROUP: list[dict] = [
    {
        "id": "K1",
        "gender": "female",
        "skin_bucket": "black",
        "profile_en": (
            "Woman, late 20s, deep brown Black skin, natural coily hair, glowing makeup, "
            "modern bathroom selfie vibe."
        ),
    },
    {
        "id": "K2",
        "gender": "female",
        "skin_bucket": "black",
        "profile_en": (
            "Woman, early 30s, rich ebony skin, short afro, confident smile, casual chic blouse."
        ),
    },
    {
        "id": "K3",
        "gender": "female",
        "skin_bucket": "black",
        "profile_en": (
            "Woman, mid 30s, dark brown skin, braided hair, minimal jewelry, home skincare moment."
        ),
    },
    {
        "id": "K4",
        "gender": "female",
        "skin_bucket": "black",
        "profile_en": (
            "Woman, early 40s, deep brown skin, warm undertone, professional casual, trust-worthy expression."
        ),
    },
    {
        "id": "K5",
        "gender": "male",
        "skin_bucket": "black",
        "profile_en": (
            "Man, early 30s, dark brown Black skin, fade haircut, grooming casual, plain tee."
        ),
    },
    {
        "id": "K6",
        "gender": "female",
        "skin_bucket": "black",
        "profile_en": (
            "Hands only: deep brown skin, feminine hands, neat nails, skincare application."
        ),
    },
    {
        "id": "K7",
        "gender": "female",
        "skin_bucket": "black",
        "profile_en": (
            "Hands only: medium-dark brown skin, soft pink nails."
        ),
    },
    {
        "id": "K8",
        "gender": "female",
        "skin_bucket": "black",
        "profile_en": (
            "Woman, mid 20s, ebony skin, radiant bare-faced after skincare, lifestyle outdoor."
        ),
    },
    {
        "id": "K9",
        "gender": "female",
        "skin_bucket": "black",
        "profile_en": (
            "Woman, late 20s, brown-black skin, curly hair, TikTok creator energy, tank top."
        ),
    },
]

_CAST_GENDER_FEMALE_KW = re.compile(
    r"(lipstick|lip\s*gloss|lip\s*color|lip\s*balm|唇|口红|唇釉|唇彩|"
    r"mascara|eyeliner|eyeshadow|foundation|concealer|blush|makeup|cosmetic|beauty|"
    r"mud\s*mask|clay\s*mask|face\s*mask|acne\s*patch|pimple\s*patch|hydrocolloid|"
    r"泥膜|面膜|痘痘贴|痘贴|护肤|"
    r"women'?s?\s+(bra|lingerie|dress|skirt|heel|pump|blouse|camisole|underwear)|"
    r"女款|女装|女性|文胸|内衣|吊带裙|高跟鞋)",
    re.I,
)
_CAST_GENDER_MALE_KW = re.compile(
    r"(men'?s?\s+(grooming|skincare|razor|shav|beard|deodorant|fragrance)|"
    r"男款|男士|男鞋|剃须|须后)",
    re.I,
)

FEMALE_CAST_NEGATIVE = (
    "man, male model, masculine face, beard, mustache, stubble on face, "
    "man applying lipstick, man wearing lip color, male hands with lipstick"
)
MALE_CAST_NEGATIVE = (
    "woman as primary model for men's product, female model for men's grooming, "
    "dress, skirt, feminine makeup look on male-target product hero"
)


def _analysis_text_blob(analysis: dict) -> str:
    parts: list[str] = []
    for key in (
        "category",
        "product_name_en",
        "product_name_es",
        "primary_function",
        "target_audience",
        "visual_identity",
    ):
        v = analysis.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v.strip())
    for key in ("key_selling_points", "usage_scenarios"):
        v = analysis.get(key)
        if isinstance(v, list):
            parts.extend(str(x) for x in v if x)
    for v in analysis.get("product_variants") or []:
        if isinstance(v, dict):
            for k in ("variant_label", "style_en", "colorway_en"):
                if v.get(k):
                    parts.append(str(v[k]))
    return " ".join(parts)


def infer_cast_gender_from_analysis(analysis: dict, user_prompt: str = "") -> str:
    blob = f"{user_prompt} {_analysis_text_blob(analysis or {})}"
    if _CAST_GENDER_FEMALE_KW.search(blob):
        return "female"
    if _CAST_GENDER_MALE_KW.search(blob):
        return "male"
    return "any"


def resolve_cast_skin_preset(plan: dict) -> str:
    raw = (plan.get("cast_skin_preset") or plan.get("talent_skin_preset") or "caucasian").strip().lower()
    if raw in VALID_SKIN_CAST_PRESETS:
        return raw
    return "caucasian"


def _rotate_profile_list(group: list[dict], rotation_index: int) -> list[dict]:
    if not group:
        return []
    n = len(group)
    shift = int(rotation_index or 0) % n
    if shift == 0:
        return list(group)
    return group[shift:] + group[:shift]


def _pick_group_for_preset(rotation_index: int, preset: str) -> list[dict]:
    if preset == "black_only":
        return _rotate_profile_list(BLACK_CAST_GROUP, rotation_index)
    if preset == "diverse":
        return _pick_group(rotation_index)
    return _rotate_profile_list(CAUCASIAN_CAST_GROUP, rotation_index)


def resolve_cast_gender(plan: dict) -> str:
    analysis = plan.get("product_analysis") or {}
    raw = (analysis.get("model_cast_gender") or plan.get("talent_cast_gender") or "").strip().lower()
    if raw in ("female", "male", "any"):
        return raw
    return infer_cast_gender_from_analysis(analysis, (plan.get("user_prompt") or plan.get("prompt") or ""))


def _profile_matches_cast(profile: dict, cast_gender: str) -> bool:
    if cast_gender == "any":
        return True
    g = (profile.get("gender") or "any").lower()
    if g == "any":
        return cast_gender in ("female", "male")
    return g == cast_gender


def _filter_group_for_cast(group: list[dict], cast_gender: str) -> list[dict]:
    if cast_gender == "any" or not group:
        return list(group)
    filtered = [p for p in group if _profile_matches_cast(p, cast_gender)]
    return filtered if filtered else list(group)


def _pick_group(rotation_index: int) -> list[dict]:
    groups = TALENT_ROTATION_GROUPS
    if not groups:
        return []
    return groups[rotation_index % len(groups)]


def resolve_talent_rotation_index(job) -> int:
    """同一用户连续套图时轮换 cast 组，降低「两套图同批模特感」。"""
    from generation.models import GenerationJob

    groups_n = max(1, len(TALENT_ROTATION_GROUPS))
    prev = (
        GenerationJob.objects.filter(
            user_id=job.user_id,
            status=GenerationJob.Status.SUCCEEDED,
        )
        .exclude(pk=job.pk)
        .order_by("-finished_at")
    )
    if job.conversation_id:
        prev = prev.filter(conversation_id=job.conversation_id)
    prev_job = prev.first()
    if prev_job:
        prev_idx = (prev_job.plan_json or {}).get("talent_rotation_index")
        if prev_idx is not None:
            try:
                return (int(prev_idx) + 1) % groups_n
            except (TypeError, ValueError):
                pass
    seed = (int(job.user_id or 0) * 7919 + int(job.conversation_id or 0) * 997 + int(job.pk or 0)) % groups_n
    return seed


def _hands_profiles(group: list[dict], *, cast_gender: str = "any") -> list[dict]:
    return [
        p
        for p in group
        if "Hands only" in (p.get("profile_en") or "") and _profile_matches_cast(p, cast_gender)
    ]


def _full_body_profiles(group: list[dict], *, cast_gender: str = "any") -> list[dict]:
    return [
        p
        for p in group
        if "Hands only" not in (p.get("profile_en") or "") and _profile_matches_cast(p, cast_gender)
    ]


def _profile_for_shot(group: list[dict], shot: dict, *, cast_gender: str = "any") -> dict | None:
    role = (shot.get("role") or "").strip()
    try:
        idx = max(1, int(shot.get("index") or 1))
    except (TypeError, ValueError):
        idx = 1
    slot = (idx - 1) % len(group)

    if shot.get("_force_hands_only") or role in HUMAN_HANDS_ROLES:
        hands = _hands_profiles(group, cast_gender=cast_gender)
        return hands[slot % len(hands)] if hands else group[slot % len(group)]

    if role in HUMAN_FULL_BODY_ROLES:
        if (shot.get("human_cast_mode") or "").lower() == "face":
            full = _full_body_profiles(group, cast_gender=cast_gender)
            return full[slot % len(full)] if full else group[slot % len(group)]
        full = _full_body_profiles(group, cast_gender=cast_gender)
        return full[slot % len(full)] if full else group[slot % len(group)]

    scene = (shot.get("scene_family") or "").lower()
    if "lifestyle" in scene or "relatable" in scene or "hands_on" in scene:
        full = _full_body_profiles(group, cast_gender=cast_gender)
        return full[slot % len(full)] if full else group[slot % len(group)]
    return None


def _gender_negative(cast_gender: str) -> str:
    if cast_gender == "female":
        return FEMALE_CAST_NEGATIVE
    if cast_gender == "male":
        return MALE_CAST_NEGATIVE
    return ""


def _cosmetics_usage_hint(plan: dict, cast_gender: str) -> str:
    if cast_gender != "female":
        return ""
    blob = _analysis_text_blob(plan.get("product_analysis") or {})
    if not _CAST_GENDER_FEMALE_KW.search(blob):
        return ""
    return (
        "Women's color cosmetics listing: only adult women may wear or apply the lip/face product; "
        "show feminine lips, hand, or vanity scene — never a man with lipstick."
    )


def apply_talent_diversity(plan: dict, *, rotation_index: int = 0) -> dict:
    cast_gender = resolve_cast_gender(plan)
    skin_preset = resolve_cast_skin_preset(plan)
    plan["talent_cast_gender"] = cast_gender
    plan["cast_skin_preset"] = skin_preset
    group = _filter_group_for_cast(_pick_group_for_preset(rotation_index, skin_preset), cast_gender)
    if not group:
        return plan

    gender_neg = _gender_negative(cast_gender)
    cosmetics_hint = _cosmetics_usage_hint(plan, cast_gender)

    shots = plan.get("shots") or []
    roster: dict[int, str] = {}
    used_ids: list[str] = []

    for shot in shots:
        role = (shot.get("role") or "").strip()
        try:
            frame_idx = int(shot.get("index") or 0)
        except (TypeError, ValueError):
            continue
        cast_mode = (shot.get("human_cast_mode") or "").strip().lower()
        if cast_mode == "none":
            shot.pop("human_model_lock", None)
            shot.pop("talent_id", None)
            continue
        if cast_mode == "hands" and role not in HUMAN_HANDS_ROLES:
            shot["_force_hands_only"] = True
        profile = _profile_for_shot(group, shot, cast_gender=cast_gender)
        if not profile:
            continue
        pid = profile.get("id") or f"T{frame_idx}"
        shot["talent_id"] = pid
        shot["talent_profile_en"] = profile.get("profile_en", "")
        roster[frame_idx] = pid
        if pid not in used_ids:
            used_ids.append(pid)

        lock = (
            "HUMAN CAST — Use this exact model identity for this frame only; "
            "photorealistic skin texture; must NOT match faces or hands in other frames. "
            f"{profile.get('profile_en', '')}"
        )
        if cast_gender == "female":
            lock += " Adult woman only for this product category."
        elif cast_gender == "male":
            lock += " Adult man only for this product category."
        if cosmetics_hint and role in HUMAN_FULL_BODY_ROLES | HUMAN_HANDS_ROLES:
            lock += f" {cosmetics_hint}"
        shot["human_model_lock"] = lock

        extra = (shot.get("negative_extra") or "").strip()
        neg_parts = [extra, TALENT_NEGATIVE, gender_neg]
        shot["negative_extra"] = ", ".join(p for p in neg_parts if p).strip(", ")

    plan["talent_rotation_index"] = rotation_index
    plan["talent_roster"] = roster
    plan["talent_group_size"] = len(group)
    neg = (plan.get("negative_prompt") or "").strip()
    plan["negative_prompt"] = ", ".join(p for p in (neg, TALENT_NEGATIVE, gender_neg) if p).strip(", ")
    if cosmetics_hint:
        plan["cosmetics_cast_hint_en"] = cosmetics_hint
    plan["shots"] = shots
    return plan
